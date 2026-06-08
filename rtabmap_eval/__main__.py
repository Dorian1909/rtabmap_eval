"""CLI entry point: python3 -m rtabmap_eval"""

import argparse
import sys
from pathlib import Path

from .config import Config
from .benchmark import run_benchmark


def main():
    parser = argparse.ArgumentParser(
        description="RTAB-Map Evaluation Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m rtabmap_eval                          # Full benchmark (11 bags × 3 runs)
  python3 -m rtabmap_eval --quick                   # Quick test (1 bag × 1 run)
  python3 -m rtabmap_eval --bags "bag1,bag2" --runs 5
  python3 -m rtabmap_eval --config my_config.yaml
  python3 -m rtabmap_eval --skip-build --clean
        """,
    )
    parser.add_argument("--config", type=str, default=None,
                        help="Path to YAML config file (default: configs/default.yaml)")
    parser.add_argument("--bags", type=str, default=None,
                        help="Comma-separated bag names to evaluate (default: all)")
    parser.add_argument("--runs", type=int, default=None,
                        help="Number of runs per bag (default: from config, usually 3)")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: single bag, single run")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip colcon build step")
    parser.add_argument("--clean", action="store_true",
                        help="Delete rtabmap.db before each run")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for results")
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config) if args.config else None
    try:
        cfg = Config.from_yaml(config_path)
    except ValueError as e:
        print(f"[CONFIG ERROR] {e}")
        sys.exit(1)

    # Determine bags
    if args.quick:
        bag_list = [sorted(cfg.bag_mapping.keys())[0]]
        num_runs = 1
        print("[QUICK] Quick mode: 1 bag, 1 run")
    elif args.bags:
        bag_list = [b.strip() for b in args.bags.split(',')]
        num_runs = args.runs or cfg.runs_per_bag
    else:
        bag_list = sorted(cfg.bag_mapping.keys())
        num_runs = args.runs or cfg.runs_per_bag

    # Validate bags
    valid = [b for b in bag_list if b in cfg.bag_mapping]
    invalid = [b for b in bag_list if b not in cfg.bag_mapping]
    if invalid:
        print(f"[WARN] Unknown bags skipped: {invalid}")
    if not valid:
        print("[ERROR] No valid bags to evaluate.")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else None
    run_benchmark(cfg, valid, num_runs, args.skip_build, args.clean, output_dir)


if __name__ == "__main__":
    main()
