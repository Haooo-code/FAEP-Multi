#!/bin/bash
# 目标搜索单场景回归脚本
# 用法：target_search_regression.sh <场景名> <confirmed|not_found> [roslaunch 参数...]
# 输出统一写入 /mnt/d/WSL/target_search_20261115，便于与仓库实验文档核对。

set -o pipefail

SCENARIO=${1:?缺少场景名}
EXPECTED=${2:?缺少期望结果 confirmed 或 not_found}
shift 2

OUT_DIR=${TARGET_SEARCH_OUT_DIR:-/mnt/d/WSL/target_search_20261115}
MAX_WAIT=${TARGET_SEARCH_MAX_WAIT:-210}
LOG="$OUT_DIR/${SCENARIO}.log"
STATUS_LOG="$OUT_DIR/${SCENARIO}_target_status.csv"
MARKER_LOG="$OUT_DIR/${SCENARIO}_marker.yaml"
FIRST_MARKER_LOG="$OUT_DIR/${SCENARIO}_first_marker.yaml"
TRACK_LOG="$OUT_DIR/${SCENARIO}_track.csv"
ROSOUT_LOG="$OUT_DIR/${SCENARIO}_rosout.log"
SUMMARY_FILE="$OUT_DIR/target_search_regression.tsv"

MAP_FILE=/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office2.pcd

mkdir -p "$OUT_DIR"
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash

