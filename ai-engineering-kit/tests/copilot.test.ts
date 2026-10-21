import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createServer } from 'node:http';
import { writeFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { Copilot, cliArgs, contextFor, endpointURL, runProcess } from '../src/copilot';
import { Project } from '../src/project';
import { startServer } from '../src/server';
import { fixture } from './fixture';
import { ReviewStorage } from '../src/storage';
let f: Awaited<ReturnType<typeof fixture>>;
beforeEach(async () => { f = await fixture(); });
afterEach(async () => { vi.unstubAllEnvs(); await f.cleanup(); });
describe('Copilot context and provider boundaries', () => {
  it('uses the same human-reviewed baseline and reported evidence as the workflow dashboard', async () => {
    const project = await Project.create(f.project); const storage = new ReviewStorage(project.root, f.data);
    const feature = await project.feature(f.id);
    const before = await contextFor(project, f.id, 'feature', undefined, id => storage.load(id));
    await storage.save(feature, feature.revision); await storage.attest(feature, feature.revision, 'analyze', 'Independent analysis completed');
    const after = await contextFor(project, f.id, 'feature', undefined, id => storage.load(id));
    expect(after.digest).not.toBe(before.digest); expect(after.text).toContain('Independent analysis completed');
    expect(after.text).toContain('"state":"reviewed"'); expect(after.text).toContain('"state":"reported"');
    expect(after.text).toContain('"pending":[]'); expect(after.text).toContain('"next":"worktree"');
  });
  it('previews bounded line-numbered docs and selected paths without reading unrelated secrets', async () => {
    await writeFile(join(f.project, '.env'), 'SECRET=never-read');
    await writeFile(join(f.feature, 'research.md'), '# Research\n' + 'word '.repeat(20000));
    const project = await Project.create(f.project);
    const context = await contextFor(project, f.id, 'feature', ['research.md']);
    expect(context.sources.map(s => s.path)).toContain(`specs/${f.id}/research.md`);
    expect(context.sources.every(s => !s.path.endsWith('/spec.md'))).toBe(true);
    expect(context.text).toContain('1: # Research'); expect(context.text).not.toContain('never-read');
    expect(context.warnings.join()).toContain('chỉ gửi phần đầu');
    const repeated = await contextFor(project, f.id, 'feature', ['research.md']); expect(repeated.digest).toBe(context.digest);
    const projectContext = await contextFor(project, f.id, 'project'); expect(projectContext.sources.some(s => s.path.endsWith('/tasks.md'))).toBe(true);
  });
  it('validates endpoint, keeps key in memory and sends chat only on explicit ask', async () => {
    for (const endpoint of ['http://example.com/v1', 'file:///etc/passwd', 'https://key@example.com/v1', 'https://example.com/v1?key=x']) expect(() => endpointURL(endpoint)).toThrow();
    expect(endpointURL('https://example.com/v1/')).toBe('https://example.com/v1/chat/completions');
    let received: { authorization?: string; payload?: { messages: { content: string }[]; stream: boolean } } = {};
    const provider = createServer(async (req, res) => {
      let raw = ''; for await (const chunk of req) raw += chunk.toString();
      received = { authorization: req.headers.authorization, payload: JSON.parse(raw) };
      res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({ choices: [{ message: { content: 'Còn T002. [specs/001-team-availability/tasks.md:6]' } }] }));
    });
    await new Promise<void>(ok => provider.listen(0, '127.0.0.1', ok));
    const address = provider.address(); if (!address || typeof address === 'string') throw new Error('Missing address');
    const endpoint = `http://127.0.0.1:${address.port}/v1`;
    try {
      const copilot = new Copilot(); copilot.configure({ provider: 'api', endpoint, model: 'test-model', apiKey: 'secret-key-test' });
      expect(JSON.stringify(copilot.status())).not.toContain('secret-key-test'); expect(received).toEqual({});
      copilot.configure({ provider: 'api', endpoint, model: 'test-model-2' }); expect(copilot.status().hasKey).toBe(true);
      const context = await contextFor(await Project.create(f.project), f.id, 'feature');
      const answer = await copilot.ask(context, 'Còn việc gì?', [], new AbortController().signal);
      expect(answer.answer).toContain('T002'); expect(received.authorization).toBe('Bearer secret-key-test');
      expect(received.payload?.stream).toBe(false); expect(received.payload?.messages[1].content).toContain(context.text);
      copilot.configure({ provider: 'api', endpoint: 'https://other.example/v1', model: 'model' }); expect(copilot.status().hasKey).toBe(false);
    } finally { await new Promise<void>(ok => provider.close(() => ok())); }
  });
  it('sanitizes provider errors and cancels active requests', async () => {
    const provider = createServer((req, res) => { req.resume(); if (req.url === '/error/chat/completions') { res.writeHead(401); res.end('SECRET_RAW_PROVIDER_DETAIL'); } });
    await new Promise<void>(ok => provider.listen(0, '127.0.0.1', ok));
    const address = provider.address(); if (!address || typeof address === 'string') throw new Error('Missing address');
    const endpoint = `http://127.0.0.1:${address.port}`; const copilot = new Copilot();
    const context = await contextFor(await Project.create(f.project), f.id, 'feature');
    try {
      copilot.configure({ provider: 'api', endpoint: endpoint + '/error', model: 'x', apiKey: 'secret' });
      await expect(copilot.ask(context, 'status?', [], new AbortController().signal)).rejects.toThrow('HTTP 401');
      copilot.configure({ provider: 'api', endpoint, model: 'x', apiKey: '' });
      const pending = copilot.ask(context, 'status?', [], new AbortController().signal);
      await expect(copilot.ask(context, 'other?', [], new AbortController().signal)).rejects.toMatchObject({ status: 409 });
      copilot.cancel(); await expect(pending).rejects.toMatchObject({ status: 499 });
    } finally { provider.closeAllConnections(); await new Promise<void>(ok => provider.close(() => ok())); }
  });
  it('runs CLI with stdin in an isolated directory, limits output and terminates on timeout', async () => {
    const result = await runProcess(process.execPath, ['-e', 'let s="";process.stdin.on("data",x=>s+=x);process.stdin.on("end",()=>console.log(JSON.stringify({cwd:process.cwd(),input:s})))'], '$(never execute)', new AbortController().signal);
    const value = JSON.parse(result); expect(value.cwd).not.toBe(f.project); expect(value.input).toBe('$(never execute)');
    await expect(runProcess(process.execPath, ['-e', 'setInterval(()=>{},1000)'], '', new AbortController().signal, 100)).rejects.toMatchObject({ status: 504 });
    await expect(runProcess(process.execPath, ['-e', 'console.log("x".repeat(1100000))'], '', new AbortController().signal)).rejects.toMatchObject({ status: 502 });
    expect(cliArgs('codex', '')).toContain('read-only'); expect(cliArgs('codex', '')).toContain('features.shell_tool=false');
    expect(cliArgs('claude', '')).toContain('--tools'); expect(cliArgs('claude', '')).toContain('{"disableAllHooks":true}');
  });
  it('uses the actual CLI adapter protocol with a fake installed binary', async () => {
    const bin = join(f.directory, 'bin'); await mkdir(bin);
    await writeFile(join(bin, 'codex'), `#!${process.execPath}\nif(process.argv.includes('--help')) { console.log('--ignore-user-config --ignore-rules --ephemeral --sandbox --json'); } else { let s=''; process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>console.log(JSON.stringify({type:'item.completed',item:{type:'agent_message',text:s.includes('CONTEXT SNAPSHOT')?'Answer from supplied docs':'missing context'}}))); }\n`, { mode: 0o700 });
    vi.stubEnv('PATH', bin + ':' + process.env.PATH);
    const copilot = new Copilot(); expect((await copilot.providers()).find(p => p.id === 'codex')?.available).toBe(true);
    copilot.configure({ provider: 'codex', endpoint: '', model: '', apiKey: '' });
    const result = await copilot.ask(await contextFor(await Project.create(f.project), f.id, 'feature'), 'status?', [], new AbortController().signal);
    expect(result.answer).toBe('Answer from supplied docs');
  });
  it('requires session auth and rejects changed context before sending to any provider', async () => {
    const app = await startServer({ project: f.project, dataDir: f.data, port: 0 });
    try {
      const token = new URLSearchParams(new URL(app.url).hash.slice(1)).get('token');
      const login = await fetch(app.origin + '/api/session', { method: 'POST', headers: { Origin: app.origin, 'Content-Type': 'application/json' }, body: JSON.stringify({ token }) });
      const cookie = login.headers.get('set-cookie')!.split(';')[0];
      const send = (path: string, value: unknown) => fetch(app.origin + path, { method: 'POST', headers: { Cookie: cookie, Origin: app.origin, 'Content-Type': 'application/json' }, body: JSON.stringify(value) });
      expect((await fetch(app.origin + '/api/copilot')).status).toBe(401);
      const context = await (await send(`/api/features/${f.id}/context`, { scope: 'feature' })).json();
      await writeFile(join(f.feature, 'plan.md'), '# New plan\n');
      expect((await send(`/api/features/${f.id}/ask`, { scope: 'feature', digest: context.digest, question: 'status?' })).status).toBe(409);
      const config = await send('/api/copilot/config', { provider: 'api', endpoint: 'https://example.com/v1', model: 'm', apiKey: 'private-key' });
      expect(await config.text()).not.toContain('private-key');
    } finally { await app.close(); }
  });
});
