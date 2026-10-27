# 脚本说明

脚本来自团队实验机环境，包含一些 WSL 路径。当前仓库保留原始脚本，方便核对实验流程。

在另一台机器运行前，请先修改这些变量或路径：

- `multi_bench_v5.sh` 和 `fault_bench.sh` 中的 `RESULTS`、`MAPFILE`、`/mnt/d/WSL`；
- `coord_logger.py` 的输出路径参数；
- `make_new_experiment_figs.py` 和 `render_multi_video.py` 中的 `D:\WSL` 或 `/mnt/d/WSL` 输入路径。

核心代码不需要依赖脚本路径。脚本只负责批跑、记录、覆盖分析和图表生成。
