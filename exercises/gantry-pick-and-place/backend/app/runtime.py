"""Process-wide singletons shared between main.py wiring and the @action handlers.

main.py builds the controller + machine + context once at import/startup and calls
``init_runtime``. The @action functions in api/commands.py read them back via the
getters. This avoids circular imports (commands need the machine; main owns its
construction) and keeps a single source of truth for the running instances.
"""

from __future__ import annotations

from app.machine.pick_place import MachineContext, PickPlaceMachine
from app.robot.controller import RobotController

_controller: RobotController | None = None
_machine: PickPlaceMachine | None = None
_context: MachineContext | None = None


def init_runtime(
    controller: RobotController,
    machine: PickPlaceMachine,
    context: MachineContext,
) -> None:
    global _controller, _machine, _context
    _controller = controller
    _machine = machine
    _context = context


def get_controller() -> RobotController:
    if _controller is None:
        raise RuntimeError("Runtime not initialized: controller missing")
    return _controller


def get_machine() -> PickPlaceMachine:
    if _machine is None:
        raise RuntimeError("Runtime not initialized: machine missing")
    return _machine


def get_context() -> MachineContext:
    if _context is None:
        raise RuntimeError("Runtime not initialized: context missing")
    return _context
