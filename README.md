# RTAB-Map 评测平台

RTAB-Map SLAM 的独立基准评测平台。自动完成编译、运行、评测全流程，支持多数据集多次重复运行，输出 APE（绝对位姿误差）和 RPE（相对位姿误差）指标。兼容 x86_64 和 ARM64 架构，支持任意 ROS2 发行版。

## 功能特点

- **全流程自动化**：启动 → 播包 → 录制轨迹 → 评测，一键完成
- **多数据集多次运行**：支持 11 个数据集 × N 次重复运行，统计均值和稳定性
- **APE + RPE 指标**：全局精度和局部漂移，平移和旋转分别评估
- **跨平台**：x86_64 / ARM64 通用，支持 humble、jazzy、rolling 等任意 ROS2 发行版
- **YAML 配置**：路径和参数集中管理，方便版本控制
- **结构化输出**：CSV + JSON 格式，便于后续分析
- **快速模式**：単数据集単次运行，3 分钟快速验证

## 快速开始

```bash
# 1. 克隆到 colcon workspace 的 src/ 下
cd <your_colcon_ws>/src
git clone https://github.com/D-Robotics/rtabmap_eval.git

# 2. 安装 Python 依赖
pip3 install -r rtabmap_eval/requirements.txt

# 3. colcon 编译
cd <your_colcon_ws>
colcon build --packages-select rtabmap_eval

# 4. 配置路径（首次使用）
cp src/rtabmap_eval/configs/default.yaml src/rtabmap_eval/configs/user.yaml
# 编辑 user.yaml，填写 bag 路径、真值路径

# 5. source ROS2 与本 workspace（每次新终端）
source /opt/ros/<distro>/setup.bash
source <your_colcon_ws>/install/setup.bash

# 6. 全量评测（11 bags × 3 runs ≈ 100 分钟）
python3 -m rtabmap_eval

# 或快速验证（1 bag × 1 run ≈ 3 分钟）
python3 -m rtabmap_eval --quick
```

## 配置说明

所有配置通过 YAML 文件管理。将 `configs/default.yaml` 复制为 `configs/user.yaml` 并修改，用户配置会覆盖默认值。

### 最小 user.yaml 示例

```yaml
paths:
  bag_dir: /data/bags
  gt_dir: /data/ground_truth
  launch_cmd: ros2 launch rtabmap.launch.py

bag_mapping:
  bag_20260527_160436: "05271604"
  bag_20260527_163821: "05271638"
  # ... 添加所有 bag → 真值前缀的映射
```

### 完整配置字段

| 分组 | 字段 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| *(顶层)* | `db_path` | path | `~/.ros/rtabmap.db` | RTAB-Map 数据库路径,`--clean` 时删除 |
| `paths` | `bag_dir` | path | 必填 | 存放 bag 子目录的根目录 |
| `paths` | `gt_dir` | path | 必填 | 存放 `_gt.tum` 真值文件的根目录 |
| `paths` | `launch_cmd` | string | 必填 | 用户 RTAB-Map 启动命令行（支持传任意 launch 参数） |
| `bag_mapping` | *(键值对)* | string | 必填 | bag 文件夹名 → 真值文件前缀的映射 |
| `eval` | `runs_per_bag` | int | `3` | 每个 bag 重复运行次数 |
| `eval` | `startup_wait_s` | float | `10` | 启动后等待 RTAB-Map 就绪的秒数 |
| `eval` | `shutdown_wait_s` | float | `5` | bag 播放结束后等待 RTAB-Map 处理完毕的秒数 |
| `eval` | `record_rate_hz` | float | `20` | TF 录制频率（Hz） |
| `eval` | `playback_timeout_s` | int | `600` | 单个 bag 播放的最大超时时间（秒） |
| `evo` | `t_max_diff` | float | `0.5` | 轨迹对齐时允许的最大时间戳差 |
| `evo` | `rpe_delta` | int | `1` | RPE 计算的帧间隔 |
| `evo` | `rpe_delta_unit` | enum | `f` | RPE 帧间隔单位：`f`=帧, `d`=距离, `r`=旋转圈数, `m`=分钟 |
| `env` | | dict | {...} | 环境变量覆盖（OpenGL 无头渲染等） |
| `eval_launch` | `static_tf.*` | dict | 见下 | 静态 TF 值（x/y/z/roll/pitch/yaw/parent/child） |
| `eval_launch` | `enable_static_tf` | bool | `true` | 是否发布静态 TF |
| `eval_launch` | `enable_nv12_to_bgr` | bool | `true` | 启动 NV12→BGR8 转换 |
| `eval_launch` | `enable_odom_to_tf` | bool | `true` | 启动 odom→TF 转换 |
| `eval_launch` | `enable_foxglove` | bool | `true` | 启动 Foxglove bridge |
| `eval_launch` | `enable_rviz` | bool | `false` | 启动 RViz |
| `eval_launch` | `enable_rtabmap_viz` | bool | `false` | 启动 RTAB-Map GUI |
| `eval_launch` | `bag_start_delay_s` | float | `3.0` | bag 播放延迟启动时间（s） |

