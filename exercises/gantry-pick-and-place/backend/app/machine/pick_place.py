"""PickPlaceMachine: sequences the robot through pick-and-place via spawned async moves.

Each moving/lowering/lifting state spawns ``_run_move`` on enter; it polls the
controller until the move converges, then fires the next trigger. Gripper states act
then advance. Any handler exception records an error and triggers ``to_fault``.
``home`` and ``start`` are guarded so they cannot interrupt a live sequence.

An operator can ``request_abort`` mid-cycle: the controller stops issuing motion and
the machine faults. Because the underlying library tracks the last sequence leaf, a
deliberate stop is resumable via ``resume`` (re-enters that leaf and continues), while
an error fault is not (it forces a fresh start after reset).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from state_machine.core import StateMachine
from state_machine.decorators import guard, on_enter_state, on_state_change

from app.config import DEFAULTS
from app.logging_config import get_logger
from app.machine import states as st
from app.machine.states import Seq, States
from app.robot.controller import MotionStopped, RobotController

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
        # True only after a deliberate operator stop, so resume is offered for a stop
        # but not after an error fault. Set in request_abort, cleared on reaching ready.
        self._resumable = False
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
        except MotionStopped:
            # Operator abort already drove the transition to fault; do not re-fault.
            return
        except Exception as exc:  # noqa: BLE001 - any failure faults the machine
            self._fault(f"Move to {target} failed: {exc}")
            return
        self._advance(next_trigger)

    async def _run_gripper(self, close: bool, next_trigger: str) -> None:
        try:
            if close:
                await self.controller.close_gripper()
            else:
                await self.controller.open_gripper()
        except Exception as exc:  # noqa: BLE001
            self._fault(f"Gripper {'close' if close else 'open'} failed: {exc}")
            return
        self._advance(next_trigger)

    def _advance(self, next_trigger: str) -> None:
        """Fire the next step only if still mid-sequence.

        A worker can finish after an abort/fault landed the machine in fault (or after
        recovery back in ready); firing the chain trigger from there would be an invalid
        transition. Guarding on state makes a late-completing worker a no-op.
        """
        if self.state in (st.READY, st.FAULT):
            return
        self.trigger(next_trigger)

    def _fault(self, message: str) -> None:
        logger.error("FAULT: %s", message)
        self._resumable = False  # errors are not resumable; require a fresh start
        self.context.error_message = message
        self.trigger(st.TO_FAULT)

    def request_abort(self) -> bool:
        """Operator stop: halt motion and fault. Returns False if nothing is running.

        The stopped sequence leaf is retained by the library, so ``resume`` can later
        re-enter it. The controller stops issuing motion immediately so the robot holds
        position rather than completing the current leg.
        """
        if self.state in (st.READY, st.FAULT):
            return False
        logger.info("Operator abort requested (state=%s)", self.state)
        self._resumable = True
        self.context.error_message = f"Stopped by operator (was {self.state})"
        self.controller.request_stop()
        self.trigger(st.TO_FAULT)
        return True

    @property
    def resumable(self) -> bool:
        """True when the current fault came from an operator stop and can be resumed."""
        return self.state == st.FAULT and self._resumable

    def resume(self) -> bool:
        """Resume a stopped sequence from the leaf it was halted in.

        Only valid after a deliberate stop (``_resumable``). Resets the fault to ready,
        then uses the library's recovery entry to re-enter the stopped leaf, whose
        on_enter re-issues the move and the chain continues.
        """
        if self.state != st.FAULT or not self._resumable:
            return False
        logger.info("Resuming sequence from %s", self.get_last_state())
        self.trigger(st.RESET)
        self.start()  # recovery-aware: fires recover__<last_state>
        return True

    def discard(self) -> bool:
        """Discard a stopped sequence and return the robot home.

        Clears the fault, then homes so the next run starts from a known position
        rather than wherever the robot halted. Returns False if not in a fault.
        """
        if self.state != st.FAULT:
            return False
        logger.info("Discarding sequence (was %s); homing", self.get_last_state())
        self.trigger(st.RESET)
        self.trigger(st.HOME)
        return True

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
        # Clear stale error and the resumable flag once we settle back at ready.
        if new_state == st.READY:
            self.context.error_message = ""
            self._resumable = False

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
