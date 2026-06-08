# RTAB-Map Evaluation Platform

A standalone benchmarking platform for RTAB-Map SLAM. Automatically builds, runs, and evaluates RTAB-Map across multiple datasets with APE and RPE metrics.

## Quick Start

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Configure paths (first time only)
cp configs/default.yaml configs/user.yaml
# Edit configs/user.yaml to match your environment

# 3. Run full benchmark
python3 -m rtabmap_eval --config configs/user.yaml

# Quick test (single bag, single run)
python3 -m rtabmap_eval --quick

# Evaluate existing trajectory files only (skip SLAM run)
python3 -m rtabmap_eval.eval_only /path/to/trajectory.tum --gt /path/to/gt.tum

# 4. View results
cat results/<timestamp>/results.csv
```

## Configuration

All paths and parameters are configured via YAML files. See `configs/default.yaml` for the full schema.

Key settings:
- `rtabmap.source_dir` — RTAB-Map source code (git repo)
- `rtabmap.ros_source_dir` — rtabmap_ros source code (git repo)
- `rtabmap.build_dir` — colcon build directory
- `paths.bag_dir` — root directory containing bag folders
- `paths.gt_dir` — root directory containing ground truth `.tum` files
- `paths.launch_file` — ROS2 launch file to use
- `bag_mapping` — maps bag folder names to GT file prefixes
- `eval.runs_per_bag` — number of repeated runs per dataset (default 3)

## Project Structure

```
rtabmap_eval/
  rtabmap_eval/          Python package
    __init__.py
    config.py            Configuration loading & validation
    runner.py            SLAM execution (build, launch, play, record)
    evaluator.py         Trajectory evaluation (APE, RPE via evo)
    benchmark.py         Orchestration & reporting
    utils.py             Process management, helpers
  configs/
    default.yaml         Default configuration with all fields
  hooks/
    pre-commit           Git hook for auto-eval on commit
  templates/
    rtabmap.launch.py    Example launch file
  requirements.txt       Python dependencies
  setup.py               Package installation
  README.md
```

## Evaluation Metrics

| Metric | Meaning | Lower is better |
|--------|---------|-----------------|
| APE RMSE | Global trajectory accuracy | Yes |
| APE Mean | Average absolute pose error | Yes |
| RPE Trans RMSE | Per-frame translation drift | Yes |
| RPE Rot RMSE | Per-frame rotation drift (deg) | Yes |

## CLI Reference

```bash
# Full benchmark
python3 -m rtabmap_eval --config my_config.yaml --runs 5 --clean

# Quick mode
python3 -m rtabmap_eval --quick

# Specify bags
python3 -m rtabmap_eval --bags "bag_20260527_160436,bag_20260527_164443"

# Skip build step
python3 -m rtabmap_eval --skip-build

# Pre-commit hook evaluation
python3 -m rtabmap_eval.eval_only --gt gt.tum trajectory.tum
```
