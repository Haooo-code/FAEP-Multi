# 多机协调：单机前沿快照（每机 5Hz 上报给协调器）
std_msgs/Header header
int32 drone_id                       # 机号
geometry_msgs/Pose pose              # 本机当前位姿
float32 yaw                          # 本机偏航角
uint8 state                          # 0=探索中 1=已完成(FINISH) 2=无前沿等待
geometry_msgs/Point[] centers        # 可访问前沿簇中心（世界系）
float32[] sizes                      # 各簇体素数（信息量近似）
