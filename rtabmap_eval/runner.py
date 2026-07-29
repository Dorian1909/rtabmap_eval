"""SLAM runner: launch RTAB-Map, launch eval, wait for trajectory."""

import subprocess
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .utils import (
    launch_process,
    terminate_process,
)


def _find_eval_launch() -> Optional[Path]:
    """Locate eval.launch.py.

    Resolution order:
      1. colcon install: <prefix>/share/rtabmap_eval/launch/eval.launch.py
         (picked up via ament_index when this package is built with colcon)
      2. Editable/source install: <repo>/scripts/eval.launch.py
      3. Wheel install fallbacks inside the package tree.
    """
    try:
        from ament_index_python.packages import get_package_share_directory
        share = Path(get_package_share_directory('rtabmap_eval'))
        candidate = share / 'launch' / 'eval.launch.py'
        if candidate.exists():
            return candidate
    except Exception:
        pass

    candidates = [
        # Editable install: <repo>/rtabmap_eval/scripts/eval.launch.py
        Path(__file__).parent.parent / "scripts" / "eval.launch.py",
        # Wheel install: package data shipped inside the package
        Path(__file__).parent / "scripts" / "eval.launch.py",
        Path(__file__).parent / "eval.launch.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


_EVAL_LAUNCH = _find_eval_launch()


def run_single_bag(cfg: Config, bag_name: str, run_idx: int,
                   output_dir: Path, clean_db: bool) -> Optional[Path]:
    """
    Execute one SLAM run for a single bag.

    Returns the trajectory.tum file path on success, None on failure.
    """
    if _EVAL_LAUNCH is None:
        print("  [ERROR] eval.launch.py not found (looked in source tree and package)")
        return None

    bag_dir = cfg.bag_dir / bag_name
    gt_file = cfg.get_gt_file(bag_name)

    if not bag_dir.exists():
        print(f"  [SKIP] Bag directory not found: {bag_dir}")
        return None
    if gt_file is None:
        print(f"  [SKIP] No ground truth for: {bag_name}")
        return None

    # Clean database
    if clean_db:
        db = cfg.db_path
        if db.exists():
            db.unlink()

    # Prepare environment
    env = cfg.env_overrides.copy()
    # Remove LIBGL_ALWAYS_INDIRECT for headless
    env.pop("LIBGL_ALWAYS_INDIRECT", None)

    # Log directory for this run
    log_dir = output_dir / bag_name / f"run_{run_idx}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Trajectory output path (passed to eval.launch via traj_file argument)
    traj_file = log_dir / "trajectory.tum"

    # 1. Launch RTAB-Map (user-provided launch command)
    print(f"  Launching RTAB-Map...")
    rtabmap_cmd = cfg.launch_cmd
    rtabmap_proc = launch_process(
        rtabmap_cmd,
        log_file=log_dir / "rtabmap.log",
        env=env,
    )
    time.sleep(cfg.startup_wait)

    # 2. Launch eval-side: auxiliary nodes + TF recorder + bag playback.
    # Quote all paths so spaces in bag_dir / traj_file / launch path don't
    # break the shell command. Robot-specific eval_launch config is appended
    # as key:=value launch arguments.
    print(f"  Launching eval (bag: {bag_name}, run {run_idx})...")
    eval_cmd = (
        f'ros2 launch "{_EVAL_LAUNCH}" '
        f'bag_path:="{bag_dir}" '
        f'traj_file:="{traj_file}" '
        f'record_rate:="{cfg.record_rate}"'
    )
    for k, v in cfg.eval_launch_args().items():
        eval_cmd += f' {k}:="{v}"'
    eval_proc = launch_process(
        eval_cmd,
        log_file=log_dir / "eval.log",
        env=env,
    )

    # 3. Wait for eval.launch to exit (it exits when bag play finishes).
    # On timeout, skip the post-playback shutdown_wait — RTAB-Map is already
    # suspected stuck, no point waiting further.
    timed_out = False
    try:
        eval_proc.wait(timeout=cfg.playback_timeout)
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Eval launch timed out after {cfg.playback_timeout}s")
        terminate_process(eval_proc, timeout=5)
        timed_out = True

    if not timed_out:
        time.sleep(cfg.shutdown_wait)

    # 4. Stop RTAB-Map launch
    terminate_process(rtabmap_proc, timeout=10)

    # 5. Verify trajectory
    if not traj_file.exists() or traj_file.stat().st_size == 0:
        print(f"  [ERROR] Empty trajectory: {traj_file}")
        return None

    lines = traj_file.read_text().strip().split('\n')
    print(f"  Trajectory: {len(lines)} poses saved")
    return traj_file
