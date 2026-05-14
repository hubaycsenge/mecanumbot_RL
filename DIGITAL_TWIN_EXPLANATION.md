# Mecanumbot Digital Twin Explanation

This file explains how the ROS 2 + MuJoCo digital twin works in this workspace.

It is written to be easy to explain in a demo, lab, or viva setting.

## One-Sentence Summary

The digital twin is a MuJoCo physics simulation wrapped in ROS 2 nodes so that teleop, TF, RViz, and robot topics behave similarly to the real robot.

## Big Picture

There are four main parts involved in the sim path:

1. `mecanumbot_description`
2. `mecanumbot_bringup`
3. `mecanumbot_core`
4. `mecanumbot_teleop`

Their roles are:

- `mecanumbot_description` contains the robot models and assets.
- `mecanumbot_bringup` contains the launch files.
- `mecanumbot_core` contains the runtime nodes that connect MuJoCo to ROS 2.
- `mecanumbot_teleop` provides keyboard control input.

## What Each Package Does

### `mecanumbot_description`

Important files:

- `src/mecanumbot/mecanumbot_description/urdf/mecanumbot.urdf`
- `src/mecanumbot/mecanumbot_description/mujoco/mecanumbot.xml`
- `src/mecanumbot/mecanumbot_description/meshes/`

Purpose:

- The URDF is the ROS-side robot model used by `robot_state_publisher` and RViz.
- The MuJoCo XML is the physics model used by the simulator.
- The meshes are used by RViz to render the robot visually.

Why there are two robot models:

- URDF is for ROS visualization and TF.
- MuJoCo XML is for physics, collisions, actuators, and simulation world setup.

### `mecanumbot_bringup`

Important file:

- `src/mecanumbot/mecanumbot_bringup/launch/launch_mecanumbot_sim.launch.py`

Purpose:

- Starts the digital twin stack.

It launches:

- `mecanumbot_sim_io_node`
- `mecanumbot_sensorproc_node`
- `robot_state_publisher`

### `mecanumbot_core`

Important files:

- `src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_sim_io_node.py`
- `src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_sensorproc_node.py`
- `src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_IO_node.py`

Purpose:

- `mecanumbot_IO_node.py` is the real hardware-facing node.
- `mecanumbot_sim_io_node.py` is the MuJoCo bridge.
- `mecanumbot_sensorproc_node.py` converts low-level simulated robot state into standard ROS topics.

### `mecanumbot_teleop`

Purpose:

- Sends keyboard commands such as `cmd_vel`.
- These commands are consumed by the simulator.

## What Happens When The Sim Starts

When you run:

```bash
ros2 launch mecanumbot_bringup launch_mecanumbot_sim.launch.py
```

the following happens:

1. `mecanumbot_sim_io_node` loads the MuJoCo model.
2. `mecanumbot_sensorproc_node` starts publishing standard robot topics.
3. `robot_state_publisher` loads the URDF and publishes the robot TF tree.

## The Real IO Node vs The Sim IO Node

This is one of the most important design decisions in the digital twin.

### Real robot path

On the physical robot, the low-level node is:

- `src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_IO_node.py`

That node is built for hardware. It:

- opens a serial connection to the robot controller
- sends wheel and accessory commands to the board
- reads back low-level state such as wheel velocities, positions, IMU values, and battery information

So this node depends on real hardware being connected.

### Sim path

In simulation, that real hardware node cannot be used directly.

Instead, the sim uses:

- `src/mecanumbot/mecanumbot_core/mecanumbot_core/mecanumbot_sim_io_node.py`

This node plays the same architectural role as the real IO node, but instead of talking to hardware it talks to MuJoCo.

It:

- receives ROS commands
- applies them to MuJoCo actuators
- steps the simulation
- reads simulated robot state
- publishes a simulated `OpenCRState`

### Why this matters

The key idea is:

- the real robot and the simulated robot both expose the same low-level ROS interface

That means the next layer of the stack can stay mostly unchanged.

So the structure is:

- real robot:
  `mecanumbot_IO_node.py` -> `OpenCRState` -> `mecanumbot_sensorproc_node.py`
- simulator:
  `mecanumbot_sim_io_node.py` -> `OpenCRState` -> `mecanumbot_sensorproc_node.py`

This is why only the hardware-facing node had to be replaced. The higher-level processing node could be reused.

### Short explanation you can say out loud

> We replaced the real hardware IO node with a simulation IO node.  
> The original node talks to OpenCR over serial, which cannot work in MuJoCo.  
> So the sim node was created to provide the same low-level ROS interface, but backed by MuJoCo instead of hardware.  
> That allowed the existing sensor processing and visualization pipeline to be reused with minimal changes.

## The Core Simulation Pipeline

### Step 1: Teleop publishes commands

Keyboard teleop publishes:

- `geometry_msgs/Twist` on `cmd_vel`
- accessory commands on `cmd_accessory_pos`

These are the robot input commands.

### Step 2: `mecanumbot_sim_io_node` receives commands

This node:

- subscribes to `cmd_vel`
- subscribes to `cmd_accessory_pos`
- converts robot motion commands into wheel actuator commands
- applies those commands to the MuJoCo model

The mecanum wheel kinematics are implemented in `vel_cmd_callback()`.

Inputs:

- `vx` = forward/backward velocity
- `vy` = sideways velocity
- `wz` = angular velocity

Outputs:

- back-left wheel command
- back-right wheel command
- front-left wheel command
- front-right wheel command

### Step 3: MuJoCo advances the physics

Every timer tick:

- wheel and accessory controls are applied
- MuJoCo steps the simulation forward
- the robot position, orientation, wheel states, and body motion update

