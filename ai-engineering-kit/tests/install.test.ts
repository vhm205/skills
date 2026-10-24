import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm, stat, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { afterEach, describe, expect, it } from 'vitest';
import { installKit, normalizePrefix, readManifest, selectSkills } from '../src/install.js';

const exec = promisify(execFile);
const KIT = fileURLToPath(new URL('../', import.meta.url));
const temps: string[] = [];

async function tempProject(): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), 'aiek-install-'));
  temps.push(dir);
  return dir;
}

async function walk(root: string, base = ''): Promise<string[]> {
  const entries = await readdir(join(root, base), { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const relative = base ? `${base}/${entry.name}` : entry.name;
    if (entry.isDirectory()) files.push(...(await walk(root, relative)));
    else files.push(relative);
  }
  return files.sort();
}

afterEach(async () => {
  await Promise.all(temps.splice(0).map((dir) => rm(dir, { recursive: true, force: true })));
});

describe('prefix and selection', () => {
  it('normalizes prefixes', () => {
    expect(normalizePrefix(undefined)).toBe('aiek-');
    expect(normalizePrefix('AIEK')).toBe('aiek-');
    expect(normalizePrefix('team-')).toBe('team-');
    expect(normalizePrefix('none')).toBe('');
    expect(normalizePrefix('')).toBe('');
    expect(() => normalizePrefix('Bad Prefix')).toThrow(/invalid --prefix/);
    expect(() => normalizePrefix('a_b')).toThrow(/invalid --prefix/);
  });

  it('selects by profile, only and skip', async () => {
    const manifest = await readManifest(KIT);
    expect(selectSkills(manifest, { profile: 'core' })).toHaveLength(11);
    expect(selectSkills(manifest, { profile: 'discovery' })).toHaveLength(4);
    expect(selectSkills(manifest, { only: ['executing-task', 'verifying-change'] })).toEqual([
      'executing-task',
      'verifying-change',
    ]);
    expect(selectSkills(manifest, { profile: 'core', skip: ['executing-task'] })).toHaveLength(10);
    expect(() => selectSkills(manifest, { only: ['nope'] })).toThrow(/unknown skill/);
  });
});

describe('installKit', () => {
  it('installs prefixed skills, rewrites names and the router', async () => {
    const target = await tempProject();
    const result = await installKit({ kitRoot: KIT, target, harness: 'codex', profile: 'discovery' });
    expect(result.prefix).toBe('aiek-');

    const root = join(target, '.agents/skills');
    const dirs = (await readdir(root)).sort();
    expect(dirs).toEqual(['aiek-exploring-idea', 'aiek-intaking-ticket', 'aiek-shaping-feature', 'aiek-shaping-project']);

    const front = await readFile(join(root, 'aiek-exploring-idea/SKILL.md'), 'utf8');
    expect(front).toMatch(/^name: aiek-exploring-idea$/m);
    expect(front).not.toContain('aiek-aiek-');
    expect(front).not.toMatch(/(?<![a-z0-9-])shaping-feature(?![a-z0-9-])/);

    const agents = await readFile(join(target, 'AGENTS.md'), 'utf8');
    expect(agents).toContain('`aiek-intaking-ticket`');
    expect(agents).not.toMatch(/(?<![a-z0-9-])intaking-ticket(?![a-z0-9-])/);
    expect(await readFile(join(target, '.aiek/adapter.md'), 'utf8')).toContain('adapter:');
  });

  it('installs bare names with --prefix none and is idempotent', async () => {
    const target = await tempProject();
    await installKit({ kitRoot: KIT, target, harness: 'claude', only: ['executing-task'], prefix: 'none' });
    expect(await readFile(join(target, '.claude/skills/executing-task/SKILL.md'), 'utf8')).toMatch(/^name: executing-task$/m);
    expect(await readFile(join(target, 'CLAUDE.md'), 'utf8')).toBe('@AGENTS.md\n');

    await installKit({ kitRoot: KIT, target, harness: 'codex', profile: 'discovery' });
    const before = await readFile(join(target, '.agents/skills/aiek-shaping-feature/SKILL.md'), 'utf8');
    await installKit({ kitRoot: KIT, target, harness: 'codex', profile: 'discovery' });
    const after = await readFile(join(target, '.agents/skills/aiek-shaping-feature/SKILL.md'), 'utf8');
    expect(after).toBe(before);
    expect(after).not.toContain('aiek-aiek-');
  });

  it('writes nothing on dry-run', async () => {
    const target = await tempProject();
    const result = await installKit({ kitRoot: KIT, target, profile: 'core', dryRun: true });
    expect(result.dryRun).toBe(true);
    expect(await readdir(target)).toEqual([]);
  });

  it('keeps a project-owned adapter without --force and overwrites with it', async () => {
    const target = await tempProject();
    await mkdir(join(target, '.aiek'), { recursive: true });
    await writeFile(join(target, '.aiek/adapter.md'), 'project-owned commands\n');
    await installKit({ kitRoot: KIT, target, harness: 'codex', only: ['executing-task'] });
    expect(await readFile(join(target, '.aiek/adapter.md'), 'utf8')).toBe('project-owned commands\n');
    await installKit({ kitRoot: KIT, target, harness: 'codex', only: ['executing-task'], force: true });
    expect(await readFile(join(target, '.aiek/adapter.md'), 'utf8')).toContain('adapter:');
  });

  it('rejects bad markers and link+prefix before writing', async () => {
    const target = await tempProject();
    await writeFile(join(target, 'AGENTS.md'), '<!-- ai-engineering-kit:begin -->\nkeep\n');
    const before = await readdir(target);
    await expect(installKit({ kitRoot: KIT, target, only: ['executing-task'] })).rejects.toThrow(/malformed kit markers/);
    expect(await readdir(target)).toEqual(before);

    const clean = await tempProject();
    await expect(installKit({ kitRoot: KIT, target: clean, link: true })).rejects.toThrow(/--link/);
    expect(await readdir(clean)).toEqual([]);
  });

  it('matches the bash installer file layout', async () => {
    if (process.platform === 'win32') return;
    const bash = await tempProject();
    const node = await tempProject();
    await exec('bash', [join(KIT, 'scripts/install.sh'), bash, '--harness', 'codex', '--profile', 'discovery'], { cwd: KIT });
    await installKit({ kitRoot: KIT, target: node, harness: 'codex', profile: 'discovery' });
    expect(await walk(node)).toEqual(await walk(bash));
    const digest = async (root: string) => {
      const hash = createHash('sha256');
      for (const file of await walk(root)) {
        hash.update(file);
        hash.update(await readFile(join(root, file)));
      }
      return hash.digest('hex');
    };
    expect(await digest(node)).toBe(await digest(bash));
    expect((await stat(join(node, '.agents/skills'))).isDirectory()).toBe(true);
  });
});
