"""SQLModel table for the persisted robot configuration (single row, id=1)."""

from __future__ import annotations

from sqlmodel import Field, SQLModel

from app.config import DEFAULTS

CONFIG_ID = 1


class RobotConfig(SQLModel, table=True):
    """Persisted configuration. Positions are stored as flat float columns."""

    id: int | None = Field(default=None, primary_key=True)

    cube_x: float = Field(default=DEFAULTS.cube_start[0])
    cube_y: float = Field(default=DEFAULTS.cube_start[1])
    cube_z: float = Field(default=DEFAULTS.cube_start[2])

    dest_x: float = Field(default=DEFAULTS.destination[0])
    dest_y: float = Field(default=DEFAULTS.destination[1])
    dest_z: float = Field(default=DEFAULTS.destination[2])

    home_x: float = Field(default=DEFAULTS.home[0])
    home_y: float = Field(default=DEFAULTS.home[1])
    home_z: float = Field(default=DEFAULTS.home[2])

    travel_z: float = Field(default=DEFAULTS.travel_z)
    speed: int = Field(default=DEFAULTS.speed)

    # Convenience converters between flat columns and [x, y, z] lists.
    @property
    def cube_start(self) -> list[float]:
        return [self.cube_x, self.cube_y, self.cube_z]

    @property
    def destination(self) -> list[float]:
        return [self.dest_x, self.dest_y, self.dest_z]

    @property
    def home(self) -> list[float]:
        return [self.home_x, self.home_y, self.home_z]
