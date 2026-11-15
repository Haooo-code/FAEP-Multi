# 脚本说明

脚本来自团队实验机环境，包含一些 WSL 路径。当前仓库保留原始脚本，方便核对实验流程。

在另一台机器运行前，请先修改这些变量或路径：

- `multi_bench_v5.sh` 和 `fault_bench.sh` 中的 `RESULTS`、`MAPFILE`、`/mnt/d/WSL`；
- `coord_logger.py` 的输出路径参数；
- `make_new_experiment_figs.py` 和 `render_multi_video.py` 中的 `D:\WSL` 或 `/mnt/d/WSL` 输入路径。

核心代码不需要依赖脚本路径。脚本只负责批跑、记录、覆盖分析和图表生成。

## 目标搜索演示

office2 中央目标 `(1.0, 3.0, 1.0)` 的三机目标搜索示例：

```bash
bash scripts/multi_bench_v5.sh C 1 1 office2 targetdemo \
  "partition_mode:=true target_search_enabled:=true \
   target_x:=1.0 target_y:=3.0 target_z:=1.0 \
   target_prior_x:=1.0 target_prior_y:=3.0 \
   target_prior_radius:=3.0 target_prior_growth:=0.05 \
   target_prior_max_radius:=8.0 target_sensor_max_range:=8.0"
```

交互式演示可分别启动：

```bash
roslaunch exploration_manager multi_bringup.launch use_coord:=true partition_mode:=true \
  map_file:=$(rospack find map_generator)/resource/office2.pcd \
  map_size_x:=42 map_size_y:=42 map_size_z:=10.0 \
  box_x_min:=-10.4 box_y_min:=-9.9 box_z_min:=-0.1 \
  box_x_max:=10.4 box_y_max:=9.9 box_z_max:=2.0 \
  d1_x:=-7.5 d1_y:=-3.5 d1_z:=1.0 \
  d2_x:=4.5 d2_y:=-3.5 d2_z:=1.4 \
  d3_x:=-3.5 d3_y:=6.5 d3_z:=1.8 \
  target_search_enabled:=true target_x:=1.0 target_y:=3.0 target_z:=1.0 \
  target_prior_x:=1.0 target_prior_y:=3.0 target_prior_radius:=3.0 \
  target_prior_growth:=0.05 target_prior_max_radius:=8.0 target_sensor_max_range:=8.0

roslaunch exploration_manager target_search_rviz.launch
bash scripts/trigger_multi.sh
```

单场景自动回归使用 `target_search_regression.sh`。脚本会检查启动状态、三机
HALT、目标状态日志，记录目标状态和 HALT 时的轨迹并集覆盖率，并保存最终
RViz 标记；设置
`TARGET_SEARCH_INJECT_INCONSISTENT=1` 时还会注入一条远离候选的假检测，
用于验证位置一致性约束。

目标搜索组件消融使用 `run_target_search_ablation_suite.sh`；目标先验在东侧
场景的专项对照使用 `run_target_prior_ablation.sh`，汇总和成图由
`analyze_target_search_ablation.py` 完成。

三级协同消融（L1 独立、L2 协调无分区、L3 扇区协同）的数据由
`data/coordination_level_ablation_results_20261115.csv` 固化，配图使用
`make_coordination_ablation_fig.py` 生成。

跨场景目标搜索使用 `TARGET_SEARCH_MAP=office3` 切换地图；覆盖率记录节点为
`target_coverage_logger.py`，汇总与成图由 `analyze_target_search_coverage.py`
完成。

国赛 RViz 全场景录屏使用：

```bash
bash scripts/record_defense_video.sh single
bash scripts/record_defense_video.sh independent
bash scripts/record_defense_video.sh partition
bash scripts/record_defense_video.sh target
bash scripts/compose_defense_demo.sh
```

录像配置由 `make_recording_rviz.py` 生成，默认显示全景点云、三机局部地图、
相机 FOV、轨迹和机体。WSLg 下使用 `xwd` 以 10 fps 抓帧，再编码为 30 fps。
