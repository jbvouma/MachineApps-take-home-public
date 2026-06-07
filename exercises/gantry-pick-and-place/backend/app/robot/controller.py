"""Robot controller: wraps the simulator and owns the move-until-done convergence loop.

robot_sim.move_to is time-based and must be polled repeatedly. We decide "done"
ourselves (per SPEC): the sim returned an error (stop + raise), axis_speed is zeroed,
or a wall-clock safety timeout elapsed. We never trust the sim's _is_motion_completed.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.config import (
    MOVE_POLL_INTERVAL_S,
    MOVE_TIMEOUT_S,
    GRIPPER_SETTLE_S,
    validate_position,
    validate_speed,
)
from app.logging_config import get_logger
from robot_sim import GripperState, Robot

logger = get_logger(__name__)


class MotionError(RuntimeError):
    """Raised when a move fails: sim error string or safety timeout."""


@dataclass
class RobotSnapshot:
    """Immutable view of robot state for telemetry."""

    position: list[float]
    moving: bool
    gripper: str  # "open" | "closed"


class RobotController:
    """Thin async wrapper around robot_sim.Robot."""

    def __init__(
        self,
        initial_position: list[float] | None = None,
        home_position: list[float] | None = None,
        *,
        poll_interval: float = MOVE_POLL_INTERVAL_S,
        timeout: float = MOVE_TIMEOUT_S,
    ) -> None:
        self._robot = Robot(
            initial_position=list(initial_position or [0.0, 0.0, 0.0]),
            home_position=list(home_position or [0.0, 0.0, 0.0]),
            gripper_state=GripperState.OPEN,
        )
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._moving = False

    @property
    def position(self) -> list[float]:
        return list(self._robot.current_position)

    @property
    def moving(self) -> bool:
        return self._moving

    @property
    def gripper(self) -> str:
        return "closed" if self._robot.gripper_state == GripperState.CLOSED else "open"

    def set_home(self, home_position: list[float]) -> None:
        self._robot.home_position = list(home_position)

    def snapshot(self) -> RobotSnapshot:
        return RobotSnapshot(
            position=self.position, moving=self._moving, gripper=self.gripper
        )

    async def move_until_done(self, target: list[float], speed: int) -> list[float]:
        """Poll move_to until the motion converges. Raises MotionError on failure."""
        err = validate_position(target)
        if err:
            raise MotionError(err)
        err = validate_speed(speed)
        if err:
            raise MotionError(err)

        logger.info("Motion start -> target=%s speed=%s", target, speed)
        self._moving = True
        deadline = time.monotonic() + self._timeout
        try:
            while True:
                _, axis_speed, error = self._robot.move_to(list(target), speed)
                if error is not None:
                    raise MotionError(str(error))
                if all(v == 0 for v in axis_speed):
                    break
                if time.monotonic() > deadline:
                    raise MotionError(
                        f"Move to {target} timed out after {self._timeout}s "
                        f"(at {self.position})"
                    )
                await asyncio.sleep(self._poll_interval)
        finally:
            self._moving = False

        logger.info("Motion done -> target=%s final=%s", target, self.position)
        return self.position

    async def close_gripper(self) -> None:
        logger.info("Gripper close")
        self._robot.closed_gripper()
        if GRIPPER_SETTLE_S > 0:
            await asyncio.sleep(GRIPPER_SETTLE_S)

    async def open_gripper(self) -> None:
        logger.info("Gripper open")
        self._robot.open_gripper()
        if GRIPPER_SETTLE_S > 0:
            await asyncio.sleep(GRIPPER_SETTLE_S)
