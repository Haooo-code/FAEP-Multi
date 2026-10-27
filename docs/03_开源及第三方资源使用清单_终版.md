# 开源及第三方资源使用清单

本清单覆盖运行软件、算法、数据、框架、组件、工具和第三方服务。版本以 2026-10-18 冻结的实验环境为准，并于 2026-10-27 按公开仓库的实际打包方式复核。

## 一、软件、算法与框架

| 类别 | 名称 | 版本 / 快照 | 来源 | 许可证 / 授权类型 | 使用方式 | 关键义务 | 自研修改 / 边界 |
|---|---|---|---|---|---|---|---|
| 上游算法 | FAEP | master，2023-06-23 快照 | https://github.com/Zyhlibrary/FAEP | GPL-3.0 | 单机自主探索基线，含建图、前沿、LKH 序列、B 样条和仿真栈 | 衍生部分按 GPL-3.0 发布，保留版权与修改说明 | 保留单机核心；新增多机协调、扇区归属、仿真多机化和 OOM 防御 |
| TSP 求解器 | LKH | FAEP 未注明具体版本 | FAEP `utils/lkh_tsp_solver`，作者 Keld Helsgaun；官方说明：http://akira.ruc.dk/~keld/research/LKH/ | 研究用途，作者保留全部权利；按作者条款和第三方发行说明，不得用于商业用途；FAEP 包内无独立 LICENSE，`package.xml` 仍写 TODO | 全局巡游顺序求解并链接进 `exploration_node` | 仅限比赛和研究使用；保留作者署名与来源；不重新授权为 GPL-3.0；商业使用前取得授权或改用许可兼容的求解器 | 未修改算法本身，仅适配 FAEP 调用接口 |
| 几何组件 | Delaunay（LKH 目录内） | 随 LKH 内置 | LKH `src/Delaunay.c`，作者 Geoff Leach，RMIT 版权声明 | RMIT 1993 独立声明：允许复制、使用及制作衍生作品，须保留署名与声明 | LKH 候选集和几何计算 | 保留 RMIT 与作者署名以及原始声明；不将其重新授权为 GPL-3.0 | 未修改 |
| 消息包 | swarmtal_msgs | 随上游源码 | HKUST/SWARM 生态，FAEP `poly_traj/traj_generator.cpp` 引用 | 按上游仓库许可，发布前复核 | 提供 `drone_onboard_command` 等消息类型；当前 `poly_traj` 构建只编译 `polynomial_traj.cpp`，该文件未进入本实验运行链路 | 保留来源和许可声明；如启用需单独核对 | 未修改，未编译进当前实验 |
| 机器人中间件 | ROS Noetic | Noetic | https://ros.org | BSD-3-Clause | 节点、话题、launch、TF 和消息通信 | 保留版权与许可声明 | 未修改框架 |
| 线性代数 | Eigen | 3.3.7 | https://eigen.tuxfamily.org | MPL-2.0 | 矩阵、向量和几何运算 | 保留许可证与版权声明 | 未修改库本身 |
| 点云库 | PCL | 1.10 | https://pointclouds.org | BSD-3-Clause | 点云读写、可视化和处理 | 保留版权与许可声明 | 未修改库本身 |
| 图像库 | OpenCV | 4.2.0 | https://opencv.org | Apache-2.0 | 深度图、图像处理和可视化 | 保留 NOTICE 与许可证 | 未修改库本身 |
| 线性代数 | Armadillo | 9.x | https://arma.sourceforge.net | Apache-2.0 | 数值计算与矩阵运算 | 保留版权与许可声明 | 未修改库本身 |
| 非线性优化 | NLopt | 2.6.1（系统库） | https://nlopt.readthedocs.io | MIT / LGPL，按具体算法模块 | B 样条优化 | 保留许可证；核实实际链接模块 | 仅替换 ROS 自带旧链接方式 |
| GPU 工具链 | CUDA Toolkit | 12.8 | NVIDIA | NVIDIA EULA | 深度相机 GPU 渲染 | 按 EULA 使用；不再分发 CUDA 二进制 | 仅使用，不修改 |
| 构建工具 | CMake / catkin / rospkg | 随 Ubuntu 20.04 与 ROS Noetic | 各自上游 | BSD / Apache 等，按发行包 | 编译、打包和启动 | 保留发行包许可证 | 未修改 |

## 二、数据与模型

