#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/sim_env.sh"

cd "${WORKSPACE_ROOT}"

# These are generated artifacts. Removing only the sim packages keeps the
# rebuild path-independent without disturbing the rest of the workspace.
rm -rf \
  "${WORKSPACE_ROOT}/build/mecanumbot_msgs" \
  "${WORKSPACE_ROOT}/build/mecanumbot_description" \
  "${WORKSPACE_ROOT}/build/mecanumbot_core" \
  "${WORKSPACE_ROOT}/build/mecanumbot_bringup" \
  "${WORKSPACE_ROOT}/build/mecanumbot_sensorprocess_smart" \
  "${WORKSPACE_ROOT}/build/mecanumbot_leading_behaviour" \
  "${WORKSPACE_ROOT}/install/mecanumbot_msgs" \
  "${WORKSPACE_ROOT}/install/mecanumbot_description" \
  "${WORKSPACE_ROOT}/install/mecanumbot_core" \
  "${WORKSPACE_ROOT}/install/mecanumbot_bringup" \
  "${WORKSPACE_ROOT}/install/mecanumbot_sensorprocess_smart" \
  "${WORKSPACE_ROOT}/install/mecanumbot_leading_behaviour"

colcon build --symlink-install \
  --packages-select mecanumbot_msgs mecanumbot_description mecanumbot_core mecanumbot_bringup mecanumbot_sensorprocess_smart mecanumbot_leading_behaviour \
  --allow-overriding mecanumbot_msgs mecanumbot_description mecanumbot_core mecanumbot_bringup mecanumbot_sensorprocess_smart mecanumbot_leading_behaviour \
  --cmake-clean-cache
