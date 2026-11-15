#!/bin/bash
# 国赛 RViz 录屏：single / independent / partition / target
set -o pipefail

MODE=${1:?用法: record_defense_video.sh single|independent|partition|target}
OUT_ROOT=${DEFENSE_VIDEO_OUT:-/mnt/d/WSL/defense_video_rec_20261115}
MAP_FILE=/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office2.pcd
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT="$OUT_ROOT/$MODE"
FRAMES_LOG="$OUT/roslaunch.log"
RViz_LOG="$OUT/rviz.log"
VIDEO="$OUT/raw_${MODE}.mp4"
FRAME_DIR="$OUT/frames"
FPS=${DEFENSE_VIDEO_FPS:-10}
OUTPUT_FPS=${DEFENSE_VIDEO_OUTPUT_FPS:-30}
STOP_FILE="/tmp/defense_video_stop_${MODE}"

source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash
mkdir -p "$OUT"
mkdir -p "$FRAME_DIR"
find "$FRAME_DIR" -maxdepth 1 -type f -name 'f_*.xwd' -delete
rm -f "$STOP_FILE"

cleanup() {
  kill "${CAPTURE_PID:-}" "${TRAIL_PID:-}" "${RVIZ_PID:-}" "${SIM_PID:-}" 2>/dev/null || true
  touch "$STOP_FILE"
  bash /mnt/d/WSL/force_clean2.sh >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

bash /mnt/d/WSL/force_clean2.sh >/dev/null 2>&1 || true
sleep 2

COMMON_MULTI=(
  map_file:="$MAP_FILE" map_size_x:=42 map_size_y:=42 map_size_z:=10.0
  box_x_min:=-10.4 box_y_min:=-9.9 box_z_min:=-0.1
  box_x_max:=10.4 box_y_max:=9.9 box_z_max:=2.0
  d1_x:=-7.5 d1_y:=-3.5 d1_z:=1.0
  d2_x:=4.5 d2_y:=-3.5 d2_z:=1.4
  d3_x:=-3.5 d3_y:=6.5 d3_z:=1.8
)

case "$MODE" in
  single)
    RVIZ_CONFIG="$REPO_ROOT/src/faep_planner/exploration_manager/config/record_single_full.rviz"
    roslaunch exploration_manager exploration.launch \
      map_file:="$MAP_FILE" map_size_x:=42 map_size_y:=42 map_size_z:=10.0 \
      box_x_min:=-10.4 box_y_min:=-9.9 box_z_min:=-0.1 \
      box_x_max:=10.4 box_y_max:=9.9 box_z_max:=2.0 \
      init_x:=-7.5 init_y:=-3.5 init_z:=1.0 >"$FRAMES_LOG" 2>&1 &
    SIM_PID=$!
    ;;
  independent|partition|target)
    RVIZ_CONFIG="$REPO_ROOT/src/faep_planner/exploration_manager/config/record_multi_full.rviz"
    USE_COORD=false
    PARTITION=false
    SECTOR_ARGS=(--sectors)
    EXTRA=()
    if [ "$MODE" = "independent" ]; then
      SECTOR_ARGS=()
    elif [ "$MODE" = "partition" ]; then
      USE_COORD=true
      PARTITION=true
    else
      USE_COORD=true
      PARTITION=true
      EXTRA+=(
        target_search_enabled:=true
        target_x:=1.0 target_y:=3.0 target_z:=1.0
        target_prior_x:=1.0 target_prior_y:=3.0 target_prior_z:=1.0
        target_prior_radius:=3.0 target_prior_growth:=0.05
        target_prior_max_radius:=8.0 target_sensor_max_range:=8.0
        target_detection_probability:=0.92
        target_stop_on_confirm:=true
      )
    fi
    roslaunch exploration_manager multi_bringup.launch \
      use_coord:="$USE_COORD" partition_mode:="$PARTITION" \
      "${COMMON_MULTI[@]}" "${EXTRA[@]}" >"$FRAMES_LOG" 2>&1 &
    SIM_PID=$!
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 2
    ;;
esac

READY=0
for _ in $(seq 1 120); do
  SESS=$(find /home/ubuntu/.ros/log -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null |
    sort -nr | head -1 | cut -d' ' -f2-)
  if [ "$MODE" = "single" ]; then
    grep -aq "WAIT_TRIGGER" "${SESS}/rosout.log" 2>/dev/null && READY=1
  else
    COUNT=$(grep -a "state: WAIT_TRIGGER" "${SESS}/rosout.log" 2>/dev/null |
      grep -oE "drone[0-9]/exploration_node" | sort -u | wc -l)
    [ "$COUNT" -ge 3 ] && READY=1
  fi
  [ "$READY" -eq 1 ] && break
  sleep 2
