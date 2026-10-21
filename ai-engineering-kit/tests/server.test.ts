import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { writeFile, rename, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { createServer, request as httpRequest } from 'node:http';
import { startServer } from '../src/server';
import { fixture, plan } from './fixture';
let f: Awaited<ReturnType<typeof fixture>>;
let app: Awaited<ReturnType<typeof startServer>>;
let cookie = '';
async function authenticate() {
  const token = new URLSearchParams(new URL(app.url).hash.slice(1)).get('token');
  const response = await fetch(app.origin + '/api/session', { method: 'POST', headers: { Origin: app.origin, 'Content-Type': 'application/json' }, body: JSON.stringify({ token }) });
  expect(response.status).toBe(200);
  cookie = response.headers.get('set-cookie')!.split(';')[0];
}
async function request(path: string, value?: unknown, headers: Record<string, string> = {}) {
  return fetch(app.origin + path, { method: value === undefined ? 'GET' : 'POST', headers: {
    Cookie: cookie, ...(value === undefined ? {} : { Origin: app.origin, 'Content-Type': 'application/json' }), ...headers,
  }, body: value === undefined ? undefined : JSON.stringify(value) });
}
beforeEach(async () => {
  f = await fixture();
  const assets = join(f.directory, 'assets'); await mkdir(assets); await writeFile(join(assets, 'index.html'), '<html>Review</html>');
  app = await startServer({ project: f.project, port: 0, dataDir: f.data, assets });
  await authenticate();
});
afterEach(async () => { await app.close(); await f.cleanup(); });

describe('Local server boundary', () => {
  it('authenticates reads, serves CSP-protected assets, rejects wrong host/origin/token', async () => {
    const response = await fetch(app.origin);
    expect(response.status).toBe(200); expect(response.headers.get('content-security-policy')).toContain("script-src 'self'");
    expect((await fetch(app.origin + '/api/project')).status).toBe(401);
    expect((await request('/api/project')).status).toBe(200);
    expect((await request('/api/project', undefined, { Origin: 'https://evil.example' })).status).toBe(403);
    const hostStatus = await new Promise<number | undefined>((resolve, reject) => {
      const req = httpRequest(app.origin + '/api/project', { headers: { Host: 'evil.example' } }, response => { response.resume(); resolve(response.statusCode); });
      req.on('error', reject); req.end();
    });
    expect(hostStatus).toBe(403);
    expect((await request('/api/session', { token: 'bad' })).status).toBe(403);
    expect((await request('/api/session', { token: 'bad' }, { Origin: '' })).status).toBe(403);
  });
  it('requires same origin for writes and rejects invalid content or arbitrary IDs', async () => {
    expect((await request(`/api/features/${f.id}/snapshot`, { revision: '' }, { Origin: '' })).status).toBe(403);
    expect((await request(`/api/features/${f.id}/snapshot`, {}, { 'Content-Type': 'text/plain' })).status).toBe(415);
    expect((await request('/api/features/%2E%2E%2Fsecret')).status).toBe(404);
    expect((await request(`/api/features/${f.id}/section`, { artifactId: '../../secret', sectionId: '1', hash: 'x', content: 'x' })).status).toBe(400);
    expect((await request('/api/run', { command: 'anything' })).status).toBe(404);
    const malformed = await fetch(app.origin + `/api/features/${f.id}/snapshot`, { method: 'POST', headers: { Cookie: cookie, Origin: app.origin, 'Content-Type': 'application/json' }, body: '{' });
    expect(malformed.status).toBe(400);
  });
  it('saves displayed snapshots and rejects stale section writes', async () => {
    const { feature } = await (await request(`/api/features/${f.id}`)).json();
    expect((await request(`/api/features/${f.id}/snapshot`, { revision: feature.revision })).status).toBe(200);
    const artifact = feature.artifacts.find((a: { path: string }) => a.path === 'plan.md');
    const section = artifact.sections.find((s: { editable: boolean }) => s.editable);
    const payload = { artifactId: artifact.id, sectionId: section.id, hash: artifact.hash, content: section.content + '\nDecision recorded\n' };
    expect((await request(`/api/features/${f.id}/section`, payload)).status).toBe(200);
    expect((await request(`/api/features/${f.id}/section`, payload)).status).toBe(409);
    expect((await request(`/api/features/${f.id}/snapshot`, { revision: feature.revision })).status).toBe(409);
  });
  it('broadcasts changes after external atomic saves and closes SSE on shutdown', async () => {
    const controller = new AbortController();
    const response = await fetch(app.origin + '/api/events', { headers: { Cookie: cookie }, signal: controller.signal });
    const reader = response.body!.getReader();
    expect(new TextDecoder().decode((await reader.read()).value)).toContain('event: change');
    // Allow the watcher to finish initial subscription before exercising an external editor.
    await new Promise<void>(resolve => setTimeout(resolve, 200));
    await writeFile(join(f.feature, 'replacement.md'), plan + '\nExternal atomic save\n');
    await rename(join(f.feature, 'replacement.md'), join(f.feature, 'plan.md'));
    const next = reader.read();
    const timeout = setTimeout(() => controller.abort(), 2500);
    try {
      let message = new TextDecoder().decode((await next).value);
      while (!message.includes('event: change')) message += new TextDecoder().decode((await reader.read()).value);
      expect(message).toContain('event: change');
    }
    finally { clearTimeout(timeout); controller.abort(); }
  });
  it('fails explicit busy ports and falls back for an implicit port', async () => {
    const blocker = createServer();
    await new Promise<void>(resolve => blocker.listen(0, '127.0.0.1', resolve));
    const address = blocker.address();
    if (!address || typeof address === 'string') throw new Error('Expected TCP address');
    try {
      await expect(startServer({ project: f.project, port: address.port, explicitPort: true, dataDir: f.data })).rejects.toMatchObject({ code: 'EADDRINUSE' });
      const fallback = await startServer({ project: f.project, port: address.port, dataDir: f.data });
      try { expect(fallback.origin).not.toBe(`http://127.0.0.1:${address.port}`); }
      finally { await fallback.close(); }
    } finally { await new Promise<void>(resolve => blocker.close(() => resolve())); }
  });
  it('manages multiple projects and fetches copilot models', async () => {
    const secondProject = join(f.directory, 'second-project');
    const secondSpecs = join(secondProject, 'specs', '002-second-feat');
    await mkdir(secondSpecs, { recursive: true });
    await writeFile(join(secondSpecs, 'spec.md'), '# Second project spec\n');

    // 1. List projects
    const listRes = await request('/api/projects');
    expect(listRes.status).toBe(200);
    const initialList = await listRes.json();
    expect(initialList.projects.length).toBe(1);
    expect(initialList.active).toBe(app.project.root);

    // 2. Add second project
    const addRes = await request('/api/projects', { path: secondProject });
    expect(addRes.status).toBe(200);
    const added = await addRes.json();
    expect(added.project.name).toBe('second-project');
    expect(added.project.features.length).toBe(1);

    // Active project is now second project
    const currentProjRes = await request('/api/project');
    expect(currentProjRes.status).toBe(200);
    expect((await currentProjRes.json()).name).toBe('second-project');

    // 3. Switch back to first project
    const switchRes = await request('/api/projects/switch', { root: app.project.root });
    expect(switchRes.status).toBe(200);
    expect((await switchRes.json()).active).toBe(app.project.root);

    // 4. Remove second project
    const removeRes = await request('/api/projects/remove', { root: secondProject });
    expect(removeRes.status).toBe(200);
    const afterRemove = await (await request('/api/projects')).json();
    expect(afterRemove.projects.length).toBe(1);

    // 5. Test copilot models endpoint
    const modelsRes = await request('/api/copilot/models', { provider: 'antigravity' });
    expect(modelsRes.status).toBe(200);
    const modelsData = await modelsRes.json();
    expect(Array.isArray(modelsData.models)).toBe(true);
    expect(modelsData.models.some((m: { id: string }) => m.id.includes('flash') || m.id.includes('claude'))).toBe(true);
  });
});
