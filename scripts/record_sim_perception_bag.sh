#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/sim_env.sh"
source_perception_runtime

RUN_LABEL="${1:-sim_perception}"
SAFE_LABEL="$(printf '%s' "${RUN_LABEL}" | tr -c '[:alnum:]_.-' '_')"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_ROOT="${WORKSPACE_ROOT}/mecanumbot_RL/perception_runs"
OUT_DIR="${OUT_ROOT}/${STAMP}_${SAFE_LABEL}"

mkdir -p "${OUT_ROOT}"

printf 'Recording sim perception bag to:\n  %s\n\n' "${OUT_DIR}"
printf 'Stop recording with Ctrl-C.\n\n'

cd "${WORKSPACE_ROOT}"
exec ros2 bag record \
  -o "${OUT_DIR}" \
  /clock \
  /tf \
  /tf_static \
  /cmd_vel \
  /mecanumbot/odom \
  /mecanumbot/imu \
  /mecanumbot/opencr_state \
  /mecanumbot/scan \
  /mecanumbot/dr_spaam/dets \
  /mecanumbot/dr_spaam/marker \
  /mecanumbot/subject_pose \
  /sim/actors \
  /sim/actor_markers \
  /sim/detection_markers \
  /sim/evaluation_markers \
  /sim/detector_debug_markers \
  /sim/subject_pose_ground_truth \
  /sim/detection_evaluation \
  /sim/behavior_evaluation
