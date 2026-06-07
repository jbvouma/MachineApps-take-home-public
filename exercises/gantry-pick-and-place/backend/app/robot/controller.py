"""Robot controller: wraps the simulator and owns the move-until-done convergence loop.

robot_sim.move_to is time-based and must be polled repeatedly. We own the "done"
decision with our own position-tolerance check (every axis within POSITION_TOLERANCE_MM
of the target), so completion does not depend on the sim's fragile _is_motion_completed.
A move also ends if the sim returns an error (raise), an operator stop is requested
(raise MotionStopped), or a wall-clock safety timeout elapses (raise).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.config import (
    MOVE_POLL_INTERVAL_S,
    MOVE_TIMEOUT_S,
    GRIPPER_SETTLE_S,
    POSITION_TOLERANCE_MM,
    validate_position,
    validate_speed,
)
from app.logging_config import get_logger
from robot_sim import GripperState, Robot

logger = get_logger(__name__)


class MotionError(RuntimeError):
    """Raised when a move fails: sim error string or safety timeout."""


class MotionStopped(MotionError):
    """Raised inside the poll loop when an operator stop is requested mid-move."""


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
        self._stop_requested = False

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

    def request_stop(self) -> None:
        """Signal any in-flight move to abort at its next poll (cooperative stop).

        We do not command the sim to decelerate; we simply stop issuing move_to, so
        the robot holds at its current integrated position. This is the stop primitive
        the machine layer drives, independent of the library's task cancellation.
        """
        self._stop_requested = True

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
        self._stop_requested = False
        self._moving = True
        # Reset the sim's residual velocity so this move replans from the current
        # position with a fresh timestamp. Without this, a move that was stopped
        # mid-flight left axis_speed/last_motion_time stale; the first poll on resume
        # would integrate the whole paused gap at once and jump the robot.
        self._robot.axis_speed = [0, 0, 0]
        deadline = time.monotonic() + self._timeout
        try:
            while True:
                if self._stop_requested:
                    raise MotionStopped(f"Move to {target} stopped by operator")
                _, axis_speed, error = self._robot.move_to(list(target), speed)
                if error is not None:
                    raise MotionError(str(error))
                # Our own completion criterion: within tolerance on every axis (with the
                # sim's zeroed axis_speed as a secondary signal). On arrival we normalize
                # the reported position to the commanded target, exactly as the sim does
                # on its own completion, so we never depend on its fragile check.
                if self._within_tolerance(target) or all(v == 0 for v in axis_speed):
                    self._robot.current_position = list(target)
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

    def _within_tolerance(self, target: list[float]) -> bool:
        pos = self._robot.current_position
        return all(abs(pos[i] - target[i]) <= POSITION_TOLERANCE_MM for i in range(len(target)))

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
