import { mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { homedir, platform } from 'node:os';
import { join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { AppError, type Baseline, type Change, type Feature, type ReviewState } from './types.js';
import { evidenceSteps } from './workflow.js';
import { hash, parseArtifact } from './parser.js';

export function dataDirectory() {
  if (process.env.AIEK_DATA_DIR) return resolve(process.env.AIEK_DATA_DIR);
  if (platform() === 'darwin') return join(homedir(), 'Library', 'Application Support', 'ai-engineering-kit');
  if (platform() === 'win32') return join(process.env.LOCALAPPDATA ?? join(homedir(), 'AppData', 'Local'), 'ai-engineering-kit');
  return join(process.env.XDG_DATA_HOME ?? join(homedir(), '.local', 'share'), 'ai-engineering-kit');
}
export class ReviewStorage {
  constructor(private projectRoot: string, private directory = dataDirectory()) {}
  private path(id: string) { return join(this.directory, hash(this.projectRoot), hash(id) + '.json'); }
  async load(id: string): Promise<Baseline | null> {
    try {
      const value: unknown = JSON.parse(await readFile(this.path(id), 'utf8'));
      if (!value || typeof value !== 'object') throw new Error('Invalid baseline');
      const b = value as Baseline;
      if (b.version !== 1 || b.feature !== id || typeof b.savedAt !== 'string' || typeof b.revision !== 'string' ||
        !b.files || typeof b.files !== 'object' || Array.isArray(b.files) || Object.values(b.files).some(v => typeof v !== 'string')) throw new Error('Invalid baseline');
      if (b.history && (!Array.isArray(b.history) || b.history.length > 20 || b.history.some(r => !r || typeof r.at !== 'string' || typeof r.revision !== 'string' || !Array.isArray(r.changed) || r.changed.some(p => typeof p !== 'string') || !Number.isInteger(r.completed) || !Number.isInteger(r.total)))) throw new Error('Invalid history');
      if (b.evidence && (!Array.isArray(b.evidence) || b.evidence.length > 20 || b.evidence.some(e => !e || typeof e.step !== 'string' || typeof e.note !== 'string' || typeof e.at !== 'string' || typeof e.revision !== 'string'))) throw new Error('Invalid evidence');
      return b;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null;
      throw new AppError(500, 'Không đọc được mốc review. Kiểm tra hoặc xóa snapshot local bị lỗi; tài liệu project vẫn nguyên vẹn.');
    }
  }
  async save(feature: Feature, expectedRevision: string) {
    if (feature.revision !== expectedRevision) throw new AppError(409, 'Feature đã đổi từ lúc hiển thị. Tải lại trước khi lưu mốc.');
    if (feature.artifacts.some(a => a.error)) throw new AppError(400, 'Không lưu mốc khi có tài liệu chưa đọc được.');
    const files = Object.fromEntries(feature.artifacts.map(a => [a.path, a.content]));
    const prior = await this.load(feature.id);
    const changed = [...new Set([...Object.keys(prior?.files ?? {}), ...Object.keys(files)])].filter(path => prior?.files[path] !== files[path]);
    const tasks = feature.artifacts.find(a => a.path === 'tasks.md')?.tasks ?? [];
    const savedAt = new Date().toISOString();
    const baseline: Baseline = { version: 1, feature: feature.id, revision: feature.revision, savedAt, files,
      evidence: prior?.evidence ?? [], history: [...(prior?.history ?? []), { at: savedAt, revision: feature.revision, changed, completed: tasks.filter(t => t.checked).length, total: tasks.length }].slice(-20) };
    await this.write(baseline);
    return baseline;
  }
  async attest(feature: Feature, expectedRevision: string, step: string, note: string) {
    if (feature.revision !== expectedRevision) throw new AppError(409, 'Docs đã đổi. Tải lại trước khi ghi nhận.');
    if (!evidenceSteps.some(id => id === step) || !note.trim() || note.length > 4000) throw new AppError(400, 'Chọn bước hợp lệ và ghi bằng chứng tối đa 4000 ký tự.');
    const prior = await this.load(feature.id);
    const baseline: Baseline = prior ?? { version: 1, feature: feature.id, revision: '', savedAt: '', files: {} };
    baseline.evidence = [...(baseline.evidence ?? []), { step, note: note.trim(), at: new Date().toISOString(), revision: feature.revision }].slice(-20);
    await this.write(baseline);
    return baseline;
  }
  private async write(baseline: Baseline) {
    const feature = { id: baseline.feature };
    const path = this.path(feature.id);
    await mkdir(join(this.directory, hash(this.projectRoot)), { recursive: true, mode: 0o700 });
    const temp = path + '.' + randomUUID() + '.tmp';
    try { await writeFile(temp, JSON.stringify(baseline), { mode: 0o600, flag: 'wx' }); await rename(temp, path); }
    finally { await unlink(temp).catch(() => undefined); }
  }
  async review(feature: Feature): Promise<ReviewState> {
    const baseline = await this.load(feature.id);
    if (!baseline?.revision) return { baseline: null, changes: [] };
    const current = new Map(feature.artifacts.map(a => [a.path, a]));
    const paths = [...new Set([...Object.keys(baseline.files), ...current.keys()])].sort();
    const changes: Change[] = [];
    for (const path of paths) {
      const artifact = current.get(path);
      if (artifact?.error) continue;
      const exists = Object.hasOwn(baseline.files, path);
      const before = exists ? baseline.files[path] : '';
      const after = artifact?.content ?? '';
      if (exists && artifact && before === after) continue;
      const old = parseArtifact(path, before); const next = parseArtifact(path, after);
      const headings = [...new Set([...old.sections, ...next.sections].map(s => s.title))];
      const bodies = (artifact: typeof old) => {
        const result = new Map<string, string[]>();
        artifact.sections.forEach((section, index) => result.set(section.title, [...(result.get(section.title) ?? []), artifact.content.slice(section.start, artifact.sections[index + 1]?.start ?? artifact.content.length)]));
        return result;
      };
      const oldBodies = bodies(old); const nextBodies = bodies(next);
      const changedHeadings = headings.filter(title => JSON.stringify(oldBodies.get(title)) !== JSON.stringify(nextBodies.get(title)));
      changes.push({ path, before, after, headings, changedHeadings, taskProgress: { before: old.tasks.filter(t => t.checked).length, after: next.tasks.filter(t => t.checked).length, totalBefore: old.tasks.length, totalAfter: next.tasks.length },
        status: !exists ? 'added' : !artifact ? 'deleted' : 'modified' });
    }
    return { baseline, changes };
  }
}
