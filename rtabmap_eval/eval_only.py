"""Standalone trajectory evaluator (no SLAM run required).

Usage:
    python3 -m rtabmap_eval.eval_only <trajectory.tum> [--gt <gt.tum>]
    python3 -m rtabmap_eval.eval_only traj1.tum traj2.tum ...
"""

import argparse
import subprocess
import sys
from pathlib import Path


def find_gt_for_traj(traj_file: Path):
    """Try to infer GT file from trajectory path using config mapping."""
    config_dir = Path(__file__).parent.parent / "configs"
    try:
        import yaml
        with open(config_dir / "default.yaml") as f:
            cfg = yaml.safe_load(f)
        bag_mapping = cfg.get("bag_mapping", {})
        gt_dir = Path(cfg["paths"]["gt_dir"])

        for bag_name, prefix in bag_mapping.items():
            if bag_name in str(traj_file):
                gt_file = gt_dir / f"{prefix}_gt.tum"
                if gt_file.exists():
                    return gt_file
    except Exception:
        pass
    return None


def eval_single(traj_file: Path, gt_file: Path):
    """Evaluate and print APE + RPE for a single trajectory."""
    print(f"\n{'='*60}")
    print(f"Trajectory: {traj_file}")
    print(f"Ground truth: {gt_file}")
    print(f"{'='*60}")

    # APE
    print("\n--- APE (Absolute Pose Error) ---")
    result = subprocess.run(
        ["evo_ape", "tum", str(gt_file), str(traj_file),
         "-a", "--t_max_diff", "0.5"],
        capture_output=True, text=True
    )
    print(result.stdout)

    # RPE translation
    print("--- RPE Translation (1-frame delta) ---")
    result = subprocess.run(
        ["evo_rpe", "tum", str(gt_file), str(traj_file),
         "-r", "trans_part", "-d", "1", "-u", "f",
         "--delta_tol", "0.5", "--t_max_diff", "0.5"],
        capture_output=True, text=True
    )
    print(result.stdout)

    # RPE rotation
    print("--- RPE Rotation (1-frame delta, degrees) ---")
    result = subprocess.run(
        ["evo_rpe", "tum", str(gt_file), str(traj_file),
         "-r", "angle_deg", "-d", "1", "-u", "f",
         "--delta_tol", "0.5", "--t_max_diff", "0.5"],
        capture_output=True, text=True
    )
    print(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Evaluate trajectory files (no SLAM run)")
    parser.add_argument("trajectories", nargs='+', help="trajectory .tum files")
    parser.add_argument("--gt", type=str, default=None, help="ground truth .tum file")
    args = parser.parse_args()

    gt_override = Path(args.gt) if args.gt else None

    for traj_path in args.trajectories:
        traj_file = Path(traj_path)
        if not traj_file.exists():
            print(f"[SKIP] Not found: {traj_file}")
            continue

        gt_file = gt_override
        if gt_file is None:
            gt_file = find_gt_for_traj(traj_file)
        if gt_file is None or not gt_file.exists():
            print(f"[ERROR] GT not found for {traj_file}. Use --gt <path>")
            continue

        eval_single(traj_file, gt_file)


if __name__ == "__main__":
    main()
