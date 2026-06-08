# RTAB-Map 评测平台

RTAB-Map SLAM 的独立基准评测平台。自动完成编译、运行、评测全流程，支持多数据集多次重复运行，输出 APE（绝对位姿误差）和 RPE（相对位姿误差）指标。兼容 x86_64 和 ARM64 架构，支持任意 ROS2 发行版。

## 功能特点

- **全流程自动化**：编译 → 启动 → 播包 → 录制轨迹 → 评测，一键完成
- **多数据集多次运行**：支持 11 个数据集 × N 次重复运行，统计均值和稳定性
- **APE + RPE 指标**：全局精度和局部漂移，平移和旋转分别评估
- **跨平台**：x86_64 / ARM64 通用，支持 humble、jazzy、rolling 等任意 ROS2 发行版
- **YAML 配置**：路径和参数集中管理，方便版本控制
- **结构化输出**：CSV + JSON 格式，便于后续分析
- **快速模式**：単数据集単次运行，3 分钟快速验证

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/D-Robotics/rtabmap_eval.git
cd rtabmap_eval

# 2. 安装 Python 依赖
pip3 install -r requirements.txt

# 3. 配置路径（首次使用）
cp configs/default.yaml configs/user.yaml
# 编辑 configs/user.yaml，填写你的 rtabmap 源码路径、编译路径、bag 路径、真值路径

# 4. 全量评测（11 bags × 3 runs ≈ 100 分钟）
python3 -m rtabmap_eval

# 或快速验证（1 bag × 1 run ≈ 3 分钟）
python3 -m rtabmap_eval --quick
```

## 配置说明

所有配置通过 YAML 文件管理。将 `configs/default.yaml` 复制为 `configs/user.yaml` 并修改，用户配置会覆盖默认值。

### 最小 user.yaml 示例

```yaml
rtabmap:
  source_dir: /home/user/rtabmap
  build_dir: /home/user/catkin_ws
  db_path: ~/.ros/rtabmap.db

ros:
  distro: jazzy                # 你的 ROS2 发行版

paths:
  bag_dir: /data/bags
  gt_dir: /data/ground_truth
  launch_file: scripts/example.launch.py
  record_script: scripts/record_tf_trajectory.py

bag_mapping:
  bag_20260527_160436: "05271604"
  bag_20260527_163821: "05271638"
  # ... 添加所有 bag → 真值前缀的映射
