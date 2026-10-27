#!/bin/bash
# 边缘优先消融：把 edge_priority_scale 置 0 重新编译前无需改代码——直接改部署的 launch 参数，
# 跑一轮并回收决策日志（用于与正常轮对比）。
set -e
LAUNCH=/home/ubuntu/catkin_ws/src/faep/faep_planner/exploration_manager/launch/algorithm.xml
BAK=/tmp/algorithm_xml_orig.bak

cp "$LAUNCH" "$BAK"
echo "[ablate] backup -> $BAK"
sed -i 's#<param name="frontier/edge_priority_scale" value="1.0" type="double"/>#<param name="frontier/edge_priority_scale" value="0.0" type="double"/>#' "$LAUNCH"
grep -n 'edge_priority_scale' "$LAUNCH"
sed -i 's#/mnt/d/WSL/edge_debug_single.log#/mnt/d/WSL/edge_debug_ablate.log#' "$LAUNCH"
grep -n 'debug_file' "$LAUNCH"

echo "[ablate] run in ablated mode ..."
bash /mnt/d/WSL/run_single_rec.sh ablate

echo "[ablate] restore launch"
cp "$BAK" "$LAUNCH"
grep -n 'edge_priority_scale' "$LAUNCH"
echo ABLATE_DONE
