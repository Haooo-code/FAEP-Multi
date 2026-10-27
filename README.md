# FAEP-Multi

FAEP-Multi 将开源单机自主探索算法 [FAEP](https://github.com/Zyhlibrary/FAEP) 扩展为三机协同系统。每架无人机保留完整的建图、前沿检测、轨迹规划和飞控逻辑，协调器只负责任务层。上游基线为 commit `5a59d0a04b527e2e93d0ac8c00111c74d6da288f`，2023-06-23。

系统按各机初始位置划分一维 Voronoi 扇区。任务创建时即归属扇区机，单机只在本扇区选择与上报前沿，完成后统一 HALT。这个顺序把空间归属放在任务生成阶段，避免 FAEP 执行看不见的远方前沿。

## 结果

三场景 A/B/C 对照中，C 组相对三机独立：

| 指标 | 结果 |
|---|---|
| 单机飞行时间 | 低 43.8% 到 50.0% |
| 每轮 wall | 低 45.1% 到 56.0% |
| 重复覆盖 | 从 89% 到 98% 降至 0 到 19% |
| 未分区 v1 | 比独立慢 21.1% 到 29.3% |

三场景数据、轨迹和汇总在 [`data/`](data/)，修订版技术报告在 [`docs/FAEP-Multi_技术报告_修订版.pdf`](docs/FAEP-Multi_技术报告_修订版.pdf)，演示视频在 [`media/`](media/)。

公开成果链接：[docs/02_成果链接_终版.md](docs/02_成果链接_终版.md)。

## 目录

```text
src/faep_planner/       FAEP 探索栈与多机协调器
src/uav_simulator/      仿真、深度相机和地图
scripts/                批跑、覆盖分析、故障注入与图表脚本
data/                   结果表、轨迹和补充数据
docs/                   技术报告、实验文档和图表
media/                  三机协同视频与真实 RViz 录屏
docs/THIRD_PARTY_LICENSES.md
```

## 快速开始

环境：Ubuntu 20.04、ROS Noetic、CUDA 12.8、Eigen 3.3.7、PCL 1.10、OpenCV 4.2。完整依赖和版本见 [`docs/THIRD_PARTY_LICENSES.md`](docs/THIRD_PARTY_LICENSES.md)。

```bash
git clone https://github.com/Haooo-code/FAEP-Multi.git
cd FAEP-Multi
mkdir -p ~/catkin_ws/src
cp -r src/* ~/catkin_ws/src/
cd ~/catkin_ws
catkin_make -j12
source devel/setup.bash
```

单机基线：

```bash
roslaunch exploration_manager exploration.launch
```

三机扇区协同：

```bash
roslaunch exploration_manager multi_bringup.launch use_coord:=true partition_mode:=true \
  map_file:=$(rospack find map_generator)/resource/office2.pcd \
  map_size_x:=42 map_size_y:=42 \
  box_x_min:=-10.4 box_y_min:=-9.9 box_x_max:=10.4 box_y_max:=9.9 \
  d1_x:=-7.5 d1_y:=-3.5 d2_x:=4.5 d2_y:=-3.5 d3_x:=-3.5 d3_y:=6.5
```

启动后向三架机的 `move_base_simple/goal` 各发一个目标，或运行 `scripts/trigger_multi.sh`。脚本中的 `/mnt/d/WSL` 路径是实验机器上的路径，换环境时请按 [`scripts/README.md`](scripts/README.md) 修改。

## 可靠性

团队定位并修复了 `KinodynamicAstar::getSamples` 搜索树父指针成环引起的 OOM。heaptrack 记录到采样路径持续增长，进一步检查确认父链成环。四层防御和 `malloc_trim` 使探索节点常驻内存稳定在约 1.54 GB。

2026-10-18 补充了 3 轮受控故障注入：office2 场景触发后 41 s 杀掉中间机，3/3 轮剩余两架接管并统一 HALT，失联扇区覆盖 77% 到 82%，wall 约为正常轮的 2.2 倍。

## 许可与引用

FAEP 衍生部分采用 GPL-3.0，保留上游版权和修改说明。LKH TSP 求解器是独立第三方组件，适用其原始许可条款，不在本项目 GPL-3.0 授权范围内；公开仓库保留原始声明。完整清单见 [`docs/THIRD_PARTY_LICENSES.md`](docs/THIRD_PARTY_LICENSES.md)。

如果用于研究，请同时引用 FAEP 和 FUEL。引用信息见 [`CITATION.cff`](CITATION.cff)。

## 状态

提交版本：2026-10-27。报告主结果采用 2026-10-17 冻结数据；覆盖指标是轨迹邻域近似，不是相机精确覆盖。
