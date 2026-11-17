#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORK_DIR="/mnt/d/WSL/video_edit_20261115/build_complete"
OLD_VIDEO="/mnt/c/Users/ONE BOY/Desktop/微信视频2026-10-29_232701_742.mp4"
OUTPUT_DESKTOP="/mnt/c/Users/ONE BOY/Desktop/FAEP-Multi_国赛答辩_完整旁白版_5min.mp4"
OUTPUT_REPO="${REPO_ROOT}/media/FAEP-Multi_国赛答辩_完整旁白版_5min.mp4"

mkdir -p "${WORK_DIR}"

build_patched_original() {
  local filter
  filter="[0:v]split=2[base][depthsrc];"
  filter+="[depthsrc]trim=start=57.5:end=68.5,setpts=PTS-STARTPTS,"
  filter+="crop=600:380:1240:534,scale=600:380,setsar=1,"
  filter+="setpts=PTS+57.5/TB[depth];"
  filter+="[1:v]fps=30,scale=1920:1080,setsar=1,"
  filter+="trim=duration=11,setpts=PTS-STARTPTS+57.5/TB,"
  filter+="drawbox=x=0:y=0:w=iw:h=124:color=0x07111F@0.60:t=fill,"
  filter+="drawbox=x=1190:y=500:w=700:h=520:color=0x07111F@0.82:t=fill[single];"
  filter+="[single][depth]overlay=x=1240:y=560:eof_action=pass,"
  filter+="drawbox=x=1236:y=556:w=608:h=388:color=0xF4F7FB@0.90:t=4,"
  filter+="fade=t=in:st=57.5:d=0.25,fade=t=out:st=68.25:d=0.25:color=white[scene1];"
  filter+="[base][scene1]overlay=x=0:y=0:eof_action=pass:"
  filter+="enable='between(t,57.5,68.5)'[base1];"
  filter+="[2:v]fps=30,scale=1920:1080,setsar=1,"
  filter+="trim=duration=20,setpts=PTS-STARTPTS+125/TB,"
  filter+="drawbox=x=0:y=0:w=iw:h=124:color=0x07111F@0.68:t=fill,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:"
  filter+="text='三机同场复现':fontcolor=white:fontsize=48:x=54:y=42:"
  filter+="box=1:boxcolor=0x07111F@0.84:boxborderw=20,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
  filter+="text='障碍物  局部地图  相机视场':fontcolor=white:fontsize=28:"
  filter+="x=w-tw-70:y=54:box=1:boxcolor=black@0.52:boxborderw=10,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
  filter+="text='D1  蓝色':fontcolor=0x4B9DFF:fontsize=28:x=1420:y=760:"
  filter+="box=1:boxcolor=black@0.58:boxborderw=10,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
  filter+="text='D2  橙色':fontcolor=0xFF9F45:fontsize=28:x=1580:y=760:"
  filter+="box=1:boxcolor=black@0.58:boxborderw=10,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
  filter+="text='D3  绿色':fontcolor=0x47C56A:fontsize=28:x=1740:y=760:"
  filter+="box=1:boxcolor=black@0.58:boxborderw=10,"
  filter+="fade=t=in:st=125:d=0.25,fade=t=out:st=144.75:d=0.25:color=white[scene2];"
  filter+="[base1][scene2]overlay=x=0:y=0:eof_action=pass:"
  filter+="enable='between(t,125,145)'[base2];"
  filter+="[3:v]fps=30,scale=1820:760:force_original_aspect_ratio=decrease,"
  filter+="pad=1920:1080:(ow-iw)/2:160:color=0xF3F6FA,setsar=1,"
  filter+="trim=duration=10,setpts=PTS-STARTPTS+145/TB,"
  filter+="drawbox=x=0:y=0:w=iw:h=124:color=0x07111F@0.68:t=fill,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:"
  filter+="text='协同效果统计验证':fontcolor=white:fontsize=48:x=54:y=42:"
  filter+="box=1:boxcolor=0x07111F@0.84:boxborderw=20,"
  filter+="drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
  filter+="text='时间指标  |  空间分工':fontcolor=white:fontsize=28:"
  filter+="x=w-tw-70:y=54:box=1:boxcolor=black@0.52:boxborderw=10,"
  filter+="format=yuv420p,"
  filter+="fade=t=in:st=145:d=0.25,fade=t=out:st=154.75:d=0.25:color=white[scene3];"
  filter+="[base2][scene3]overlay=x=0:y=0:eof_action=pass:"
  filter+="enable='between(t,145,155)',"
  filter+="ass=${SCRIPT_DIR}/patched_original.ass:fontsdir=/usr/share/fonts/opentype/noto,"
  filter+="format=yuv420p[vout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -i "${OLD_VIDEO}" \
    -ss 36 -t 11 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 10 -t 20 -i "${REPO_ROOT}/media/rviz_multi_partition_full_scene.mp4" \
    -loop 1 -framerate 30 -t 10 -i "${REPO_ROOT}/docs/figures/fig_coordination_ladder_20261115.png" \
    -filter_complex "${filter}" \
    -map "[vout]" -map 0:a:0 \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart \
    "${WORK_DIR}/original_patched_complete_audio.mp4"
}

build_final() {
  printf "file '%s'\n" \
    "${WORK_DIR}/original_patched_complete_audio.mp4" \
    "/mnt/d/WSL/video_edit_20261115/build/experiments_section_76_7s.mp4" \
    > "${WORK_DIR}/concat.txt"

  ffmpeg -y -hide_banner -loglevel warning \
    -f concat -safe 0 -i "${WORK_DIR}/concat.txt" \
    -c copy -movflags +faststart "${WORK_DIR}/FAEP-Multi_国赛答辩_完整旁白版_5min.mp4"

  cp "${WORK_DIR}/FAEP-Multi_国赛答辩_完整旁白版_5min.mp4" "${OUTPUT_DESKTOP}"
  cp "${WORK_DIR}/FAEP-Multi_国赛答辩_完整旁白版_5min.mp4" "${OUTPUT_REPO}"
}

build_patched_original
build_final

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels \
  -of default=nw=1 "${WORK_DIR}/FAEP-Multi_国赛答辩_完整旁白版_5min.mp4"
