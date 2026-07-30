"""Trajectory evaluation using evo: APE and RPE metrics."""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config


def _run_evo(cmd: List[str], key_mapping: Dict[str, str],
             label: str, metrics: Dict[str, float]) -> None:
    """Run one evo subprocess, parse stdout metrics, warn on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
    except Exception as e:
        print(f"  [WARN] {label} invocation failed: {e}")
        return
    if result.returncode != 0:
        # Surface genuine evo errors (bad file, no overlap, parse error)
        # instead of silently dropping the metric block.
        stderr_tail = (result.stderr or "").strip().splitlines()[-3:]
        tail = " | ".join(stderr_tail) if stderr_tail else "(no stderr)"
        print(f"  [WARN] {label} exited {result.returncode}: {tail}")
        return
    for line in result.stdout.split('\n'):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] in key_mapping:
            try:
                metrics[key_mapping[parts[0]]] = float(parts[1])
            except ValueError:
                pass


def evaluate_trajectory(traj_file: Path, gt_file: Path,
                        cfg: Config) -> Optional[Dict[str, float]]:
    """
    Evaluate a single trajectory against ground truth.

    Returns dict with metric names and values, or None on failure.
    """
    metrics: Dict[str, float] = {}
    t_max_diff = str(cfg.evo_t_max_diff)
    rpe_delta = str(cfg.evo_rpe_delta)
    rpe_unit = cfg.evo_rpe_delta_unit

    # --- APE ---
    _run_evo(
        ["evo_ape", "tum", str(gt_file), str(traj_file),
         "-a", "--t_max_diff", t_max_diff],
        {'rmse': 'ape_rmse', 'mean': 'ape_mean',
         'median': 'ape_median', 'max': 'ape_max',
         'min': 'ape_min', 'std': 'ape_std', 'sse': 'ape_sse'},
        "evo_ape", metrics,
    )

    # --- RPE translation ---
    _run_evo(
        ["evo_rpe", "tum", str(gt_file), str(traj_file),
         "-r", "trans_part",
         "-d", rpe_delta, "-u", rpe_unit,
         "--delta_tol", "0.5", "--t_max_diff", t_max_diff],
        {'rmse': 'rpe_trans_rmse', 'mean': 'rpe_trans_mean',
         'median': 'rpe_trans_median', 'max': 'rpe_trans_max'},
        "evo_rpe(trans)", metrics,
    )

    # --- RPE rotation (degrees) ---
    _run_evo(
        ["evo_rpe", "tum", str(gt_file), str(traj_file),
         "-r", "angle_deg",
         "-d", rpe_delta, "-u", rpe_unit,
         "--delta_tol", "0.5", "--t_max_diff", t_max_diff],
        {'rmse': 'rpe_rot_rmse', 'mean': 'rpe_rot_mean',
         'median': 'rpe_rot_median', 'max': 'rpe_rot_max'},
        "evo_rpe(rot)", metrics,
    )

    return metrics if metrics else None
