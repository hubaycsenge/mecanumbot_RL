#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/sim_env.sh"
source_perception_runtime

cd "${WORKSPACE_ROOT}"
exec ros2 launch mecanumbot_bringup launch_mecanumbot_sim_perception.launch.py \
  use_rviz:=true \
  enable_detector_debug_markers:=true \
  "$@"
