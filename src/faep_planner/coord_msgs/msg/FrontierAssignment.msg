# 多机协调：协调器下发给单机的任务分配（空间区域白名单）
std_msgs/Header header
int32 version                        # 分配版本号（单调递增，用于单机判断新旧）
geometry_msgs/Point[] centers        # 任务区域中心（世界系）
float32[] radii                      # 任务区域半径（与 centers 一一对应）
bool free_explore                    # true=兜底自由探索（无任务可分配时，单机不限制探索范围）

# ---- v2.0 空间分区（partition_mode）----
# 按各机初始位置沿"离散度大的轴"划分 Voronoi 扇区：每机只在自己的扇区内
# 选择前沿、只上报本扇区前沿；协调器按扇区归属任务、不再重派。
bool partition                       # true=启用扇区划分（单机按 sector_lo/hi 过滤）
int32 sector_axis                    # 0=x, 1=y
float32 sector_lo                    # 扇区下界（该轴坐标）
float32 sector_hi                    # 扇区上界（该轴坐标）
