"""Workspace constants, default positions, and env-driven settings (SPEC section 3)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Hard physical limits, matching robot_sim.py (robot_limits [1000,1000,1000], speed 0..100).
AXIS_LIMIT_MM: float = 1000.0
SPEED_MIN: int = 0
SPEED_MAX: int = 100

# Workspace footprint (2m x 2m), informational for the frontend.
WORKSPACE_MM: float = 2000.0

# Wall-clock safety timeout for a single move; the controller aborts if exceeded.
MOVE_TIMEOUT_S: float = 30.0
MOVE_POLL_INTERVAL_S: float = 0.02
GRIPPER_SETTLE_S: float = 0.1


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class DefaultConfig:
    """Seed defaults for the persisted RobotConfig row.

    The robot's hard limit is +/-1000mm per axis, so the 2m x 2m workspace is modeled
    with the origin at the center (robot home) and axes spanning -1000..1000. Table A
    sits in the upper-left quadrant (-X, +Y); Table B in the lower-right (+X, -Y).
    """

    home: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    cube_start: list[float] = field(default_factory=lambda: [-600.0, 600.0, 0.0])
    destination: list[float] = field(default_factory=lambda: [600.0, -600.0, 0.0])
    travel_z: float = 200.0
    speed: int = 90


DEFAULTS = DefaultConfig()


@dataclass
class Settings:
    """Env-driven runtime settings."""

    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    # vention-storage reads VENTION_STORAGE_DATABASE_URL itself; None -> ./storage.db.
    database_url: str | None = field(
        default_factory=lambda: os.environ.get("VENTION_STORAGE_DATABASE_URL")
    )


SETTINGS = Settings()


def validate_position(position: list[float]) -> str | None:
    """Return an error string if any axis is outside +/-AXIS_LIMIT_MM, else None."""
    if len(position) != 3:
        return f"Position must have exactly 3 axes, got {len(position)}"
    for axis, value in enumerate(position):
        if value > AXIS_LIMIT_MM or value < -AXIS_LIMIT_MM:
            return f"Position {value} for axis {axis} is outside +/-{AXIS_LIMIT_MM}"
    return None


def validate_speed(speed: int) -> str | None:
    """Return an error string if speed is outside 0..100, else None."""
    if speed < SPEED_MIN or speed > SPEED_MAX:
        return f"Speed {speed} is outside [{SPEED_MIN},{SPEED_MAX}]"
    return None
