import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { writeFile, unlink, mkdir, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { Project } from '../src/project';
import { ReviewStorage } from '../src/storage';
import { fixture, plan } from './fixture';
let f: Awaited<ReturnType<typeof fixture>>;
beforeEach(async () => { f = await fixture(); });
afterEach(async () => { await f.cleanup(); });

describe('Review snapshots', () => {
  it('starts empty, persists a baseline and detects add/modify/delete including empty files', async () => {
    const p = await Project.create(f.project); const storage = new ReviewStorage(p.root, f.data);
    const initial = await p.feature(f.id);
    expect(await storage.review(initial)).toEqual({ baseline: null, changes: [] });
    await storage.save(initial, initial.revision);
    await writeFile(join(f.feature, 'plan.md'), plan + '\nChanged\n');
    await unlink(join(f.feature, 'tasks.md')); await writeFile(join(f.feature, 'empty.md'), '');
    const changes = (await new ReviewStorage(p.root, f.data).review(await p.feature(f.id))).changes;
    expect(changes.map(c => [c.path, c.status])).toEqual([['empty.md', 'added'], ['plan.md', 'modified'], ['tasks.md', 'deleted']]);
    expect(changes[1].headings).toContain('Decisions Needed');
    expect(changes[1].changedHeadings).toEqual(['Key Design Decisions']);
    expect(changes[2].taskProgress).toMatchObject({ before: 1, after: 0, totalBefore: 2, totalAfter: 0 });
  });
  it('rejects unseen changes and unreadable documents', async () => {
    const p = await Project.create(f.project); const storage = new ReviewStorage(p.root, f.data);
    const initial = await p.feature(f.id);
    await writeFile(join(f.feature, 'plan.md'), plan + '\nNew\n');
    await expect(storage.save(await p.feature(f.id), initial.revision)).rejects.toMatchObject({ status: 409 });
    await writeFile(join(f.feature, 'bad.md'), Buffer.from([0xff]));
    const broken = await p.feature(f.id);
    await expect(storage.save(broken, broken.revision)).rejects.toMatchObject({ status: 400 });
  });
  it('keeps project/worktree identities separate', async () => {
    const p = await Project.create(f.project); const storage = new ReviewStorage(p.root, f.data);
    const initial = await p.feature(f.id); await storage.save(initial, initial.revision);
    await mkdir(join(f.directory, 'other-worktree'));
    expect(await new ReviewStorage(join(f.directory, 'other-worktree'), f.data).load(f.id)).toBeNull();
    expect(await storage.load('002-other')).toBeNull();
  });
  it('reports corrupt baseline while leaving project docs usable', async () => {
    const p = await Project.create(f.project); const storage = new ReviewStorage(p.root, f.data);
    const initial = await p.feature(f.id); await storage.save(initial, initial.revision);
    const sub = (await readdir(f.data))[0]; const file = (await readdir(join(f.data, sub)))[0];
    await writeFile(join(f.data, sub, file), '{}');
    await expect(storage.load(f.id)).rejects.toMatchObject({ status: 500 });
    expect((await p.feature(f.id)).artifacts).toHaveLength(3);
  });
});
