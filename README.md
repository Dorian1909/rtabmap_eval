# RTAB-Map Evaluation Platform

A standalone benchmarking platform for RTAB-Map SLAM. Automatically builds, runs, and evaluates RTAB-Map across multiple datasets, collecting APE (absolute pose error) and RPE (relative pose error) metrics. Works on x86_64 and ARM64 with any ROS2 distribution.

## Features

- **Full pipeline automation**: build → launch → bag playback → trajectory recording → evaluation
- **Multi-dataset, multi-run**: evaluate all 11 datasets with N repeated runs each
- **APE + RPE metrics**: global accuracy and local drift, translation and rotation
- **Cross-platform**: x86_64 / ARM64, any ROS2 distro (humble, jazzy, rolling...)
- **YAML configuration**: all paths and parameters in one file, easy to version-control
- **CSV + JSON output**: structured results for downstream analysis
- **Quick mode**: fast single-bag verification

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Dorian1909/rtabmap_eval.git
cd rtabmap_eval

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Configure paths (first time only)
cp configs/default.yaml configs/user.yaml
# Edit configs/user.yaml — set your rtabmap source, build dir, bag dir, GT dir, launch file

# 4. Run full benchmark (11 bags × 3 runs each ≈ 100 min)
python3 -m rtabmap_eval

# Or quick test (1 bag × 1 run ≈ 3 min)
python3 -m rtabmap_eval --quick
```

## Configuration

All settings live in YAML config files. Copy `configs/default.yaml` to `configs/user.yaml` and modify — user config overrides defaults.

### Minimal user.yaml example

```yaml
rtabmap:
  source_dir: /home/user/rtabmap
  build_dir: /home/user/catkin_ws
  db_path: ~/.ros/rtabmap.db

ros:
  distro: jazzy          # your ROS2 distro

paths:
  bag_dir: /data/bags
  gt_dir: /data/ground_truth
  launch_file: /home/user/rtabmap.launch.py
  record_script: /home/user/record_tf_trajectory.py

bag_mapping:
  bag_20260527_160436: "05271604"
  bag_20260527_163821: "05271638"
  # ... add all your bag -> GT prefix mappings
```

### Full config schema

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `ros` | `distro` | string | `humble` | ROS2 distribution name |
| `ros` | `setup_bash` | path | auto | Override path to setup.bash (auto-derived from distro if not set) |
| `rtabmap` | `source_dir` | path | required | RTAB-Map git repo (contains corelib/) |
| `rtabmap` | `ros_source_dir` | path | auto | rtabmap_ros git repo (auto-derived if not set) |
| `rtabmap` | `build_dir` | path | required | colcon workspace root (contains install/ and build/) |
| `rtabmap` | `db_path` | path | `~/.ros/rtabmap.db` | RTAB-Map database file (deleted with `--clean`) |
| `paths` | `bag_dir` | path | required | Root directory containing bag subfolders |
| `paths` | `gt_dir` | path | required | Root directory containing `_gt.tum` ground truth files |
| `paths` | `launch_file` | path | required | ROS2 launch file for SLAM |
| `paths` | `record_script` | path | required | Python TF→TUM trajectory recorder |
| `bag_mapping` | *(key-value)* | string | required | Maps bag folder name → GT filename prefix |
| `eval` | `runs_per_bag` | int | `3` | Number of repeated runs per bag |
| `eval` | `startup_wait_s` | float | `10` | Seconds to wait after launch before playing bag |
| `eval` | `shutdown_wait_s` | float | `5` | Seconds to wait after bag ends before stopping |
| `eval` | `record_rate_hz` | float | `20` | TF recording frequency |
| `eval` | `playback_timeout_s` | int | `600` | Max seconds per bag playback (safety cutoff) |
| `evo` | `t_max_diff` | float | `0.5` | Max timestamp difference for trajectory alignment |
| `evo` | `rpe_delta` | int | `1` | Frame interval for relative pose error |
| `evo` | `rpe_delta_unit` | enum | `f` | RPE delta unit: `f`=frames, `d`=distance, `r`=rotations |
| `kill_patterns` | | list | [...] | Process name patterns to clean up between runs |
| `env` | | dict | {...} | Environment variable overrides (OpenGL, etc.) |

## Evaluation Metrics

All metrics are computed by [evo](https://github.com/MichaelGrupp/evo).

### APE — Absolute Pose Error

Measures global trajectory accuracy. For each timestamp, compute the Euclidean distance between the estimated pose and the aligned ground truth pose.

| Metric | Meaning |
|--------|---------|
| **APE RMSE** | Root mean square of all pose errors — primary accuracy indicator |
| APE Mean | Average absolute pose error |
| APE Median | Median pose error (robust to outliers) |
| APE Max | Worst single-frame error |
| APE Std | Standard deviation of errors |

### RPE — Relative Pose Error

Measures local consistency (drift per frame). For each pair of frames separated by `delta`, compute the difference between estimated and ground-truth relative motion.

| Metric | Meaning |
|--------|---------|
| **RPE Trans RMSE** | Translation drift per frame (m/frame) |
| RPE Trans Mean | Average translation drift |
| RPE Rot RMSE | Rotation drift per frame (deg/frame) |
| RPE Rot Mean | Average rotation drift |

Lower is better for all metrics. APE reflects global drift correction quality; RPE reflects odometry/local matching quality.

## Output

Results are saved to a timestamped directory (default: `/tmp/rtabmap_benchmark_YYYYMMDD_HHMMSS/`).

### Directory structure

```
rtabmap_benchmark_20260608_115040/
  meta.json                                    # Run metadata (git commit, config, etc.)
  results.csv                                  # All runs in one CSV
  bag_20260527_160436/
    run_1/
      trajectory.tum                           # SLAM output trajectory
      rtabmap.log                              # Full RTAB-Map console log
      tf_recorder.log                          # TF recorder log
    run_2/
      ...
    run_3/
      ...
  bag_20260527_163821/
    ...
