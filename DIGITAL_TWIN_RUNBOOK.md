# Mecanumbot Digital Twin Runbook

This is the current command and interpretation guide for the ROS 2 Humble + MuJoCo digital twin in this workspace. It covers the completed Phase 1-4 stack: scenario actors, simulated LiDAR, detector evaluation, behavior safety evaluation, RViz, and teleop.

## Workspace

Use this workspace root in the examples below:

```bash
WORKSPACE=/path/to/mecanumbot
cd "$WORKSPACE"
```

Do not copy `build/`, `install/`, or `log/` between machines. They are generated locally. Rebuild after moving the workspace or changing messages/launch files.

## Quick Start: Truth Twin With Teleop

This is the short command lineup for the normal digital-twin UX path: MuJoCo truth twin, RViz, oracle subject tracking, and keyboard teleoperation.

Terminal 1:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_truth_twin.sh use_rviz:=true
```

Terminal 2:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_sim_teleop.sh
```

Keyboard controls:

- `w/x`: forward/back
- `a/d`: strafe left/right
- `q/e`: rotate
- `space` or `s`: stop

If the install tree is stale or missing, rebuild first:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/rebuild_sim.sh
```

## Full Perception Debug Terminal Lineup

Use this longer path only when testing the real perception/debug stack. The short truth-twin path is enough for normal teleop and behavior demos; this path adds DR-SPAAM detections, detector-vs-truth evaluation, behavior safety evaluation, timestamp checks, and optional bag recording.

Terminal 1, launch the sim/perception stack with RViz:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_sim_perception.sh \
  use_rviz:=true \
  scenario_path:="$WORKSPACE/install/mecanumbot_bringup/share/mecanumbot_bringup/config/sim_scenarios/two_humans_wall_discrimination.yaml"
```

Terminal 2, teleoperate the robot:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_sim_teleop.sh
```

Terminal 3, source the perception runtime before running debug commands:

```bash
cd "$WORKSPACE"
source ./mecanumbot_RL/scripts/sim_env.sh
source_perception_runtime
```

Then verify the graph, timestamps, and evaluation topics:

```bash
ros2 topic list | rg 'sim/|dr_spaam|subject_pose|scan|odom|clock'
ros2 topic info /clock -v
ros2 topic echo /sim/actors --once
ros2 topic echo /sim/detection_evaluation --once
ros2 topic echo /sim/behavior_evaluation --once
```

`/clock` should have exactly one publisher from `mecanumbot_sim_io_node`. If RViz is launched separately instead of through `use_rviz:=true`, set it to simulation time:

```bash
ros2 param set /rviz2 use_sim_time true
```

Optional Terminal 4, record the run for later replay:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/record_sim_perception_bag.sh two_humans_wall_discrimination
```

## Rebuild

Preferred rebuild:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/rebuild_sim.sh
```

This rebuilds the simulation/perception packages needed by the current digital twin:

- `mecanumbot_msgs`
- `mecanumbot_description`
- `mecanumbot_core`
- `mecanumbot_bringup`
- `mecanumbot_sensorprocess_smart`
- `mecanumbot_leading_behaviour`

Manual equivalent:

```bash
cd "$WORKSPACE"
source /opt/ros/humble/setup.bash
rm -rf build/mecanumbot_msgs build/mecanumbot_description build/mecanumbot_core build/mecanumbot_bringup build/mecanumbot_sensorprocess_smart build/mecanumbot_leading_behaviour
rm -rf install/mecanumbot_msgs install/mecanumbot_description install/mecanumbot_core install/mecanumbot_bringup install/mecanumbot_sensorprocess_smart install/mecanumbot_leading_behaviour
colcon build --symlink-install \
  --packages-select mecanumbot_msgs mecanumbot_description mecanumbot_core mecanumbot_bringup mecanumbot_sensorprocess_smart mecanumbot_leading_behaviour \
  --allow-overriding mecanumbot_msgs mecanumbot_description mecanumbot_core mecanumbot_bringup mecanumbot_sensorprocess_smart mecanumbot_leading_behaviour \
  --cmake-clean-cache
```

## Launch Truth Twin

Use this first for behavior, teleop, scenarios, and UX. It does not run DR-SPAAM. The subject pose is oracle ground truth, so RViz should be clean and deterministic.

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_truth_twin.sh \
  use_rviz:=true \
  scenario_path:="$WORKSPACE/install/mecanumbot_bringup/share/mecanumbot_bringup/config/sim_scenarios/two_humans_wall_discrimination.yaml"
```

Expected processes:

