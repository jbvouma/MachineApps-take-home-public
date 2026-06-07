"""Config accessor: load-or-seed the single RobotConfig row and persist updates."""

from __future__ import annotations

from storage.accessor import ModelAccessor

from app.config import DEFAULTS
from app.logging_config import get_logger
from app.machine.pick_place import MachineContext
from app.storage.models import CONFIG_ID, RobotConfig

logger = get_logger(__name__)

config_accessor = ModelAccessor(RobotConfig, component_name="config")


def load_or_create_config() -> RobotConfig:
    """Return the config row at id=1, seeding SPEC defaults on first boot."""
    existing = config_accessor.get(CONFIG_ID)
    if existing is not None:
        return existing

    seeded = RobotConfig(
        id=CONFIG_ID,
        cube_x=DEFAULTS.cube_start[0],
        cube_y=DEFAULTS.cube_start[1],
        cube_z=DEFAULTS.cube_start[2],
        dest_x=DEFAULTS.destination[0],
        dest_y=DEFAULTS.destination[1],
        dest_z=DEFAULTS.destination[2],
        home_x=DEFAULTS.home[0],
        home_y=DEFAULTS.home[1],
        home_z=DEFAULTS.home[2],
        travel_z=DEFAULTS.travel_z,
        speed=DEFAULTS.speed,
    )
    config_accessor.save(seeded, actor="system:bootstrap")
    logger.info("Seeded default RobotConfig (id=%s)", CONFIG_ID)
    return seeded


def apply_to_context(config: RobotConfig, context: MachineContext) -> None:
    """Copy persisted config into the live machine context."""
    context.cube_start = config.cube_start
    context.destination = config.destination
    context.home = config.home
    context.travel_z = config.travel_z
    context.speed = config.speed


def save_config(
    *,
    cube_start: list[float],
    destination: list[float],
    home: list[float],
    travel_z: float,
    speed: int,
    actor: str = "api:set_config",
) -> RobotConfig:
    """Persist a full config update to the id=1 row."""
    row = config_accessor.get(CONFIG_ID) or RobotConfig(id=CONFIG_ID)
    row.cube_x, row.cube_y, row.cube_z = cube_start
    row.dest_x, row.dest_y, row.dest_z = destination
    row.home_x, row.home_y, row.home_z = home
    row.travel_z = travel_z
    row.speed = speed
    config_accessor.save(row, actor=actor)
    logger.info("Persisted RobotConfig update by %s", actor)
    return row
