"""Pydantic request/response models for the RPC surface.

Fields are idiomatic snake_case but serialize to camelCase on the wire via a
camelCase alias generator. populate_by_name lets handlers build models with the
snake_case names while inputs accept either casing. We set the generator here at
class-creation time because the communication layer's own post-hoc aliasing does
not take effect under this pydantic version.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Vec3 = list[float]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StatusResponse(CamelModel):
    position: Vec3
    moving: bool
    gripper: str  # "open" | "closed"
    state: str
    last_state: str | None
    resumable: bool
    cube_start: Vec3
    destination: Vec3
    home: Vec3
    error_message: str


class CommandResponse(CamelModel):
    ok: bool
    message: str
    state: str


class ConfigPayload(CamelModel):
    cube_start: Vec3
    destination: Vec3
    home: Vec3 | None = None
    travel_z: float | None = None
    speed: int | None = None


class ConfigResponse(CamelModel):
    cube_start: Vec3
    destination: Vec3
    home: Vec3
    travel_z: float
    speed: int
    ok: bool = True
    message: str = ""