- `mecanumbot_sim_io_node`
- `mecanumbot_sensorproc_node`
- `robot_state_publisher`
- `static_transform_publisher`
- `mecanumbot_sim_oracle_subject_node`
- `mecanumbot_sim_truth_target_evaluator_node`
- `mecanumbot_sim_behavior_evaluator_node`
- `mecanumbot_sim_visualization_node`
- `rviz2` when `use_rviz:=true`

Expected truth-mode detection status:

```yaml
status: oracle_tracking_subject
subject_tracking_ok: true
raw_detection_available: false
```

That is intentional: it means behavior is being tested against ground truth, not against DR-SPAAM.

## Launch Truth Twin With Actual Behavior Tree

This is the additive sim-only path for running the existing leading behavior tree in the digital twin. The real behavior tree source and real robot launch files are not changed. The sim adds a small Nav2/AMCL shim that provides the interfaces the behavior tree expects:

- `/amcl_pose`
- `/goal_pose`
- `/navigate_to_pose/_action/status`
- `/cmd_vel`
- `/set_led_status` as a dummy success service

Run:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_sim_behaviour.sh use_rviz:=true
```

Optional condition:

```bash
./mecanumbot_RL/scripts/run_sim_behaviour.sh condition:=Doglike use_rviz:=true
./mecanumbot_RL/scripts/run_sim_behaviour.sh condition:=Control use_rviz:=true
./mecanumbot_RL/scripts/run_sim_behaviour.sh condition:=LED use_rviz:=true
```

Default sim behavior config:

```text
$WORKSPACE/src/mecanumbot_behaviours/mecanumbot_leading_behaviour/config/sim_behaviour_setting_constants.yaml
```

Default scenario:

```text
single_human_follow.yaml
```

Expected added processes beyond truth twin:

- `mecanumbot_sim_nav_shim_node`
- one existing behavior executable depending on `condition`: `doglike_leading_bt_node`, `control_leading_bt_node`, or `LED_leading_bt_node`

Important: this is not full Nav2. It is a lightweight shim that converts `/goal_pose` into `/cmd_vel` and publishes Nav2-like status so the existing behavior tree can run in sim first. Once this path is stable, replace the shim with real Nav2 in sim.

## Launch Detector Debug

Use this only when testing the real LiDAR detector path. This mode can look wrong if scan geometry, TF, and detector assumptions are not aligned; that is what it is meant to expose.

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_detector_debug.sh \
  scenario_path:="$WORKSPACE/install/mecanumbot_bringup/share/mecanumbot_bringup/config/sim_scenarios/two_humans_wall_discrimination.yaml"
```

Important: keep the `scenario_path:=...yaml` path as one continuous shell argument. Do not split it after `install/mecanumbot_bringup/`; if it is split, the sim receives a directory path and fails with `IsADirectoryError`.

Expected processes:

- `mecanumbot_sim_io_node`
- `mecanumbot_sensorproc_node`
- `robot_state_publisher`
- `static_transform_publisher`
- `mecanumbot_lidar_detect_people`
- `mecanumbot_sim_detection_evaluator_node`
- `mecanumbot_sim_behavior_evaluator_node`
- `mecanumbot_sim_visualization_node`
- `mecanumbot_sim_detector_debug_node`
- `rviz2` when `use_rviz:=true`

Expected launch log line for this scenario:

```text
Loaded sim scenario: two_humans_wall_discrimination
```

The detector-debug stack publishes `/mecanumbot/dr_spaam/dets`, `/mecanumbot/subject_pose`, detector-vs-truth errors, and `/sim/detector_debug_markers`.

In RViz, `/sim/detector_debug_markers` draws each raw detector output in `map` and connects it to the nearest truth actor. Use those lines and distance labels to debug scan/detector alignment. Do not use this as the primary behavior UX until detector/frame alignment is verified.

Detector profiles are separated by launch parameters:

- Physical robot default: `robot_profile:=physical`, `tracker_mode:=kalman`, `enable_map_filter:=true`.
- Simulation debug launch: `robot_profile:=sim`, `tracker_mode:=simple`, `enable_map_filter:=false`.

The topic/frame compatibility fixes are shared by both paths: `scan_topic`, `detections_topic`, `rviz_topic`, and header-based detection frame handling stay configurable. Behavior-changing detector logic should be changed through these parameters, not by silently replacing physical defaults.

## Source Runtime In New Terminals

In every new terminal used for `ros2 topic ...` commands:

```bash
cd "$WORKSPACE"
source "$WORKSPACE/mecanumbot_RL/scripts/sim_env.sh"
source_perception_runtime
```

