#!/bin/bash
# 依次触发三机探索（间隔 1s，便于日志与录屏观察）
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash
for i in 1 2 3; do
  rostopic pub -1 /drone$i/move_base_simple/goal geometry_msgs/PoseStamped \
    '{header: {frame_id: "world"}, pose: {position: {x: 0.0, y: 0.0, z: 1.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}'
  sleep 1
done
echo TRIGGER_MULTI_DONE
