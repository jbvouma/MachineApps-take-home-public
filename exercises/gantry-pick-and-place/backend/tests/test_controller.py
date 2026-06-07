"""Controller tests: real Robot convergence and the safety-timeout path."""

from __future__ import annotations

import asyncio

import pytest

from app.robot.controller import MotionError, MotionStopped, RobotController


async def test_move_converges_to_target():
    ctrl = RobotController(initial_position=[0, 0, 0])
    final = await ctrl.move_until_done([100, 50, 25], speed=100)
    assert final == [100, 50, 25]
    assert ctrl.position == [100, 50, 25]
    assert ctrl.moving is False


async def test_gripper_open_close():
    ctrl = RobotController()
    assert ctrl.gripper == "open"
    await ctrl.close_gripper()
    assert ctrl.gripper == "closed"
    await ctrl.open_gripper()
    assert ctrl.gripper == "open"


async def test_invalid_position_raises():
    ctrl = RobotController()
    with pytest.raises(MotionError):
        await ctrl.move_until_done([5000, 0, 0], speed=50)


async def test_invalid_speed_raises():
    ctrl = RobotController()
    with pytest.raises(MotionError):
        await ctrl.move_until_done([10, 0, 0], speed=200)


async def test_safety_timeout_fires(monkeypatch):
    """A move that never converges must abort via the wall-clock timeout."""
    ctrl = RobotController(timeout=0.1, poll_interval=0.01)

    # Force the sim to always report it is still moving (never zeroes axis_speed).
    def never_done(target, speed=90):
        return ctrl.position, [1, 0, 0], None

    monkeypatch.setattr(ctrl._robot, "move_to", never_done)

    with pytest.raises(MotionError, match="timed out"):
        await ctrl.move_until_done([100, 0, 0], speed=50)
    assert ctrl.moving is False


async def test_request_stop_aborts_in_flight_move():
    """A slow move must abort promptly with MotionStopped once stop is requested."""
    ctrl = RobotController(initial_position=[0, 0, 0], poll_interval=0.01)
    # speed=1 over a 1000mm axis would take ~1000s, so it cannot converge on its own.
    task = asyncio.create_task(ctrl.move_until_done([1000, 0, 0], speed=1))
    await asyncio.sleep(0.05)
    assert ctrl.moving is True
    ctrl.request_stop()
    with pytest.raises(MotionStopped):
        await task
    assert ctrl.moving is False


async def test_stop_flag_resets_between_moves():
    """A stop request must not leak into the next move."""
    ctrl = RobotController(initial_position=[0, 0, 0], poll_interval=0.01)
    ctrl.request_stop()
    # The next move clears the flag at entry and should still converge normally.
    final = await ctrl.move_until_done([50, 0, 0], speed=100)
    assert final == [50, 0, 0]
