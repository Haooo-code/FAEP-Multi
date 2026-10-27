#!/bin/bash
# 大场景（office2/office3 或 big_map）单机跑 n 轮，日志按 tag 归档
# 用法: run_bigscene.sh <map> <xmin> <ymin> <xmax> <ymax> <n> [map_tag]
#   map: office2 | office3 | /abs/path/to/map.pcd
export DISPLAY=:0
MAP=$1; XMIN=$2; YMIN=$3; XMAX=$4; YMAX=$5; N=${6:-1}; TAGBASE=${7:-$MAP}

RESDIR=/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource
case "$MAP" in
  office2|office3) MAPFILE=$RESDIR/$MAP.pcd ;;
  *) MAPFILE=$MAP ;;
esac
MAPSIZE_X=$(python3 -c "print(round(($XMAX)-($XMIN)+20,1))")
MAPSIZE_Y=$(python3 -c "print(round(($YMAX)-($YMIN)+20,1))")

for i in $(seq 1 "$N"); do
  TAG=${TAGBASE}_r$i
  SIMLOG=/mnt/d/WSL/sim_$TAG.log
  DBGLOG=/mnt/d/WSL/edge_debug_$TAG.log
  rm -f "$SIMLOG" "$DBGLOG"
  echo "===== $TAG start $(date +%H:%M:%S) ====="
  bash /mnt/d/WSL/force_clean2.sh | tail -1
  # debug_file 参数在 algorithm_node.xml（algorithm.xml 只负责 include）；改文件要改对
  LAUNCH=/home/ubuntu/catkin_ws/src/faep/faep_planner/exploration_manager/launch/algorithm_node.xml
  sed -i "s#<param name=\"frontier/debug_file\" value=\"[^\"]*\" type=\"string\"/>#<param name=\"frontier/debug_file\" value=\"$DBGLOG\" type=\"string\"/>#" "$LAUNCH"
  grep -q "$DBGLOG" "$LAUNCH" || echo "[warn] debug_file patch failed"
  cat > /tmp/run_big_$TAG.sh <<SIMEOF
#!/bin/bash
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash
exec roslaunch exploration_manager exploration.launch map_file:=$MAPFILE \
  map_size_x:=$MAPSIZE_X map_size_y:=$MAPSIZE_Y \
  box_x_min:=$XMIN box_y_min:=$YMIN box_x_max:=$XMAX box_y_max:=$YMAX > $SIMLOG 2>&1
SIMEOF
  nohup bash /tmp/run_big_$TAG.sh >/dev/null 2>&1 &
  READY=0
  for t in $(seq 1 60); do
    grep -q "WAIT_TRIGGER" "$SIMLOG" 2>/dev/null && { READY=1; break; }
    sleep 2
  done
  if [ "$READY" != "1" ]; then echo "$TAG SIM NOT READY"; tail -10 "$SIMLOG"; continue; fi
  sleep 12
  bash /mnt/d/WSL/trigger.sh
  FIN=0
  for t in $(seq 1 150); do
    grep -q "Flight_time]" "$SIMLOG" 2>/dev/null && { FIN=1; break; }
    sleep 4
  done
  TT=$(grep -o "Flight_time]: .*" "$SIMLOG" | tail -1)
  DD=$(grep -o "Flight_dist]: .*" "$SIMLOG" | tail -1)
  SA=$(grep -c "small area higher priority" "$SIMLOG")
  echo "BIGRUN $TAG | $TT | $DD | small_area=$SA | finished=$FIN"
done
bash /mnt/d/WSL/force_clean2.sh | tail -1
echo BIGSCENE_DONE
