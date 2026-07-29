"""Benchmark orchestration: coordinate runs, evaluations, and reporting."""

import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config
from .evaluator import evaluate_trajectory
from .runner import run_single_bag


def run_benchmark(cfg: Config, bags: List[str], num_runs: int,
                  clean_db: bool,
                  output_dir: Optional[Path] = None) -> None:
    """Run the full benchmark pipeline."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_dir is None:
        output_dir = Path(f"/tmp/rtabmap_benchmark_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("RTAB-Map Evaluation Platform")
    print("=" * 60)
    print(f"Datasets:  {len(bags)}")
    print(f"Runs each: {num_runs}")
    print(f"Output:    {output_dir}")
    print()

    # Save metadata
    meta = {
        "timestamp": timestamp,
        "bags": bags,
        "num_runs": num_runs,
        "clean_db": clean_db,
        "config": cfg.to_dict(),
    }
    (output_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str))

    # Run all bags
    all_results: List[Dict] = []
    total = len(bags) * num_runs
    current = 0

    for bag_name in bags:
        for run_idx in range(1, num_runs + 1):
            current += 1
            print(f"\n[{current}/{total}] {bag_name} — run {run_idx}/{num_runs}")

            t0 = time.time()
            traj_file = run_single_bag(cfg, bag_name, run_idx, output_dir, clean_db)
            elapsed = time.time() - t0
            print(f"  Elapsed: {elapsed:.0f}s")

            if traj_file is None:
                continue

            gt_file = cfg.get_gt_file(bag_name)
            if gt_file is None:
                continue

            metrics = evaluate_trajectory(traj_file, gt_file, cfg)
            if metrics:
                result = {
                    "bag": bag_name,
                    "run": run_idx,
                    "run_time_s": round(elapsed, 1),
                    "traj_file": str(traj_file),
                    **metrics,
                }
                all_results.append(result)

                ape = metrics.get('ape_rmse', -1)
                rpe_t = metrics.get('rpe_trans_rmse', -1)
                rpe_r = metrics.get('rpe_rot_rmse', -1)
                print(f"  APE RMSE: {ape:.4f}m | RPE trans: {rpe_t:.4f}m | RPE rot: {rpe_r:.2f}deg")

    if not all_results:
        print("\n[WARN] No valid results collected.")
        return

    # Save CSV
    _save_csv(all_results, output_dir / "results.csv")

    # Print summary
    _print_summary(all_results)

    print(f"\nResults:  {output_dir / 'results.csv'}")
    print(f"Output:   {output_dir}")


def _save_csv(results: List[Dict], path: Path) -> None:
    fieldnames = list(results[0].keys())
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def _print_summary(results: List[Dict]) -> None:
    print("\n" + "=" * 85)
    print("Evaluation Summary")
    print("=" * 85)

    # Group by bag
    by_bag: Dict[str, List[Dict]] = {}
    for r in results:
        by_bag.setdefault(r['bag'], []).append(r)

    hdr = (f"{'Bag':<28} {'APE RMSE':>10} {'APE Mean':>10}"
           f" {'RPE T RMSE':>11} {'RPE R RMSE':>11} {'Runs':>5}")
    print(hdr)
    print("-" * 85)

    all_ape, all_rpe_t, all_rpe_r = [], [], []

    for bag_name in sorted(by_bag.keys()):
        runs = by_bag[bag_name]
        apes = [r['ape_rmse'] for r in runs if 'ape_rmse' in r]
        ape_means = [r['ape_mean'] for r in runs if 'ape_mean' in r]
        rpe_ts = [r['rpe_trans_rmse'] for r in runs if 'rpe_trans_rmse' in r]
        rpe_rs = [r['rpe_rot_rmse'] for r in runs if 'rpe_rot_rmse' in r]

        a = _avg(apes)
        am = _avg(ape_means)
        rt = _avg(rpe_ts)
        rr = _avg(rpe_rs)

        all_ape.extend(apes)
        all_rpe_t.extend(rpe_ts)
        all_rpe_r.extend(rpe_rs)

        short = bag_name.replace("bag_20260527_", "")
        print(f"{short:<28} {a:>10.4f} {am:>10.4f} {rt:>11.4f} {rr:>11.2f} {len(runs):>5}")

    print("-" * 85)
    if all_ape:
        oa = _avg(all_ape)
        ot = _avg(all_rpe_t)
        orr = _avg(all_rpe_r)
        print(f"{'Overall':<28} {oa:>10.4f} {'':>10} {ot:>11.4f} {orr:>11.2f} {len(results):>5}")
        print(f"{'APE range':<28} {min(all_ape):>10.4f} ~ {max(all_ape):<8.4f}")
    print("=" * 85)


def _avg(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0
