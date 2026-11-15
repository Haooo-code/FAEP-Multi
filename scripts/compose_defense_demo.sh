#!/bin/bash
# 将四段 RViz 原始录像裁剪并合成为 75 秒答辩演示。
set -o pipefail

SOURCE_ROOT=${DEFENSE_VIDEO_OUT:-/mnt/d/WSL/defense_video_rec_20261115}
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT="$SOURCE_ROOT/demo_75s.mp4"
SRT="$SOURCE_ROOT/demo_75s.srt"

cp "$REPO_ROOT/media/demo_75s.srt" "$SRT"

crop_recording() {
  local source=$1
  local output=$2
  ffmpeg -y -loglevel error -i "$source" \
    -vf "crop=1128:634:350:350,fps=30" \
    -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -r 30 -movflags +faststart \
    "$output"
}

crop_recording "$SOURCE_ROOT/single/raw_single.mp4" "$SOURCE_ROOT/single_full_rviz.mp4"
crop_recording "$SOURCE_ROOT/independent/raw_independent.mp4" "$SOURCE_ROOT/independent_full_rviz.mp4"
crop_recording "$SOURCE_ROOT/partition/raw_partition.mp4" "$SOURCE_ROOT/partition_full_rviz.mp4"
crop_recording "$SOURCE_ROOT/target/raw_target.mp4" "$SOURCE_ROOT/target_full_rviz.mp4"

ffmpeg -y -loglevel error \
  -ss 55 -t 15 -i "$SOURCE_ROOT/single/raw_single.mp4" \
  -ss 135 -t 15 -i "$SOURCE_ROOT/independent/raw_independent.mp4" \
  -ss 58 -t 15 -i "$SOURCE_ROOT/partition/raw_partition.mp4" \
  -ss 4.7 -t 30 -i "$SOURCE_ROOT/target/raw_target.mp4" \
  -filter_complex "\
[0:v]crop=1128:634:350:350,scale=1920:1080,setsar=1,setpts=PTS-STARTPTS[v0];\
[1:v]crop=1128:634:350:350,scale=1920:1080,setsar=1,setpts=PTS-STARTPTS[v1];\
[2:v]crop=1128:634:350:350,scale=1920:1080,setsar=1,setpts=PTS-STARTPTS[v2];\
[3:v]crop=1128:634:350:350,scale=1920:1080,setsar=1,setpts=PTS-STARTPTS[v3];\
[v0][v1][v2][v3]concat=n=4:v=1:a=0[v];\
[v]subtitles='$SRT':force_style='FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&H00151515,BackColour=&H80FFFFFF,BorderStyle=4,Outline=0,Shadow=0,MarginV=28,Alignment=2'[out]" \
  -map "[out]" -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -r 30 -movflags +faststart \
  "$OUT"

ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
echo "DEMO_READY=$OUT"