For truth twin commands without the detector package, `source_sim_runtime` is also valid.

## Store Perception Data

RViz and MuJoCo are only live visualizers. They do not store perception data by themselves.

To save a detector-debug run, launch the sim/perception stack first, then open another terminal and record a ROS 2 bag:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/record_sim_perception_bag.sh two_humans_wall_discrimination
```

Bags are stored under:

```text
$WORKSPACE/mecanumbot_RL/perception_runs/
```

Each bag records:

- `/mecanumbot/scan`: LiDAR input to the detector.
- `/mecanumbot/dr_spaam/dets`: raw detector output.
- `/mecanumbot/subject_pose`: selected tracked subject pose.
- `/sim/actors`: scenario ground truth actors.
- `/sim/subject_pose_ground_truth`: subject ground truth.
- `/sim/detection_evaluation`: detector-vs-truth result.
- `/sim/behavior_evaluation`: motion safety result.
- `/sim/actor_markers`, `/sim/detection_markers`, `/sim/evaluation_markers`: RViz labels and overlays.
- `/sim/detector_debug_markers`: detector-to-nearest-truth association overlay for detector-debug runs.
- `/cmd_vel`, `/mecanumbot/odom`, `/tf`, `/tf_static`, `/clock`: context needed to replay and debug.

Note: `/sim/actor_markers` includes both scenario actors and fixed MuJoCo world obstacles that affect LiDAR, so RViz truth geometry should match the scan-producing model.

Stop the recorder with `Ctrl-C` when the scenario is done.

Inspect recorded bags:

```bash
ls -1 "$WORKSPACE/mecanumbot_RL/perception_runs"
ros2 bag info "$WORKSPACE/mecanumbot_RL/perception_runs/<bag_directory>"
```

Replay a bag:

```bash
ros2 bag play "$WORKSPACE/mecanumbot_RL/perception_runs/<bag_directory>" --clock
```

## Core Topics

Robot/sim topics:

- `/clock`
- `/mecanumbot/opencr_state`
- `/mecanumbot/odom`
- `/mecanumbot/imu`
- `/mecanumbot/joint_states`
- `/mecanumbot/battery_state`
- `/mecanumbot/scan`
- `/tf`
- `/tf_static`

Scenario/perception/evaluation topics:

- `/sim/actors`
- `/sim/subject_pose_ground_truth`
- `/mecanumbot/dr_spaam/dets`
- `/mecanumbot/dr_spaam/marker`
- `/mecanumbot/subject_pose`
- `/sim/detection_evaluation`
- `/sim/behavior_evaluation`
- `/sim/actor_markers`
- `/sim/detection_markers`
- `/sim/evaluation_markers`
- `/sim/detector_debug_markers`

Quick graph check:

```bash
ros2 topic list | rg 'sim/|dr_spaam|subject_pose|scan|odom|clock'
ros2 topic info /clock -v
```

`/clock` should have exactly one publisher from `mecanumbot_sim_io_node`.

## Scenario List

Static and oracle scenarios:

- `single_human_follow.yaml`: one static subject human.
- `human_near_wall.yaml`: static subject human near a wall actor.

Moving perception scenarios:

- `moving_human_patrol.yaml`: one moving subject human.
- `moving_human_near_wall.yaml`: moving subject human near a wall panel.

Discrimination/evaluation scenarios:

- `human_wall_discrimination.yaml`: one moving subject and wall decoys.
- `two_humans_wall_discrimination.yaml`: subject human, distractor human, and wall decoys.

Behavior safety scenarios:

- `behavior_subject_stop.yaml`: subject starts close to robot, useful for close-human safety checks.
- `behavior_wall_false_positive.yaml`: wall decoy in front of robot with subject offset.
- `behavior_wrong_human_crossing.yaml`: subject plus crossing distractor human.

Run any scenario with:

```bash
./mecanumbot_RL/scripts/run_sim_perception.sh \
  use_rviz:=true \
  scenario_path:="$WORKSPACE/install/mecanumbot_bringup/share/mecanumbot_bringup/config/sim_scenarios/<scenario_name>.yaml"