cleanup() {
  kill "${INJECT_PID:-}" "${FIRST_MARKER_PID:-}" "${STATUS_PID:-}" "${TRACK_PID:-}" "${LAUNCH_PID:-}" 2>/dev/null || true
  wait "${INJECT_PID:-}" "${FIRST_MARKER_PID:-}" "${STATUS_PID:-}" "${TRACK_PID:-}" "${LAUNCH_PID:-}" 2>/dev/null || true
  sleep 1
  bash /mnt/d/WSL/force_clean2.sh >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

bash /mnt/d/WSL/force_clean2.sh >/dev/null 2>&1 || true
sleep 2

roslaunch exploration_manager multi_bringup.launch \
  use_coord:=true partition_mode:=true \
  map_file:="$MAP_FILE" map_size_x:=42 map_size_y:=42 map_size_z:=10.0 \
  box_x_min:=-10.4 box_y_min:=-9.9 box_z_min:=-0.1 \
  box_x_max:=10.4 box_y_max:=9.9 box_z_max:=2.0 \
  d1_x:=-7.5 d1_y:=-3.5 d1_z:=1.0 \
  d2_x:=4.5 d2_y:=-3.5 d2_z:=1.4 \
  d3_x:=-3.5 d3_y:=6.5 d3_z:=1.8 \
  target_search_enabled:=true "$@" >"$LOG" 2>&1 &
LAUNCH_PID=$!

READY=0
for _ in $(seq 1 100); do
  SESS=$(find /home/ubuntu/.ros/log -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null |
    sort -nr | head -1 | cut -d' ' -f2-)
  READY_COUNT=$(grep -a "state: WAIT_TRIGGER" "${SESS}/rosout.log" 2>/dev/null |
    grep -oE "drone[0-9]/exploration_node" | sort -u | wc -l)
  if [ "$READY_COUNT" -ge 3 ]; then
    READY=1
    break
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    break
  fi
  sleep 2
done

if [ "$READY" -ne 1 ]; then
  RESULT=startup_timeout
  WALL_S=0
else
  python3 "/mnt/c/Users/ONE BOY/Documents/ChatGPT/aic算法/repo_ready/scripts/coord_logger.py" \
    "$TRACK_LOG" >/dev/null 2>&1 &
  TRACK_PID=$!
  rostopic echo -p /target/status >"$STATUS_LOG" 2>&1 &
  STATUS_PID=$!
  sleep 8
  rostopic echo -n 1 /target/marker >"$FIRST_MARKER_LOG" 2>&1 &
  FIRST_MARKER_PID=$!
  if [ "${TARGET_SEARCH_INJECT_INCONSISTENT:-0}" = "1" ]; then
    (
      for _ in $(seq 1 600); do
        if grep -aq "\[target\] state=VERIFYING" "$LOG" 2>/dev/null; then
          rostopic pub -1 /target/detection coord_msgs/TargetDetection \
            "{header: {frame_id: world}, source_id: 1, target_class: person, confidence: 0.99, position: {x: -5.0, y: -5.0, z: 1.0}, requires_verification: false}" \
            >/dev/null 2>&1
          break
        fi
        sleep 0.2
      done
    ) &
    INJECT_PID=$!
  fi
  START_S=$(date +%s)
  bash /mnt/d/WSL/trigger_multi.sh >/dev/null 2>&1

  RESULT=timeout
  for _ in $(seq 1 "$MAX_WAIT"); do
    HALT_COUNT=$(grep -ac "HALT received" "$LOG" 2>/dev/null | tail -1)
    HALT_COUNT=${HALT_COUNT:-0}
    if [ "$EXPECTED" = "confirmed" ] &&
       grep -aq "\[target\] CONFIRMED" "$LOG" && [ "$HALT_COUNT" -ge 3 ]; then
      RESULT=confirmed
      break
    fi
    if [ "$EXPECTED" = "not_found" ] &&
       grep -aq "\[target\] NOT_FOUND" "$LOG" && [ "$HALT_COUNT" -ge 3 ]; then
      RESULT=not_found
      break
    fi
    if [ "$EXPECTED" = "halt_only" ] && [ "$HALT_COUNT" -ge 3 ]; then
      RESULT=full_coverage
      break
    fi
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
      RESULT=launch_exited
      break
    fi
    sleep 1
  done
  WALL_S=$(( $(date +%s) - START_S ))
fi

timeout 5 rostopic echo -n 1 /target/marker >"$MARKER_LOG" 2>&1 || true
SESS=$(find /home/ubuntu/.ros/log -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null |
  sort -nr | head -1 | cut -d' ' -f2-)
cp "${SESS}/rosout.log" "$ROSOUT_LOG" 2>/dev/null || true

CONFIRM_LINE=$(grep -a "\[target\] CONFIRMED" "$LOG" | tail -1)
NOT_FOUND_LINE=$(grep -a "\[target\] NOT_FOUND" "$LOG" | tail -1)
VERIFIER_LINES=$(grep -a "assigned to verify candidate" "$LOG" | sed 's/.*\[TARGET\] //' |
  paste -sd' | ' -)
STATE_LINES=$(grep -a "\[target\] state=" "$LOG" | sed 's/.*\[target\] //' |
  paste -sd' | ' -)
INCONSISTENT_COUNT=$(grep -ac "ignored inconsistent detection" "$LOG" 2>/dev/null | tail -1)
INJECT_REQUESTED=${TARGET_SEARCH_INJECT_INCONSISTENT:-0}
HALT_COUNT=$(grep -ac "HALT received" "$LOG" 2>/dev/null | tail -1)
FLIGHT_TIMES=$(grep -a "Flight_time" "$LOG" |
  grep -aoE "\[Flight_time\]: [0-9.]+ \(drone [0-9]\)" | sort -u | paste -sd' | ' -)
MARKER_TYPE=$(grep -a "^type:" "$MARKER_LOG" | tail -1 | awk '{print $2}')
MARKER_X=$(awk '/^scale:/{in_scale=1; next} in_scale && /^  x:/{print $2; exit}' "$MARKER_LOG")
MARKER_R=$(awk '/^color:/{in_color=1; next} in_color && /^  r:/{print $2; exit}' "$MARKER_LOG")
MARKER_G=$(awk '/^color:/{in_color=1; next} in_color && /^  g:/{print $2; exit}' "$MARKER_LOG")
FIRST_MARKER_TYPE=$(grep -a "^type:" "$FIRST_MARKER_LOG" | head -1 | awk '{print $2}')
FIRST_MARKER_X=$(awk '/^scale:/{in_scale=1; next} in_scale && /^  x:/{print $2; exit}' "$FIRST_MARKER_LOG")
FIRST_MARKER_R=$(awk '/^color:/{in_color=1; next} in_color && /^  r:/{print $2; exit}' "$FIRST_MARKER_LOG")
FIRST_MARKER_G=$(awk '/^color:/{in_color=1; next} in_color && /^  g:/{print $2; exit}' "$FIRST_MARKER_LOG")

printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$SCENARIO" "$EXPECTED" "$RESULT" "$WALL_S" "$HALT_COUNT" \
  "$CONFIRM_LINE" "$NOT_FOUND_LINE" "$VERIFIER_LINES" "$STATE_LINES" \
  "$INCONSISTENT_COUNT" "$FLIGHT_TIMES" >>"$SUMMARY_FILE"

{
  echo "scenario=$SCENARIO"
  echo "expected=$EXPECTED"
  echo "result=$RESULT"
  echo "wall_s=$WALL_S"
  echo "halt_count=$HALT_COUNT"
  echo "marker_type=$MARKER_TYPE"
  echo "marker_scale_x=$MARKER_X"
  echo "marker_color_r=$MARKER_R"
  echo "marker_color_g=$MARKER_G"
  echo "first_marker_type=$FIRST_MARKER_TYPE"
  echo "first_marker_scale_x=$FIRST_MARKER_X"
  echo "first_marker_color_r=$FIRST_MARKER_R"
  echo "first_marker_color_g=$FIRST_MARKER_G"
  echo "inconsistent_detections=$INCONSISTENT_COUNT"
  echo "inconsistent_injection_requested=$INJECT_REQUESTED"
  echo "confirm=$CONFIRM_LINE"
  echo "not_found=$NOT_FOUND_LINE"
  echo "verifier_assignments=$VERIFIER_LINES"
  echo "state_transitions=$STATE_LINES"
  echo "flight_times=$FLIGHT_TIMES"
} >"$OUT_DIR/${SCENARIO}_summary.txt"

cat "$OUT_DIR/${SCENARIO}_summary.txt"
