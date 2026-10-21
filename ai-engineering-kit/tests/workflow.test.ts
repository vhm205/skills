import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fixture } from './fixture';
import { Project } from '../src/project';
import { ReviewStorage } from '../src/storage';
import { workflow } from '../src/workflow';
let f: Awaited<ReturnType<typeof fixture>>;
beforeEach(async () => { f = await fixture(); });
afterEach(async () => { await f.cleanup(); });
describe('Workflow observations and human review rounds', () => {
  it('requires review, analyze and isolation for Large without trusting planned PASS', async () => {
    const project = await Project.create(f.project); const storage = new ReviewStorage(project.root, f.data);
    const feature = await project.feature(f.id);
    expect(workflow(feature, null)).toMatchObject({ current: 'Thực hiện · 1/2 task', next: 'review-docs', completed: 1, total: 2 });
    let baseline = await storage.save(feature, feature.revision);
    expect(workflow(feature, baseline).next).toBe('analyze');
    baseline = await storage.attest(feature, feature.revision, 'analyze', 'analysis report resolved');
    expect(workflow(feature, baseline).next).toBe('worktree');
    baseline = await storage.attest(feature, feature.revision, 'worktree', 'isolated branch confirmed');
    expect(workflow(feature, baseline).next).toBe('execute');
    expect(workflow(feature, baseline).steps.find(s => s.id === 'verify')?.state).toBe('unknown');
    await writeFile(join(f.feature, 'plan.md'), feature.artifacts.find(a => a.path === 'plan.md')!.content + '\nNew design\n');
    const changed = await project.feature(f.id);
    expect(workflow(changed, baseline).steps.find(s => s.id === 'analyze')?.state).toBe('stale');
    expect(workflow(changed, baseline).pending).toEqual(['plan.md']);
    await expect(storage.attest(changed, feature.revision, 'verify', 'old evidence')).rejects.toMatchObject({ status: 409 });
  });
  it('keeps twenty review rounds and human evidence without marking docs reviewed implicitly', async () => {
    const project = await Project.create(f.project); const storage = new ReviewStorage(project.root, f.data);
    const feature = await project.feature(f.id);
    await storage.attest(feature, feature.revision, 'verify', 'npm test exit 0');
    expect((await storage.review(feature)).baseline).toBeNull();
    for (let i = 0; i < 22; i++) await storage.save(feature, feature.revision);
    const baseline = await storage.load(f.id);
    expect(baseline?.history).toHaveLength(20); expect(baseline?.evidence).toHaveLength(1);
    expect(baseline?.history?.at(-1)).toMatchObject({ changed: [], completed: 1, total: 2 });
    await expect(storage.attest(feature, feature.revision, 'execute-anything', 'x')).rejects.toMatchObject({ status: 400 });
  });
  it('handles clarify and Small lanes without inventing successful gates', async () => {
    const project = await Project.create(f.project); const feature = await project.feature(f.id);
    expect(workflow({ ...feature, clarifications: 2 }, null).next).toBe('clarify');
    const small = workflow({ ...feature, lane: 'SMALL' }, { version: 1, feature: f.id, revision: feature.revision, savedAt: '', files: Object.fromEntries(feature.artifacts.map(a => [a.path, a.content])) });
    expect(small.steps.map(s => s.id)).toEqual(['execute', 'verify', 'review']); expect(small.next).toBe('execute');
  });
});
