#!/bin/bash
# 目标触发式搜索组件消融：每类配置默认运行 3 轮。

set -o pipefail

RUNS=${ABLATION_RUNS:-3}
OUT_DIR=${TARGET_SEARCH_OUT_DIR:-/mnt/d/WSL/target_search_ablation_20261115}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RUNNER="$SCRIPT_DIR/target_search_regression.sh"

COMMON=(
  target_x:=1.0 target_y:=3.0 target_z:=1.0
  target_prior_x:=1.0 target_prior_y:=3.0 target_prior_z:=1.0
  target_prior_radius:=3.0 target_prior_growth:=0.05
  target_prior_max_radius:=8.0 target_sensor_max_range:=8.0
  target_detection_probability:=0.92
  target_position_noise:=0.08 target_confidence_noise:=0.05
)

run_case() {
  local name=$1
  local expected=$2
  local max_wait=$3
  shift 3
  for run in $(seq 1 "$RUNS"); do
    echo "===== ${name} run ${run}/${RUNS} ====="
    TARGET_SEARCH_OUT_DIR="$OUT_DIR" TARGET_SEARCH_MAX_WAIT="$max_wait" \
      bash "$RUNNER" "${name}_${run}" "$expected" "${COMMON[@]}" "$@"
  done
}

mkdir -p "$OUT_DIR"

# 完整方案：先验 + 多帧确认 + 无进展换人 + 确认后停止。
run_case ablation_full confirmed 120 \
  target_prior_enabled:=true \
  target_confirm_frames:=3 target_high_confidence:=0.80 target_low_confidence:=0.45 \
  target_verification_sources:=2 target_verification_timeout:=20.0 \
  target_verifier_switch_timeout:=10.0 target_stop_on_confirm:=true

# 去掉目标先验，只在发现后保留目标处理逻辑。
run_case ablation_no_prior confirmed 120 \
  target_prior_enabled:=false \
  target_confirm_frames:=3 target_high_confidence:=0.80 target_low_confidence:=0.45 \
  target_verification_sources:=2 target_verification_timeout:=20.0 \
  target_verifier_switch_timeout:=10.0 target_stop_on_confirm:=true

# 严格双机确认，保留 10 秒无视觉进展换人。
run_case ablation_with_handoff_strict confirmed 180 \
  target_prior_enabled:=true \
  target_confirm_frames:=3 target_high_confidence:=1.0 target_low_confidence:=0.45 \
  target_verification_sources:=2 target_verification_timeout:=60.0 \
  target_verifier_switch_timeout:=10.0 target_stop_on_confirm:=true

# 严格双机确认，但关闭无视觉进展换人。
run_case ablation_no_handoff target_terminal 180 \
  target_prior_enabled:=true \
  target_confirm_frames:=3 target_high_confidence:=1.0 target_low_confidence:=0.45 \
  target_verification_sources:=2 target_verification_timeout:=60.0 \
  target_verifier_switch_timeout:=999.0 target_stop_on_confirm:=true

# 去掉多帧确认，仅保留检测与停止链路。
run_case ablation_single_frame confirmed 120 \
  target_prior_enabled:=true \
  target_confirm_frames:=1 target_high_confidence:=0.0 target_low_confidence:=0.0 \
  target_verification_sources:=2 target_verification_timeout:=20.0 \
  target_verifier_switch_timeout:=10.0 target_stop_on_confirm:=true

# 已确认目标后继续探索，用于衡量停止策略本身节省的时间。
run_case ablation_no_stop halt_only 150 \
  target_prior_enabled:=true \
  target_confirm_frames:=3 target_high_confidence:=0.80 target_low_confidence:=0.45 \
  target_verification_sources:=2 target_verification_timeout:=20.0 \
  target_verifier_switch_timeout:=10.0 target_stop_on_confirm:=false

echo "ABLATION_SUITE_DONE"