```

## Confirm The Current Stack

After launching `two_humans_wall_discrimination.yaml`, run:

```bash
ros2 topic echo /sim/actors --once
ros2 topic echo /sim/detection_evaluation --once
ros2 topic echo /sim/behavior_evaluation --once
```

Expected `/sim/actors` shape in `two_humans_wall_discrimination`:

- `subject_human`, kind `human`, `is_subject: true`, moving.
- `distractor_human`, kind `human`, `is_subject: false`, moving.
- `close_wall_panel`, kind `wall`.
- `side_wall_panel`, kind `wall`.

A valid hard-case detection output may look like this:

```yaml
status: subject_error_high
subject_tracking_ok: false
nearest_actor_name: distractor_human
nearest_actor_kind: human
raw_detection_count: 2
```

That is not a sim failure. It means the detector currently associates closer to the distractor than the designated subject. The point of the digital twin is to expose that failure mode.

A safe idle behavior output may look like this:

```yaml
status: safe_idle_invalid_target
robot_moving: false
target_valid: false
unsafe_motion: false
reason: Target is invalid, but robot is stopped.
```

That means behavior is safe because the robot is not moving while perception is invalid.

## Detection Evaluation Statuses

`/sim/detection_evaluation` answers: what did perception appear to track?

Useful statuses:

- `tracking_subject`: detector pose is closest to the designated subject actor.
- `oracle_tracking_subject`: truth twin/oracle pose is close to the designated subject actor.
- `false_wall_lock`: detector pose is closest to a wall actor.
- `wrong_human_lock`: detector pose is closest to a non-subject human.
- `subject_error_high`: detector exists but is too far from the designated subject.
- `pose_memory_only`: `/mecanumbot/subject_pose` exists, but the current raw detector frame has no poses.
- `no_detection`: no detector subject pose has been seen yet.

Key fields:

- `raw_detection_available`: true when the current raw detector frame has at least one pose.
- `raw_detection_count`: number of raw detector poses in the current frame.
- `subject_tracking_ok`: true when the active target source is close enough to the designated subject. In detector-debug mode this also requires a raw detection; in truth mode it comes from oracle pose.
- `nearest_actor_name` / `nearest_actor_kind`: actor closest to the detector pose.
- `subject_error`: distance from detector pose to the designated subject.

## Behavior Evaluation Statuses

`/sim/behavior_evaluation` answers: is robot motion safe given perception and ground truth?

Useful statuses:

- `safe_idle`: robot is stopped.
- `safe_idle_invalid_target`: perception target is invalid, but robot is stopped.
- `safe_following_subject`: robot is moving with a valid target and safe distances.
- `safe_approaching_subject`: robot is moving with a valid target outside the follow band.
- `unsafe_motion_with_invalid_target`: robot is moving while perception is tracking a wall, wrong human, or high-error target.
- `unsafe_motion_with_stale_detection`: robot is moving while raw detector output is missing.
- `unsafe_close_to_human`: robot is moving inside the human stop distance.
- `unsafe_close_to_wall`: robot is moving inside the wall stop distance.

Key fields:

- `robot_moving`: true when `/cmd_vel` magnitude is above threshold.
- `target_valid`: copied from `subject_tracking_ok` in detection evaluation.
- `unsafe_motion`: high-level safety fail flag.
- `subject_distance`: robot-to-subject ground-truth distance.
- `nearest_actor_name` / `nearest_actor_kind`: closest visible actor to the robot.
- `reason`: human-readable explanation.

## Test Unsafe Behavior With Cmd Vel

In a running Phase 4 scenario, publish a small forward command:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.12, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Then check:

```bash
ros2 topic echo /sim/behavior_evaluation --once
```

Stop immediately after the test:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

In `behavior_subject_stop.yaml`, moving forward near the subject should produce an unsafe status such as:

```yaml
status: unsafe_close_to_human
unsafe_motion: true
robot_moving: true
```

## Teleoperation

Teleop is supported. Start the sim/perception stack first, then in another terminal:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_sim_teleop.sh
```

Keyboard mapping:

- `w/x`: linear x
- `a/d`: linear y
- `q/e`: angular z
- `space` or `s`: stop
- `i/k/j/l`: accessories

Notes:

- `w/x` and `q/e` are the most reliable in the simplified MuJoCo contact model.
- `a/d` sideways motion is limited by the simplified wheel contact model.
- Behavior safety still evaluates teleop motion because teleop publishes `/cmd_vel`.

## RViz

The easiest RViz path is to launch it together with perception:

```bash
./mecanumbot_RL/scripts/run_sim_perception.sh use_rviz:=true
```

If launching RViz separately:

```bash
cd "$WORKSPACE"
./mecanumbot_RL/scripts/run_sim_rviz.sh
ros2 param set /rviz2 use_sim_time true
```

Recommended RViz settings:

