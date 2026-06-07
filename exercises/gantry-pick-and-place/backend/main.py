"""Application entrypoint. Run with: uvicorn main:app (cwd=backend).

Wiring order (matters): logging -> VentionApp -> controller + machine + shared
context -> runtime singletons -> storage bootstrap + config seed -> /sm router ->
/health -> CORS -> import @action module (registers RPC) -> app.finalize() LAST.
"""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from communication.app import VentionApp
from state_machine.router import build_router
from storage.bootstrap import bootstrap

from app.config import SETTINGS
from app.logging_config import configure_logging, get_logger
from app.machine.pick_place import MachineContext, PickPlaceMachine
from app.robot.controller import RobotController
from app.runtime import init_runtime
from app.storage import accessors

configure_logging()
logger = get_logger("main")

# VentionApp is a FastAPI subclass; the sanitized service name is GantryPickAndPlace.
app = VentionApp(name="Gantry Pick And Place")

# Build the shared context, controller (seeded at home), and the machine.
context = MachineContext()
controller = RobotController(
    initial_position=list(context.home), home_position=list(context.home)
)
machine = PickPlaceMachine(controller=controller, context=context)

# Expose the singletons to the @action handlers before importing commands.
init_runtime(controller=controller, machine=machine, context=context)

# Persistence: wire CRUD + /db/health + /db/audit, then load/seed the config row
# and apply it to the live context.
bootstrap(app, accessors=[accessors.config_accessor], create_tables=True)
config_row = accessors.load_or_create_config()
accessors.apply_to_context(config_row, context)
controller.set_home(context.home)
logger.info(
    "Config loaded: cube=%s dest=%s home=%s travel_z=%s speed=%s",
    context.cube_start,
    context.destination,
    context.home,
    context.travel_z,
    context.speed,
)

# State-machine observability router: read-only (state/history/diagram). Control lives
# in the RPC actions, so no trigger POST routes are exposed here.
app.include_router(build_router(machine, triggers=[]), prefix="/sm")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Allow the Vite/CRA dev frontends.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importing these modules registers the @action RPC handlers (must precede finalize).
# Use `from app.api import ...` so the name `app` is not rebound to the package,
# which would shadow the VentionApp instance above.
from app.api import commands as commands  # noqa: E402,F401

# Finalize wires /rpc and mounts the RPC routes. Must be LAST.
app.finalize()
logger.info("Backend ready")
