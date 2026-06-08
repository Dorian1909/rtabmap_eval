"""Utility functions: process management, file helpers."""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import List


def kill_processes(patterns: List[str], my_pid: int = None):
    """Kill all processes matching any of the given pgrep patterns."""
    if my_pid is None:
        my_pid = os.getpid()
    for pattern in patterns:
        try:
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True, text=True
            )
            pids = [p for p in result.stdout.strip().split('\n')
                    if p and p != str(my_pid)]
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        except Exception:
            pass
    time.sleep(2)


def source_ros_cmd(build_dir: Path = None) -> str:
    """Return a shell snippet to source ROS2 + colcon workspace."""
    cmd = "source /opt/ros/humble/setup.bash"
    if build_dir:
        cmd += f" && source {build_dir}/install/setup.bash"
    return cmd


def build_colcon(build_dir: Path) -> bool:
    """Run colcon build and return True on success."""
    result = subprocess.run(
        ["colcon", "build", "--symlink-install",
         "--cmake-args", "-DCMAKE_BUILD_TYPE=Release"],
        cwd=str(build_dir),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[BUILD FAILED]\n{result.stderr[-800:]}")
        return False
    return True


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
    """Start a background进程, redirecting stdout/stderr to log_file."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.Popen(
        ["bash", "-c", cmd],
        env=run_env,
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        cwd=cwd,
        preexec_fn=os.setsid,
    )


def terminate_process(proc: subprocess.Popen, timeout: float = 5):
    """Gracefully terminate a process group, then kill if needed."""
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
