#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { readFile } from 'node:fs/promises';
import open from 'open';
import { startServer } from './server.js';

async function main() {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    project: { type: 'string' }, port: { type: 'string' }, 'no-open': { type: 'boolean' },
    help: { type: 'boolean', short: 'h' }, version: { type: 'boolean', short: 'v' },
  } });
  if (values.version) {
    const manifest = JSON.parse(await readFile(new URL('../../manifest.json', import.meta.url), 'utf8'));
    console.log(manifest.version); return;
  }
  if (values.help || positionals.length === 0) {
    console.log('AI Engineering Kit\n\n  aiek web [--project <path>] [--port <port>] [--no-open]\n\nMở giao diện review local. Node >=22.12. Ctrl+C để dừng.'); return;
  }
  if (positionals.length !== 1 || positionals[0] !== 'web') throw new Error('Lệnh không hợp lệ. Dùng aiek --help.');
  const port = values.port === undefined ? undefined : Number(values.port);
  if (port !== undefined && (!/^\d+$/.test(values.port!) || !Number.isInteger(port) || port < 1 || port > 65535)) throw new Error('Port phải từ 1 đến 65535.');
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
main().catch(error => { console.error(error.message); process.exitCode = 1; });
