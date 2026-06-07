"""Command (RPC action) tests: call the @action functions directly.

We point storage at a temp SQLite DB and import main once to wire the singletons,
then make motion instant so a full startSequence cycle completes quickly.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest


@pytest.fixture(scope="module")
def app_runtime():
    """Import main with a temp DB so the singletons are wired for the action handlers."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["VENTION_STORAGE_DATABASE_URL"] = f"sqlite:///{tmp.name}"

    import main  # noqa: F401 - import wires runtime + finalizes app
    from app import runtime

    yield runtime

    os.remove(tmp.name)


@pytest.fixture
def instant_motion(app_runtime, monkeypatch):
    """Make the real controller's motion + gripper complete immediately."""
    controller = app_runtime.get_controller()

    async def fast_move(target, speed):
        controller._robot.current_position = list(target)
        return list(target)

    async def fast_close():
        controller._robot.closed_gripper()

    async def fast_open():
        controller._robot.open_gripper()

    monkeypatch.setattr(controller, "move_until_done", fast_move)
    monkeypatch.setattr(controller, "close_gripper", fast_close)
    monkeypatch.setattr(controller, "open_gripper", fast_open)
    return controller


def test_get_status_shape(app_runtime):
    from app.api import commands

    status = commands.get_status()
    assert status.state == "ready"
    assert len(status.position) == 3
    assert status.gripper in ("open", "closed")


def test_rpc_wire_uses_camelcase(app_runtime):
    """The frontend depends on camelCase keys; assert the real HTTP wire emits them.

    Guards the CamelModel alias generator against a future pydantic/communication
    version bump that would silently fall back to snake_case.
    """
    from starlette.testclient import TestClient

    import main

    path = next(
        r.path for r in main.app.routes if getattr(r, "path", "").endswith("/getStatus")
    )
    body = TestClient(main.app).post(path, json={}).json()

    for camel in ("cubeStart", "lastState", "errorMessage"):
        assert camel in body, f"missing {camel}; got {sorted(body)}"
    for snake in ("cube_start", "last_state", "error_message"):
        assert snake not in body
    assert body["gripper"] in ("open", "closed")


def test_set_config_roundtrip(app_runtime):
    from app.api import commands

    resp = commands.set_config(
        commands.ConfigPayload(
            cube_start=[100, 200, 0],
            destination=[300, 400, 0],
            travel_z=150,
            speed=80,
        )
    )
    assert resp.ok is True
    assert resp.cube_start == [100, 200, 0]
    assert resp.destination == [300, 400, 0]
    assert resp.travel_z == 150
    assert resp.speed == 80

    got = commands.get_config()
    assert got.cube_start == [100, 200, 0]
    assert got.speed == 80


def test_set_config_rejects_out_of_bounds(app_runtime):
    from app.api import commands

    resp = commands.set_config(
        commands.ConfigPayload(cube_start=[9999, 0, 0], destination=[0, 0, 0])
    )
    assert resp.ok is False
    assert "cubeStart" in resp.message


def test_set_config_rejects_bad_speed(app_runtime):
    from app.api import commands

    resp = commands.set_config(
        commands.ConfigPayload(cube_start=[0, 0, 0], destination=[0, 0, 0], speed=500)
    )
    assert resp.ok is False


async def test_full_start_sequence_cycle(app_runtime, instant_motion):
    from app.api import commands

    machine = app_runtime.get_machine()
    if machine.state != "ready":
        machine.reset()

    resp = await commands.start_sequence()
    assert resp.ok is True

    deadline = asyncio.get_event_loop().time() + 3.0
    left_ready = False
    while True:
        if machine.state != "ready":
            left_ready = True
        elif left_ready:
            break
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"cycle did not finish; stuck at {machine.state}")
        await asyncio.sleep(0.005)

    final = commands.get_status()
    assert final.state == "ready"
    assert final.gripper == "open"


async def test_start_rejected_when_not_ready(app_runtime):
    from app.api import commands

    machine = app_runtime.get_machine()
    if machine.state == "fault":
        machine.reset()
    # Force into fault, then start must be rejected.
    machine.trigger("to_fault")
    resp = await commands.start_sequence()
    assert resp.ok is False
    # Recover for other tests.
    machine.reset()


async def test_stop_rejected_when_idle(app_runtime):
    from app.api import commands

    machine = app_runtime.get_machine()
    if machine.state == "fault":
        machine.reset()
    resp = await commands.stop_sequence()
    assert resp.ok is False
    assert "nothing to stop" in resp.message.lower()


async def test_stop_config_lock_and_resume(app_runtime, monkeypatch):
    """Mid-sequence: config is locked, stop faults resumably, resume finishes the cycle."""
    from app.api import commands

    machine = app_runtime.get_machine()
    controller = app_runtime.get_controller()
    if machine.state != "ready":
        machine.reset()

    # Park each move until released, so the machine sits in a sequence leaf.
    release = asyncio.Event()

    async def blocking_move(target, speed):
        controller._robot.current_position = list(target)
        await release.wait()
        return list(target)

    monkeypatch.setattr(controller, "move_until_done", blocking_move)

    assert (await commands.start_sequence()).ok is True
    await asyncio.sleep(0.02)
    assert machine.state.startswith("Seq_")

    # setConfig must be rejected while the sequence runs.
    cfg = commands.set_config(
        commands.ConfigPayload(cube_start=[0, 0, 0], destination=[10, 10, 0])
    )
    assert cfg.ok is False
    assert "locked" in cfg.message.lower()

    # Stop faults the machine and marks it resumable.
    stop = await commands.stop_sequence()
    assert stop.ok is True
    assert machine.state == "fault"
    assert commands.get_status().resumable is True

    # From here moves complete instantly; release the parked one and resume.
    async def fast_move(target, speed):
        controller._robot.current_position = list(target)
        return list(target)

    monkeypatch.setattr(controller, "move_until_done", fast_move)
    release.set()

    assert (await commands.resume_sequence()).ok is True

    deadline = asyncio.get_event_loop().time() + 3.0
    while machine.state != "ready":
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"resume did not finish; stuck at {machine.state}")
        await asyncio.sleep(0.005)
    assert commands.get_status().resumable is False
