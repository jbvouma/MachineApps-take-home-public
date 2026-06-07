from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Position = list[float]


class GripperState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StatusResponse(CamelModel):
    position: Position
    moving: bool
    gripper: GripperState
    state: str
    last_state: str | None
    resumable: bool
    cube_start: Position
    destination: Position
    home: Position
    error_message: str


class CommandResponse(CamelModel):
    ok: bool
    message: str
    state: str


class ConfigPayload(CamelModel):
    cube_start: Position
    destination: Position
    home: Position | None = None
    travel_z: float | None = None
    speed: int | None = None


class ConfigResponse(CamelModel):
    cube_start: Position
    destination: Position
    home: Position
    travel_z: float
    speed: int
    ok: bool = True
    message: str = ""