done
[ "$READY" -eq 1 ] || { echo "SIMULATOR_NOT_READY"; exit 3; }

if [ "$MODE" != "single" ]; then
  python3 "$REPO_ROOT/scripts/trail_pub.py" "${SECTOR_ARGS[@]}" \
    --y-min=-9.9 --y-max=9.9 >"$OUT/trail_pub.log" 2>&1 &
  TRAIL_PID=$!
fi

export DISABLE_ROS1_EOL_WARNINGS=1
rviz -d "$RVIZ_CONFIG" >"$RViz_LOG" 2>&1 &
RVIZ_PID=$!
sleep 10

WID=$(xwininfo -root -tree 2>/dev/null | grep -E "record_(single|multi)_full|RViz" |
  grep -oE "0x[0-9a-f]+" | head -1)
[ -n "$WID" ] || { echo "RVIZ_WINDOW_NOT_FOUND"; exit 4; }
eval "$(xwininfo -id "$WID" | awk '
  /Absolute upper-left X:/{print "X=" $4}
  /Absolute upper-left Y:/{print "Y=" $4}
  /Width:/{print "W=" $2}
  /Height:/{print "H=" $2}
')"
W=$((W - W % 2)); H=$((H - H % 2))
echo "RVIZ_WID=$WID geometry=${W}x${H}+${X}+${Y}"

if [ -f /mnt/d/WSL/pin_rviz_size.ps1 ]; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File 'D:\WSL\pin_rviz_size.ps1' -W "$W" -H "$H" 2>/dev/null || true
fi
sleep 3

(
  capture_start=$(date +%s.%N)
  frame_index=0
  while [ ! -f "$STOP_FILE" ] && [ "$frame_index" -lt 7000 ]; do
    frame_index=$((frame_index + 1))
    xwd -id "$WID" -silent -out "$FRAME_DIR/f_$(printf '%05d' "$frame_index").xwd" 2>/dev/null
    now=$(date +%s.%N)
    target_time=$(awk -v start="$capture_start" -v frame_no="$frame_index" -v fps="$FPS" \
      'BEGIN{printf "%.3f", start + frame_no / fps}')
    sleep_ms=$(awk -v target_time="$target_time" -v now="$now" \
      'BEGIN{printf "%.0f", (target_time - now) * 1000}')
    if [ "$sleep_ms" -gt 0 ]; then
      sleep "$(awk -v value="$sleep_ms" 'BEGIN{printf "%.3f", value / 1000}')"
    fi
  done
) &
CAPTURE_PID=$!
PRE_ROLL=3
POST_ROLL=3
if [ "$MODE" = "target" ]; then
  PRE_ROLL=8
  POST_ROLL=5
fi
sleep "$PRE_ROLL"

if [ "$MODE" = "single" ]; then
  bash /mnt/d/WSL/trigger.sh >/dev/null 2>&1
  for _ in $(seq 1 160); do
    grep -aq "Flight_time]" "$FRAMES_LOG" && break
    sleep 2
  done
elif [ "$MODE" = "target" ]; then
  bash "$REPO_ROOT/scripts/trigger_multi.sh" >/dev/null 2>&1
  for _ in $(seq 1 120); do
    HALT_COUNT=$(grep -ac "HALT received" "$FRAMES_LOG" 2>/dev/null | tail -1)
    [ "${HALT_COUNT:-0}" -ge 3 ] && break
    sleep 2
  done
else
  bash "$REPO_ROOT/scripts/trigger_multi.sh" >/dev/null 2>&1
  for _ in $(seq 1 160); do
    COUNT=$(grep -aoE "\[Flight_time\]: [0-9.]+ \(drone [0-9]\)" "$FRAMES_LOG" 2>/dev/null |
      grep -oE "drone [0-9]" | sort -u | wc -l)
    [ "$COUNT" -ge 3 ] && break
    sleep 2
  done
fi

sleep "$POST_ROLL"
touch "$STOP_FILE"
wait "$CAPTURE_PID" 2>/dev/null || true
CAPTURE_PID=
rm -f "$STOP_FILE"
FRAME_COUNT=$(find "$FRAME_DIR" -maxdepth 1 -name 'f_*.xwd' | wc -l)
[ "$FRAME_COUNT" -gt 0 ] || { echo "NO_FRAMES"; exit 5; }
ffmpeg -y -loglevel error -framerate "$FPS" -i "$FRAME_DIR/f_%05d.xwd" \
  -vf "crop=${W}:${H}:0:0,fps=${OUTPUT_FPS}" -c:v libx264 -preset veryfast \
  -crf 18 -pix_fmt yuv420p -r "$OUTPUT_FPS" \
  "$VIDEO"
echo "frames=$FRAME_COUNT capture_fps=$FPS output_fps=$OUTPUT_FPS"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$VIDEO"
echo "VIDEO_READY=$VIDEO"