```

### results.csv columns

```
bag, run, run_time_s, traj_file,
ape_max, ape_mean, ape_median, ape_min, ape_rmse, ape_sse, ape_std,
rpe_trans_max, rpe_trans_mean, rpe_trans_median, rpe_trans_rmse,
rpe_rot_max, rpe_rot_mean, rpe_rot_median, rpe_rot_rmse
```

### results.csv example

```csv
bag,run,run_time_s,traj_file,ape_max,ape_mean,ape_median,ape_min,ape_rmse,ape_sse,ape_std,rpe_trans_max,rpe_trans_mean,rpe_trans_median,rpe_trans_rmse,rpe_rot_max,rpe_rot_mean,rpe_rot_median,rpe_rot_rmse
bag_20260527_160436,1,185.1,/tmp/.../trajectory.tum,0.509181,0.317285,0.330553,0.049187,0.328917,17.634359,0.086699,6.6395,2.987459,3.509348,3.316322,60.38681,15.449988,10.600897,21.58995
bag_20260527_160436,2,183.5,/tmp/.../trajectory.tum,0.523122,0.325694,0.334933,0.053197,0.338205,18.758801,0.091140,6.5547,2.970283,3.498692,3.306028,61.22340,15.350056,10.596675,21.521104
bag_20260527_160436,3,187.2,/tmp/.../trajectory.tum,0.498765,0.310452,0.328714,0.047231,0.322156,16.901234,0.083427,6.7123,3.012876,3.520187,3.342110,59.87654,15.567123,10.612456,21.654321
```

### Console output example

```
============================================================
RTAB-Map Evaluation Platform
============================================================
Datasets:  11
Runs each: 3
Output:    /tmp/rtabmap_benchmark_20260608_143022

[BUILD] Compiling RTAB-Map...
[BUILD] Done.

[1/33] bag_20260527_160436 — run 1/3
  Playing bag_20260527_160436 (run 1)...
  Elapsed: 185s
  APE RMSE: 0.3289m | RPE trans: 3.3163m | RPE rot: 21.59deg

[2/33] bag_20260527_160436 — run 2/3
  ...

