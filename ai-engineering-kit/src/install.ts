import { spawn } from 'node:child_process';
import { access, copyFile, mkdir, readFile, readdir, rm, stat, symlink, writeFile } from 'node:fs/promises';
import { dirname, isAbsolute, join, resolve, sep } from 'node:path';

const BEGIN = '<!-- ai-engineering-kit:begin -->';
const END = '<!-- ai-engineering-kit:end -->';
const HARNESS_ROOTS: Record<string, string> = {
  claude: '.claude/skills',
  codex: '.agents/skills',
  agy: '.agents/skills',
  antigravity: '.agents/skills',
};
const TEXT_SUFFIXES = new Set(['.md', '.json', '.yml', '.yaml', '.txt']);
const PREFIX_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*-$/;

export type Profile = 'core' | 'discovery' | 'full';

export interface InstallOptions {
  /** Kit checkout or installed package root (the directory holding manifest.json). */
  kitRoot: string;
  /** Project directory that receives `.aiek/` and the skill roots. */
  target: string;
  harness?: string;
  adapter?: string;
  profile?: Profile;
  only?: string[];
  skip?: string[];
  /** Namespace for installed skills; `aiek-` by default, `none` for bare names. */
  prefix?: string;
  force?: boolean;
  dryRun?: boolean;
  /** Symlink skill directories instead of copying (kit development; POSIX only). */
  link?: boolean;
  /** Register the Spec Kit extension, preset and workflows. */
  speckit?: boolean;
}

export interface InstallResult {
  kitRoot: string;
  target: string;
  prefix: string;
  skills: string[];
  skipped: string[];
  skillRoots: string[];
  actions: string[];
  dryRun: boolean;
}

interface Manifest {
  version: string;
  skills: { name: string; path: string; role?: string }[];
  profiles: Record<string, string[]>;
  scripts: string[];
}

export function normalizePrefix(value: string | undefined): string {
  const raw = (value ?? 'aiek-').trim();
  if (raw === '' || raw.toLowerCase() === 'none') return '';
  const lowered = raw.toLowerCase();
  const withDash = lowered.endsWith('-') ? lowered : `${lowered}-`;
  if (!PREFIX_PATTERN.test(withDash)) {
    throw new Error(`invalid --prefix '${raw}' (use lowercase letters, digits and hyphens, e.g. aiek-)`);
  }
  return withDash;
}

export async function readManifest(kitRoot: string): Promise<Manifest> {
  const manifest = JSON.parse(await readFile(join(kitRoot, 'manifest.json'), 'utf8')) as Manifest;
  if (!Array.isArray(manifest.skills) || !manifest.profiles) throw new Error(`manifest.json is incomplete: ${kitRoot}`);
  return manifest;
}

function parseList(value: string | string[] | undefined): string[] {
  if (value === undefined) return [];
  const items = (Array.isArray(value) ? value : [value]).flatMap((item) => item.split(','));
  return items.map((item) => item.trim()).filter(Boolean);
}

export function selectSkills(manifest: Manifest, options: Pick<InstallOptions, 'profile' | 'only' | 'skip'>): string[] {
  const known = new Set(manifest.skills.map((skill) => skill.name));
  const only = parseList(options.only);
  const skip = new Set(parseList(options.skip));
  for (const name of [...only, ...skip]) {
    if (!known.has(name)) {
      throw new Error(`unknown skill '${name}' (valid: ${[...known].join(', ')})`);
    }
  }
  const profile = options.profile ?? 'full';
  if (!(profile in manifest.profiles)) {
    throw new Error(`unknown profile '${profile}' (use ${Object.keys(manifest.profiles).join(', ')})`);
  }
  const base = only.length > 0 ? only : manifest.profiles[profile];
  const selected = manifest.profiles.full.filter((name) => base.includes(name) && !skip.has(name));
  if (selected.length === 0) throw new Error(`no skills selected (profile '${profile}' with the given --only/--skip)`);
  return selected;
}

