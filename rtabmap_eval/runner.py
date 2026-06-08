"""SLAM runner: build, launch, record, play bag, collect trajectory."""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .utils import (
    build_colcon,
    kill_processes,
    launch_process,
    run_shell,
    source_ros_cmd,
    terminate_process,
)


def run_single_bag(cfg: Config, bag_name: str, run_idx: int,
                   output_dir: Path, clean_db: bool) -> Optional[Path]:
    """
    Execute one SLAM run for a single bag.

    Returns the trajectory.tum file path on success, None on failure.
    """
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

    # Kill residual processes
    kill_processes(cfg.kill_patterns)

    # Prepare environment
    env = cfg.env_overrides.copy()
    # Remove LIBGL_ALWAYS_INDIRECT for headless
    env.pop("LIBGL_ALWAYS_INDIRECT", None)
    src = source_ros_cmd(cfg.build_dir, cfg.ros_setup_bash)

    # Log directory for this run
    log_dir = output_dir / bag_name / f"run_{run_idx}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 1. Launch RTAB-Map
    print(f"  Launching RTAB-Map...")
    launch_cmd = f"{src} && ros2 launch {cfg.launch_file}"
    launch_proc = launch_process(
        launch_cmd,
        log_file=log_dir / "rtabmap.log",
        env=env,
    )
    time.sleep(cfg.startup_wait)

    # 2. Start TF recorder
    traj_file = log_dir / "trajectory.tum"
    tf_cmd = f"python3 {cfg.record_script} {traj_file} {cfg.record_rate}"
    tf_proc = launch_process(
        tf_cmd,
        log_file=log_dir / "tf_recorder.log",
        env=env,
    )
    time.sleep(2)

    # 3. Play bag
    print(f"  Playing {bag_name} (run {run_idx})...")
    play_cmd = f"{src} && ros2 bag play {bag_dir} --clock"
    try:
        play_result = run_shell(
            play_cmd, env=env, timeout=cfg.playback_timeout
        )
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Bag playback timed out after {cfg.playback_timeout}s")

    time.sleep(cfg.shutdown_wait)

    # 4. Stop TF recorder
    tf_proc.terminate()
    try:
        tf_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        tf_proc.kill()

    # 5. Stop RTAB-Map
    terminate_process(launch_proc, timeout=10)
    kill_processes(cfg.kill_patterns)

    # 6. Verify trajectory
    if not traj_file.exists() or traj_file.stat().st_size == 0:
        print(f"  [ERROR] Empty trajectory: {traj_file}")
        return None

    lines = traj_file.read_text().strip().split('\n')
    print(f"  Trajectory: {len(lines)} poses saved")
    return traj_file


def build(cfg: Config) -> bool:
    """Build RTAB-Map via colcon. Returns True on success."""
    return build_colcon(cfg.build_dir)
