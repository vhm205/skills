import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, writeFile, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const exec = promisify(execFile);
const kit = fileURLToPath(new URL('../', import.meta.url));
const temp = await mkdtemp(join(tmpdir(), 'aiek-package-'));
const project = join(temp, 'project with spaces');
let child;
const stop = async () => {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  child.kill('SIGTERM');
  await new Promise(resolve => {
    const timer = setTimeout(() => { child.kill('SIGKILL'); }, 5000);
    child.once('exit', () => { clearTimeout(timer); resolve(); });
  });
};
try {
  await exec('npm', ['run', 'build'], { cwd: kit });
  const { stdout } = await exec('npm', ['pack', '--ignore-scripts', '--json', '--pack-destination', temp], { cwd: kit });
  const pack = JSON.parse(stdout)[0];
  const paths = pack.files.map(file => file.path);
  for (const path of ['dist/server/cli.js', 'dist/ui/index.html', 'manifest.json', 'core/WORKFLOW.md', 'skills/executing-task/SKILL.md', 'skills/shaping-project/SKILL.md', 'speckit/workflows/aiek-project/workflow.yml', 'scripts/install.sh', 'scripts/init-project.sh']) assert(paths.includes(path), `Missing ${path}`);
  assert(!paths.some(path => /^(node_modules|tests|src|ui|specs)\//.test(path)), 'Package contains development sources');
  await mkdir(join(project, 'specs', '001-smoke'), { recursive: true });
  await writeFile(join(project, 'specs', '001-smoke', 'spec.md'), '# Packaged feature\n');
  const packed = join(temp, pack.filename);
  // npm exec selects the package from the tarball, never the repository checkout.
  child = spawn('npm', ['exec', '--yes', `--package=${packed}`, '--', 'aiek', 'web', '--project', project, '--no-open'], {
    cwd: temp, env: { ...process.env, AIEK_DATA_DIR: join(temp, 'state') }, stdio: ['ignore', 'pipe', 'pipe'], detached: process.platform !== 'win32',
  });
  let stderr = '';
  child.stderr.on('data', chunk => { stderr += chunk; });
  const url = await new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(() => reject(new Error(`Packaged startup timeout: ${stderr}`)), 120000);
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('exit', code => { clearTimeout(timer); reject(new Error(`Packaged CLI exited ${code}: ${stderr}`)); });
    child.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+\/#token=[a-f0-9]+/);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
  });
  const parsed = new URL(url); const origin = parsed.origin;
  const response = await fetch(origin); assert.equal(response.status, 200);
  const html = await response.text();
  const assetPaths = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map(match => match[1]);
  assert(assetPaths.length >= 2, 'No packaged JS/CSS');
  for (const path of assetPaths) assert.equal((await fetch(origin + path)).status, 200);
  const session = await fetch(origin + '/api/session', { method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' }, body: JSON.stringify({ token: new URLSearchParams(parsed.hash.slice(1)).get('token') }) });
  assert.equal(session.status, 200);
  const cookie = session.headers.get('set-cookie').split(';')[0];
  const info = await (await fetch(origin + '/api/project', { headers: { Cookie: cookie } })).json();
  assert.equal(info.features[0].id, '001-smoke');
  assert.equal((await readFile(join(project, 'specs', '001-smoke', 'spec.md'), 'utf8')), '# Packaged feature\n');
  if (process.platform !== 'win32') process.kill(-child.pid, 'SIGTERM'); else child.kill('SIGTERM');
  await stop();
  await assert.rejects(fetch(origin));
  console.log(`PASS: npm tarball (${pack.size} bytes), npx launch, JS/CSS, authenticated feature read, unchanged project and clean shutdown`);
} finally { await stop(); await rm(temp, { recursive: true, force: true }); }