function harnessRoots(harness: string | undefined): string[] {
  const values = parseList(harness ?? 'all');
  if (values.length === 0 || values.some((value) => value === '')) throw new Error('empty harness');
  const roots: string[] = [];
  for (const value of values) {
    const root = value === 'all' ? null : HARNESS_ROOTS[value];
    if (value === 'all') {
      for (const candidate of [HARNESS_ROOTS.claude, HARNESS_ROOTS.codex]) {
        if (!roots.includes(candidate)) roots.push(candidate);
      }
      continue;
    }
    if (!root) throw new Error(`unknown harness '${value}' (use claude, codex or agy)`);
    if (!roots.includes(root)) roots.push(root);
  }
  return roots;
}

async function exists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function isDirectory(path: string): Promise<boolean> {
  try {
    return (await stat(path)).isDirectory();
  } catch {
    return false;
  }
}

async function walkFiles(root: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) files.push(...(await walkFiles(path)));
    else if (entry.isFile()) files.push(path);
  }
  return files;
}

/** Copy (or symlink) one path, honouring `force`; existing paths are skipped, not merged. */
async function copyEntry(
  src: string,
  dest: string,
  options: { force: boolean; dryRun: boolean; link: boolean },
  actions: string[],
): Promise<void> {
  if (await exists(dest)) {
    if (!options.force) {
      actions.push(`skip (exists): ${dest}`);
      return;
    }
    if (!options.dryRun) await rm(dest, { recursive: true, force: true });
  }
  if (options.dryRun) {
    actions.push(`would install: ${dest}`);
    return;
  }
  await mkdir(dirname(dest), { recursive: true });
  if ((await stat(src)).isDirectory() && options.link) {
    await symlink(resolve(src), dest, process.platform === 'win32' ? 'junction' : 'dir');
  } else if ((await stat(src)).isDirectory()) {
    await mkdir(dest, { recursive: true });
    for (const entry of await readdir(src, { withFileTypes: true })) {
      await copyEntry(join(src, entry.name), join(dest, entry.name), { ...options, link: false }, []);
    }
  } else {
    await copyFile(src, dest);
  }
  actions.push(`installed: ${dest}`);
}

