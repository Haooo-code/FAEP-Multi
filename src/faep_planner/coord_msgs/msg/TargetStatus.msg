# 多机目标搜索状态
std_msgs/Header header

uint8 SEARCHING=0
uint8 CANDIDATE=1
uint8 VERIFYING=2
uint8 CONFIRMED=3
uint8 NOT_FOUND=4

uint8 state
float32 confidence
uint8 source_id
uint8 verifier_id
geometry_msgs/Point estimated_position
string message
