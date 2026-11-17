#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ASSET_DIR="/mnt/d/WSL/video_edit_20261115/final_story"
WORK_DIR="${ASSET_DIR}/build"
OUTPUT_NAME="${OUTPUT_NAME:-FAEP-Multi_国赛答辩_新实验版_公式与旁白修订版.mp4}"
OUTPUT_DESKTOP="/mnt/c/Users/ONE BOY/Desktop/${OUTPUT_NAME}"
OUTPUT_REPO="${REPO_ROOT}/media/${OUTPUT_NAME}"
BOLD_FONT="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REGULAR_FONT="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_DIR="/usr/share/fonts/opentype/noto"
HEADER_H=100
FOOTER_Y=970
FOOTER_H=110
STAGE_X=187
STAGE_Y=100
STAGE_W=1546
STAGE_H=870

mkdir -p "${WORK_DIR}"

video_scale="fps=30,scale=${STAGE_W}:${STAGE_H}:force_original_aspect_ratio=increase,crop=${STAGE_W}:${STAGE_H},setsar=1,pad=1920:1080:${STAGE_X}:${STAGE_Y}:color=0x07111F"
image_scale="fps=30,scale=${STAGE_W}:${STAGE_H}:force_original_aspect_ratio=decrease,pad=${STAGE_W}:${STAGE_H}:(ow-iw)/2:(oh-ih)/2:color=0xF3F6FA,setsar=1,pad=1920:1080:${STAGE_X}:${STAGE_Y}:color=0xF3F6FA"

