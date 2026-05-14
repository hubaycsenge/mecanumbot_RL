#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUN_SCRIPT_ROOT="${WORKSPACE_ROOT}/mecanumbot_RL/scripts"
ROS_DISTRO="${ROS_DISTRO:-humble}"
ROS_LOG_DIR_DEFAULT="${WORKSPACE_ROOT}/log/ros"

if [ ! -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]; then
  echo "ROS 2 ${ROS_DISTRO} is not installed under /opt/ros/${ROS_DISTRO}" >&2
  return 1 2>/dev/null || exit 1
fi

# ROS setup scripts assume some variables may be unset while they initialize.
# Temporarily relax nounset so sourcing works under `set -u`.
restore_nounset=0
if [[ $- == *u* ]]; then
  restore_nounset=1
  set +u
fi
source "/opt/ros/${ROS_DISTRO}/setup.bash"
if [ "${restore_nounset}" -eq 1 ]; then
  set -u
fi

export ROS_LOG_DIR="${ROS_LOG_DIR:-${ROS_LOG_DIR_DEFAULT}}"
mkdir -p "${ROS_LOG_DIR}"

source_if_exists() {
  local file="$1"
  if [ ! -f "${file}" ]; then
    echo "Missing required package environment: ${file}" >&2
    echo "Run ${RUN_SCRIPT_ROOT}/rebuild_sim.sh first." >&2
    return 1
  fi
  local restore_nounset=0
  if [[ $- == *u* ]]; then
    restore_nounset=1
    set +u
  fi
  # shellcheck disable=SC1090
  source "${file}"
  if [ "${restore_nounset}" -eq 1 ]; then
    set -u
  fi
}

source_sim_runtime() {
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_msgs/share/mecanumbot_msgs/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_description/share/mecanumbot_description/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_core/share/mecanumbot_core/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_bringup/share/mecanumbot_bringup/package.bash"
}

source_teleop_runtime() {
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_msgs/share/mecanumbot_msgs/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_teleop/share/mecanumbot_teleop/package.bash"
}

source_perception_runtime() {
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_msgs/share/mecanumbot_msgs/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_description/share/mecanumbot_description/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_core/share/mecanumbot_core/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_bringup/share/mecanumbot_bringup/package.bash"
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_sensorprocess_smart/share/mecanumbot_sensorprocess_smart/package.bash"
  if [ -d "${WORKSPACE_ROOT}/DR-SPAAM-Detector/dr_spaam/src" ]; then
    export PYTHONPATH="${WORKSPACE_ROOT}/DR-SPAAM-Detector/dr_spaam/src:${PYTHONPATH:-}"
  fi
}

source_sim_behaviour_runtime() {
  source_sim_runtime
  source_if_exists "${WORKSPACE_ROOT}/install/mecanumbot_leading_behaviour/share/mecanumbot_leading_behaviour/package.bash"
}
