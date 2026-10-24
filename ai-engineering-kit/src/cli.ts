#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import open from 'open';
import { startServer } from './server.js';
import { installKit, type InstallOptions, type Profile } from './install.js';

const KIT_ROOT = fileURLToPath(new URL('../../', import.meta.url));

const HELP = `AI Engineering Kit

  aiek install [dir] [options]   Cài kit vào một project (cross-platform)
  aiek web [--project <path>] [--port <port>] [--no-open]
                                 Mở giao diện review local
  aiek --version                 In phiên bản
  aiek --help                    Trợ giúp

install options:
  --harness <list>    claude -> .claude/skills/, codex|agy -> .agents/skills/ (default: all)
  --adapter <name>    Adapter dưới adapters/ hoặc đường dẫn tới thư mục adapter (default: default)
  --profile <name>    core | discovery | full (default: full)
  --only <a,b>        Chỉ cài các skill này; thay cho --profile
  --skip <a,b>        Bỏ các skill này khỏi lựa chọn
  --prefix <p|none>   Namespace skill đã cài (default: aiek-); "none" để dùng tên trần
  --speckit           Đăng ký extension, preset và workflow Spec Kit (cần specify + .specify/)
  --link              Symlink skill thay vì copy (phát triển kit; không dùng với --prefix)
  --force             Ghi đè file kit đã tồn tại
  --dry-run           Chỉ in kế hoạch, không ghi gì

Ví dụ:
  npx @moment/aiek install . --profile core --harness codex
  npx @moment/aiek install . --prefix none --dry-run
  aiek web --project ./my-app`;

async function readVersion(): Promise<string> {
  const manifest = JSON.parse(await readFile(join(KIT_ROOT, 'manifest.json'), 'utf8'));
  return String(manifest.version);
}

function parseInstallArgs(argv: string[]): InstallOptions & { target: string } {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      harness: { type: 'string' },
      adapter: { type: 'string' },
      profile: { type: 'string' },
      only: { type: 'string' },
      skip: { type: 'string' },
      prefix: { type: 'string' },
      speckit: { type: 'boolean' },
      link: { type: 'boolean' },
      force: { type: 'boolean' },
      'dry-run': { type: 'boolean' },
      help: { type: 'boolean', short: 'h' },
    },
  });
  if (values.help) {
    console.log(HELP);
    process.exit(0);
  }
  if (positionals.length > 1) throw new Error('install nhận tối đa một thư mục đích');
  const profile = values.profile as Profile | undefined;
  if (profile !== undefined && !['core', 'discovery', 'full'].includes(profile)) {
    throw new Error(`unknown profile '${profile}' (use core, discovery or full)`);
  }
  return {
    kitRoot: KIT_ROOT,
    target: positionals[0] ?? process.cwd(),
    harness: values.harness,
    adapter: values.adapter,
    profile,
    only: values.only === undefined ? [] : [values.only],
    skip: values.skip === undefined ? [] : [values.skip],
    prefix: values.prefix,
    speckit: values.speckit,
    link: values.link,
    force: values.force,
    dryRun: values['dry-run'],
  };
}

async function runInstall(argv: string[]): Promise<void> {
  const options = parseInstallArgs(argv);
  if (options.dryRun) console.log('AI Engineering Kit (dry-run: nothing will be written)');
  const result = await installKit(options);
  for (const action of result.actions) console.log(`  ${action}`);
  console.log(`\nInstalled ${result.skills.length} skill(s) into ${result.target}`);
  console.log(`  namespace: ${result.prefix || '(none)'}`);
  console.log(`  skill roots: ${result.skillRoots.join(', ')}`);
  if (result.skipped.length > 0) console.log(`  skipped: ${result.skipped.join(', ')}`);
  console.log('\nNext: review .aiek/adapter.md and fill in project commands (see .aiek/core/adapter-contract.md).');
}

async function main(): Promise<void> {
  const [command, ...rest] = process.argv.slice(2);
  if (command === '--version' || command === '-v') {
    console.log(await readVersion());
    return;
  }
  if (command === 'install') {
    await runInstall(rest);
    return;
  }
  if (command === '--help' || command === '-h' || command === undefined) {
    console.log(HELP);
    return;
  }
  if (command !== 'web') throw new Error('Lệnh không hợp lệ. Dùng aiek --help.');

  const { values } = parseArgs({
    args: rest,
    options: {
      project: { type: 'string' }, port: { type: 'string' }, 'no-open': { type: 'boolean' },
    },
  });
  const port = values.port === undefined ? undefined : Number(values.port);
  if (port !== undefined && (!/^\d+$/.test(values.port!) || !Number.isInteger(port) || port < 1 || port > 65535)) {
    throw new Error('Port phải từ 1 đến 65535.');
  }
  const app = await startServer({ project: values.project ?? process.cwd(), port, explicitPort: values.port !== undefined });
  console.log(`AI Engineering Kit · ${app.project.root}\n${app.url}\nCtrl+C để dừng.`);
  let stopping = false;
  const stop = () => {
    if (stopping) return;
    stopping = true;
    void app.close().catch(error => { console.error(error.message); process.exitCode = 1; });
  };
  process.once('SIGINT', stop); process.once('SIGTERM', stop);
  if (!values['no-open']) {
    try { await open(app.url, { wait: false }); }
    catch { console.error('Không mở được trình duyệt. Dùng URL ở trên.'); }
  }
}

main().catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