- Fixed Frame: `mecanumbot/odom` for robot-centric view, or `map` when using evaluator/map-level topics.
- Add `TF`.
- Add `RobotModel`.
- Add `LaserScan` on `/mecanumbot/scan`.
- Add `Odometry` on `/mecanumbot/odom`.
- Add `PoseArray` on `/mecanumbot/dr_spaam/dets`.
- Add `PoseStamped` on `/mecanumbot/subject_pose`.
- Add `MarkerArray` on `/sim/actor_markers` to see labeled truth actors.
- Add `MarkerArray` on `/sim/detection_markers` to see detector labels.
- Add `MarkerArray` on `/sim/detector_debug_markers` to see detector-to-truth association lines.
- Add `MarkerArray` on `/sim/evaluation_markers` to see perception/behavior status text.

If `LaserScan` does not appear, set the display reliability policy to `Reliable`.

The default RViz config already includes the sim marker displays. If labels do not appear, verify:

```bash
ros2 topic echo /sim/actor_markers --once
ros2 topic echo /sim/evaluation_markers --once
```

## Oracle Mode

Oracle mode bypasses the detector and publishes ground truth subject pose to `/mecanumbot/subject_pose`.

```bash
./mecanumbot_RL/scripts/run_sim.sh subject_source:=oracle
```

Alternate oracle scenario:

```bash
./mecanumbot_RL/scripts/run_sim.sh \
  subject_source:=oracle \
  scenario_path:="$WORKSPACE/install/mecanumbot_bringup/share/mecanumbot_bringup/config/sim_scenarios/human_near_wall.yaml"
```

Oracle mode is useful to separate behavior bugs from perception bugs.

## Clean Restart

If RViz shows `TF_OLD_DATA`, time jumps, duplicate nodes, or topics have multiple unexpected publishers, stop the launch with `Ctrl-C`. If needed, clean stale processes:

```bash
pkill -f launch_mecanumbot_sim_perception.launch.py
pkill -f launch_mecanumbot_sim.launch.py
pkill -f mecanumbot_sim_io_node
pkill -f mecanumbot_sensorproc_node
pkill -f mecanumbot_lidar_detect_people
pkill -f mecanumbot_sim_detection_evaluator_node
pkill -f mecanumbot_sim_behavior_evaluator_node
pkill -f robot_state_publisher
pkill -f rviz2
```

Then verify:

```bash
pgrep -af 'mecanumbot_sim|mecanumbot_lidar_detect_people|launch_mecanumbot_sim'
ros2 topic info /clock -v
```

Then relaunch from scratch.

## Code Locations

Main sim bridge:

- `$WORKSPACE/src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_sim_io_node.py`

Scenario loader and actor runtime:

- `$WORKSPACE/src/mecanumbot/mecanumbot_core/mecanumbot_core/sim_scenarios.py`
- `$WORKSPACE/src/mecanumbot/mecanumbot_core/mecanumbot_core/sim_actor_runtime.py`

Evaluation nodes:

- `$WORKSPACE/src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_sim_detection_evaluator_node.py`
- `$WORKSPACE/src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_sim_behavior_evaluator_node.py`

Launch files:

- `$WORKSPACE/src/mecanumbot/mecanumbot_bringup/launch/launch_mecanumbot_sim.launch.py`
- `$WORKSPACE/src/mecanumbot/mecanumbot_bringup/launch/launch_mecanumbot_sim_perception.launch.py`

MuJoCo model:

- `$WORKSPACE/src/mecanumbot/mecanumbot_description/mujoco/mecanumbot.xml`

Scenarios:

- `$WORKSPACE/src/mecanumbot/mecanumbot_bringup/config/sim_scenarios/`

Messages:

- `$WORKSPACE/src/mecanumbot_msgs/mecanumbot_msgs/msg/SimActor.msg`
- `$WORKSPACE/src/mecanumbot_msgs/mecanumbot_msgs/msg/SimActorArray.msg`
- `$WORKSPACE/src/mecanumbot_msgs/mecanumbot_msgs/msg/SimDetectionEvaluation.msg`
- `$WORKSPACE/src/mecanumbot_msgs/mecanumbot_msgs/msg/SimBehaviorEvaluation.msg`

## Current Limitations

- The MuJoCo robot model is simplified, especially wheel-ground contact and sideways mecanum behavior.
- Human models are simplified collision/visual proxies, not articulated people.
- The detector is the real DR-SPAAM path, so hard scenarios may legitimately produce `subject_error_high` or wrong-target statuses.
- The behavior evaluator watches `/cmd_vel`; it does not itself control the robot.
- The existing behavior tree is not yet fully integrated into a single full-stack launch. Oracle mode and `/sim/behavior_evaluation` are available to test that next.
