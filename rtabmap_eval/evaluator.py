"""Trajectory evaluation using evo: APE and RPE metrics."""

import subprocess
from pathlib import Path
from typing import Dict, Optional

from .config import Config


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
    try:
        result = subprocess.run(
            ["evo_ape", "tum", str(gt_file), str(traj_file),
             "-a", "--t_max_diff", t_max_diff],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2:
                key, val = parts[0], parts[1]
                mapping = {
                    'rmse': 'ape_rmse', 'mean': 'ape_mean',
                    'median': 'ape_median', 'max': 'ape_max',
                    'min': 'ape_min', 'std': 'ape_std', 'sse': 'ape_sse',
                }
                if key in mapping:
                    try:
                        metrics[mapping[key]] = float(val)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"  [WARN] APE evaluation failed: {e}")

    # --- RPE translation ---
    try:
        result = subprocess.run(
            ["evo_rpe", "tum", str(gt_file), str(traj_file),
             "-r", "trans_part",
             "-d", rpe_delta, "-u", rpe_unit,
             "--delta_tol", "0.5", "--t_max_diff", t_max_diff],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2:
                key, val = parts[0], parts[1]
                mapping = {
                    'rmse': 'rpe_trans_rmse', 'mean': 'rpe_trans_mean',
                    'median': 'rpe_trans_median', 'max': 'rpe_trans_max',
                }
                if key in mapping:
                    try:
                        metrics[mapping[key]] = float(val)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"  [WARN] RPE (trans) evaluation failed: {e}")

    # --- RPE rotation (degrees) ---
    try:
        result = subprocess.run(
            ["evo_rpe", "tum", str(gt_file), str(traj_file),
             "-r", "angle_deg",
             "-d", rpe_delta, "-u", rpe_unit,
             "--delta_tol", "0.5", "--t_max_diff", t_max_diff],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split('\n'):
            parts = line.strip().split()
            if len(parts) >= 2:
                key, val = parts[0], parts[1]
                mapping = {
                    'rmse': 'rpe_rot_rmse', 'mean': 'rpe_rot_mean',
                    'median': 'rpe_rot_median', 'max': 'rpe_rot_max',
                }
                if key in mapping:
                    try:
                        metrics[mapping[key]] = float(val)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"  [WARN] RPE (rot) evaluation failed: {e}")

    return metrics if metrics else None
