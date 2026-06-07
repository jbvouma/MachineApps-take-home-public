"""PickPlaceMachine: sequences the robot through pick-and-place via spawned async moves.

Each moving/lowering/lifting state spawns ``_run_move`` on enter; it polls the
controller until the move converges, then fires the next trigger. Gripper states act
then advance. Any handler exception records an error and triggers ``to_fault``.
``home`` and ``start`` are guarded so they cannot interrupt a live sequence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from state_machine.core import StateMachine
from state_machine.decorators import guard, on_enter_state, on_state_change

from app.config import DEFAULTS
from app.logging_config import get_logger
from app.machine import states as st
from app.machine.states import Seq, States
from app.robot.controller import RobotController

logger = get_logger(__name__)


@dataclass
class MachineContext:
    """Live config + error state shared with the API layer."""

    cube_start: list[float] = field(default_factory=lambda: list(DEFAULTS.cube_start))
    destination: list[float] = field(default_factory=lambda: list(DEFAULTS.destination))
    home: list[float] = field(default_factory=lambda: list(DEFAULTS.home))
    travel_z: float = DEFAULTS.travel_z
    speed: int = DEFAULTS.speed
    error_message: str = ""


class PickPlaceMachine(StateMachine):
    """Drives the gantry through the pick-and-place cycle."""

    def __init__(self, controller: RobotController, context: MachineContext) -> None:
        self.controller = controller
        self.context = context
        super().__init__(
            States,
            transitions=st.TRANSITIONS,
            enable_last_state_recovery=True,
        )

    # -- step helpers: build the target / pick the action, spawn it, advance on done --
    def _move(self, xy: list[float], z: float, next_trigger: str) -> None:
        self.spawn(self._run_move([xy[0], xy[1], z], next_trigger))

    def _grip(self, *, close: bool, next_trigger: str) -> None:
        self.spawn(self._run_gripper(close=close, next_trigger=next_trigger))

    # -- async workers -------------------------------------------------------
    async def _run_move(self, target: list[float], next_trigger: str) -> None:
        try:
            await self.controller.move_until_done(target, self.context.speed)
        except Exception as exc:  # noqa: BLE001 - any failure faults the machine
            self._fault(f"Move to {target} failed: {exc}")
            return
        self.trigger(next_trigger)

    async def _run_gripper(self, close: bool, next_trigger: str) -> None:
        try:
            if close:
                await self.controller.close_gripper()
            else:
                await self.controller.open_gripper()
        except Exception as exc:  # noqa: BLE001
            self._fault(f"Gripper {'close' if close else 'open'} failed: {exc}")
            return
        self.trigger(next_trigger)

    def _fault(self, message: str) -> None:
        logger.error("FAULT: %s", message)
        self.context.error_message = message
        self.trigger(st.TO_FAULT)

    # -- guards --------------------------------------------------------------
    @guard(st.START)
    def _guard_start(self, *_args, **_kwargs) -> bool:
        allowed = self.state == st.READY
        if not allowed:
            logger.warning("start rejected: machine not ready (state=%s)", self.state)
        return allowed

    @guard(st.HOME)
    def _guard_home(self, *_args, **_kwargs) -> bool:
        allowed = self.state == st.READY
        if not allowed:
            logger.warning("home rejected: machine not ready (state=%s)", self.state)
        return allowed

    # -- logging -------------------------------------------------------------
    @on_state_change
    def _log_transition(self, old_state, new_state, trigger_name) -> None:
        logger.info("Transition %s -> %s (%s)", old_state, new_state, trigger_name)
        # Clear stale error once we recover to ready.
        if new_state == st.READY:
            self.context.error_message = ""

    # -- sequence handlers: each builds its target/action and advances when done --
    @on_enter_state(Seq.movingToCube)
    def _enter_moving_to_cube(self, _event) -> None:
        self._move(self.context.cube_start, self.context.travel_z, st.CUBE_REACHED)

    @on_enter_state(Seq.loweringToCube)
    def _enter_lowering_to_cube(self, _event) -> None:
        self._move(self.context.cube_start, self.context.cube_start[2], st.LOWERED_TO_CUBE)

    @on_enter_state(Seq.closingGripper)
    def _enter_closing_gripper(self, _event) -> None:
        self._grip(close=True, next_trigger=st.GRIPPED)

    @on_enter_state(Seq.liftingWithCube)
    def _enter_lifting_with_cube(self, _event) -> None:
        self._move(self.context.cube_start, self.context.travel_z, st.LIFTED_WITH_CUBE)

    @on_enter_state(Seq.movingToDestination)
    def _enter_moving_to_destination(self, _event) -> None:
        self._move(self.context.destination, self.context.travel_z, st.DESTINATION_REACHED)

    @on_enter_state(Seq.loweringToDestination)
    def _enter_lowering_to_destination(self, _event) -> None:
        self._move(self.context.destination, self.context.destination[2], st.LOWERED_TO_DESTINATION)

    @on_enter_state(Seq.openingGripper)
    def _enter_opening_gripper(self, _event) -> None:
        self._grip(close=False, next_trigger=st.RELEASED)

    @on_enter_state(Seq.liftingClear)
    def _enter_lifting_clear(self, _event) -> None:
        self._move(self.context.destination, self.context.travel_z, st.CYCLE_COMPLETE)

    @on_enter_state(Seq.homing)
    def _enter_homing(self, _event) -> None:
        self.controller.set_home(self.context.home)
        self._move(self.context.home, self.context.home[2], st.HOMED)
