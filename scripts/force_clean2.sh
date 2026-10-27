#!/bin/bash
for pat in "roslaunch" "rosmaster" "rosout" "exploration_manager/exploration_node" "quadrotor_simulator_so3" "pcl_render_node" "so3_control" "so3_disturbance_generator" "odom_visualization" "waypoint_generator" "map_generator/map_pub" "rviz" "gdb -p" "attach_gdb" "faep_coordinator"; do
  pkill -9 -f "$pat" 2>/dev/null || true
done
sleep 2
ps -ef | grep -E "roslaunch|rosmaster|exploration_node|quadrotor|pcl_render|so3_|odom_vis|waypoint|map_pub|rviz|gdb|coordinator" | grep -v grep || echo "ALL CLEAN2"