render_section_01() {
  local duration=31.200
  local filter
  filter="[0:v]${video_scale},trim=duration=8.500,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=0:y=0:w=iw:h=ih:color=0x07111F@0.70:t=fill,"
  filter+="drawbox=x=(iw-520)/2:y=270:w=520:h=5:color=0x2F80ED@0.95:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='FAEP-Multi':"
  filter+="fontcolor=white:fontsize=76:x=(w-text_w)/2:y=300,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='AI+开源 · 开源项目改进与生态贡献':"
  filter+="fontcolor=0xDDEBFA:fontsize=32:x=(w-text_w)/2:y=410,"
  filter+="drawbox=x=250:y=510:w=1420:h=66:color=0x10243D@0.96:t=fill,"
  filter+="drawbox=x=250:y=510:w=7:h=66:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='上游项目：Zyhlibrary / FAEP':"
  filter+="fontcolor=white:fontsize=25:x=290:y=527,"
  filter+="drawbox=x=250:y=592:w=1420:h=60:color=0x10243D@0.96:t=fill,"
  filter+="drawbox=x=250:y=592:w=7:h=60:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='GPL-3.0 · commit 5a59d0a · 2023-06-23':"
  filter+="fontcolor=0xBFD7F5:fontsize=22:x=290:y=608,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='复用单机栈  |  新增多机协同、目标停止、故障接管':"
  filter+="fontcolor=0x8FC6FF:fontsize=25:x=(w-text_w)/2:y=690,"
  filter+="fade=t=out:st=8.000:d=0.5[v0];"
  filter+="[1:v]${video_scale},trim=duration=11.800,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=1180:y=145:w=680:h=64:color=0x07111F@0.84:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='上游已有：建图 · 前沿 · 平滑轨迹':"
  filter+="fontcolor=white:fontsize=24:x=1210:y=162,"
  filter+="fade=t=in:st=0:d=0.5,fade=t=out:st=11.300:d=0.5[v1];"
  filter+="[2:v]${video_scale},trim=duration=5.700,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=120:y=145:w=1120:h=66:color=0x07111F@0.86:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='团队增量：Voronoi 分工、目标停止、故障接管':"
  filter+="fontcolor=white:fontsize=25:x=150:y=162,"
  filter+="fade=t=in:st=0:d=0.5,fade=t=out:st=5.200:d=0.5[v2];"
  filter+="[3:v]${image_scale},trim=duration=5.200,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=120:y=870:w=760:h=48:color=0x07111F@0.90:t=fill,"
  filter+="drawbox=x=120:y=870:w=6:h=48:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='开放成果：代码 · 数据 · 评测脚本':"
  filter+="fontcolor=white:fontsize=22:x=148:y=881,"
  filter+="fade=t=in:st=0:d=0.5[v3];"
  filter+="[v0][v1][v2][v3]concat=n=4:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@0.86:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='01  开源基线、团队增量与验证路线':"
  filter+="fontcolor=white:fontsize=34:x=66:y=24,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='AI+开源 · 上游复用与自主改进边界':"
  filter+="fontcolor=white:fontsize=20:x=68:y=66,"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_01.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=0.7,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=30.500:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[4:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=30.200:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -ss 38 -t 8.500 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 80 -t 11.800 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 24 -t 5.700 -i "${REPO_ROOT}/media/rviz_multi_partition_full_scene.mp4" \
    -loop 1 -framerate 30 -t 5.200 -i "${REPO_ROOT}/docs/figures/fig_arch.png" \
    -i "${ASSET_DIR}/narration_01.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_01.mp4"
}

render_section_02() {
  local duration=37.400
  local filter
  filter="[0:v]${video_scale},trim=duration=13.900,setpts=PTS-STARTPTS[v0];"
  filter+="[1:v]${video_scale},trim=duration=7.900,setpts=PTS-STARTPTS[v1];"
  filter+="[2:v]${video_scale},trim=duration=6.800,setpts=PTS-STARTPTS[v2];"
  filter+="[3:v]${video_scale},trim=duration=8.800,setpts=PTS-STARTPTS[v3];"
  filter+="[v0][v1][v2][v3]concat=n=4:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@1:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='02  开源单机 FAEP 基线':"
  filter+="fontcolor=white:fontsize=34:x=66:y=24,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='障碍物 · 局部地图 · 相机视场':"
  filter+="fontcolor=white:fontsize=20:x=68:y=66,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='局部建图与障碍物':"
  filter+="fontcolor=white:fontsize=24:x=60:y=120:box=1:boxcolor=black@0.55:boxborderw=8:"
  filter+="enable='between(t,0,13.900)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='前沿与候选视点':"
  filter+="fontcolor=white:fontsize=24:x=60:y=120:box=1:boxcolor=black@0.55:boxborderw=8:"
  filter+="enable='between(t,13.900,21.800)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='相机朝向与平滑轨迹':"
  filter+="fontcolor=white:fontsize=24:x=60:y=120:box=1:boxcolor=black@0.55:boxborderw=8:"
  filter+="enable='between(t,21.800,28.600)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='到达后继续选择前沿':"
  filter+="fontcolor=white:fontsize=24:x=60:y=120:box=1:boxcolor=black@0.55:boxborderw=8:"
  filter+="enable='between(t,28.600,36.700)',"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_02.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=0.7,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=36.700:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[4:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=36.400:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -ss 36 -t 13.900 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 55 -t 7.900 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 70 -t 6.800 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -ss 90 -t 8.800 -i "${REPO_ROOT}/media/rviz_single_full_scene.mp4" \
    -i "${ASSET_DIR}/narration_02.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_02.mp4"
}

render_section_03() {
  local duration=36.300
  local filter
  filter="[0:v]${video_scale},trim=duration=10.200,setpts=PTS-STARTPTS[v0];"
  filter+="[1:v]${image_scale},trim=duration=9.050,setpts=PTS-STARTPTS[v1];"
  filter+="color=c=0xF3F6FA:s=1920x1080:r=30:d=7.300[bg];"
  filter+="[2:v]fps=30,scale=770:433:force_original_aspect_ratio=increase,crop=770:433,setsar=1,"
  filter+="trim=duration=7.300,setpts=PTS-STARTPTS[left];"
  filter+="[3:v]fps=30,scale=770:433:force_original_aspect_ratio=increase,crop=770:433,setsar=1,"
  filter+="trim=duration=7.300,setpts=PTS-STARTPTS[right];"
  filter+="[bg][left]overlay=x=187:y=300[tmp];[tmp][right]overlay=x=963:y=300[v2];"
  filter+="color=c=0x07111F:s=1920x1080:r=30:d=9.750,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='L3 相对 L1':"
  filter+="fontcolor=0x8FC6FF:fontsize=34:x=(w-text_w)/2:y=300,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='单机飞行时间下降 43.8％ - 50.0％':"
  filter+="fontcolor=white:fontsize=52:x=(w-text_w)/2:y=390,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='空间分工是主要收益来源':"
  filter+="fontcolor=0xBFD7F5:fontsize=30:x=(w-text_w)/2:y=500[v3];"
  filter+="[v0][v1][v2][v3]concat=n=4:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@1:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='03  三机协同：空间分工才是增益':"
  filter+="fontcolor=white:fontsize=34:x=66:y=28,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='L1 三机独立':"
  filter+="fontcolor=0xFFA64D:fontsize=28:x=60:y=120:box=1:boxcolor=black@0.50:boxborderw=10:"
  filter+="enable='between(t,0,10.200)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='L1 三机独立':"
  filter+="fontcolor=0xFFA64D:fontsize=28:x=250:y=190:box=1:boxcolor=black@0.50:boxborderw=10:"
  filter+="enable='between(t,19.250,26.550)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='L3 Voronoi 分区':"
  filter+="fontcolor=0x62A8FF:fontsize=28:x=1025:y=190:box=1:boxcolor=black@0.50:boxborderw=10:"
  filter+="enable='between(t,19.250,26.550)',"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_03.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=0.7,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=35.600:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[4:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=35.300:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -ss 55 -t 10.200 -i "${REPO_ROOT}/media/rviz_multi_independent_full_scene.mp4" \
    -loop 1 -framerate 30 -t 9.050 -i "${REPO_ROOT}/docs/figures/fig_coordination_ladder_20261115.png" \
    -ss 55 -t 7.300 -i "${REPO_ROOT}/media/rviz_multi_independent_full_scene.mp4" \
    -ss 10 -t 7.300 -i "${REPO_ROOT}/media/rviz_multi_partition_full_scene.mp4" \
    -i "${ASSET_DIR}/narration_03.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_03.mp4"
}

render_section_04() {
  local duration=75.000
  local filter
  filter="color=c=0x07111F:s=1920x1080:r=30:d=5.900,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='Voronoi 已作为正式方案':"
  filter+="fontcolor=white:fontsize=44:x=(w-text_w)/2:y=280,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='随后补做等宽与等面积分区对照':"
  filter+="fontcolor=0xBFD7F5:fontsize=32:x=(w-text_w)/2:y=390,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='两者均未形成稳定优势，等面积保留为实验分支':"
  filter+="fontcolor=0x8FC6FF:fontsize=27:x=(w-text_w)/2:y=475[v0];"
  filter+="[0:v]${image_scale},trim=duration=29.400,setpts=PTS-STARTPTS[v1];"
  filter+="color=c=0x07111F:s=1920x1080:r=30:d=1.800,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='故障注入':"
  filter+="fontcolor=0x8FC6FF:fontsize=30:x=(w-text_w)/2:y=330,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='终止中间无人机 · 观察任务接管':"
  filter+="fontcolor=white:fontsize=48:x=(w-text_w)/2:y=390,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='失联检测 · 任务释放 · 幸存机接管 · 统一停止':"
  filter+="fontcolor=0xBFD7F5:fontsize=27:x=(w-text_w)/2:y=485,"
  filter+="fade=t=in:st=0:d=0.18,fade=t=out:st=1.540:d=0.26[v1b];"
  filter+="[1:v]${image_scale},trim=duration=15.700,setpts=PTS-STARTPTS[v2];"
  filter+="[2:v]${image_scale},trim=duration=12.550,setpts=PTS-STARTPTS[v3];"
  filter+="color=c=0x07111F:s=1920x1080:r=30:d=9.650,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='异常检测':fontcolor=0x8FC6FF:fontsize=29:x=355:y=270,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='任务接管':fontcolor=0x8FC6FF:fontsize=29:x=760:y=270,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='统一停止':fontcolor=0x8FC6FF:fontsize=29:x=1165:y=270,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='3/3 轮成功':"
  filter+="fontcolor=white:fontsize=58:x=(w-text_w)/2:y=370,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='故障注入覆盖 77％ - 82％，恢复代价约为 2.2 倍':"
  filter+="fontcolor=0xBFD7F5:fontsize=30:x=(w-text_w)/2:y=480,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='机制验证不等同于真实飞行安全认证':"
  filter+="fontcolor=0x8FC6FF:fontsize=26:x=(w-text_w)/2:y=550[v4];"
  filter+="[v0][v1][v1b][v2][v3][v4]concat=n=6:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@0.96:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='04  分区对照：Voronoi 保留为正式方案':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='between(t,0,35.300)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='04A 故障注入：两架幸存机接管':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='between(t,35.300,52.800)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='04B 资源边界：OOM 根因修复':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='between(t,52.800,65.350)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='04C 可靠性结论：机制验证有边界':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='gte(t,65.350)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='D1/D2/D3 = 三架无人机 · 面积单位 m²':"
  filter+="fontcolor=0xBFD7F5:fontsize=19:x=w-tw-48:y=38:enable='between(t,0,35.300)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='kill -9 中间机 · 3/3 接管':"
  filter+="fontcolor=0xBFD7F5:fontsize=20:x=w-tw-48:y=38:enable='between(t,35.300,52.800)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='峰值 8.6 GB → 稳态 1.54 GB':"
  filter+="fontcolor=0xBFD7F5:fontsize=19:x=w-tw-48:y=38:enable='between(t,52.800,65.350)',"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_04.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=0.7,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=74.300:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[3:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=74.000:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -loop 1 -framerate 30 -t 29.400 -i "${REPO_ROOT}/docs/figures/fig_equal_area_office2.png" \
    -loop 1 -framerate 30 -t 15.700 -i "${REPO_ROOT}/docs/figures/fig_fault_recovery.png" \
    -loop 1 -framerate 30 -t 12.550 -i "${REPO_ROOT}/docs/figures/fig_oom.png" \
    -i "${ASSET_DIR}/narration_04.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_04.mp4"
}

render_section_05() {
  local duration=35.700
  local filter
  filter="[0:v]${video_scale},trim=duration=34.7,setpts=PTS-STARTPTS[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@0.90:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='05  目标触发搜索：确认后停止':"
  filter+="fontcolor=white:fontsize=34:x=66:y=28,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='黄=候选 · 绿=确认 · 模拟感知':"
  filter+="fontcolor=white:fontsize=18:x=w-tw-48:y=39:box=1:boxcolor=black@0.55:boxborderw=8,"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_05.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=1.00,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=35.00:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=34.70:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -i "${REPO_ROOT}/media/rviz_target_search_full_scene.mp4" \
    -i "${ASSET_DIR}/narration_05.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_05.mp4"
}

render_section_06() {
  local duration=33.600
  local filter
  filter="[0:v]${image_scale},trim=duration=4.300,setpts=PTS-STARTPTS[v0];"
  filter+="[1:v]${image_scale},trim=duration=8.900,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=280:y=122:w=1360:h=72:color=0x10243D@0.92:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='office3：正常 55 s · 错误先验 71 s · 无目标 85 s':"
  filter+="fontcolor=white:fontsize=28:x=(w-text_w)/2:y=142[v1];"
  filter+="[2:v]${image_scale},trim=duration=12.700,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=280:y=122:w=1360:h=72:color=0x10243D@0.92:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='确认后继续：多花 52.2 s，只增加 12.9 个百分点':"
  filter+="fontcolor=white:fontsize=28:x=(w-text_w)/2:y=142[v2];"
  filter+="color=c=0x07111F:s=1920x1080:r=30:d=7.700,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='正式策略在确认后停止':"
  filter+="fontcolor=white:fontsize=48:x=(w-text_w)/2:y=300,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='未确认继续探索 · 无目标返回 NOT_FOUND · 三机统一 HALT':"
  filter+="fontcolor=0xBFD7F5:fontsize=28:x=(w-text_w)/2:y=410,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='office3 每类 1 轮，用于跨场景机制验证':"
  filter+="fontcolor=0x8FC6FF:fontsize=24:x=(w-text_w)/2:y=490[v3];"
  filter+="[v0][v1][v2][v3]concat=n=4:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@0.94:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='06A  office2 目标回归':"
  filter+="fontcolor=white:fontsize=34:x=66:y=28:enable='between(t,0,4.300)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='06B  office3 跨场景验证':"
  filter+="fontcolor=white:fontsize=34:x=66:y=28:enable='between(t,4.300,13.200)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='06C  确认后停止收益':"
  filter+="fontcolor=white:fontsize=34:x=66:y=28:enable='between(t,13.200,25.900)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='06D  任务闭环与验证边界':"
  filter+="fontcolor=white:fontsize=34:x=66:y=28:enable='gte(t,25.900)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='逐条件回归 · 非统计显著性':"
  filter+="fontcolor=0xBFD7F5:fontsize=17:x=w-tw-48:y=40:enable='between(t,0,4.300)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='office3 每类 1 轮':"
  filter+="fontcolor=0xBFD7F5:fontsize=18:x=w-tw-48:y=40:enable='between(t,4.300,13.200)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='轨迹 1 m 邻域 · 非相机精确覆盖':"
  filter+="fontcolor=0xBFD7F5:fontsize=17:x=w-tw-48:y=40:enable='between(t,13.200,25.900)',"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_06.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=0.7,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=32.9:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[3:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=32.6:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -loop 1 -framerate 30 -t 4.300 -i "${REPO_ROOT}/docs/figures/fig_target_search_final_20261115.png" \
    -loop 1 -framerate 30 -t 8.900 -i "${REPO_ROOT}/docs/figures/fig_target_search_office3_coverage_20261115.png" \
    -loop 1 -framerate 30 -t 12.700 -i "${REPO_ROOT}/docs/figures/fig_target_search_office3_coverage_20261115.png" \
    -i "${ASSET_DIR}/narration_06.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_06.mp4"
}

render_section_07() {
  local duration=49.600
  local filter
  filter="color=c=0x07111F:s=1920x1080:r=30:d=19.900,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='目标停止收益：确认后停止无效探索':"
  filter+="fontcolor=white:fontsize=44:x=(w-text_w)/2:y=145,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='找到目标后不急着停机，先复核；确认一致后，三机再统一停止':"
  filter+="fontcolor=0xBFD7F5:fontsize=27:x=(w-text_w)/2:y=215,"
  filter+="drawbox=x=250:y=305:w=420:h=190:color=0x10243D@1:t=fill,"
  filter+="drawbox=x=250:y=305:w=7:h=190:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='1  找到候选目标':fontcolor=0x8FC6FF:fontsize=30:x=286:y=335,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='目标进入视野，但先不停止':fontcolor=white:fontsize=24:x=286:y=402,"
  filter+="drawbox=x=750:y=305:w=420:h=190:color=0x10243D@1:t=fill,"
  filter+="drawbox=x=750:y=305:w=7:h=190:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='2  多帧与交叉复核':fontcolor=0x8FC6FF:fontsize=30:x=786:y=335,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='证据一致，才算真正确认':fontcolor=white:fontsize=24:x=786:y=402,"
  filter+="drawbox=x=1250:y=305:w=420:h=190:color=0x10243D@1:t=fill,"
  filter+="drawbox=x=1250:y=305:w=7:h=190:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='3  三机统一停止':fontcolor=0x8FC6FF:fontsize=30:x=1286:y=335,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='省掉后续不必要的探索':fontcolor=white:fontsize=24:x=1286:y=402,"
  filter+="drawbox=x=250:y=565:w=1420:h=74:color=0x10243D@0.96:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='收益：不再继续探索，节省任务时间':fontcolor=white:fontsize=27:x=(w-text_w)/2:y=585,"
  filter+="drawbox=x=250:y=665:w=1420:h=72:color=0x3A1F16@0.96:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='边界：防止误检提前停机；没有目标时完成全图再结束':fontcolor=0xFFD3B5:fontsize=25:x=(w-text_w)/2:y=685[v0];"
  filter+="[0:v]${image_scale},trim=duration=23.100,setpts=PTS-STARTPTS,"
  filter+="drawbox=x=220:y=112:w=1480:h=104:color=0x07111F@0.94:t=fill,"
  filter+="drawbox=x=220:y=112:w=7:h=104:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='T：对应配置的平均单机飞行时间，不是 wall 总耗时':"
  filter+="fontcolor=white:fontsize=21:x=258:y=121,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='R_BC = T_B / T_C    R_AC = T_A / T_C    长宽比 = Lmax / Lmin':"
  filter+="fontcolor=white:fontsize=20:x=258:y=153,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='A 单机 | B 三机独立 | C Voronoi 协同 | R > 1：C 的平均单机飞行时间更短':"
  filter+="fontcolor=0xBFD7F5:fontsize=18:x=258:y=184[v1];"
  filter+="color=c=0x07111F:s=1920x1080:r=30:d=6.600,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='扇区分工收益：不能只由地图面积和长宽比解释':"
  filter+="fontcolor=white:fontsize=48:x=(w-text_w)/2:y=230,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='3 个场景中，协同都更快；但收益没有随面积或长宽比单调变化':"
  filter+="fontcolor=0xBFD7F5:fontsize=29:x=(w-text_w)/2:y=340,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='地图面积和长宽比，只能描述场景，不能单独预测分区收益':"
  filter+="fontcolor=white:fontsize=30:x=(w-text_w)/2:y=430,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='图中的连线只连接 3 个实验点，不是拟合出的边界':"
  filter+="fontcolor=0x8FC6FF:fontsize=27:x=(w-text_w)/2:y=510,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='后续：更多场景 · 障碍复杂度 · 扇区负载 · 起始位置':"
  filter+="fontcolor=0xBFD7F5:fontsize=25:x=(w-text_w)/2:y=590,"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='旁白：AI 生成':"
  filter+="fontcolor=0xAAB8C8:fontsize=22:x=w-tw-70:y=h-100[v2];"
  filter+="[v0][v1][v2]concat=n=3:v=1:a=0[vc];"
  filter+="[vc]drawbox=x=0:y=0:w=iw:h=${HEADER_H}:color=0x07111F@0.92:t=fill,"
  filter+="drawbox=x=40:y=24:w=6:h=52:color=0x2F80ED@1:t=fill,"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='07A 目标停止收益：确认后停止继续探索':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='between(t,0,19.900)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='07B 扇区分工收益：不能只由面积和长宽比解释':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='between(t,19.900,43.000)',"
  filter+="drawtext=fontfile=${BOLD_FONT}:text='07C 结论：地图尺寸不能单独预测分工收益':"
  filter+="fontcolor=white:fontsize=33:x=66:y=28:enable='gte(t,43.000)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='目标停止：减少后续探索':"
  filter+="fontcolor=0xBFD7F5:fontsize=19:x=w-tw-48:y=39:enable='between(t,0,19.900)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='三场景呈非单调关系':"
  filter+="fontcolor=0xBFD7F5:fontsize=19:x=w-tw-48:y=39:enable='between(t,19.900,43.000)',"
  filter+="drawtext=fontfile=${REGULAR_FONT}:text='趋势分析，不拟合边界':"
  filter+="fontcolor=0xBFD7F5:fontsize=19:x=w-tw-48:y=39:enable='gte(t,43.000)',"
  filter+="drawbox=x=0:y=${FOOTER_Y}:w=iw:h=${FOOTER_H}:color=0x07111F@1:t=fill,"
  filter+="ass=${ASSET_DIR}/narration_07.ass:fontsdir=${FONT_DIR},"
  filter+="tpad=stop_mode=clone:stop_duration=0.7,"
  filter+="fade=t=in:st=0:d=0.35,fade=t=out:st=48.9:d=0.7,"
  filter+="format=yuv420p[vout];"
  filter+="[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=3.5dB,"
  filter+="alimiter=limit=0.95:level=false,apad,atrim=duration=${duration},"
  filter+="afade=t=out:st=48.6:d=1[aout]"

  ffmpeg -y -hide_banner -loglevel warning \
    -loop 1 -framerate 30 -t 23.100 -i "${REPO_ROOT}/docs/figures/fig_benefit_boundary.png" \
    -i "${ASSET_DIR}/narration_07.mp3" \
    -filter_complex "${filter}" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "${WORK_DIR}/section_07.mp4"
}

render_section_01
render_section_02
render_section_03
render_section_04
render_section_05
render_section_06
render_section_07

printf "file '%s'\n" \
  "${WORK_DIR}/section_01.mp4" \
  "${WORK_DIR}/section_02.mp4" \
  "${WORK_DIR}/section_03.mp4" \
  "${WORK_DIR}/section_04.mp4" \
  "${WORK_DIR}/section_05.mp4" \
  "${WORK_DIR}/section_06.mp4" \
  "${WORK_DIR}/section_07.mp4" > "${WORK_DIR}/concat.txt"

ffmpeg -y -hide_banner -loglevel warning \
  -f concat -safe 0 -i "${WORK_DIR}/concat.txt" \
  -c copy -movflags +faststart "${WORK_DIR}/${OUTPUT_NAME}"

cp "${WORK_DIR}/${OUTPUT_NAME}" "${OUTPUT_DESKTOP}"
cp "${WORK_DIR}/${OUTPUT_NAME}" "${OUTPUT_REPO}"

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels \
  -of default=nw=1 "${WORK_DIR}/${OUTPUT_NAME}"
