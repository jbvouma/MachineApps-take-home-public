"""State, trigger, and transition definitions for the pick-and-place sequence.

State member names must be underscore-free: the underlying transitions library uses
"_" as its hierarchical separator, so a leaf like "moving_to_cube" would be mis-parsed
as nested scopes. Hence camelCase members, which stringify to e.g. "Seq_movingToCube".
Trigger names may contain underscores; they are events, not hierarchical states.
"""

from __future__ import annotations

from state_machine.defs import State, StateGroup, Trigger


class Seq(StateGroup):
    movingToCube: State = State()
    loweringToCube: State = State()
    closingGripper: State = State()
    liftingWithCube: State = State()
    movingToDestination: State = State()
    loweringToDestination: State = State()
    openingGripper: State = State()
    liftingClear: State = State()
    homing: State = State()


class States:
    seq = Seq()


# Built-in triggers provided by the library.
START = "start"
RESET = "reset"
TO_FAULT = "to_fault"

# Sequence-advancing triggers.
HOME = "home"
CUBE_REACHED = "cube_reached"
LOWERED_TO_CUBE = "lowered_to_cube"
GRIPPED = "gripped"
LIFTED_WITH_CUBE = "lifted_with_cube"
DESTINATION_REACHED = "destination_reached"
LOWERED_TO_DESTINATION = "lowered_to_destination"
RELEASED = "released"
CYCLE_COMPLETE = "cycle_complete"
HOMED = "homed"

READY = "ready"
FAULT = "fault"


def build_transitions() -> list[dict]:
    s = States.seq
    return [
        Trigger(START).transition(READY, s.movingToCube),
        Trigger(CUBE_REACHED).transition(s.movingToCube, s.loweringToCube),
        Trigger(LOWERED_TO_CUBE).transition(s.loweringToCube, s.closingGripper),
        Trigger(GRIPPED).transition(s.closingGripper, s.liftingWithCube),
        Trigger(LIFTED_WITH_CUBE).transition(s.liftingWithCube, s.movingToDestination),
        Trigger(DESTINATION_REACHED).transition(s.movingToDestination, s.loweringToDestination),
        Trigger(LOWERED_TO_DESTINATION).transition(s.loweringToDestination, s.openingGripper),
        Trigger(RELEASED).transition(s.openingGripper, s.liftingClear),
        Trigger(CYCLE_COMPLETE).transition(s.liftingClear, READY),
        Trigger(HOME).transition(READY, s.homing),
        Trigger(HOMED).transition(s.homing, READY),
    ]


TRANSITIONS = build_transitions()
