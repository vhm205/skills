import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { readFile, writeFile, symlink, mkdir, stat, chmod } from 'node:fs/promises';
import { join } from 'node:path';
import { Project } from '../src/project';
import { fixture, plan } from './fixture';
let f: Awaited<ReturnType<typeof fixture>>;
let project: Project;
beforeEach(async () => { f = await fixture(); project = await Project.create(f.project); });
afterEach(async () => { await f.cleanup(); });

describe('Project reader and guarded section writes', () => {
  it('reads sources, lane, features and installed adapter', async () => {
    expect((await project.info()).context.map(a => a.path)).toContain('.aiek/adapter.md');
    const feature = await project.feature(f.id);
    expect(feature.lane).toBe('LARGE'); expect(feature.artifacts).toHaveLength(3);
  });
  it('handles a project without specs or kit', async () => {
    const empty = await Project.create(f.directory);
    expect(await empty.info()).toMatchObject({ features: [], kitInstalled: false });
  });
  it('preserves bytes outside chosen section, UTF-8, CRLF and permissions', async () => {
    const content = '\ufeff' + plan.replaceAll('\n', '\r\n');
    const path = join(f.feature, 'plan.md');
    await writeFile(path, content); await chmod(path, 0o666);
    const artifact = (await project.feature(f.id)).artifacts.find(a => a.path === 'plan.md')!;
    const section = artifact.sections.find(s => s.editable)!;
    const replacement = section.content.replace('Chọn timezone dùng tính trạng thái.', 'Quyết định: workspace 🪴.');
    await project.updateSection(f.id, artifact.id, section.id, artifact.hash, replacement);
    expect(await readFile(path, 'utf8')).toBe(content.slice(0, section.start) + replacement + content.slice(section.end));
    expect((await stat(path)).mode & 0o777).toBe(0o666);
  });
  it('rejects edits after a whole-file external change', async () => {
    const artifact = (await project.feature(f.id)).artifacts.find(a => a.path === 'plan.md')!;
    const section = artifact.sections.find(s => s.editable)!;
    await writeFile(join(f.feature, 'plan.md'), '\n' + plan + '\nExternal change\n');
    await expect(project.updateSection(f.id, artifact.id, section.id, artifact.hash, section.content + '\nDraft')).rejects.toMatchObject({ status: 409 });
    expect(await readFile(join(f.feature, 'plan.md'), 'utf8')).toBe('\n' + plan + '\nExternal change\n');
  });
  it('serializes concurrent updates, rejecting the stale writer', async () => {
    const a = (await project.feature(f.id)).artifacts.find(a => a.path === 'plan.md')!;
    const s = a.sections.find(s => s.editable)!;
    const outcomes = await Promise.allSettled([project.updateSection(f.id, a.id, s.id, a.hash, s.content + '\nFirst\n'), project.updateSection(f.id, a.id, s.id, a.hash, s.content + '\nSecond\n')]);
    expect(outcomes.map(o => o.status)).toEqual(['fulfilled', 'rejected']);
  });
  it('rejects traversal, symlinks, unsupported sections and heading escapes', async () => {
    await expect(project.feature('../outside')).rejects.toMatchObject({ status: 404 });
    await expect(project.read('../outside')).rejects.toMatchObject({ status: 403 });
    const external = join(f.directory, 'secret.md'); await writeFile(external, 'secret');
    await symlink(external, join(f.feature, 'linked.md'));
    const feature = await project.feature(f.id);
    expect(feature.artifacts.find(a => a.path === 'linked.md')?.error).toContain('symlink');
    await mkdir(join(f.directory, 'external')); await symlink(join(f.directory, 'external'), join(f.feature, 'linked-dir'));
    await expect(project.read(`specs/${f.id}/linked-dir/anything`)).rejects.toMatchObject({ status: 403 });
    const a = feature.artifacts.find(a => a.path === 'plan.md')!;
    const s = a.sections.find(s => s.editable)!;
    await expect(project.updateSection(f.id, a.id, a.sections[0].id, a.hash, 'Bad')).rejects.toMatchObject({ status: 400 });
    await expect(project.updateSection(f.id, a.id, s.id, a.hash, '## Decisions Needed\nX\n## Escape\nBad')).rejects.toMatchObject({ status: 400 });
  });
  it('rejects Markdown blocks that absorb a later read-only section', async () => {
    const a = (await project.feature(f.id)).artifacts.find(a => a.path === 'plan.md')!;
    const s = a.sections.find(s => s.editable)!;
    for (const draft of ['## Decisions Needed\n\n```text\n', '## Decisions Needed\n\n<!-- open comment\n']) {
      await expect(project.updateSection(f.id, a.id, s.id, a.hash, draft)).rejects.toMatchObject({ status: 400 });
      expect(await readFile(join(f.feature, 'plan.md'), 'utf8')).toBe(plan);
    }
  });
  it('reports invalid UTF-8 and missing documents without crashing feature', async () => {
    await writeFile(join(f.feature, 'bad.md'), Buffer.from([0xff, 0xfe]));
    const feature = await project.feature(f.id);
    expect(feature.artifacts.find(a => a.path === 'bad.md')?.error).toBeTruthy();
  });
});
