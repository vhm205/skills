import { constants } from 'node:fs';
import { lstat, readdir, realpath, open, rename, unlink } from 'node:fs/promises';
import { basename, dirname, join, relative, resolve, sep } from 'node:path';
import { randomUUID } from 'node:crypto';
import { AppError, type Artifact, type Feature, type ProjectInfo } from './types.js';
import { declaredLane, hash, normalize, parseArtifact } from './parser.js';

const MAX_FILE = 2 * 1024 * 1024;
const MAX_TOTAL = 20 * 1024 * 1024;
const decoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });
const inside = (root: string, target: string) => target === root || target.startsWith(root + sep);
const missing = (error: unknown) => (error as NodeJS.ErrnoException).code === 'ENOENT';

export class Project {
  private queue: Promise<unknown> = Promise.resolve();
  private constructor(public root: string) {}
  static async create(path: string) {
    const root = await realpath(resolve(path));
    if (!(await lstat(root)).isDirectory()) throw new AppError(400, 'Project phải là thư mục.');
    return new Project(root);
  }
  serialize<T>(work: () => Promise<T>): Promise<T> {
    const result = this.queue.then(work, work);
    this.queue = result.catch(() => undefined);
    return result;
  }
  async safePath(path: string) {
    const target = resolve(this.root, path);
    if (!inside(this.root, target)) throw new AppError(403, 'Đường dẫn ngoài project.');
    let current = this.root;
    for (const part of relative(this.root, target).split(sep).filter(Boolean)) {
      current = join(current, part);
      const info = await lstat(current);
      if (info.isSymbolicLink()) throw new AppError(403, 'Không đọc hoặc ghi qua symlink.');
    }
    if (!inside(this.root, await realpath(target))) throw new AppError(403, 'Đường dẫn ngoài project.');
    return target;
  }
  async read(path: string) {
    const target = await this.safePath(path);
    const handle = await open(target, constants.O_RDONLY | constants.O_NOFOLLOW);
    try {
      const info = await handle.stat();
      if (!info.isFile() || info.size > MAX_FILE) throw new AppError(400, 'Tài liệu không phải file hoặc vượt 2 MiB.');
      const bytes = await handle.readFile();
      if (bytes.length > MAX_FILE) throw new AppError(400, 'Tài liệu vượt 2 MiB.');
      return { target, bytes, info, content: decoder.decode(bytes) };
    } finally { await handle.close(); }
  }
  private async documents(directory: string, prefix = ''): Promise<string[]> {
    const target = await this.safePath(directory);
    const entries = await readdir(target, { withFileTypes: true });
    const result: string[] = [];
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.name.startsWith('.')) continue;
      const path = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (entry.isDirectory() && prefix.split('/').length < 5) result.push(...await this.documents(`${directory}/${entry.name}`, path));
      else if (entry.name.endsWith('.md') && (entry.isFile() || entry.isSymbolicLink())) result.push(path);
      if (result.length > 512) throw new AppError(400, 'Feature vượt giới hạn 512 tài liệu.');
    }
    return result;
  }
  async info(): Promise<ProjectInfo> {
    const warnings: string[] = [];
    let features: ProjectInfo['features'] = [];
    try {
      const path = await this.safePath('specs');
      features = (await readdir(path, { withFileTypes: true })).filter(item => item.isDirectory() && !item.name.startsWith('.'))
        .map(item => ({ id: item.name, name: item.name })).sort((a, b) => a.id.localeCompare(b.id));
    } catch (error) {
      if (!missing(error)) warnings.push('Không đọc được thư mục specs: ' + this.message(error));
    }
    let kitInstalled = false;
    const context: Artifact[] = [];
    try {
      await this.safePath('.aiek'); kitInstalled = true;
      const docs = (await this.documents('.aiek')).filter(path => path === 'adapter.md' || path.startsWith('core/'));
      for (const path of docs) {
        try { context.push(parseArtifact(`.aiek/${path}`, (await this.read(`.aiek/${path}`)).content)); }
        catch (error) { warnings.push(`.aiek/${path}: ${this.message(error)}`); }
      }
    } catch (error) { if (!missing(error)) warnings.push(this.message(error)); }
    return { root: this.root, name: basename(this.root), kitInstalled, features, context, warnings };
  }
  async feature(id: string): Promise<Feature> {
    const info = await this.info();
    if (!info.features.some(feature => feature.id === id)) throw new AppError(404, 'Không tìm thấy feature.');
    const paths = await this.documents(`specs/${id}`);
    const artifacts: Artifact[] = [];
    const warnings: string[] = [];
    let total = 0;
    for (const path of paths) {
      try {
        const value = await this.read(`specs/${id}/${path}`);
        total += value.bytes.length;
        if (total > MAX_TOTAL) throw new AppError(400, 'Feature vượt giới hạn 20 MiB.');
        artifacts.push(parseArtifact(path, value.content));
      } catch (error) {
        const message = this.message(error);
        artifacts.push({ ...parseArtifact(path, ''), error: message });
        warnings.push(`${path}: ${message}`);
      }
    }
    for (const path of ['spec.md', 'plan.md', 'tasks.md']) {
      if (!paths.includes(path)) warnings.push(`Chưa có ${path}.`);
    }
    return { id, artifacts, warnings, revision: hash(JSON.stringify(artifacts.map(a => [a.path, a.hash, a.error]))),
      lane: declaredLane(artifacts.find(a => a.path === 'plan.md')),
      clarifications: artifacts.filter(a => a.path === 'spec.md').reduce((n, a) => n + [...a.content.matchAll(/\[NEEDS CLARIFICATION[^\]]*\]/g)].length, 0) };
  }
  async updateSection(featureId: string, artifactId: string, sectionId: string, expectedHash: string, replacement: string) {
    return this.serialize(async () => {
      const feature = await this.feature(featureId);
      const artifact = feature.artifacts.find(item => item.id === artifactId);
      if (!artifact || artifact.error) throw new AppError(400, 'Tài liệu không hỗ trợ chỉnh sửa.');
      if (artifact.hash !== expectedHash) throw new AppError(409, 'File đã thay đổi. Bản nháp được giữ lại; tải phiên bản mới trước khi thử lại.');
      const section = artifact.sections.find(item => item.id === sectionId);
      if (!section?.editable) throw new AppError(400, 'Section không hỗ trợ chỉnh sửa.');
      const parsed = parseArtifact(artifact.path, replacement);
      if (!parsed.sections.length || parsed.sections[0].start !== 0 || parsed.sections[0].depth !== section.depth ||
        normalize(parsed.sections[0].title) !== normalize(section.title) || parsed.sections.some((s, i) => i > 0 && s.depth <= section.depth)) {
        throw new AppError(400, 'Giữ nguyên heading của section; chỉ thêm heading con bên trong.');
      }
      if (Buffer.byteLength(replacement) > MAX_FILE) throw new AppError(400, 'Nội dung quá lớn.');
      const newline = artifact.content.includes('\r\n') ? '\r\n' : '\n';
      const normalized = replacement.replace(/\r?\n/g, newline);
      const body = normalized.endsWith(newline) ? normalized : normalized + newline;
      const result = artifact.content.slice(0, section.start) + body + artifact.content.slice(section.end);
      if (Buffer.byteLength(result) > MAX_FILE) throw new AppError(400, 'Tài liệu vượt 2 MiB.');
      const composed = parseArtifact(artifact.path, result);
      const delta = body.length - (section.end - section.start);
      const outside = artifact.sections.filter(item => item.start < section.start || item.start >= section.end);
      const sameBoundaries = outside.every(item => composed.sections.some(next =>
        next.start === item.start + (item.start >= section.end ? delta : 0) && next.depth === item.depth && next.title === item.title));
      if (!sameBoundaries || composed.sections.find(item => item.start === section.start)?.end !== section.end + delta) {
        throw new AppError(400, 'Markdown làm thay đổi ranh giới section khác. Đóng code fence hoặc HTML block trước khi lưu.');
      }
      const original = await this.read(`specs/${featureId}/${artifact.path}`);
      if (hash(original.bytes) !== expectedHash) throw new AppError(409, 'File đã thay đổi; chưa lưu.');
      const temp = join(dirname(original.target), `.aiek-${randomUUID()}.tmp`);
      try {
        const handle = await open(temp, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL, original.info.mode & 0o777);
        try { await handle.chmod(original.info.mode & 0o777); await handle.writeFile(result); await handle.sync(); } finally { await handle.close(); }
        const fresh = await this.read(`specs/${featureId}/${artifact.path}`);
        if (fresh.info.ino !== original.info.ino || fresh.info.dev !== original.info.dev || hash(fresh.bytes) !== expectedHash) {
          throw new AppError(409, 'File đã thay đổi; chưa lưu.');
        }
        await rename(temp, original.target);
      } finally { await unlink(temp).catch(() => undefined); }
      return this.feature(featureId);
    });
  }
  private message(error: unknown) { return error instanceof AppError ? error.message : 'Không thể đọc tài liệu; kiểm tra quyền hoặc UTF-8.'; }
}
