import { createServer, type ServerResponse, type IncomingMessage } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, extname, sep } from 'node:path';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { watch } from 'chokidar';
import { AppError } from './types.js';
import { Project } from './project.js';
import { ReviewStorage } from './storage.js';
import { workflow } from './workflow.js';
import { Copilot, contextFor, contextPaths, handoffPrompt } from './copilot.js';

interface Options { project: string; port?: number; explicitPort?: boolean; dataDir?: string; assets?: string }
const json = (res: ServerResponse, status: number, value: unknown) => {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(value));
};
const equal = (a: string, b: string) => {
  const left = Buffer.from(a); const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
};
async function body(req: IncomingMessage): Promise<Record<string, unknown>> {
  if (req.headers['content-type']?.split(';')[0] !== 'application/json') throw new AppError(415, 'Yêu cầu JSON.');
  let size = 0;
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 2 * 1024 * 1024) throw new AppError(413, 'Nội dung quá lớn.');
    chunks.push(Buffer.from(chunk));
  }
  let value: unknown;
  try { value = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new AppError(400, 'JSON không hợp lệ.'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new AppError(400, 'Yêu cầu JSON object.');
  return value as Record<string, unknown>;
}
function string(value: unknown) {
  if (typeof value !== 'string') throw new AppError(400, 'Thiếu trường văn bản.');
  return value;
}
export async function startServer(options: Options) {
  const initialProject = await Project.create(options.project);
  const initialStorage = new ReviewStorage(initialProject.root, options.dataDir);
  const projects = new Map<string, { project: Project; storage: ReviewStorage }>();
  projects.set(initialProject.root, { project: initialProject, storage: initialStorage });
  let activeRoot = initialProject.root;
  const currentProject = () => projects.get(activeRoot)!.project;
  const currentStorage = () => projects.get(activeRoot)!.storage;
  const copilot = new Copilot();
  const launchToken = randomBytes(32).toString('hex');
  const cookieName = 'aiek_' + randomBytes(8).toString('hex');
  const sessionToken = randomBytes(32).toString('hex');
  const clients = new Set<ServerResponse>();
  const assets = options.assets ?? fileURLToPath(new URL('../ui/', import.meta.url));
  let origin = '';
  let closing = false;
  let watcher: ReturnType<typeof createWatcher>;
  const broadcast = () => {
    for (const client of clients) client.write('event: change\ndata: {}\n\n');
  };
  const resetWatcher = async () => {
    if (watcher) {
      try { await watcher.close(); } catch { /* ignore */ }
    }
    watcher = createWatcher(activeRoot);
  };
  const server = createServer(async (req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
    res.setHeader('Cache-Control', 'no-store');
    try {
      if (closing) throw new AppError(503, 'Server đang đóng.');
      if (req.headers.host !== new URL(origin).host) throw new AppError(403, 'Host không hợp lệ.');
      if (req.headers.origin && req.headers.origin !== origin) throw new AppError(403, 'Origin không hợp lệ.');
      if (req.headers['sec-fetch-site'] === 'cross-site') throw new AppError(403, 'Không cho phép cross-site request.');
      const url = new URL(req.url ?? '/', origin);
      const method = req.method ?? 'GET';
      if (url.pathname.startsWith('/api/')) {
        if (!['GET', 'POST'].includes(method)) throw new AppError(405, 'Method không hỗ trợ.');
        if (method === 'POST' && req.headers.origin !== origin) throw new AppError(403, 'Yêu cầu Origin cùng server.');
        if (url.pathname === '/api/session' && method === 'POST') {
          const payload = await body(req);
          if (!equal(string(payload.token), launchToken)) throw new AppError(403, 'Phiên truy cập không hợp lệ.');
          res.setHeader('Set-Cookie', `${cookieName}=${sessionToken}; HttpOnly; SameSite=Strict; Path=/`);
          json(res, 200, { ok: true }); return;
        }
        const cookies = (req.headers.cookie ?? '').split(';').map(value => value.trim());
        if (!cookies.some(value => equal(value, `${cookieName}=${sessionToken}`))) throw new AppError(401, 'Mở URL do CLI cung cấp để bắt đầu phiên.');
        if (url.pathname === '/api/events' && method === 'GET') {
          res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-store', Connection: 'keep-alive' });
          clients.add(res); res.write('event: change\ndata: {}\n\n');
          if (watcherError) res.write(`event: warning\ndata: ${JSON.stringify({ error: watcherError })}\n\n`);
          req.on('close', () => clients.delete(res)); return;
        }
        if (url.pathname === '/api/projects' && method === 'GET') {
          const list = await Promise.all(Array.from(projects.values()).map(async ({ project: p }) => {
            const info = await p.info();
            return {
              name: info.name,
              root: p.root,
              active: p.root === activeRoot,
              featureCount: info.features.length,
              kitInstalled: info.kitInstalled,
            };
          }));
          json(res, 200, { projects: list, active: activeRoot });
          return;
        }
        if (url.pathname === '/api/projects' && method === 'POST') {
          const payload = await body(req);
          const targetPath = string(payload.path);
          const newProject = await Project.create(targetPath);
          if (!projects.has(newProject.root)) {
            projects.set(newProject.root, { project: newProject, storage: new ReviewStorage(newProject.root, options.dataDir) });
          }
          if (payload.setActive !== false) {
            activeRoot = newProject.root;
            await resetWatcher();
          }
          broadcast();
          json(res, 200, { ok: true, active: activeRoot, project: await currentProject().info() });
          return;
        }
        if (url.pathname === '/api/projects/switch' && method === 'POST') {
          const payload = await body(req);
          const targetRoot = string(payload.root);
          let realTarget = targetRoot;
          try { realTarget = await (await import('node:fs/promises')).realpath(targetRoot); } catch { /* ignore */ }
          const matched = Array.from(projects.keys()).find(k => k === targetRoot || k === realTarget || resolve(k) === resolve(targetRoot));
          if (!matched) throw new AppError(404, 'Không tìm thấy project trong danh sách đã mở.');
          activeRoot = matched;
          await resetWatcher();
          broadcast();
          json(res, 200, { ok: true, active: activeRoot, project: await currentProject().info() });
          return;
        }
        if (url.pathname === '/api/projects/remove' && method === 'POST') {
          const payload = await body(req);
          const targetRoot = string(payload.root);
          let realTarget = targetRoot;
          try { realTarget = await (await import('node:fs/promises')).realpath(targetRoot); } catch { /* ignore */ }
          const matched = Array.from(projects.keys()).find(k => k === targetRoot || k === realTarget || resolve(k) === resolve(targetRoot));
          if (!matched) throw new AppError(404, 'Không tìm thấy project để xóa.');
          if (projects.size <= 1) throw new AppError(400, 'Không thể xóa project duy nhất đang mở.');
          projects.delete(matched);
          if (activeRoot === matched) {
            activeRoot = projects.keys().next().value!;
            await resetWatcher();
          }
          broadcast();
          json(res, 200, { ok: true, active: activeRoot });
          return;
        }
        if (url.pathname === '/api/project' && method === 'GET') { json(res, 200, await currentProject().info()); return; }
        if (url.pathname === '/api/copilot' && method === 'GET') { json(res, 200, { settings: copilot.status(), providers: await copilot.providers() }); return; }
        if (url.pathname === '/api/copilot/config' && method === 'POST') { json(res, 200, copilot.configure(await body(req))); return; }
        if (url.pathname === '/api/copilot/models' && method === 'POST') {
          const payload = await body(req);
          const provider = (typeof payload.provider === 'string' ? payload.provider : 'api') as import('./copilot.js').Provider;
          const endpoint = typeof payload.endpoint === 'string' ? payload.endpoint : undefined;
          const apiKey = typeof payload.apiKey === 'string' ? payload.apiKey : undefined;
          const models = await copilot.fetchModels(provider, endpoint, apiKey);
          json(res, 200, { models });
          return;
        }
        if (url.pathname === '/api/copilot/cancel' && method === 'POST') { copilot.cancel(); json(res, 200, { ok: true }); return; }
        const match = url.pathname.match(/^\/api\/features\/([^/]+)(?:\/(snapshot|section|evidence|context|ask|handoff))?$/);
        if (match) {
          let id: string;
          try { id = decodeURIComponent(match[1]); } catch { throw new AppError(400, 'Feature ID không hợp lệ.'); }
          if (method === 'GET' && !match[2]) {
            const feature = await currentProject().feature(id);
            // A broken baseline must not make the project documents unreadable.
            try { json(res, 200, { feature, review: await currentStorage().review(feature), reviewError: null, workflow: workflow(feature, await currentStorage().load(id)) }); }
            catch (error) {
              if (!(error instanceof AppError)) throw error;
              json(res, 200, { feature, review: { baseline: null, changes: [] }, reviewError: error.message, workflow: workflow(feature, null) });
            }
            return;
          }
          if (method === 'POST' && match[2] === 'snapshot') {
            const payload = await body(req);
            const baseline = await currentProject().serialize(async () => currentStorage().save(await currentProject().feature(id), string(payload.revision)));
            json(res, 200, baseline); broadcast(); return;
          }
          if (method === 'POST' && match[2] === 'section') {
            const payload = await body(req);
            const feature = await currentProject().updateSection(id, string(payload.artifactId), string(payload.sectionId), string(payload.hash), string(payload.content));
            json(res, 200, feature); broadcast(); return;
          }
          if (method === 'POST' && match[2] === 'evidence') {
            const payload = await body(req);
            const value = await currentProject().serialize(async () => currentStorage().attest(await currentProject().feature(id), string(payload.revision), string(payload.step), string(payload.note)));
            json(res, 200, { evidence: value.evidence }); broadcast(); return;
          }
          if (method === 'POST' && ['context', 'ask', 'handoff'].includes(match[2])) {
            const payload = await body(req);
            if (payload.scope !== 'feature' && payload.scope !== 'project') throw new AppError(400, 'Scope không hợp lệ.');
            const context = await contextFor(currentProject(), id, payload.scope, contextPaths(payload.paths), featureId => currentStorage().load(featureId));
            if (match[2] === 'context') { json(res, 200, context); return; }
            if (string(payload.digest) !== context.digest) throw new AppError(409, 'Context đã đổi. Xem lại context mới trước khi gửi.');
            const question = string(payload.question);
            if (question.length > 8000) throw new AppError(400, 'Câu hỏi quá dài.');
            if (match[2] === 'handoff') { json(res, 200, { prompt: handoffPrompt(context, question) }); return; }
            const controller = new AbortController();
            const abort = () => { if (!res.writableEnded) controller.abort(); };
            res.on('close', abort);
            try { json(res, 200, await copilot.ask(context, question, payload.history, controller.signal)); }
            finally { res.off('close', abort); }
            return;
          }
        }
        throw new AppError(404, 'Không tìm thấy API.');
      }
      if (method !== 'GET' && method !== 'HEAD') throw new AppError(405, 'Method không hỗ trợ.');
      let pathname: string;
      try { pathname = decodeURIComponent(url.pathname); } catch { throw new AppError(400, 'URL không hợp lệ.'); }
      const target = resolve(assets, pathname === '/' ? 'index.html' : '.' + pathname);
      if (!target.startsWith(resolve(assets) + sep)) throw new AppError(403, 'Đường dẫn không hợp lệ.');
      try {
        if (!(await stat(target)).isFile()) throw new Error('Not file');
        const content = await readFile(target);
        const mime: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml' };
        res.writeHead(200, { 'Content-Type': mime[extname(target)] ?? 'application/octet-stream' });
        res.end(method === 'HEAD' ? undefined : content);
      } catch { throw new AppError(404, 'Không tìm thấy giao diện. Chạy npm run build trước.'); }
    } catch (error) {
      if (res.headersSent) { res.end(); return; }
      const known = error instanceof AppError;
      json(res, known ? error.status : 500, { error: known ? error.message : 'Lỗi đọc hoặc lưu dữ liệu local; chưa xác nhận thao tác thành công.' });
    }
  });
  let port = options.port ?? 3080;
  for (let attempts = 0; ; attempts++) {
    try {
      await new Promise<void>((ok, fail) => {
        const onError = (error: Error) => { server.off('listening', onListen); fail(error); };
        const onListen = () => { server.off('error', onError); ok(); };
        server.once('error', onError); server.once('listening', onListen); server.listen(port, '127.0.0.1');
      });
      break;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EADDRINUSE' || options.explicitPort || attempts >= 20 || port >= 65535) throw error;
      port++;
    }
  }
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('No server address');
  origin = `http://127.0.0.1:${address.port}`;
  let timer: NodeJS.Timeout | undefined;
  let watcherError: string | null = null;
  let polling = process.env.AIEK_WATCH_POLLING === '1';
  const createWatcher = (root: string) => {
    const instance = watch([resolve(root, 'specs'), resolve(root, '.aiek')], {
      ignoreInitial: true, followSymlinks: false, depth: 7, usePolling: polling, interval: 250,
      awaitWriteFinish: { stabilityThreshold: 100, pollInterval: 25 },
      ignored: path => /(?:^|[/\\])(?:node_modules|\.git)(?:[/\\]|$)|\.tmp$/.test(path),
    });
    instance.on('all', () => { clearTimeout(timer); timer = setTimeout(broadcast, 100); });
    instance.on('error', error => {
      const code = (error as NodeJS.ErrnoException).code ?? 'WATCH_ERROR';
      if (!polling && ['EMFILE', 'ENOSPC', 'EPERM'].includes(code)) {
        polling = true;
        watcherError = 'Filesystem watcher đạt giới hạn; đang theo dõi bằng polling local.';
        void instance.close().then(() => { if (!closing) watcher = createWatcher(activeRoot); });
      } else watcherError = `Không theo dõi được thay đổi filesystem (${code}). Tải lại trang để đọc phiên bản hiện tại.`;
      for (const client of clients) client.write(`event: warning\ndata: ${JSON.stringify({ error: watcherError })}\n\n`);
    });
    return instance;
  };
  watcher = createWatcher(activeRoot);
  const heartbeat = setInterval(() => { for (const client of clients) client.write(': heartbeat\n\n'); }, 15000);
  heartbeat.unref();
  const close = async () => {
    if (closing) return;
    closing = true; clearTimeout(timer); clearInterval(heartbeat);
    copilot.cancel();
    for (const client of clients) client.end();
    await watcher?.close();
    await new Promise<void>((ok, fail) => {
      server.close(error => error ? fail(error) : ok()); server.closeIdleConnections();
    });
  };
  return { origin, url: `${origin}/#token=${launchToken}`, close, get project() { return currentProject(); }, get storage() { return currentStorage(); }, server, get watcherError() { return watcherError; } };
}
