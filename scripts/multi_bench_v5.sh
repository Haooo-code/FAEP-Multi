#!/bin/bash
# 大场景 A/B/C 批跑（office2/office3）
#   A = 单机（exploration.launch 参数化）
#   B = 三机独立（multi_bringup，无协调）
#   C = 三机协同（multi_bringup + 协调器）
# 用法: multi_bench_v5.sh <A|B|C> <轮数> <起始轮> <地图名> <场景标签> [附加roslaunch参数]
#   地图名: office | office2 | office3 | <绝对路径.pcd>
# 结果: /mnt/d/WSL/multi_big_results.txt；每轮日志 multi_<场景><MODE>_runN.log
MODE=${1:?用法: multi_bench_v5.sh A|B|C <轮数> <起始轮> <地图名> <场景标签>}
N=${2:-1}
START=${3:-1}
MAPNAME=${4:-office2}
SCEN=${5:-$MAPNAME}
EXTRA=${6:-}
RESULTS=/mnt/d/WSL/multi_big_results.txt

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
    MAPFILE=$MAPNAME; BX0=-10; BY0=-10; BX1=10; BY1=10; MSIZE=42
    D1X=0; D1Y=0; D1Z=1.0; D2X=4; D2Y=4; D2Z=1.4; D3X=-4; D3Y=-4; D3Z=1.8
    ;;
esac

source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash

for i in $(seq "$START" $((START + N - 1))); do
  LOG="/mnt/d/WSL/multi_${SCEN}${MODE}_run${i}.log"
  echo "===== [${SCEN}-${MODE} RUN $i] START $(date +%H:%M:%S) ====="
  bash /mnt/d/WSL/force_clean2.sh > /dev/null 2>&1
  sleep 2

  if [ "$MODE" = "A" ]; then
    roslaunch exploration_manager exploration.launch \
      map_file:=$MAPFILE map_size_x:=$MSIZE map_size_y:=$MSIZE \
      box_x_min:=$BX0 box_y_min:=$BY0 box_x_max:=$BX1 box_y_max:=$BY1 \
      init_x:=$D1X init_y:=$D1Y init_z:=$D1Z > "$LOG" 2>&1 &
    RPID=$!
    OK=0
    for t in $(seq 1 90); do
      grep -q "WAIT_TRIGGER" "$LOG" 2>/dev/null && { OK=1; break; }
      sleep 2
    done
    [ "$OK" != "1" ] && { echo "[$SCEN-$MODE RUN $i] ready timeout"; kill $RPID 2>/dev/null; continue; }
    sleep 10
    T0=$(date +%s)
    bash /mnt/d/WSL/trigger.sh > /dev/null 2>&1
    for t in $(seq 1 200); do
      grep -q "Flight_time]" "$LOG" 2>/dev/null && break
      sleep 3
    done
  else
    COORD=false
    [ "$MODE" = "C" ] && COORD=true
    roslaunch exploration_manager multi_bringup.launch use_coord:=$COORD \
      map_file:=$MAPFILE map_size_x:=$MSIZE map_size_y:=$MSIZE map_size_z:=10.0 \
      box_x_min:=$BX0 box_y_min:=$BY0 box_z_min:=-0.1 box_x_max:=$BX1 box_y_max:=$BY1 box_z_max:=2.0 \
      d1_x:=$D1X d1_y:=$D1Y d1_z:=$D1Z d2_x:=$D2X d2_y:=$D2Y d2_z:=$D2Z d3_x:=$D3X d3_y:=$D3Y d3_z:=$D3Z \
      $EXTRA \
      > "$LOG" 2>&1 &
    RPID=$!
    TRACK="/mnt/d/WSL/track_${SCEN}_${MODE}_${i}.csv"
    python3 /mnt/d/WSL/coord_logger.py "$TRACK" > /dev/null 2>&1 &
    LPID=$!
    OK=0
    for t in $(seq 1 90); do
      SESS=$(ls -td /home/ubuntu/.ros/log/*/ 2>/dev/null | head -1)
      CNT=$(grep -a "state: WAIT_TRIGGER" "${SESS}rosout.log" 2>/dev/null | grep -oE "drone[0-9]/exploration_node" | sort -u | wc -l)
      [ "$CNT" -ge 3 ] && { OK=1; break; }
      sleep 2
    done
    [ "$OK" != "1" ] && { echo "[$SCEN-$MODE RUN $i] ready timeout"; kill $RPID $LPID 2>/dev/null; continue; }
    sleep 8
    SESS=$(ls -td /home/ubuntu/.ros/log/*/ 2>/dev/null | head -1)
    T0=$(date +%s)
    bash /mnt/d/WSL/trigger_multi.sh > /dev/null 2>&1
    if [ "$COORD" = "true" ]; then
      for t in $(seq 1 300); do
        CNT=$(grep -ac "HALT received" "$LOG" 2>/dev/null | tail -1); [ -z "$CNT" ] && CNT=0
        [ "$CNT" -ge 3 ] && break
        sleep 3
      done
    else
      for t in $(seq 1 300); do
        CNT=$(grep -a "state: FINISH" "${SESS}rosout.log" 2>/dev/null | grep -oE "drone[0-9]/exploration_node" | sort -u | wc -l)
        [ "$CNT" -ge 3 ] && break
        sleep 3
      done
    fi
    kill $LPID 2>/dev/null
  fi
  T1=$(date +%s)
  sleep 3
  kill $RPID 2>/dev/null
  sleep 3
  bash /mnt/d/WSL/force_clean2.sh > /dev/null 2>&1
  cp "${SESS}rosout.log" "/mnt/d/WSL/multi_${SCEN}${MODE}_run${i}_rosout.log" 2>/dev/null

  echo "--- [${SCEN}-${MODE} RUN $i] wall_total=$((T1 - T0))s" >> "$RESULTS"
  grep -a "Flight_time" "$LOG" | grep -aoE "\[Flight_time\]: [0-9.]+ \(drone [0-9]\)" | sort -u | sed "s/^/[$SCEN-$MODE-$i] /" >> "$RESULTS"
  grep -a "Flight_dist" "$LOG" | grep -aoE "\[Flight_dist\]: [0-9.]+ \(drone [0-9]\)" | sort -u | sed "s/^/[$SCEN-$MODE-$i] /" >> "$RESULTS"
  if [ "$MODE" = "C" ]; then
    grep -a "HALT received" "$LOG" | grep -aoE "drone [0-9]" | sort -u | head -3 | sed "s/^/[$SCEN-$MODE-$i] HALT /" >> "$RESULTS"
  fi
  echo "===== [${SCEN}-${MODE} RUN $i] DONE $(date +%H:%M:%S) ====="
done
echo "ALL ${SCEN}-${MODE} RUNS DONE"