```

### 完整配置字段

| 分组 | 字段 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `ros` | `distro` | string | `humble` | ROS2 发行版名称 |
| `ros` | `setup_bash` | path | 自动推导 | 手动指定 setup.bash 路径（不填则根据 distro 自动生成） |
| `rtabmap` | `source_dir` | path | 必填 | RTAB-Map 源码路径（包含 corelib/） |
| `rtabmap` | `ros_source_dir` | path | 自动推导 | rtabmap_ros 源码路径（不填则自动推导） |
| `rtabmap` | `build_dir` | path | 必填 | colcon 工作空间根目录（包含 install/ 和 build/） |
| `rtabmap` | `db_path` | path | `~/.ros/rtabmap.db` | RTAB-Map 数据库文件（`--clean` 时删除） |
| `paths` | `bag_dir` | path | 必填 | 存放 bag 子目录的根目录 |
| `paths` | `gt_dir` | path | 必填 | 存放 `_gt.tum` 真值文件的根目录 |
| `paths` | `launch_file` | path | 必填 | ROS2 launch 文件（支持相对路径） |
| `paths` | `record_script` | path | 必填 | TF→TUM 轨迹录制脚本（支持相对路径） |
| `bag_mapping` | *(键值对)* | string | 必填 | bag 文件夹名 → 真值文件前缀的映射 |
| `eval` | `runs_per_bag` | int | `3` | 每个 bag 重复运行次数 |
| `eval` | `startup_wait_s` | float | `10` | 启动后等待 RTAB-Map 就绪的秒数 |
| `eval` | `shutdown_wait_s` | float | `5` | bag 播放结束后等待 RTAB-Map 处理完毕的秒数 |
| `eval` | `record_rate_hz` | float | `20` | TF 录制频率（Hz） |
| `eval` | `playback_timeout_s` | int | `600` | 单个 bag 播放的最大超时时间（秒） |
| `evo` | `t_max_diff` | float | `0.5` | 轨迹对齐时允许的最大时间戳差 |
| `evo` | `rpe_delta` | int | `1` | RPE 计算的帧间隔 |
| `evo` | `rpe_delta_unit` | enum | `f` | RPE 帧间隔单位：`f`=帧, `d`=距离, `r`=旋转圈数, `m`=分钟 |
| `kill_patterns` | | list | [...] | 每次运行前后需要清理的进程名模式 |
| `env` | | dict | {...} | 环境变量覆盖（OpenGL 无头渲染等） |

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

`scripts/` 目录包含运行评测所需的全部辅助脚本，配置文件中通过相对路径引用，评测时自动调用。

### `scripts/record_tf_trajectory.py`

录制 `map → base_footprint` TF 变换为 TUM 格式轨迹文件。这是 SLAM 的估计路径——每次运行的核心输出。

**工作原理**：以可配置频率（默认 20 Hz）订阅 TF 树，缓存所有位姿，收到 SIGTERM/SIGINT 时写入磁盘。评测运行器与 RTAB-Map 同时启动此脚本，bag 播放结束后停止。

**单独使用：**
```bash
python3 scripts/record_tf_trajectory.py [输出文件.tum] [频率Hz]
```

### `scripts/odom_to_tf.py`

从 `/odom` 话题发布 `odom → base_footprint` TF。当里程计源发布 `nav_msgs/Odometry` 但不发布 TF 时需要此脚本（例如某些轮式里程计驱动）。

**单独使用：**
```bash
python3 scripts/odom_to_tf.py
```

### `scripts/nv12_to_bgr.py`

将 NV12 编码图像转换为 BGR8 供 RTAB-Map 使用。仅当相机驱动发布 NV12 格式时需要（常见于带硬件编码器的嵌入式平台）。如果相机已发布 BGR8/RGB8，则不需要此脚本。

**单独使用：**
```bash
python3 scripts/nv12_to_bgr.py
```

### `scripts/rtabmap_xfeat_matcher.py`

XFeat 描述子匹配器，用于 RTAB-Map 的 `PyMatcher` 接口。实现了互最近邻（MNN）匹配 + 余弦相似度阈值（0.82），与 XFeat 原生 `match()` 方法逻辑一致。

**使用场景**：设置 `Vis/CorNNType=0`（PyMatcher）代替内置 C++ 匹配器（CorNNType=9）时使用。

### `scripts/example.launch.py`

示例 ROS2 launch 文件，展示评测的完整启动配置。复制并修改此文件适配你的机器人——修改话题重映射、TF 变换、RTAB-Map 参数等。

需要自定义的关键部分：
- **话题重映射** — 匹配你 bag 中的 RGB、depth、camera_info、odom 话题
- **静态 TF** — 调整 `base_footprint → camera_depth_frame` 变换
- **RTAB-Map 参数** — 特征类型、PnP 设置、回环配置
- **辅助脚本** — 按需包含 `odom_to_tf.py` 和 `nv12_to_bgr.py`

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
      rtabmap.log                              # RTAB-Map 完整控制台日志
      tf_recorder.log                          # TF 录制器日志
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

[BUILD] 编译 RTAB-Map...
[BUILD] 完成.

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
  "skip_build": true,
  "git_commit": "a48710d5",
  "git_branch": "feature/xfeat-pydetector",
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
  --skip-build        跳过 colcon 编译步骤
  --clean             每次运行前删除 rtabmap.db
  --output 目录       指定结果输出目录
  -h, --help          显示帮助信息
```

### 使用示例

```bash
# 全量评测（全新编译 + 清理数据库）
python3 -m rtabmap_eval --clean

# 快速验证
python3 -m rtabmap_eval --quick --skip-build

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

无架构相关代码，纯 Python + ROS2 CLI + evo。在 YAML 配置中设置 `ros.distro` 为你的发行版即可。

## 项目结构

```
rtabmap_eval/
  rtabmap_eval/           Python 包
    __init__.py
    __main__.py           CLI 入口
    config.py             YAML 配置加载与验证
    runner.py             SLAM 执行（编译、启动、播包、录制）
    evaluator.py          轨迹评测（APE, RPE via evo）
    benchmark.py          编排与报表
    utils.py              进程管理、Shell 工具
    eval_only.py          独立评测已有轨迹
  scripts/                辅助脚本（从配置文件引用）
    record_tf_trajectory.py   录制 map→base_footprint 为 TUM 轨迹
    odom_to_tf.py             从 /odom 发布 odom→base_footprint TF
    nv12_to_bgr.py            NV12 图像转 BGR8（嵌入式平台可选）
    rtabmap_xfeat_matcher.py  XFeat MNN 匹配器（PyMatcher 接口）
    example.launch.py         示例 launch 文件（复制修改）
  configs/
    default.yaml          默认配置（所有字段均有文档）
  requirements.txt        evo, pyyaml
  setup.py                pip install -e .
  README.md
```

## 依赖

- **ROS2** Humble 或更高版本（colcon, ros2 CLI）
- **Python 3.8+**
- **evo** `>=1.30.0` — 轨迹评测（`pip install evo`）
- **PyYAML** — 配置加载（`pip install pyyaml`）
- RTAB-Map 已在 colcon 工作空间中编译完成
