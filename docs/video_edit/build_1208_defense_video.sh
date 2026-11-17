#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORK_DIR="/mnt/d/WSL/video_edit_20261115/build"
OLD_VIDEO="/mnt/c/Users/ONE BOY/Desktop/微信视频2026-10-29_232701_742.mp4"
OUTPUT_DESKTOP="/mnt/c/Users/ONE BOY/Desktop/FAEP-Multi_国赛答辩_5min.mp4"
OUTPUT_REPO="${REPO_ROOT}/media/FAEP-Multi_国赛答辩_5min.mp4"

mkdir -p "${WORK_DIR}"

render_runtime() {
  local filter
  filter="[0:v]fps=30,scale=1920:1080,setsar=1,trim=duration=17,setpts=PTS-STARTPTS[v0];"
  filter+="[1:v]fps=30,scale=1920:1080,setsar=1,trim=duration=8.7,setpts=PTS-STARTPTS[v1];"
  filter+="[2:v]fps=30,scale=1920:1080,setsar=1,trim=duration=8.3,setpts=PTS-STARTPTS[v2];"
  filter+="[3:v]fps=30,scale=960:540,pad=960:1080:0:270:color=0x0B1420,setsar=1,trim=duration=11,setpts=PTS-STARTPTS[v3];"
  filter+="[4:v]fps=30,scale=960:540,pad=960:1080:0:270:color=0x0B1420,setsar=1,trim=duration=11,setpts=PTS-STARTPTS[v4];"
  filter+="[v3][v4]hstack=inputs=2,drawbox=x=958:y=0:w=4:h=1080:color=0xF3F6FA@0.55:t=fill[split];"
  filter+="[v0][v1][v2][split]concat=n=4:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=142:color=0x0B1420@0.72:t=fill,"
  filter+="drawbox=x=0:y=ih-140:w=iw:h=140:color=0x0B1420@0.78:t=fill,"
  filter+="drawbox=x=52:y=54:w=7:h=62:color=0x2F80ED@1:t=fill,"
  filter+="ass=${SCRIPT_DIR}/runtime_section.ass:fontsdir=/usr/share/fonts/opentype/noto,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=44.55:d=0.45,format=yuv420p[vout];"
  filter+="[5:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,adelay=500|500,apad,"
  filter+="atrim=duration=45,asetpts=N/SR/TB,afade=t=in:st=0:d=0.25,"
  filter+="afade=t=out:st=43.8:d=1.2[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -ss 32 -t 17 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 55 -t 8.7 -i "${REPO_ROOT}/media/rviz_multi_independent_full_scene.mp4" \
    -ss 10 -t 8.3 -i "${REPO_ROOT}/media/rviz_multi_partition_full_scene.mp4" \
    -ss 72 -t 11 -i "${REPO_ROOT}/media/rviz_multi_independent_full_scene.mp4" \
    -ss 27 -t 11 -i "${REPO_ROOT}/media/rviz_multi_partition_full_scene.mp4" \
    -i "/mnt/d/WSL/video_edit_20261115/runtime_narration.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/runtime_section_45s.mp4"
}

