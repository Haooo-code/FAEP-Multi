#!/bin/bash
# 故障注入批跑：三机协同跑到中途，kill -9 指定机的 exploration_node
# 用法: fault_bench.sh <轮数> <起始轮> <地图名> <标签> <杀机秒> <目标机号> [附加roslaunch参数]
#   例: fault_bench.sh 3 1 office2 fault 30 2 "partition_mode:=true"
# 结果: /mnt/d/WSL/fault_results.txt；日志 multi_<标签>C_runN.log
# ROS 的 setup.bash 会引用未定义的 ROS_DISTRO，不能用 set -u
set +u

N=${1:-1}
START=${2:-1}
MAPNAME=${3:-office2}
SCEN=${4:-$MAPNAME}
KILL_AT=${5:-30}
KILL_ID=${6:-2}
EXTRA=${7:-}
RESULTS=/mnt/d/WSL/fault_results.txt

case "$MAPNAME" in
  office)
    MAPFILE=/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office.pcd
    BX0=-8.0; BY0=-15.0; BX1=8.0; BY1=15.0; MSIZE=50
    D1X=-6.0; D1Y=0.0; D1Z=1.0; D2X=6.0; D2Y=2.0; D2Z=1.4; D3X=0.0; D3Y=10.0; D3Z=1.8
    ;;
  office2)
    MAPFILE=/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office2.pcd
    BX0=-10.4; BY0=-9.9; BX1=10.4; BY1=9.9; MSIZE=42
    D1X=-7.5; D1Y=-3.5; D1Z=1.0; D2X=4.5; D2Y=-3.5; D2Z=1.4; D3X=-3.5; D3Y=6.5; D3Z=1.8
    ;;
  office3)
    MAPFILE=/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office3.pcd
    BX0=-9.6; BY0=-14.2; BX1=10.0; BY1=14.4; MSIZE=44
    D1X=-3.2; D1Y=10.2; D1Z=1.0; D2X=-3.2; D2Y=2.2; D2Z=1.4; D3X=-3.2; D3Y=-5.8; D3Z=1.8
    ;;
  *)
    echo "未知地图: $MAPNAME"; exit 2
    ;;
esac

source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash

