"""RPC command handlers (@action). Action names serialize to camelCase.

Handlers read the singleton controller/machine/context from app.runtime, which
main.py initializes before importing this module. Command rejections return a
structured CommandResponse(ok=false, ...) rather than raising, so the frontend
always gets a consistent shape.
"""

from __future__ import annotations

from communication.decorators import action

from app.api.schemas import (
    CommandResponse,
    ConfigPayload,
    ConfigResponse,
    StatusResponse,
)
from app.config import validate_position, validate_speed
from app.logging_config import get_logger
from app.machine import states as st
from app.runtime import get_context, get_controller, get_machine
from app.storage import accessors

logger = get_logger(__name__)


def _config_response(ctx, *, ok: bool = True, message: str = "") -> ConfigResponse:
    """Snapshot the current context as a ConfigResponse; ok/message vary per caller."""
    return ConfigResponse(
        cube_start=list(ctx.cube_start),
        destination=list(ctx.destination),
        home=list(ctx.home),
        travel_z=ctx.travel_z,
        speed=ctx.speed,
        ok=ok,
        message=message,
    )


@action(name="getStatus")
def get_status() -> StatusResponse:
    machine = get_machine()
    controller = get_controller()
    ctx = get_context()
    snap = controller.snapshot()
    return StatusResponse(
        position=snap.position,
        moving=snap.moving,
        gripper=snap.gripper,
        state=machine.state,
        last_state=machine.get_last_state(),
        resumable=machine.resumable,
        cube_start=list(ctx.cube_start),
        destination=list(ctx.destination),
        home=list(ctx.home),
        error_message=ctx.error_message,
    )


def _fire(trigger: str, success_msg: str, reject_msg: str) -> CommandResponse:
    """Fire a trigger and report whether it was accepted (guard / valid transition).

    Async so it runs on the event loop: on_enter handlers call self.spawn(), which
    needs a running loop. A guard rejection leaves the state unchanged with no
    exception, which we surface as ok=False.
    """
    machine = get_machine()
    logger.info("Command received: %s (state=%s)", trigger, machine.state)
    before = machine.state
    try:
        machine.trigger(trigger)
    except Exception as exc:  # noqa: BLE001 - invalid transition from current state
        logger.warning("Command %s failed: %s", trigger, exc)
        return CommandResponse(ok=False, message=f"{reject_msg}: {exc}", state=machine.state)
    if machine.state == before:
        return CommandResponse(ok=False, message=reject_msg, state=machine.state)
    return CommandResponse(ok=True, message=success_msg, state=machine.state)


@action(name="homeRobot")
async def home_robot() -> CommandResponse:
    return _fire(st.HOME, "Homing started", "Home rejected (busy)")


@action(name="startSequence")
async def start_sequence() -> CommandResponse:
    return _fire(st.START, "Sequence started", "Start rejected (not ready)")


@action(name="resetFault")
async def reset_fault() -> CommandResponse:
    return _fire(st.RESET, "Fault reset", "Reset rejected")


@action(name="stopSequence")
async def stop_sequence() -> CommandResponse:
    """Operator stop: halt motion mid-cycle and fault. Resumable afterwards."""
    machine = get_machine()
    logger.info("Command received: stopSequence (state=%s)", machine.state)
    if not machine.request_abort():
        return CommandResponse(
            ok=False, message="Nothing to stop (robot is idle)", state=machine.state
        )
    return CommandResponse(ok=True, message="Sequence stopped", state=machine.state)


@action(name="resumeSequence")
async def resume_sequence() -> CommandResponse:
    """Resume a sequence that was stopped by the operator, from where it halted."""
    machine = get_machine()
    logger.info("Command received: resumeSequence (state=%s)", machine.state)
    if not machine.resume():
        return CommandResponse(
            ok=False, message="Nothing to resume", state=machine.state
        )
    return CommandResponse(ok=True, message="Sequence resumed", state=machine.state)


@action(name="discardSequence")
async def discard_sequence() -> CommandResponse:
    """Discard a stopped sequence and home the robot to a known position."""
    machine = get_machine()
    logger.info("Command received: discardSequence (state=%s)", machine.state)
    if not machine.discard():
        return CommandResponse(
            ok=False, message="Nothing to discard", state=machine.state
        )
    return CommandResponse(ok=True, message="Sequence discarded; homing", state=machine.state)


@action(name="getConfig")
def get_config() -> ConfigResponse:
    return _config_response(get_context())


@action(name="setConfig")
def set_config(payload: ConfigPayload) -> ConfigResponse:
    ctx = get_context()
    controller = get_controller()

    # Config is only mutable while idle (ready) or faulted. Editing live trajectory
    # inputs mid-sequence would corrupt an in-flight pick, so reject it.
    machine = get_machine()
    if machine.state not in (st.READY, st.FAULT):
        return _config_response(
            ctx, ok=False, message="Configuration locked while a sequence is running"
        )

    # Fall back to current context values for omitted optional fields.
    home = payload.home if payload.home is not None else list(ctx.home)
    travel_z = payload.travel_z if payload.travel_z is not None else ctx.travel_z
    speed = payload.speed if payload.speed is not None else ctx.speed

    # Validate every position (including the travel-height target) and speed; reject
    # on the first failure, echoing back the unchanged config.
    checks = [
        ("cubeStart", validate_position(payload.cube_start)),
        ("destination", validate_position(payload.destination)),
        ("home", validate_position(home)),
        ("travelZ", validate_position([0.0, 0.0, travel_z])),
        ("speed", validate_speed(speed)),
    ]
    for label, err in checks:
        if err:
            return _config_response(ctx, ok=False, message=f"{label}: {err}")

    # Persist, then update the live machine context + controller home.
    accessors.save_config(
        cube_start=payload.cube_start,
        destination=payload.destination,
        home=home,
        travel_z=travel_z,
        speed=speed,
    )
    ctx.cube_start = list(payload.cube_start)
    ctx.destination = list(payload.destination)
    ctx.home = list(home)
    ctx.travel_z = travel_z
    ctx.speed = speed
    controller.set_home(home)
    logger.info("Config updated via setConfig")

    return _config_response(ctx, message="Configuration saved")