This happens in `timer_callback()` inside `mecanumbot_sim_io_node.py`.

### Step 4: The MuJoCo bridge publishes ROS topics

`mecanumbot_sim_io_node` publishes:

- `/clock`
- `/mecanumbot/scan`
- `/mecanumbot/opencr_state`

What each means:

- `/clock` is simulation time.
- `/mecanumbot/scan` is a synthetic LiDAR scan generated by MuJoCo raycasting.
- `/mecanumbot/opencr_state` is a simulated version of the low-level board state used on the real robot.

## Why `opencr_state` Exists In The Sim

On the real robot, an OpenCR-based low-level interface provides wheel, IMU, battery, and accessory state.

In the sim, there is no physical OpenCR board. Instead, the simulation publishes the same type of low-level state so that the rest of the ROS stack can stay compatible.

This is why the sim does not jump directly from physics to odom only. It intentionally preserves the real robot interface structure.

## What `mecanumbot_sensorproc_node` Does

This node subscribes to:

- `/mecanumbot/opencr_state`

Then it publishes:

- `/mecanumbot/odom`
- `/mecanumbot/imu`
- `/mecanumbot/joint_states`
- `/mecanumbot/battery_state`
- TF from `mecanumbot/odom` to `mecanumbot/base_footprint`

So this node is the translator from simulated low-level hardware state to standard ROS outputs.

## How Odometry Is Computed

Odometry is computed from wheel velocities.

The node reads:

- `vel_bl`
- `vel_br`
- `vel_fl`
- `vel_fr`

Then it computes:

- linear x velocity
- linear y velocity
- angular z velocity

Then it integrates these over time to estimate:

- x position
- y position
- robot heading

This is what creates `/mecanumbot/odom`.

## How The LiDAR Scan Is Computed

The LiDAR is not coming from a real sensor.

Instead:

- the node finds the simulated laser frame in MuJoCo
- it casts rays outward in many directions
- each ray measures distance to the first hit
- those distances are packed into a `sensor_msgs/LaserScan`

This is why the scan works in RViz even though the robot is entirely simulated.

## What `robot_state_publisher` Does

`robot_state_publisher` does not simulate motion.

Its job is:

- read the URDF
- publish the link/joint TF tree
- use `/joint_states` to place moving links correctly

This is what allows RViz to show the robot structure.

Examples of frames it publishes:

- `mecanumbot/base_link`
- `mecanumbot/base_scan`
- `mecanumbot/head_link`
- wheel links
- camera links

## Why RViz Needs `mecanumbot_description`

The URDF uses mesh URIs like:

```text
package://mecanumbot_description/meshes/base.stl
```

RViz can only load those meshes if the `mecanumbot_description` package is visible in the current shell environment.

If RViz starts without the correct package environment sourced:

- TF may still work
- `/robot_description` may still exist
- but meshes will fail to load

That is why RViz must be launched from a terminal where `mecanumbot_description` is sourced.

## Data Flow Summary

The easiest way to describe the whole system is:

1. Teleop publishes `cmd_vel`
2. `mecanumbot_sim_io_node` converts `cmd_vel` into wheel commands
3. MuJoCo simulates robot motion
4. `mecanumbot_sim_io_node` publishes:
   - simulated board state
   - simulated scan
   - simulated clock
5. `mecanumbot_sensorproc_node` converts board state into:
   - odom
   - imu
   - joint states
   - battery state
   - TF
6. `robot_state_publisher` uses the URDF to publish the robot model tree
7. RViz visualizes the robot and sensor data

## Why The Timestamp Fix Matters

Originally, `mecanumbot_sensorproc_node` was using its own local node clock for timing.

That can drift from the actual simulated state timing.

The fix keeps the node aligned with the incoming simulated message timestamps, which improves:

- odometry timing
- TF timestamps
- IMU and joint-state consistency
- RViz behavior under sim time

In short:

- before: timing depended on the node loop clock
- now: timing follows the simulated robot state timestamps

## What You Can Say In A Demo

If you need a short explanation:

> The digital twin uses MuJoCo for physics and ROS 2 for communication and visualization.  
> A bridge node converts ROS commands into MuJoCo actuator inputs and then publishes simulated low-level robot state, clock, and LiDAR scan.  
> A second node converts that simulated low-level state into standard ROS topics like odometry, IMU, joint states, battery state, and TF.  
> The robot model in RViz comes from the URDF and `robot_state_publisher`.

## Good Short Answers For Questions

### “Why use `OpenCRState` in simulation?”

Because the sim is imitating the real robot’s low-level interface so higher-level ROS components can stay compatible.

### “Why separate URDF and MuJoCo XML?”

URDF is for ROS visualization and TF. MuJoCo XML is for physics and actuators.

### “Where does `/mecanumbot/odom` come from?”

It is published by `mecanumbot_sensorproc_node`, which computes body motion from the simulated wheel state.

### “Where does `/mecanumbot/scan` come from?”

It is generated by MuJoCo raycasting in `mecanumbot_sim_io_node`.

### “What publishes `/robot_description`?”

`robot_state_publisher`, using the URDF loaded by the sim launch file.

### “Why did RViz fail to show meshes before?”

Because RViz was started without the `mecanumbot_description` package environment sourced, so `package://...` mesh paths could not be resolved.

## Honest Summary Of What Was Recently Changed

The recent work on this sim path can be described honestly as:

- repaired the moved-workspace build/install state
- fixed sim timestamp handling in `mecanumbot_sensorproc_node`
- made the sim workflow portable by removing dependence on machine-specific absolute paths