| 类别 | 名称 | 版本 / 快照 | 来源 | 许可证 / 授权类型 | 使用方式 | 关键义务 | 自研修改 / 边界 |
|---|---|---|---|---|---|---|---|
| 仿真地图 | office / office2 / office3 PCD | FAEP master 快照 | FAEP `uav_simulator/map_generator/resource/` | 随 FAEP 仓库 LICENSE 处理 | 三个场景的仿真环境 | 保留上游来源和 LICENSE；说明不是赛事地图 | 未修改地图文件 |
| 实验数据 | A/B/C 结果、轨迹、覆盖统计 | 2026-10-15 至 2026-10-18 | 本团队仿真运行 | 随项目发布，另行标注者除外 | 复现实验、图表和报告 | 不包含个人身份信息；保留原始日志 | 全部由团队生成 |
| 外部预训练模型 | 无 | 不适用 | 不适用 | 不适用 | 未使用外部模型或权重 | 无 | 不涉及 |

## 三、工具、运行环境与第三方服务

| 类别 | 名称 | 版本 | 来源 | 许可证 / 授权类型 | 使用方式 | 关键义务 | 自研修改 / 边界 |
|---|---|---|---|---|---|---|---|
| 编程语言 | Python | 3.8.10 | https://python.org | PSF License | 批跑、分析、图表和视频脚本 | 保留许可证声明 | 自写脚本 |
| 数值计算 | NumPy | 1.17.4 | https://numpy.org | BSD-3-Clause | 数据处理与统计 | 保留许可证 | 自写分析逻辑 |
| 绘图 | Matplotlib | 3.1.2 | https://matplotlib.org | PSF / BSD 兼容 | 生成报告图表 | 保留许可证 | 自写绘图脚本 |
| 图像处理 | Pillow | 7.0.0 | https://python-pillow.org | HPND | 视频帧、标题卡和图像处理 | 保留许可证 | 自写渲染脚本 |
| 视频编码 | FFmpeg | 4.2.7 | https://ffmpeg.org | LGPL-2.1+，取决于构建选项 | 录屏编码、裁剪和合成 | 使用 LGPL 动态构建；保留声明；核实构建 flag | 自写录制与叠加脚本 |
| 操作系统 | Ubuntu | 20.04.6 LTS | https://ubuntu.com | 多个开源许可证 | 仿真和编译环境 | 保留发行包许可证 | 未修改系统 |
| 代码托管 | GitHub | 2026-10 | https://github.com | GitHub Terms of Service | 公开仓库、Issue、版本发布 | 遵守服务条款；开源许可证不因托管而改变 | 仅作为托管平台 |
| AI 辅助 | OpenAI Codex / ChatGPT | 2026-10 | https://openai.com | OpenAI 服务条款 | 代码调试建议、文档初稿、图表脚本 | 按比赛要求披露 AI 辅助；实验数据由团队实测，不用 AI 生成或修改 | AI 输出经团队审核和复跑 |
| 文字编辑 | humanizer | 3.1.0 | https://github.com/blader/humanizer | MIT | 检查并改写报告中的模板化表达 | 保留 MIT 许可证；仅用于文字编辑，不进入运行链路 | 不修改实验数据 |

## 四、自研内容声明

- 三机命名空间、共享真值地图、多机 launch 与批量运行脚本。
- `coordinator` 协调器：任务池、扇区归属、租约、卡住检测、统一 HALT。
- v2.0 一维 Voronoi 扇区归属、单机前沿过滤和等待态修复。
- `KinodynamicAstar::getSamples` 父链成环的 OOM 根因修复与四层防御。
- 三场景 A/B/C 数据、覆盖分析、图表、视频和复现文档。

## 五、许可结论与发布前复核

- FAEP 衍生代码和团队新增代码按 GPL-3.0 发布，保留上游版权、LICENSE 和修改说明。
- 仓库是混合许可项目，不能表述为“整个仓库均为纯 GPL-3.0”。LKH 官方说明为“distributed for research use”，作者保留全部权利；第三方发行说明普遍将其进一步解释为学术、非商业使用。LKH 被链接进 `exploration_node`，因此本公开版本仅面向比赛和研究，商业使用前必须取得 LKH 作者授权或替换求解器。
- LKH 包内没有独立 LICENSE，`package.xml` 仍写 TODO；本清单以作者公开说明为依据，不虚构许可证名称。Delaunay 代码保留 RMIT 独立声明。
- 三张 PCD 地图来自 FAEP 上游示例场景，不是赛事提供的地图；保留来源说明。
- 实验数据由团队自行生成，不包含个人身份信息；发布时按项目许可证处理。
- 未使用外部预训练模型、外部数据集或需要账号权限的模型服务。
- 第三方服务仅用于代码托管和 AI 辅助写作，不改变代码、数据和实验结果的许可归属。
