from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np


DEFAULT_MODEL_PATH = Path(__file__).with_name("mecanumbot_sim") / "base_mecanumbot.xml"
WHEEL_ACTUATORS = ("fl", "fr", "bl", "br")
PRIMITIVE_BEHAVIORS = (
    "idle",
    "forward",
    "backward",
    "strafe_left",
    "strafe_right",
    "rotate_ccw",
    "rotate_cw",
)
SCRIPTED_BEHAVIORS = ("demo", "square", "out_and_back", "spin_scan", "zigzag")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open a MuJoCo viewer for the mecanumbot model.")
    parser.add_argument(
        "model",
        nargs="?",
        default=DEFAULT_MODEL_PATH,
        type=Path,
        help=f"Path to the MuJoCo XML model (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--behavior",
        choices=PRIMITIVE_BEHAVIORS + SCRIPTED_BEHAVIORS,
        default="demo",
        help="Wheel behavior to run in the viewer.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=4.0,
        help="Wheel target speed used by the selected behavior.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=20.0,
        help="Simulation time in seconds before the behavior loops.",
    )
    return parser.parse_args()


def yaw_from_xmat(xmat: np.ndarray) -> float:
    return math.atan2(xmat[3], xmat[0])


def wrap_to_pi(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def primitive_command(name: str, speed: float) -> tuple[float, float, float, float]:
    if name == "idle":
        return (0.0, 0.0, 0.0, 0.0)
    if name == "forward":
        return (-speed, speed, -speed, speed)
    if name == "backward":
        return (speed, -speed, speed, -speed)
    if name == "strafe_left":
        return (-speed, -speed, speed, speed)
    if name == "strafe_right":
        return (speed, speed, -speed, -speed)
    if name == "rotate_ccw":
        return (-speed, -speed, -speed, -speed)
    if name == "rotate_cw":
        return (speed, speed, speed, speed)
    raise ValueError(f"Unknown primitive behavior: {name}")


def turn_command_from_error(yaw_error: float, max_speed: float) -> tuple[float, float, float, float]:
    if abs(yaw_error) < 0.05:
        return primitive_command("idle", 0.0)

    turn_speed = min(max_speed, max(0.8, 2.2 * abs(yaw_error)))
    if yaw_error > 0.0:
        return primitive_command("rotate_ccw", turn_speed)
    return primitive_command("rotate_cw", turn_speed)


@dataclass
class ScriptState:
    phase_name: str = "init"
    step_index: int = 0
    phase_start_xy: np.ndarray | None = None
    target_yaw: float | None = None


class ScriptedController:
    def __init__(self) -> None:
        self.state = ScriptState()
        self.active_behavior: str | None = None

    def begin_behavior(self, behavior_name: str) -> None:
        if self.active_behavior != behavior_name:
            self.active_behavior = behavior_name
            self.state = ScriptState()

    def reset_phase(self, phase_name: str, pos_xy: np.ndarray, target_yaw: float | None = None) -> None:
        self.state.phase_name = phase_name
        self.state.phase_start_xy = pos_xy.copy()
        self.state.target_yaw = target_yaw

    def square(self, pos_xy: np.ndarray, yaw: float, speed: float) -> tuple[str, tuple[float, float, float, float]]:
        side_length = 0.8

        if self.state.phase_name == "init":
            self.state.step_index = 0
            self.reset_phase("square_forward", pos_xy)

        if self.state.phase_name == "square_forward":
            distance = np.linalg.norm(pos_xy - self.state.phase_start_xy)
            if distance >= side_length:
                self.reset_phase("square_turn", pos_xy, wrap_to_pi(yaw + math.pi / 2.0))
            else:
                return (self.state.phase_name, primitive_command("forward", speed))

        if self.state.phase_name == "square_turn":
            yaw_error = wrap_to_pi(self.state.target_yaw - yaw)
            if abs(yaw_error) < 0.05:
                self.state.step_index = (self.state.step_index + 1) % 4
                self.reset_phase("square_forward", pos_xy)
                return (self.state.phase_name, primitive_command("forward", speed))
            return (self.state.phase_name, turn_command_from_error(yaw_error, speed))

        return ("square_forward", primitive_command("forward", speed))

    def out_and_back(self, pos_xy: np.ndarray, yaw: float, speed: float) -> tuple[str, tuple[float, float, float, float]]:
        leg_length = 1.2

        if self.state.phase_name == "init":
            self.state.step_index = 0
            self.reset_phase("out", pos_xy)

        if self.state.phase_name == "out":
            distance = np.linalg.norm(pos_xy - self.state.phase_start_xy)
            if distance >= leg_length:
                self.reset_phase("turn_around", pos_xy, wrap_to_pi(yaw + math.pi))
            else:
                return (self.state.phase_name, primitive_command("forward", speed))

        if self.state.phase_name == "turn_around":
            yaw_error = wrap_to_pi(self.state.target_yaw - yaw)
            if abs(yaw_error) < 0.05:
                self.reset_phase("back", pos_xy)
                return (self.state.phase_name, primitive_command("forward", speed))
            return (self.state.phase_name, turn_command_from_error(yaw_error, speed))

        if self.state.phase_name == "back":
            distance = np.linalg.norm(pos_xy - self.state.phase_start_xy)
            if distance >= leg_length:
                self.reset_phase("settle", pos_xy)
            else:
                return (self.state.phase_name, primitive_command("forward", speed))

        if self.state.phase_name == "settle":
            return (self.state.phase_name, primitive_command("idle", 0.0))

        return ("out", primitive_command("forward", speed))


def scripted_behavior(
    name: str, speed: float, sim_time: float, duration: float
) -> tuple[str, tuple[float, float, float, float]]:
    phase = sim_time % duration

    if name == "demo":
        segment = duration / 4.0
        if phase < segment:
            return ("forward", primitive_command("forward", speed))
        if phase < 2 * segment:
            return ("strafe_left", primitive_command("strafe_left", speed))
        if phase < 3 * segment:
            return ("rotate_ccw", primitive_command("rotate_ccw", speed))
        return ("idle", primitive_command("idle", 0.0))

    if name == "square":
        segment = duration / 8.0
        index = int(phase // segment)
        if index % 2 == 0:
            return ("square_forward", primitive_command("forward", speed))
        return ("square_turn", primitive_command("rotate_ccw", speed * 0.8))

    if name == "out_and_back":
        segment = duration / 4.0
        if phase < segment:
            return ("out", primitive_command("forward", speed))
        if phase < 2 * segment:
            return ("turn_around", primitive_command("rotate_ccw", speed))
        if phase < 3 * segment:
            return ("back", primitive_command("forward", speed))
        return ("settle", primitive_command("idle", 0.0))

    if name == "spin_scan":
        segment = duration / 3.0
        if phase < segment:
            return ("scan_ccw", primitive_command("rotate_ccw", speed * 0.7))
        if phase < 2 * segment:
            return ("pause", primitive_command("idle", 0.0))
        return ("scan_cw", primitive_command("rotate_cw", speed * 0.7))

    if name == "zigzag":
        segment = duration / 6.0
        index = int(phase // segment)
        if index in (0, 3):
            return ("forward", primitive_command("forward", speed))
        if index in (1, 4):
            return ("turn_left", primitive_command("rotate_ccw", speed * 0.7))
        return ("turn_right", primitive_command("rotate_cw", speed * 0.7))

    raise ValueError(f"Unknown scripted behavior: {name}")


def behavior_command(
    name: str,
    speed: float,
    sim_time: float,
    duration: float,
    pos_xy: np.ndarray,
    yaw: float,
    controller: ScriptedController,
) -> tuple[str, tuple[float, float, float, float]]:
    if name in PRIMITIVE_BEHAVIORS:
        return (name, primitive_command(name, speed))
    if name == "square":
        controller.begin_behavior(name)
        return controller.square(pos_xy, yaw, speed)
    if name == "out_and_back":
        controller.begin_behavior(name)
        return controller.out_and_back(pos_xy, yaw, speed)
    return scripted_behavior(name, speed, sim_time, duration)


def set_wheel_ctrl(model: mujoco.MjModel, data: mujoco.MjData, wheel_cmd: tuple[float, float, float, float]) -> None:
    data.ctrl[:] = 0.0
    for actuator_name, ctrl in zip(WHEEL_ACTUATORS, wheel_cmd):
        actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name)
        if actuator_id >= 0:
            data.ctrl[actuator_id] = ctrl


def main() -> None:
    args = parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)

    base_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base")
    last_log_time = -1.0
    controller = ScriptedController()

    with mujoco.viewer.launch_passive(model, data) as viewer:
        start_wall_time = time.time()
        while viewer.is_running():
            sim_time = (time.time() - start_wall_time) % args.duration
            pos = data.xpos[base_body_id]
            yaw = yaw_from_xmat(data.xmat[base_body_id])
            phase_name, wheel_cmd = behavior_command(
                args.behavior,
                args.speed,
                sim_time,
                args.duration,
                pos[:2],
                yaw,
                controller,
            )
            set_wheel_ctrl(model, data, wheel_cmd)

            mujoco.mj_step(model, data)
            viewer.sync()

            if data.time - last_log_time >= 1.0:
                pos = data.xpos[base_body_id]
                yaw = yaw_from_xmat(data.xmat[base_body_id])
                print(
                    f"time={data.time:6.2f}s "
                    f"phase={phase_name:>12s} "
                    f"pos=({pos[0]: .3f}, {pos[1]: .3f}, {pos[2]: .3f}) "
                    f"yaw={yaw: .3f} "
                    f"ctrl={wheel_cmd}"
                )
                last_log_time = data.time


if __name__ == "__main__":
    main()
