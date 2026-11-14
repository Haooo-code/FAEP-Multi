# 模拟目标感知或真实目标检测器发布的统一检测结果
std_msgs/Header header

# 检测来源机号，与 /droneN 的 N 一致
uint8 source_id

# 当前目标类别。半决赛原型固定使用 person。
string target_class

# 检测置信度，范围 [0, 1]
float32 confidence

# 估计的目标位置，world 坐标系，不是仿真真值
geometry_msgs/Point position

# 置信度不足时建议由第二架飞机换视角复核
bool requires_verification