render_experiments() {
  local filter
  filter="[0:v]fps=30,scale=1820:760:force_original_aspect_ratio=decrease,"
  filter+="pad=1920:1080:(ow-iw)/2:155:color=0xF3F6FA,setsar=1,"
  filter+="trim=duration=17,setpts=PTS-STARTPTS[v0];"
  filter+="[1:v]fps=30,scale=1820:760:force_original_aspect_ratio=decrease,"
  filter+="pad=1920:1080:(ow-iw)/2:155:color=0xF3F6FA,setsar=1,"
  filter+="trim=duration=23,setpts=PTS-STARTPTS[v1];"
  filter+="[2:v]fps=30,scale=1920:1080,setsar=1,"
  filter+="trim=duration=11,setpts=PTS-STARTPTS[v2];"
  filter+="[3:v]fps=30,scale=1820:760:force_original_aspect_ratio=decrease,"
  filter+="pad=1920:1080:(ow-iw)/2:155:color=0xF3F6FA,setsar=1,"
  filter+="trim=duration=9.2,setpts=PTS-STARTPTS[v3];"
  filter+="[4:v]fps=30,scale=1820:760:force_original_aspect_ratio=decrease,"
  filter+="pad=1920:1080:(ow-iw)/2:155:color=0xF3F6FA,setsar=1,"
  filter+="trim=duration=16.5,setpts=PTS-STARTPTS[v4];"
  filter+="[v0][v1][v2][v3][v4]concat=n=5:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=126:color=0x091421@0.96:t=fill,"
  filter+="drawbox=x=0:y=ih-146:w=iw:h=146:color=0x091421@0.88:t=fill,"
  filter+="drawbox=x=52:y=48:w=7:h=64:color=0x2F80ED@1:t=fill,"
  filter+="ass=${SCRIPT_DIR}/experiments_section.ass:fontsdir=/usr/share/fonts/opentype/noto,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=76.25:d=0.45,format=yuv420p[vout];"
  filter+="[5:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,adelay=350|350,apad,"
  filter+="atrim=duration=76.7,asetpts=N/SR/TB,afade=t=in:st=0:d=0.25,"
  filter+="afade=t=out:st=75.2:d=1.5[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -loop 1 -framerate 30 -t 17 -i "${REPO_ROOT}/docs/figures/fig_fault_recovery.png" \
    -loop 1 -framerate 30 -t 23 -i "${REPO_ROOT}/docs/figures/fig_coordination_ladder_20261115.png" \
    -ss 3 -t 11 -i "${REPO_ROOT}/media/rviz_target_search_full_scene.mp4" \
    -loop 1 -framerate 30 -t 9.2 -i "${REPO_ROOT}/docs/figures/fig_target_search_ablation_20261115.png" \
    -loop 1 -framerate 30 -t 16.5 -i "${REPO_ROOT}/docs/figures/fig_target_search_office3_coverage_20261115.png" \
    -i "/mnt/d/WSL/video_edit_20261115/experiments_narration.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/experiments_section_76_7s.mp4"
}

render_old_clip() {
  local start="$1"
  local duration="$2"
  local output="$3"
  local fade_out_start="$4"

  ffmpeg -y -hide_banner -loglevel warning \
    -ss "${start}" -t "${duration}" -i "${OLD_VIDEO}" \
    -vf "fps=30,scale=1920:1080,setsar=1,fade=t=in:st=0:d=0.3,fade=t=out:st=${fade_out_start}:d=0.35,format=yuv420p" \
    -af "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,afade=t=in:st=0:d=0.2,afade=t=out:st=${fade_out_start}:d=0.35" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${output}"
}

if [[ "${1:-}" != "--sections-only" ]]; then
  render_runtime >&2
  render_experiments >&2

  render_old_clip 0 124 "${WORK_DIR}/old_00_204.mp4" 123.55
  render_old_clip 155 44 "${WORK_DIR}/old_235_319.mp4" 43.55
  render_old_clip 200 10.072 "${WORK_DIR}/old_320_end.mp4" 9.62

  printf "file '%s'\n" \
    "${WORK_DIR}/old_00_204.mp4" \
    "${WORK_DIR}/runtime_section_45s.mp4" \
    "${WORK_DIR}/old_235_319.mp4" \
    "${WORK_DIR}/experiments_section_76_7s.mp4" \
    "${WORK_DIR}/old_320_end.mp4" > "${WORK_DIR}/concat.txt"

  ffmpeg -y -hide_banner -loglevel warning \
    -f concat -safe 0 -i "${WORK_DIR}/concat.txt" \
    -c copy -movflags +faststart "${WORK_DIR}/FAEP-Multi_国赛答辩_5min.mp4"

  cp "${WORK_DIR}/FAEP-Multi_国赛答辩_5min.mp4" "${OUTPUT_DESKTOP}"
  cp "${WORK_DIR}/FAEP-Multi_国赛答辩_5min.mp4" "${OUTPUT_REPO}"
fi

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels \
  -of default=nw=1 "${WORK_DIR}/FAEP-Multi_国赛答辩_5min.mp4"
