#!/bin/bash
# 单机 office 跑一轮 + 全程 RViz 抓帧 + 日志采样（供"小区域机制"录屏素材）
# 用法: run_single_rec.sh [TAG] [init_x] [init_y] [init_z]
#   产出：rec_frames_<TAG>/*.png、edge_debug_<TAG>.log、sim_<TAG>.log
export DISPLAY=:0
TAG=${1:-main}
INIT_X=${2:-0.0}
INIT_Y=${3:-0.0}
INIT_Z=${4:-1.0}
OUT=/mnt/d/WSL/rec_frames_$TAG
SIMLOG=/mnt/d/WSL/sim_$TAG.log
DBGLOG=/mnt/d/WSL/edge_debug_$TAG.log
mkdir -p "$OUT"
rm -f "$OUT"/*.png "$SIMLOG" "$DBGLOG" 2>/dev/null
rm -f /tmp/cap_loop_$TAG.log

echo "=== clean old procs ==="
bash /mnt/d/WSL/force_clean2.sh | tail -2

echo "=== start sim ==="
# debug_file 参数在 algorithm_node.xml（algorithm.xml 只负责 include）
sed -i "s#<param name=\"frontier/debug_file\" value=\"[^\"]*\" type=\"string\"/>#<param name=\"frontier/debug_file\" value=\"$DBGLOG\" type=\"string\"/>#" \
  /home/ubuntu/catkin_ws/src/faep/faep_planner/exploration_manager/launch/algorithm_node.xml
cat > /tmp/run_sim_$TAG.sh <<SIMEOF
#!/bin/bash
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash
ulimit -c unlimited
export LIBC_FATAL_STDERR_=1
exec roslaunch exploration_manager exploration.launch init_x:=$INIT_X init_y:=$INIT_Y init_z:=$INIT_Z > $SIMLOG 2>&1
SIMEOF
nohup bash /tmp/run_sim_$TAG.sh >/dev/null 2>&1 &
for t in $(seq 1 60); do
  grep -q "WAIT_TRIGGER" "$SIMLOG" 2>/dev/null && break
  sleep 2
done
grep -q "WAIT_TRIGGER" "$SIMLOG" || { echo "SIM NOT READY"; tail -20 "$SIMLOG"; exit 1; }
echo "sim ready"

echo "=== start log sampler ==="
nohup python3 /mnt/d/WSL/log_sampler.py "$SIMLOG" /mnt/d/WSL/progress_$TAG.log >/dev/null 2>&1 &
echo $! > /tmp/sampler.pid
sleep 1

echo "=== start rviz (rec config) ==="
cat > /tmp/run_rviz_rec.sh <<'RVEOF'
#!/bin/bash
source /opt/ros/noetic/setup.bash
source /home/ubuntu/catkin_ws/devel/setup.bash
export DISABLE_ROS1_EOL_WARNINGS=1
exec rviz -d /mnt/d/WSL/faep_rec.rviz > /mnt/d/WSL/rviz_rec.log 2>&1
RVEOF
nohup bash /tmp/run_rviz_rec.sh >/dev/null 2>&1 &
sleep 15

echo "=== capture window ids ==="
# 匹配主窗口标题（避开 ROS1 EOL 弹窗：它标题里也含 rviz 字样）
RVIZ=$(xwininfo -root -tree 2>/dev/null | grep -i "rviz" | grep -viE "End-of-Life|EOL" | grep -oE "0x[0-9a-f]+" | head -1)
echo "RVIZ=$RVIZ"
[ -z "$RVIZ" ] && { echo "NO RVIZ WINDOW"; exit 1; }

echo "=== start frame capture ==="
rm -f /tmp/cap_stop_xwd
RVIZ_WID=$RVIZ OUTDIR=$OUT STOPFILE=/tmp/cap_stop_xwd nohup python3 /mnt/d/WSL/capture_loop_xwd.py > /tmp/cap_loop_$TAG.log 2>&1 &
echo $! > /tmp/cap.pid
sleep 2

echo "=== trigger exploration ==="
bash /mnt/d/WSL/trigger.sh

echo "=== wait for finish (max 420s) ==="
FIN=0
for t in $(seq 1 140); do
  grep -q "Flight_time]" "$SIMLOG" 2>/dev/null && { FIN=1; break; }
  sleep 3
done
echo "FINISHED=$FIN after ~$((t*3))s"

echo "=== stop capture ==="
touch /tmp/cap_stop_xwd
sleep 2
kill "$(cat /tmp/sampler.pid)" 2>/dev/null || true

grep -o "Flight_time]: .*" "$SIMLOG" | tail -1
grep -o "Flight_dist]: .*" "$SIMLOG" | tail -1
echo "frames: $(ls "$OUT" | wc -l)"
echo "small-area triggers in sim log: $(grep -c 'small area higher priority' "$SIMLOG")"
echo "REC_DONE"