for i in $(seq "$START" $((START + N - 1))); do
  LOG="/mnt/d/WSL/multi_${SCEN}C_run${i}.log"
  TRACK="/mnt/d/WSL/track_${SCEN}_fault_${i}.csv"
  echo "===== [${SCEN}-FAULT RUN $i] START $(date +%H:%M:%S) kill=d${KILL_ID}@${KILL_AT}s ====="
  bash /mnt/d/WSL/force_clean2.sh > /dev/null 2>&1
  sleep 2

  roslaunch exploration_manager multi_bringup.launch use_coord:=true \
    map_file:=$MAPFILE map_size_x:=$MSIZE map_size_y:=$MSIZE map_size_z:=10.0 \
    box_x_min:=$BX0 box_y_min:=$BY0 box_z_min:=-0.1 box_x_max:=$BX1 box_y_max:=$BY1 box_z_max:=2.0 \
    d1_x:=$D1X d1_y:=$D1Y d1_z:=$D1Z d2_x:=$D2X d2_y:=$D2Y d2_z:=$D2Z d3_x:=$D3X d3_y:=$D3Y d3_z:=$D3Z \
    $EXTRA > "$LOG" 2>&1 &
  RPID=$!
  python3 /mnt/d/WSL/coord_logger.py "$TRACK" > /dev/null 2>&1 &
  LPID=$!

  OK=0
  for t in $(seq 1 90); do
    SESS=$(ls -td /home/ubuntu/.ros/log/*/ 2>/dev/null | head -1)
    CNT=$(grep -a "state: WAIT_TRIGGER" "${SESS}rosout.log" 2>/dev/null | grep -oE "drone[0-9]/exploration_node" | sort -u | wc -l)
    [ "$CNT" -ge 3 ] && { OK=1; break; }
    sleep 2
  done
  if [ "$OK" != "1" ]; then
    echo "[${SCEN}-FAULT RUN $i] ready timeout"
    kill $RPID $LPID 2>/dev/null
    continue
  fi
  sleep 8
  SESS=$(ls -td /home/ubuntu/.ros/log/*/ 2>/dev/null | head -1)
  T0=$(date +%s)
  bash /mnt/d/WSL/trigger_multi.sh > /dev/null 2>&1

  sleep "$KILL_AT"
  KILL_TS=$(date +%s)
  # 直接从 /proc 命令行按 droneN 重映射找 PID，避免 rosnode info 的十余秒握手延迟
  PID=$(pgrep -af "exploration_node" | grep "/drone${KILL_ID}/" | awk '{print $1}' | head -1)
  if [ -z "$PID" ]; then
    INFO=$(rosnode info "/drone${KILL_ID}/exploration_node" 2>/dev/null || true)
    PID=$(printf '%s\n' "$INFO" | sed -n 's/^Pid: //p' | head -1)
  fi
  if [ -n "$PID" ]; then
    kill -9 "$PID" 2>/dev/null || true
    echo "[${SCEN}-FAULT RUN $i] killed /drone${KILL_ID}/exploration_node pid=$PID at +$((KILL_TS - T0))s"
  else
    echo "[${SCEN}-FAULT RUN $i] WARN: cannot resolve pid for /drone${KILL_ID}/exploration_node"
  fi

  # 失联检测 10s + 降级恢复；给足 300s 让幸存机完成或触发全局超时
  for t in $(seq 1 100); do
    CNT=$(grep -ac "HALT received" "$LOG" 2>/dev/null | tail -1); [ -z "$CNT" ] && CNT=0
    [ "$CNT" -ge 2 ] && break
    sleep 3
  done
  T1=$(date +%s)
  sleep 3
  kill $RPID $LPID 2>/dev/null
  sleep 3
  bash /mnt/d/WSL/force_clean2.sh > /dev/null 2>&1
  cp "${SESS}rosout.log" "/mnt/d/WSL/multi_${SCEN}C_run${i}_rosout.log" 2>/dev/null

  HALT_CNT=$(grep -ac "HALT received" "$LOG" 2>/dev/null | tail -1); [ -z "$HALT_CNT" ] && HALT_CNT=0
  LOST_CNT=$(grep -ac "drone${KILL_ID} lost (>" "$LOG" 2>/dev/null | tail -1); [ -z "$LOST_CNT" ] && LOST_CNT=0
  DEGRADED_CNT=$(grep -ac "partition degraded" "$LOG" 2>/dev/null | tail -1); [ -z "$DEGRADED_CNT" ] && DEGRADED_CNT=0
  echo "--- [${SCEN}-FAULT RUN $i] wall_total=$((T1 - T0))s kill_at=$((KILL_TS - T0))s target=drone${KILL_ID} halt=$HALT_CNT lost=$LOST_CNT degraded=$DEGRADED_CNT" >> "$RESULTS"
  grep -a "Flight_time" "$LOG" | grep -aoE "\[Flight_time\]: [0-9.]+ \(drone [0-9]\)" | sort -u | sed "s/^/[$SCEN-FAULT-$i] /" >> "$RESULTS"
  grep -a "Flight_dist" "$LOG" | grep -aoE "\[Flight_dist\]: [0-9.]+ \(drone [0-9]\)" | sort -u | sed "s/^/[$SCEN-FAULT-$i] /" >> "$RESULTS"
  grep -a "assign task" "$LOG" | tail -n 20 | sed "s/^/[$SCEN-FAULT-$i] /" >> "$RESULTS"
  echo "===== [${SCEN}-FAULT RUN $i] DONE $(date +%H:%M:%S) ====="
done
echo "ALL ${SCEN}-FAULT RUNS DONE"