> 使用前请自行 `source` ROS2 环境（`/opt/ros/<distro>/setup.bash`）与 colcon 工作空间（`<ws>/install/setup.bash`）。

## 评测指标

所有指标由 [evo](https://github.com/MichaelGrupp/evo) 工具计算。

### APE — 绝对位姿误差

衡量全局轨迹精度。对每个时间戳，计算估计位姿与对齐后真值位姿之间的欧氏距离。

| 指标 | 含义 |
|------|------|
| **APE RMSE** | 所有位姿误差的均方根 — 主要精度指标 |
| APE Mean | 绝对位姿误差均值 |
| APE Median | 绝对位姿误差中位数（抗异常值） |
| APE Max | 单帧最大误差 |
| APE Std | 误差标准差 |

### RPE — 相对位姿误差

衡量局部一致性（每帧漂移）。对每对间隔 `delta` 帧的帧，计算估计与真值相对运动的差异。

| 指标 | 含义 |
|------|------|
| **RPE 平移 RMSE** | 每帧平移漂移（m/frame） |
| RPE 平移 Mean | 平均平移漂移 |
| **RPE 旋转 RMSE** | 每帧旋转漂移（deg/frame） |
| RPE 旋转 Mean | 平均旋转漂移 |

所有指标越低越好。APE 反映全局漂移校正质量，RPE 反映里程计/局部匹配质量。

## 内置脚本

本工具的所有 Node 与 launch 文件在 `colcon build` 后通过 ament 索引按 package 名调用，无需手动指定路径。

### `record_tf_trajectory.py`(包内)

录制 `map → base_footprint` TF 变换为 TUM 格式轨迹文件。这是 SLAM 的估计路径——每次运行的核心输出。

**工作原理**：以可配置频率（默认 20 Hz）订阅 TF 树，缓存所有位姿，收到 SIGTERM/SIGINT 时写入磁盘。作为 ROS2 Node(`rtabmap_eval` 包的 `record_tf_trajectory` entry point)在 `eval.launch.py` 中启动,通过 ROS 参数 `output_path` 与 `rate_hz` 传入输出路径与录制频率。

**单独使用**(需先 `colcon build` 并 `source install/setup.bash`):
```bash
ros2 run rtabmap_eval record_tf_trajectory --ros-args -p output_path:=/tmp/traj.tum -p rate_hz:=20.0
```

### `odom_to_tf.py`

从 `/odom` 话题发布 `odom → base_footprint` TF。当里程计源发布 `nav_msgs/Odometry` 但不发布 TF 时需要此脚本（例如某些轮式里程计驱动）。在 `eval.launch.py` 中启动。

**单独使用：**
```bash
ros2 run rtabmap_eval odom_to_tf
```

### `nv12_to_bgr.py`

将 NV12 编码图像转换为 BGR8 供 RTAB-Map 使用。仅当相机驱动发布 NV12 格式时需要（常见于带硬件编码器的嵌入式平台）。如果相机已发布 BGR8/RGB8，则不需要此脚本。在 `eval.launch.py` 中启动。

**单独使用：**
```bash
ros2 run rtabmap_eval nv12_to_bgr
```

### `launch/eval.launch.py`

eval 侧 launch 文件,承载所有辅助进程与 bag 播放。由 eval 项目内部通过 ament 索引按 package 名调用(`runner.py` 解析 `share/rtabmap_eval/launch/eval.launch.py`),用户无需在配置中指定 launch 文件路径。每次 run 启动一次,bag 播放结束后自动退出,所有子进程由 ROS2 launch 框架清理。

runner 自动追加 `bag_path`/`traj_file`/`record_rate` 三个 launch 参数,并把 yaml 中 `eval_launch` section 的字段扁平化后追加(如 `static_tf_x:=0.0`、`enable_nv12_to_bgr:=true`),用户可在 user.yaml 中按机器人定制。

**包含的进程**(均可通过 `eval_launch` 配置开关):
- `nv12_to_bgr.py` — NV12 → BGR8 图像转换(`enable_nv12_to_bgr`)
- `odom_to_tf.py` — `/odom` → `odom→base_footprint` TF(`enable_odom_to_tf`)
- `static_transform_publisher` — 可配置的静态 TF(`enable_static_tf` + `static_tf.*`)
- `record_tf_trajectory` — TF 录制为 TUM 轨迹(始终启动)
- `foxglove_bridge` — Web 可视化(`enable_foxglove`,默认开)
- `rtabmap_viz` — RTAB-Map GUI(`enable_rtabmap_viz`,默认关)
- `rviz2` — RViz(`enable_rviz`,默认关)
- `ros2 bag play` — 延迟启动(`bag_start_delay_s`),播完触发整个 launch 退出

**定制示例**(user.yaml):
```yaml
eval_launch:
  static_tf:
    x: 0.1
    y: 0
    z: 0.2
    roll: 0
    pitch: 0
    yaw: 0
    parent: base_link
    child: camera_link
  enable_nv12_to_bgr: false   # 相机已发 BGR8
  enable_odom_to_tf: false   # 驱动已发 TF
  enable_rviz: true
```

## 输出说明

结果保存到带时间戳的目录（默认：`/tmp/rtabmap_benchmark_YYYYMMDD_HHMMSS/`）。

### 目录结构

```
rtabmap_benchmark_20260608_115040/
  meta.json                                    # 运行元数据（git commit、配置等）
  results.csv                                  # 所有运行结果的 CSV 汇总
  bag_20260527_160436/
    run_1/
      trajectory.tum                           # SLAM 输出轨迹
      rtabmap.log                              # RTAB-Map launch 日志
      eval.log                                 # eval launch 日志（辅助进程 + 播包）
    run_2/
      ...
    run_3/
      ...
  bag_20260527_163821/
    ...
```

### results.csv 列说明

```
bag, run, run_time_s, traj_file,
ape_max, ape_mean, ape_median, ape_min, ape_rmse, ape_sse, ape_std,
rpe_trans_max, rpe_trans_mean, rpe_trans_median, rpe_trans_rmse,
rpe_rot_max, rpe_rot_mean, rpe_rot_median, rpe_rot_rmse
```

### results.csv 示例

```csv
bag,run,run_time_s,traj_file,ape_max,ape_mean,ape_median,ape_min,ape_rmse,ape_sse,ape_std,rpe_trans_max,rpe_trans_mean,rpe_trans_median,rpe_trans_rmse,rpe_rot_max,rpe_rot_mean,rpe_rot_median,rpe_rot_rmse
bag_20260527_160436,1,185.1,/tmp/.../trajectory.tum,0.509181,0.317285,0.330553,0.049187,0.328917,17.634359,0.086699,6.6395,2.987459,3.509348,3.316322,60.38681,15.449988,10.600897,21.58995
bag_20260527_160436,2,183.5,/tmp/.../trajectory.tum,0.523122,0.325694,0.334933,0.053197,0.338205,18.758801,0.091140,6.5547,2.970283,3.498692,3.306028,61.22340,15.350056,10.596675,21.521104
bag_20260527_160436,3,187.2,/tmp/.../trajectory.tum,0.498765,0.310452,0.328714,0.047231,0.322156,16.901234,0.083427,6.7123,3.012876,3.520187,3.342110,59.87654,15.567123,10.612456,21.654321
```

### 控制台输出示例

```
============================================================
RTAB-Map 评测平台
============================================================
数据集数量:  11
每数据集运行: 3 次
输出目录:    /tmp/rtabmap_benchmark_20260608_143022

[1/33] bag_20260527_160436 — 第 1/3 次
  播放 bag_20260527_160436 (第 1 次)...
  运行耗时: 185s
  APE RMSE: 0.3289m | RPE 平移: 3.3163m | RPE 旋转: 21.59deg

[2/33] bag_20260527_160436 — 第 2/3 次
  ...

=====================================================================================
评测结果汇总
=====================================================================================
Bag                            APE RMSE   APE Mean  RPE 平移     RPE 旋转     运行次数
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
总体平均                         0.3481                 3.3847       21.97    33
APE 范围                         0.3142 ~ 0.4015
=====================================================================================

详细结果:  /tmp/rtabmap_benchmark_20260608_143022/results.csv
输出目录:  /tmp/rtabmap_benchmark_20260608_143022
```

### meta.json 示例

```json
{
  "timestamp": "20260608_115040",
  "bags": ["bag_20260527_160436"],
  "num_runs": 1,
  "clean_db": false,
  "config": { ... }
}
```

## CLI 参考

```
python3 -m rtabmap_eval [选项]

选项:
  --config 路径       YAML 配置文件（默认: configs/default.yaml + configs/user.yaml）
  --bags "b1,b2"     逗号分隔的 bag 名称（默认: 所有配置中的 bag）
  --runs N            每个 bag 的重复运行次数（默认: 从配置读取，通常 3）
  --quick             快速模式：1 个 bag × 1 次运行
  --clean             每次运行前删除 rtabmap.db
  --output 目录       指定结果输出目录
  -h, --help          显示帮助信息
```

### 使用示例

```bash
# 全量评测（清理数据库）
python3 -m rtabmap_eval --clean

# 快速验证
python3 -m rtabmap_eval --quick

# 指定数据集，重复 5 次
python3 -m rtabmap_eval --bags "bag_20260527_160436,bag_20260527_164443" --runs 5

# 使用不同机器人配置
python3 -m rtabmap_eval --config configs/robot_b.yaml

# 仅评估已有的轨迹文件（跳过 SLAM 运行）
python3 -m rtabmap_eval.eval_only /tmp/rtabmap_benchmark_xxx/trajectory.tum --gt /path/to/gt.tum
```

## 平台兼容性

| 平台 | ROS2 发行版 | 状态 |
|------|-------------|------|
| x86_64 (Ubuntu 22.04) | Humble | 已测试 |
| x86_64 (Ubuntu 24.04) | Jazzy | 兼容 |
| ARM64 / aarch64 | Humble / Jazzy | 兼容 |

无架构相关代码，纯 Python + ROS2 CLI + evo。使用前请自行 `source` 对应 ROS2 发行版与 colcon workspace。

## 项目结构

```
rtabmap_eval/                  ROS2 ament_python package
  rtabmap_eval/                Python 包
    __init__.py
    __main__.py                CLI 入口
    config.py                  YAML 配置加载与验证
    runner.py                  SLAM 执行（启动、播包、录制）
    evaluator.py               轨迹评测（APE, RPE via evo）
    benchmark.py               编排与报表
    utils.py                   进程管理、Shell 工具
    record_tf_trajectory.py    TF 录制为 TUM 轨迹（ROS Node entry point）
    odom_to_tf.py              从 /odom 发布 TF（ROS Node entry point）
    nv12_to_bgr.py             NV12 转 BGR8（ROS Node entry point）
    eval_only.py               独立评测已有轨迹
  launch/
    eval.launch.py             eval 侧 launch（辅助进程 + TF 录制 + 播包）
  configs/
    default.yaml               默认配置（所有字段均有文档）
  resource/rtabmap_eval        ament package 注册占位
  requirements.txt             evo, pyyaml
  package.xml                  ROS2 package 声明
  setup.py                     ament_python 安装脚本
  setup.cfg                    ament_python 脚本安装配置
  README.md
```

## 依赖

- **ROS2** Humble 或更高版本（colcon, ros2 CLI）— 使用前请自行 `source` ROS2 与 colcon workspace
- **Python 3.8+**
- **evo** `>=1.30.0` — 轨迹评测（`pip install evo`）
- **PyYAML** — 配置加载（`pip install pyyaml`）
- RTAB-Map 已在 colcon 工作空间中编译完成（本工具不负责编译）
