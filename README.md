# RTAB-Map 评测平台

针对 RTAB-Map SLAM 的独立基准测试平台。自动构建、运行并评测 RTAB-Map 在多个数据集上的表现，提供 APE 和 RPE 指标。

## 快速开始

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 配置路径（首次使用）
cp configs/default.yaml configs/user.yaml
# 编辑 configs/user.yaml 以匹配你的环境

# 3. 运行完整评测
python3 -m rtabmap_eval --config configs/user.yaml

# 快速测试（单个 bag，单次运行）
python3 -m rtabmap_eval --quick

# 仅评估已有轨迹文件（跳过 SLAM 运行）
python3 -m rtabmap_eval.eval_only /path/to/trajectory.tum --gt /path/to/gt.tum

# 4. 查看结果
cat results/<timestamp>/results.csv
```

## 配置说明

所有路径和参数均通过 YAML 文件配置，完整字段参见 `configs/default.yaml`。

主要配置项：
- `rtabmap.source_dir` — RTAB-Map 源码（git 仓库）
- `rtabmap.ros_source_dir` — rtabmap_ros 源码（git 仓库）
- `rtabmap.build_dir` — colcon 构建目录
- `paths.bag_dir` — bag 文件夹的根目录
- `paths.gt_dir` — 真值 `.tum` 文件的根目录
- `paths.launch_file` — 使用的 ROS2 launch 文件
- `bag_mapping` — bag 文件夹名与真值文件前缀的映射
- `eval.runs_per_bag` — 每个数据集的重复运行次数（默认 3）

## 项目结构

```
rtabmap_eval/
  rtabmap_eval/          Python 包
    __init__.py
    config.py            配置加载与校验
    runner.py            SLAM 执行（构建、启动、播放、录制）
    evaluator.py         轨迹评测（基于 evo 的 APE、RPE）
    benchmark.py         编排与报告
    utils.py             进程管理、辅助工具
  configs/
    default.yaml         包含所有字段的默认配置
  hooks/
    pre-commit           提交时自动评测的 Git hook
  templates/
    rtabmap.launch.py    示例 launch 文件
  requirements.txt       Python 依赖
  setup.py               包安装
  README.md
```

## 评测指标

| 指标 | 含义 | 越小越好 |
|------|------|----------|
| APE RMSE | 全局轨迹精度 | 是 |
| APE Mean | 绝对位姿误差均值 | 是 |
| RPE Trans RMSE | 逐帧平移漂移 | 是 |
| RPE Rot RMSE | 逐帧旋转漂移（度） | 是 |

## 命令行参考

```bash
# 完整评测
python3 -m rtabmap_eval --config my_config.yaml --runs 5 --clean

# 快速模式
python3 -m rtabmap_eval --quick

# 指定 bag
python3 -m rtabmap_eval --bags "bag_20260527_160436,bag_20260527_164443"

# 跳过构建步骤
python3 -m rtabmap_eval --skip-build

# pre-commit hook 评测
python3 -m rtabmap_eval.eval_only --gt gt.tum trajectory.tum
```