/** Rewrite bare skill names to `<prefix><name>` inside the installed copies only. */
export async function remapSkillNames(
  paths: string[],
  names: string[],
  prefix: string,
  dryRun: boolean,
): Promise<string[]> {
  if (!prefix || names.length === 0) return [];
  const ordered = [...names].sort((a, b) => b.length - a.length);
  const pattern = new RegExp(`(?<![a-z0-9-])(${ordered.map(escapeRegExp).join('|')})(?![a-z0-9-])`, 'g');
  const changed: string[] = [];
  for (const path of paths) {
    if (!(await exists(path))) continue;
    const files = (await isDirectory(path)) ? await walkFiles(path) : [path];
    for (const file of files) {
      if (!TEXT_SUFFIXES.has(file.slice(file.lastIndexOf('.')))) continue;
      let text: string;
      try {
        text = await readFile(file, 'utf8');
      } catch {
        continue;
      }
      const next = text.replace(pattern, (_match, name: string) => prefix + name);
      if (next === text) continue;
      changed.push(file);
      if (!dryRun) await writeFile(file, next, 'utf8');
    }
  }
  return changed;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Insert or replace the marked kit block in AGENTS.md / CLAUDE.md. */
export async function upsertBlock(file: string, body: string, dryRun: boolean): Promise<boolean> {
  const block = [BEGIN, ...body.replace(/\n$/, '').split('\n'), END];
  const current = (await exists(file)) ? await readFile(file, 'utf8') : null;
  if (current === null) {
    if (!dryRun) await writeFile(file, `${block.join('\n')}\n`, 'utf8');
    return true;
  }
  const lines = current.split('\n');
  const beginIndex = lines.indexOf(BEGIN);
  const endIndex = lines.indexOf(END);
  let next: string[];
  if (beginIndex >= 0 && endIndex >= 0) {
    next = [...lines.slice(0, beginIndex), ...block, ...lines.slice(endIndex + 1)];
  } else {
    const prefixLines = current.length > 0 && !current.endsWith('\n') ? [...lines, ''] : lines;
    next = [...prefixLines, ...block];
  }
  if (!dryRun) await writeFile(file, next.join('\n').replace(/\n*$/, '\n'), 'utf8');
  return true;
}

function validateMarkers(text: string, file: string): void {
  const lines = text.split('\n');
  const beginCount = text.split(BEGIN).length - 1;
  const endCount = text.split(END).length - 1;
  if (beginCount === 0 && endCount === 0) return;
  const beginIndex = lines.indexOf(BEGIN);
  const endIndex = lines.indexOf(END);
  if (beginCount !== 1 || endCount !== 1 || beginIndex < 0 || endIndex < 0 || beginIndex >= endIndex) {
    throw new Error(`malformed kit markers in ${file}; repair before installing`);
  }
}

async function runSpecify(target: string, args: string[]): Promise<void> {
  await new Promise<void>((resolvePromise, rejectPromise) => {
    const child = spawn('specify', args, { cwd: target, stdio: 'inherit', shell: process.platform === 'win32' });
    child.once('error', rejectPromise);
    child.once('exit', (code) => {
      if (code === 0) resolvePromise();
      else rejectPromise(new Error(`specify ${args.join(' ')} exited ${code}`));
    });
  });
}

export async function installKit(options: InstallOptions): Promise<InstallResult> {
  const kitRoot = resolve(options.kitRoot);
  const target = resolve(options.target);
  const dryRun = options.dryRun === true;
  const force = options.force === true;
  const link = options.link === true;
  const prefix = normalizePrefix(options.prefix);
  if (prefix && link) {
    throw new Error('--link cannot be combined with --prefix: a symlink cannot carry a renamed skill (use --prefix none)');
  }
  if (kitRoot === target) throw new Error('refusing to install the kit into itself');
  if (!(await isDirectory(target))) throw new Error(`target dir not found: ${target}`);

  const manifest = await readManifest(kitRoot);
  const skills = selectSkills(manifest, options);
  const skipped = parseList(options.skip);
  if (prefix) {
    for (const name of skills) {
      if (`${prefix}${name}`.length > 64) {
        throw new Error(`prefixed skill name '${prefix}${name}' exceeds the 64-character skill-name limit`);
      }
    }
  }

  const adapter = options.adapter ?? 'default';
  const adapterDir = isAbsolute(adapter) || adapter.includes('/') || adapter.includes(sep)
    ? resolve(adapter)
    : join(kitRoot, 'adapters', adapter);
  if (!(await exists(join(adapterDir, 'adapter.md')))) throw new Error(`adapter.md not found in ${adapterDir}`);
  for (const script of manifest.scripts) {
    if (!(await exists(join(kitRoot, script)))) throw new Error(`missing helper script: ${script}`);
  }
  if (options.speckit) {
    if (!(await exists(join(target, '.specify')))) throw new Error('run specify init in the target before --speckit');
  }

  for (const file of ['AGENTS.md', 'CLAUDE.md']) {
    const path = join(target, file);
    if (await exists(path)) validateMarkers(await readFile(path, 'utf8'), path);
  }

  const skillRoots = harnessRoots(options.harness);
  const actions: string[] = [];
  const installed: string[] = [];
  const skillNames = manifest.skills.map((skill) => skill.name);

  // 1. Core policies, notice and adapter.
  const coreDir = join(kitRoot, 'core');
  if (await isDirectory(coreDir)) {
    for (const entry of await readdir(coreDir)) {
      if (!entry.endsWith('.md') || entry === 'router.md') continue;
      await copyEntry(join(coreDir, entry), join(target, '.aiek', 'core', entry), { force, dryRun, link: false }, actions);
    }
  }
  await copyEntry(join(kitRoot, 'NOTICE.md'), join(target, '.aiek', 'NOTICE.md'), { force, dryRun, link: false }, actions);
  await copyEntry(join(adapterDir, 'adapter.md'), join(target, '.aiek', 'adapter.md'), { force, dryRun, link: false }, actions);
  for (const extra of ['references', 'scripts']) {
    if (await isDirectory(join(adapterDir, extra))) {
      await copyEntry(join(adapterDir, extra), join(target, '.aiek', 'adapter', extra), { force, dryRun, link: false }, actions);
    }
  }

  // 2. Helper scripts.
  for (const script of manifest.scripts) {
    await copyEntry(join(kitRoot, script), join(target, '.aiek', script), { force, dryRun, link: false }, actions);
  }

  // 3. Skills under <prefix><name>, then namespace the copies.
  for (const root of skillRoots) {
    for (const name of skills) {
      const installedName = `${prefix}${name}`;
      await copyEntry(join(kitRoot, 'skills', name), join(target, root, installedName), { force, dryRun, link }, actions);
      installed.push(`${root}/${installedName}`);
    }
  }
  const remapRoots = [join(target, '.aiek'), ...installed.map((entry) => join(target, entry))];
  const changed = await remapSkillNames(remapRoots, skillNames, prefix, dryRun);
  if (changed.length > 0) actions.push(`${dryRun ? '[dry-run] would rewrite' : 'rewrote'} ${changed.length} file(s) to ${prefix}* names`);

  // 4. Agent instructions.
  const router = await readFile(join(kitRoot, 'core', 'router.md'), 'utf8');
  const routerBody = prefix ? remapText(router, skillNames, prefix) : router;
  await upsertBlock(join(target, 'AGENTS.md'), routerBody, dryRun);
  actions.push(`updated kit block: AGENTS.md`);
  if (skillRoots.includes('.claude/skills')) {
    const claudeMd = join(target, 'CLAUDE.md');
    if (!(await exists(claudeMd))) {
      if (!dryRun) await writeFile(claudeMd, '@AGENTS.md\n', 'utf8');
      actions.push('created: CLAUDE.md (imports AGENTS.md)');
    } else if (!/^@AGENTS\.md/m.test(await readFile(claudeMd, 'utf8'))) {
      await upsertBlock(claudeMd, routerBody, dryRun);
      actions.push('updated kit block: CLAUDE.md');
    } else {
      actions.push('CLAUDE.md already imports AGENTS.md');
    }
  }

  // 5. Spec Kit registration.
  if (options.speckit) {
    const adapterPreset = join(adapterDir, 'speckit-preset', 'preset.yml');
    const steps: string[][] = [
      ['extension', 'add', '--dev', join(kitRoot, 'speckit', 'extensions', 'aiek')],
      ['preset', 'add', '--dev', join(kitRoot, 'speckit', 'presets', 'aiek-core'), '--priority', '10'],
      ...(await exists(adapterPreset)
        ? [['preset', 'add', '--dev', join(adapterDir, 'speckit-preset'), '--priority', '5']]
        : []),
      ['workflow', 'add', '--dev', join(kitRoot, 'speckit', 'workflows', 'aiek-normal')],
      ['workflow', 'add', '--dev', join(kitRoot, 'speckit', 'workflows', 'aiek-large')],
      ['workflow', 'add', '--dev', join(kitRoot, 'speckit', 'workflows', 'aiek-project')],
    ];
    for (const step of steps) {
      if (!dryRun) await runSpecify(target, step);
      actions.push(`${dryRun ? 'would run' : 'ran'}: specify ${step.join(' ')}`);
    }
  }

  return { kitRoot, target, prefix, skills, skipped, skillRoots, actions, dryRun };
}

function remapText(text: string, names: string[], prefix: string): string {
  const ordered = [...names].sort((a, b) => b.length - a.length);
  const pattern = new RegExp(`(?<![a-z0-9-])(${ordered.map(escapeRegExp).join('|')})(?![a-z0-9-])`, 'g');
  return text.replace(pattern, (_match, name: string) => prefix + name);
}

export { BEGIN, END };
