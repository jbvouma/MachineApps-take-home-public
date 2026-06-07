"""State machine tests: full happy path, guards, and fault recovery.

Motion is made instant via a fake controller so spawned move loops complete in one
event-loop turn. We then yield to the loop until the machine settles.
"""

from __future__ import annotations

import asyncio

import pytest

from app.machine import states as st
from app.machine.pick_place import MachineContext, PickPlaceMachine


class InstantController:
    """Controller stub whose moves and gripper actions complete immediately."""

    def __init__(self) -> None:
        self.position = [0.0, 0.0, 0.0]
        self.moving = False
        self.gripper = "open"

    async def move_until_done(self, target, speed):
        self.position = list(target)
        return self.position

    async def close_gripper(self):
        self.gripper = "closed"

    async def open_gripper(self):
        self.gripper = "open"

    def set_home(self, home):
        pass

    def snapshot(self):
        return None


async def _settle(machine: PickPlaceMachine, target: str, timeout: float = 2.0) -> None:
    """Yield to the event loop until the machine reaches ``target`` (or timeout)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while machine.state != target:
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"stuck in {machine.state}, expected {target}")
        await asyncio.sleep(0.01)


@pytest.fixture
def machine():
    return PickPlaceMachine(controller=InstantController(), context=MachineContext())


async def test_full_happy_path(machine):
    assert machine.state == st.READY
    machine.start()
    # The whole chain auto-advances through spawned tasks back to ready.
    await _settle(machine, st.READY)
    assert machine.state == st.READY
    assert machine.context.error_message == ""


async def test_each_transition_visited(machine):
    """Drive a full cycle and confirm every expected leaf state was recorded.

    We check machine.history (a deterministic record of every transition) rather
    than sampling machine.state, since instant-motion transitions fire faster than
    any polling interval could observe.
    """
    machine.start()
    await _settle(machine, st.READY)

    seen = {entry["state"] for entry in machine.history}

    expected = {
        "Seq_movingToCube",
        "Seq_loweringToCube",
        "Seq_closingGripper",
        "Seq_liftingWithCube",
        "Seq_movingToDestination",
        "Seq_loweringToDestination",
        "Seq_openingGripper",
        "Seq_liftingClear",
    }
    assert expected.issubset(set(seen)), f"missing states; saw {set(seen)}"


async def test_start_rejected_mid_sequence(machine):
    machine.start()
    await asyncio.sleep(0)  # let it leave ready
    assert machine.state != st.READY
    # A second start mid-sequence must not restart the cycle. Guard blocks it
    # (no-op) or the library raises; both are acceptable rejections.
    try:
        machine.start()
    except Exception:
        pass
    assert machine.state != st.READY


async def test_home_rejected_mid_sequence(machine):
    machine.start()
    await asyncio.sleep(0)
    assert machine.state != st.READY
    # Home off ready only: mid-sequence it must not enter homing. The library may
    # either block via the guard (no-op) or raise an invalid-transition error;
    # either way we must not land in homing.
    try:
        machine.home()
    except Exception:
        pass
    assert machine.state != "Seq_homing"


async def test_home_from_ready(machine):
    assert machine.state == st.READY
    machine.home()
    await _settle(machine, st.READY)
    assert machine.state == st.READY


async def test_fault_and_reset_recovers(machine):
    machine.trigger(st.TO_FAULT)
    assert machine.state == st.FAULT
    machine.reset()
    assert machine.state == st.READY
    # After reset, the sequence can run again.
    machine.start()
    await _settle(machine, st.READY)
    assert machine.state == st.READY
