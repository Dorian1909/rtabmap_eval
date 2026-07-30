"""SLAM runner: launch RTAB-Map, launch eval, wait for trajectory."""

import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

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


def _bag_duration_seconds(bag_dir: Path) -> Optional[float]:
    """Return bag duration in seconds from metadata.yaml, or None if unavailable."""
    meta = bag_dir / "metadata.yaml"
    if not meta.exists():
        return None
    try:
        data = yaml.safe_load(meta.read_text())
        ns = data["rosbag2_bagfile_information"]["duration"]["nanoseconds"]
        return float(ns) * 1e-9
    except Exception:
        return None


def _gt_duration_seconds(gt_file: Path) -> Optional[float]:
    """Return GT trajectory time span (last - first timestamp) in seconds, or None."""
    try:
        lines = gt_file.read_text().strip().split('\n')
        if len(lines) < 2:
            return None
        t0 = float(lines[0].split()[0])
        t1 = float(lines[-1].split()[0])
        span = abs(t1 - t0)
        return span if span > 0 else None
    except Exception:
        return None


def _validate_trajectory(
    traj_file: Path,
    cfg: Config,
    bag_dir: Path,
    gt_file: Optional[Path],
) -> Tuple[bool, str, int]:
    """
    Reject degenerate SLAM output (broken TF, truncated/stationary trajectory).

    Returns (ok, reason, n_poses). When ok is False, reason is a human-readable
    string for the log line; when ok is True, reason is empty.
    """
    ts: List[float] = []
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    try:
        lines = traj_file.read_text().strip().split('\n')
    except Exception:
        return False, "trajectory file unreadable", 0

    for line in lines:
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            ts.append(float(parts[0]))
            xs.append(float(parts[1]))
            ys.append(float(parts[2]))
            zs.append(float(parts[3]))
        except ValueError:
            continue

    n = len(ts)
    if n == 0:
        return False, "no parseable poses", 0

    # 1. Pose count
    min_poses = cfg.validity_min_poses
    if min_poses > 0 and n < min_poses:
        return False, f"only {n} poses (min {min_poses})", n

    # 2. Time coverage
    min_cov = cfg.validity_min_coverage
    if min_cov > 0:
        traj_span = max(ts) - min(ts)
        expected = _bag_duration_seconds(bag_dir)
        if expected is None and gt_file is not None:
            expected = _gt_duration_seconds(gt_file)
        if expected and expected > 0:
            required = expected * min_cov - cfg.validity_span_tolerance_s
            if traj_span < required:
                pct = traj_span / expected * 100
                return (False,
                        f"covers {traj_span:.1f}s of {expected:.1f}s "
                        f"({pct:.0f}%, need {min_cov*100:.0f}%)", n)

    # 3. Stationary / extent
    min_extent = cfg.validity_min_extent_m
    if min_extent > 0:
        extent = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        if extent < min_extent:
            return (False,
                    f"stationary, extent {extent*1000:.1f}mm < "
                    f"{min_extent*1000:.1f}mm", n)

    return True, "", n


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

    ok, reason, n_poses = _validate_trajectory(traj_file, cfg, bag_dir, gt_file)
    if not ok:
        print(f"  [FAIL] trajectory degenerate: {reason}")
        return None

    print(f"  Trajectory: {n_poses} poses saved")
    return traj_file
