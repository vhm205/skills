"""Bounded subprocess execution with process-group cleanup (POSIX)."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def run_process(cmd: list[str], *, cwd: Path, timeout: float, env: dict | None = None,
                max_output_bytes: int = 4 * 1024 * 1024) -> tuple:
    started = time.monotonic()
    if timeout <= 0 or max_output_bytes < 1:
        raise ValueError("positive timeout and output limit required")
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, start_new_session=os.name == "posix")
        except OSError as exc:
            return None, "", f"[eval] cannot execute {cmd[0]}: {exc}", time.monotonic() - started, cmd
        reason = ""
        try:
            while True:
                if os.fstat(out.fileno()).st_size > max_output_bytes or os.fstat(err.fileno()).st_size > max_output_bytes:
                    reason = "output limit exceeded"
                    break
                if proc.poll() is not None:
                    break
                if time.monotonic() - started >= timeout:
                    reason = f"timeout after {timeout:g}s"
                    break
                time.sleep(.02)
        finally:
            # Also reap descendants left behind by a parent that exited normally.
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    # macOS may reject a group signal after the last member exited.
                    if proc.poll() is None:
                        proc.kill()
                        reason = reason or "process group cleanup denied"
            elif proc.poll() is None:
                proc.kill()
            proc.wait()
        out.seek(0)
        err.seek(0)
        stdout = out.read(max_output_bytes).decode("utf-8", "replace")
        stderr = err.read(max_output_bytes).decode("utf-8", "replace")
        if reason:
            stderr += f"\n[eval] {reason}"
        return (None if reason else proc.returncode), stdout, stderr, time.monotonic() - started, cmd
