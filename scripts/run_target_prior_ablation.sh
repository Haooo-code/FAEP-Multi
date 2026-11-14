#!/bin/bash
# 目标先验消融：东侧目标 (5,5)，只切换 target_prior_enabled。

set -o pipefail

RUNS=${ABLATION_RUNS:-3}
OUT_DIR=${TARGET_SEARCH_OUT_DIR:-/mnt/d/WSL/target_search_ablation_20261115}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RUNNER="$SCRIPT_DIR/target_search_regression.sh"

COMMON=(
  target_x:=5.0 target_y:=5.0 target_z:=1.0
  target_prior_x:=5.0 target_prior_y:=5.0 target_prior_z:=1.0
  target_prior_radius:=3.0 target_prior_growth:=0.05
  target_prior_max_radius:=8.0 target_sensor_max_range:=8.0
  target_detection_probability:=0.92
  target_position_noise:=0.08 target_confidence_noise:=0.05
  target_confirm_frames:=3 target_high_confidence:=0.80 target_low_confidence:=0.45
  target_verification_sources:=2 target_verification_timeout:=20.0
  target_verifier_switch_timeout:=10.0 target_stop_on_confirm:=true
)

run_case() {
  local name=$1
  local enabled=$2
  for run in $(seq 1 "$RUNS"); do
    echo "===== ${name} run ${run}/${RUNS} ====="
    TARGET_SEARCH_OUT_DIR="$OUT_DIR" TARGET_SEARCH_MAX_WAIT=150 \
      bash "$RUNNER" "${name}_${run}" confirmed \
      "${COMMON[@]}" "target_prior_enabled:=$enabled"
  done
}

mkdir -p "$OUT_DIR"
run_case ablation_prior_on_east true
run_case ablation_prior_off_east false
echo "PRIOR_ABLATION_DONE"
