"""Verified DSH model patch and macOS process boundary for trusted local fixtures.

Credentials load through DSH's own bootstrap, stay in child memory, then only the
DeepSeek provider key/proxy environment passes into an isolated DSH home. The
managed credential reference is read using the installed DSH parser, read-only.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

from .contracts import ContractError
from .process import run_process


def model_patch(model: str) -> list[dict]:
    if not re.fullmatch(r"[A-Za-z0-9_.\-/]{1,120}", model):
        raise ContractError("invalid model identifier")
    return [{"id": "agent-default-model", "config": {"provider": "deepseek-official", "model": model}}]


def pinned_model(dump: str) -> str | None:
    block = re.search(r"(?ms)^- id: agent-default-model\n(.*?)(?=^- id:|\Z)", dump)
    match = re.search(r"(?m)^\s+model:\s*['\"]?([A-Za-z0-9_.\-/]+)['\"]?\s*$", block[1]) if block else None
    return match[1] if match else None


def boot_module(binary: str) -> Path:
    return Path(binary).resolve().parent.parent / "node_modules/@deepseek-ai/dsh-app-boot/lib/index.js"


def policy(allowed: Path, denied: list[Path]) -> str:
    lines = ["(version 1)", "(allow default)", "(deny file-write*)",
             f"(allow file-write* (subpath {json.dumps(str(allowed.resolve()))}))",
             '(allow file-write* (literal "/dev/null"))']
    for path in denied:
        lines.append(f"(deny file-read* (subpath {json.dumps(str(path.resolve()))}))")
    return "\n".join(lines)


# Exercise the installed subprocess provider and bundled ripgrep without booting
# an agent or loading any provider. A write-deny sandbox must still permit the
# runtime's own temporary process artifacts inside the trial root.
TOOL_RUNTIME_PROBE = r'''
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';
const req=createRequire(pathToFileURL(process.argv[1]));
const {Context}=await import(pathToFileURL(req.resolve('@deepseek-ai/cordis')));
const {LocalSubprocessRuntime}=await import(pathToFileURL(req.resolve('@deepseek-ai/dsh-subprocess-local')));
const {rgPath}=req('@vscode/ripgrep');
const ctx=new Context();
const runtime=new LocalSubprocessRuntime(ctx);
try {
  for (const argv of [['/bin/sh','-c','printf TOOL_RUNTIME_OK > runtime-marker'],
                      [rgPath,'--no-config','TOOL_RUNTIME_OK','runtime-marker']]) {
    const handle=runtime.spawn({argv,cwd:process.cwd(),
      stdio:{stdin:'ignore',stdout:{maxBytes:1024},stderr:{maxBytes:1024}},graceMs:100});
    if ((await handle.done).exitCode!==0) throw new Error('Tool runtime failed');
  }
  if (readFileSync('runtime-marker','utf8')!=='TOOL_RUNTIME_OK') throw new Error('Marker missing');
  process.stdout.write('TOOL_RUNTIME_OK');
} finally {
  await runtime.disposeManagedProcesses();
  await ctx.fiber.dispose();
}
'''


def capabilities(binary: str) -> dict:
    """Local probes only: no task, provider request, credentials, or config dump saved."""
    supported = {"model_pinning": False, "global_config_isolation": False, "grader_isolation": False, "tool_runtime": False}
    if not shutil.which("node") or not boot_module(binary).is_file():
        return supported
    rc, default, _, _, _ = run_process([binary, "--profile", "headless", "--dump-default-config"],
                                     cwd=Path(tempfile.gettempdir()), timeout=15)
    if rc == 0 and pinned_model(default):
        with tempfile.TemporaryDirectory(prefix="aiek-dsh-pin-") as tmp:
            patch = Path(tmp) / "model.json"
            patch.write_text(json.dumps(model_patch("eval-probe-model")))
            rc, patched, _, _, _ = run_process([binary, "--profile", "headless", "--patch", str(patch), "--dump-config"],
                                               cwd=Path(tmp), timeout=15)
            supported["model_pinning"] = rc == 0 and pinned_model(patched) == "eval-probe-model"
    sandbox = shutil.which("sandbox-exec")
    if not sandbox:
        return supported
    with tempfile.TemporaryDirectory(prefix="aiek-boundary-") as tmp:
        base = Path(tmp)
        allowed = base / "allowed"
        allowed.mkdir()
        canary = base / "private"
        canary.write_text("EVAL_CANARY_MUST_NOT_BE_READ")
        outside = base / "outside-write"
        profile = policy(allowed, [canary])
        code = ("from pathlib import Path\n"
                f"Path({str(allowed / 'inside')!r}).write_text('ok')\n"
                f"try: Path({str(canary)!r}).read_text(); raise SystemExit(41)\n"
                "except PermissionError: pass\n"
                f"try: Path({str(outside)!r}).write_text('bad'); raise SystemExit(42)\n"
                "except PermissionError: pass\n")
        rc, _, _, _, _ = run_process([sandbox, "-p", profile, sys.executable, "-I", "-c", code],
                                     cwd=allowed, timeout=10)
        boundary = rc == 0 and not outside.exists() and (allowed / "inside").exists()
        supported["grader_isolation"] = boundary
        supported["global_config_isolation"] = boundary and boot_module(binary).is_file()
        if boundary:
            import os
            runtime_tmp = allowed / "tmp"
            runtime_tmp.mkdir()
            rc, output, _, _, _ = run_process(
                [sandbox, "-p", profile, shutil.which("node"), "--input-type=module", "--eval",
                 TOOL_RUNTIME_PROBE, str(boot_module(binary))], cwd=allowed, timeout=15,
                env={**os.environ, "TMPDIR": str(runtime_tmp), "TMP": str(runtime_tmp), "TEMP": str(runtime_tmp)})
            supported["tool_runtime"] = rc == 0 and output == "TOOL_RUNTIME_OK"
    return supported


# Read-only bridge to the installed DSH parser. The managed reference wins over
# environment fallbacks, as in LocalCredentialProvider.resolve(). Never migrate,
# rewrite, log, or copy the credential document into a candidate workspace.
CREDENTIAL_LOADER = r'''
async function officialCredential(boot, cwd) {
  const {loadLayeredEnv} = await import(pathToFileURL(boot).href);
  loadLayeredEnv('dsh', cwd, () => {});
  const {resolveDshHome} = await import(new URL('../../dsh-home-paths/lib/index.js', pathToFileURL(boot)));
  const {join} = await import('node:path');
  const {open} = await import('node:fs/promises');
  const filename = join(resolveDshHome(), '.credentials.yaml');
  let file;
  try {
    file = await open(filename, 'r');
  } catch (error) {
    if (error.code !== 'ENOENT') throw new Error('Credential store unavailable');
  }
  if (file) {
    try {
      const info = await file.stat();
      if (!info.isFile() || info.size > 1024 * 1024 ||
          (process.platform !== 'win32' && (info.mode & 63) !== 0)) {
        throw new Error('Credential store permissions or size invalid');
      }
      const {parseCredentialsDocument} = await import(new URL('../../dsh-credentials-local/lib/index.js', pathToFileURL(boot)));
      const document = parseCredentialsDocument(await file.readFile('utf8'), filename);
      const stored = document.refs.get('DEEPSEEK_API_KEY');
      if (stored !== undefined) return stored;
    } finally { await file.close(); }
  }
  return process.env.DEEPSEEK_API_KEY;
}
'''


def authentication_available(binary: str) -> bool:
    if not boot_module(binary).is_file() or not shutil.which("node"):
        return False
    code = ("import {pathToFileURL} from 'node:url';" + CREDENTIAL_LOADER +
            "try {const key=await officialCredential(process.argv[1],process.cwd());"
            "process.stdout.write(key?'AUTH_READY':'AUTH_MISSING');"
            "} catch {process.stdout.write('AUTH_MISSING');}")
    rc, out, _, _, _ = run_process([shutil.which("node"), "--input-type=module", "--eval", code,
                                   str(boot_module(binary))], cwd=Path(tempfile.gettempdir()), timeout=10)
    return rc == 0 and out == "AUTH_READY"


# Fixed trusted wrapper. No generated shell, credential printing, or config mutation.
BOOTSTRAP = "import { pathToFileURL } from 'node:url';\n" + CREDENTIAL_LOADER + r'''
import { spawnSync } from 'node:child_process';
const [boot, binary, sandbox, profile, home, agents, patch, work] = process.argv.slice(1);
try {
  const apiKey = await officialCredential(boot, work);
  if (!apiKey) {
    process.stderr.write('AUTH_ERROR: DEEPSEEK_API_KEY unavailable through DSH bootstrap\n');
    process.exit(2);
  }
  const env = {};
  for (const key of ['PATH', 'HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'LC_ALL', 'DEEPSEEK_API_KEY',
                     'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'NO_PROXY',
                     'https_proxy', 'http_proxy', 'all_proxy', 'no_proxy']) {
    if (process.env[key] !== undefined) env[key] = process.env[key];
  }
  env.DEEPSEEK_API_KEY = apiKey;
  env.DSH_HOME = home;
  env.DSH_AGENTS_HOME = agents;
  env.GIT_CONFIG_NOSYSTEM = '1';
  env.GIT_CONFIG_GLOBAL = '/dev/null';
  const child = spawnSync(sandbox, ['-p', profile, binary, '--profile', 'headless',
                         '--patch', patch, '--json', process.env.AIEK_EVAL_PROMPT],
                         { cwd: work, env, encoding: 'utf8', maxBuffer: 4 * 1024 * 1024 });
  const sensitive = ['DEEPSEEK_API_KEY', 'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY',
                     'https_proxy', 'http_proxy', 'all_proxy'].map(key => env[key]).filter(Boolean);
  const scrub = value => sensitive.reduce((text, secret) => text.split(secret).join('[REDACTED]'), value ?? '');
  process.stdout.write(scrub(child.stdout));
  process.stderr.write(scrub(child.stderr));
  if (child.error) process.stderr.write('DSH_BOOT_ERROR: isolated launch failed\n');
  process.exit(child.status ?? 2);
} catch {
  process.stderr.write('AUTH_ERROR: DSH environment bootstrap failed\n');
  process.exit(2);
}
'''


def run_isolated(binary: str, prompt: str, work: Path, base: Path, kit: Path,
                 model: str, env: dict, timeout: float):
    from .harnesses import DshHarness
    config = base / "dsh-config"
    config.mkdir()
    patch = config / "model.json"
    patch.write_text(json.dumps(model_patch(model)))
    denied = [kit.parent, Path.home() / ".agents", Path.home() / ".codex",
              Path.home() / ".claude", Path(env.get("DSH_HOME", str(Path.home() / ".dsh")))]
    runtime_tmp = base / "runtime-tmp"
    runtime_tmp.mkdir()
    launch_env = {**env, "TMPDIR": str(runtime_tmp), "TMP": str(runtime_tmp),
                  "TEMP": str(runtime_tmp), "AIEK_EVAL_PROMPT": prompt}
    command = [shutil.which("node") or "node", "--input-type=module", "--eval", BOOTSTRAP, "--",
               str(boot_module(binary)), binary, shutil.which("sandbox-exec") or "sandbox-exec",
               policy(base, denied), str(config / "home"), str(config / "agents"), str(patch), str(work)]
    rc, out, err, duration, _ = run_process(command, cwd=work, timeout=timeout, env=launch_env)
    parser = object.__new__(DshHarness)
    response = parser.parse(out, err, duration, timeout)
    response.raw_stdout, response.raw_stderr = out, err
    response.command = ["node", "<trusted DSH bootstrap>", "sandbox-exec", "dsh", "--profile", "headless", "--patch", "<model patch>", "--json", "<prompt>"]
    if rc is None or rc != 0:
        response.error = err[-800:] or f"isolated DSH exited {rc}"
    return response