=====================================================================================
Evaluation Summary
=====================================================================================
Bag                            APE RMSE   APE Mean  RPE T RMSE  RPE R RMSE  Runs
-------------------------------------------------------------------------------------
160436                           0.3297     0.3178      3.3215       21.59     3
163821                           0.3512     0.3389      3.2847       20.83     3
164108                           0.3425     0.3301      3.4102       22.14     3
164443                           0.3189     0.3047      3.1523       19.76     3
164810                           0.3654     0.3521      3.5234       23.41     3
165435                           0.3378     0.3245      3.3987       21.88     3
170516                           0.3892     0.3768      3.6105       24.52     3
171004                           0.4015     0.3892      3.7821       25.13     3
171537                           0.3265     0.3134      3.2678       20.45     3
172146                           0.3142     0.3013      3.1234       19.34     3
172930                           0.3489     0.3367      3.4523       22.67     3
-------------------------------------------------------------------------------------
Overall                          0.3481                 3.3847       21.97    33
APE range                        0.3142 ~ 0.4015
=====================================================================================

Results:  /tmp/rtabmap_benchmark_20260608_143022/results.csv
Output:   /tmp/rtabmap_benchmark_20260608_143022
```

### meta.json example

```json
{
  "timestamp": "20260608_115040",
  "bags": ["bag_20260527_160436"],
  "num_runs": 1,
  "clean_db": false,
  "skip_build": true,
  "git_commit": "a48710d5",
  "git_branch": "feature/xfeat-pydetector",
  "config": { ... }
}
```

## CLI Reference

```
python3 -m rtabmap_eval [OPTIONS]

Options:
  --config PATH        YAML config file (default: configs/default.yaml + configs/user.yaml)
  --bags "b1,b2"       Comma-separated bag names (default: all in bag_mapping)
  --runs N             Repeated runs per bag (default: from config)
  --quick              Quick mode: 1 bag, 1 run
  --skip-build         Skip colcon build step
  --clean              Delete rtabmap.db before each run
  --output DIR         Output directory (default: /tmp/rtabmap_benchmark_<timestamp>)
  -h, --help           Show help message
```

### Examples

```bash
# Full benchmark with fresh build and clean DB
python3 -m rtabmap_eval --clean

# Quick smoke test
python3 -m rtabmap_eval --quick --skip-build

# Specific bags with 5 repeated runs
python3 -m rtabmap_eval --bags "bag_20260527_160436,bag_20260527_164443" --runs 5

# Custom config for a different robot
python3 -m rtabmap_eval --config configs/robot_b.yaml

# Only evaluate existing trajectory files (skip SLAM run)
python3 -m rtabmap_eval.eval_only /tmp/rtabmap_benchmark_xxx/trajectory.tum --gt /path/to/gt.tum
```

## Platform Compatibility

| Platform | ROS2 Distro | Status |
|----------|-------------|--------|
| x86_64 (Ubuntu 22.04) | Humble | Tested |
| x86_64 (Ubuntu 24.04) | Jazzy | Compatible |
| ARM64 / aarch64 | Humble / Jazzy | Compatible |

No architecture-specific code — just Python + ROS2 CLI + evo. Configure `ros.distro` in your YAML to match your installation.

## Project Structure

```
rtabmap_eval/
  rtabmap_eval/           Python package
    __init__.py
    __main__.py           CLI entry point
    config.py             YAML config loading & validation
    runner.py             SLAM execution (build, launch, play, record)
    evaluator.py          Trajectory evaluation (APE, RPE via evo)
    benchmark.py          Orchestration & reporting
    utils.py              Process management, shell helpers
    eval_only.py          Standalone evaluator for existing trajectories
  configs/
    default.yaml          Default configuration (all fields documented)
  requirements.txt        evo, pyyaml
  setup.py                pip install -e .
  README.md
```

## Dependencies

- **ROS2** Humble or later (colcon, ros2 CLI)
- **Python 3.8+**
- **evo** `>=1.30.0` — trajectory evaluation (`pip install evo`)
- **PyYAML** — config loading (`pip install pyyaml`)
- RTAB-Map compiled with ROS2 support in a colcon workspace
