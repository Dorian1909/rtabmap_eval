"""Utility functions: process management, file helpers."""

import os
import signal
import subprocess
from pathlib import Path


def run_shell(cmd: str, env: dict = None, timeout: float = None,
              capture: bool = True, cwd: str = None) -> subprocess.CompletedProcess:
    """Run a bash command with optional timeout and env overrides."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", "-c", cmd],
        env=run_env,
        capture_output=capture,
        text=capture,
        timeout=timeout,
        cwd=cwd,
    )


def launch_process(cmd: str, log_file: Path, env: dict = None,
                   cwd: str = None) -> subprocess.Popen:
    """Start a background process, redirecting stdout/stderr to log_file.

    The log file handle is attached to the returned Popen as `_log_fh` so
    its lifetime is bound to the process — closing/terminating the process
    releases the handle, avoiding fd leaks.
    """
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    log_fh = open(log_file, "w")
    proc = subprocess.Popen(
        ["bash", "-c", cmd],
        env=run_env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        preexec_fn=os.setsid,
    )
    proc._log_fh = log_fh  # keep the handle alive until proc is gone
    return proc


def terminate_process(proc: subprocess.Popen, timeout: float = 5):
    """Gracefully terminate a process group, then kill if needed.

    Also closes the log file handle attached by `launch_process`.
    """
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            pass
    except Exception:
        pass
    finally:
        log_fh = getattr(proc, "_log_fh", None)
        if log_fh is not None and not log_fh.closed:
            try:
                log_fh.close()
            except Exception:
                pass
