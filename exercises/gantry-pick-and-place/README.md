# Gantry Pick & Place

A proof-of-concept for a 3-axis gantry robot that picks a cube from Table A and places it
on Table B. A Python/FastAPI backend drives a simulated robot through a state machine, and
a React + TypeScript frontend visualizes and configures the operation live.

The robot motion is simulated (no real hardware). The workspace is a 2m x 2m top-down
footprint; coordinates are millimeters on axes `[X, Y, Z]` with Z up and the gripper
pointing down.

## Architecture

```
            HTTP (Connect RPC, polling ~250ms)
  Browser  <------------------------------------>  Backend (FastAPI / VentionApp)
  React + TS                                         |
  React Query + axios                                +-- vention-state-machine  (pick-and-place sequence)
  top-down SVG view                                  +-- vention-storage        (SQLite config persistence)
                                                     +-- robot_sim (move_to polling loop)
```

- Backend: a `VentionApp` (FastAPI) exposes RPC commands under `/rpc`. The control logic
  is a `vention-state-machine` driving the pick-and-place sequence. Each motion state
  spawns an async loop that calls `robot_sim.move_to(target, speed)` repeatedly until the
  move completes, then fires the next trigger. Config is persisted with `vention-storage`
  in a SQLite database.
- Frontend: a Vite React + TypeScript app. A thin `rpc()` axios helper posts to the
  Connect unary endpoints. React Query polls `getStatus` (~250ms) for telemetry, and
  mutations wrap the action commands. A top-down SVG renders the workspace, tables, robot,
  and cube, with a state badge and an error banner.

## Pick-and-place sequence

The state machine adds these states to the built-in `ready` and `fault`:

```
ready --start--> moving_to_cube --> lowering_to_cube --> closing_gripper
   --> lifting_with_cube --> moving_to_destination --> lowering_to_destination
   --> opening_gripper --> lifting_clear --> (cycle_complete) --> ready

homing:  any non-fault --home--> homing --> ready
fault:   any --to_fault--> fault ;  fault --reset--> ready
```

- Each `moving_*` / `lowering_*` / `lifting_*` state polls `move_to` until the target is
  reached, then advances.
- `closing_gripper` / `opening_gripper` actuate the gripper, then advance.
- Any handler exception triggers `to_fault` with an error message. `fault` is recoverable
  via `reset`.
- `home` is accepted from `ready` (and after a fault reset) but rejected mid-sequence so a
  live pick is never interrupted.

## Setup and run

### Docker (canonical path)

The backend libraries require Python 3.10, so Docker is the source of truth. A single
command builds and starts the whole stack:

```bash
docker compose up --build
# or:
make up
```

Then open:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs (OpenAPI): http://localhost:8000/docs
- State machine diagram: http://localhost:8000/sm/diagram.svg

The frontend waits for the backend healthcheck (`GET /health`) before starting. Config is
stored in a named volume (`gantry-data`), so it survives `docker compose down` and restarts.

Stop the stack with `make down`, tail logs with `make logs`.

### Native (no Docker)

The backend requires Python 3.10 (`>=3.10,<3.11`); use pyenv if your system Python differs.
`make dev` prints the exact steps. In short:

```bash
# Backend (Python 3.10)
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (second terminal)
cd frontend && npm install && npm run dev
```

## Tests

```bash
make test            # backend + frontend
make test-backend    # docker compose run --rm backend pytest -q
make test-frontend   # docker compose run --rm frontend npm test --silent
```

Backend tests use pytest (state transitions, motion polling, API actions). Frontend tests
use Vitest + React Testing Library for the main action controls.

## API surface

RPC actions (Connect surface under `/rpc/...`):

| Action | Input | Effect |
|---|---|---|
| `getStatus` | none | Full telemetry snapshot (position, moving, gripper, state, positions, error) |
| `homeRobot` | none | Trigger `home` (move to home position) |
| `startSequence` | none | Trigger `start`; rejected if not in `ready` |
| `resetFault` | none | Trigger `reset` to recover from `fault` |
| `getConfig` | none | Current persisted config |
| `setConfig` | config payload | Validate, persist, update the live context |

Other mounted routes:

- `GET /health` for container healthchecks.
- `/sm` from the state machine router: `GET /sm/state`, `GET /sm/history`,
  `GET /sm/diagram.svg`.
- `/db` from storage: CRUD plus `GET /db/health`, `GET /db/audit`.
- `/docs` for the OpenAPI explorer.

Action names are camelCase in the JSON contract; the communication library auto-aliases
Python snake_case to camelCase, so the frontend and `/docs` see `getStatus`, `homeRobot`,
and so on.

## Design decisions and trade-offs

- Why Docker: the Vention libraries (`vention-communication`, `vention-state-machine`,
  `vention-storage`) all require Python `>=3.10,<3.11`. The dev machine runs a newer
  Python, so a `python:3.10-slim` container is the canonical, reproducible runtime. Native
  runs are documented as a fallback for anyone with pyenv 3.10.
- Polling, not streaming: the frontend polls `getStatus` (~250ms) over plain HTTP, and
  after each mutation we invalidate the status query so the UI reflects commands quickly.
  This was a deliberate choice for simplicity and robustness. The `vention-communication`
  library also offers a server-push `@stream` primitive; consuming it would mean parsing
  Connect stream frames on the client plus reconnect/fallback handling. For a single-cube
  proof of concept the polling cadence is more than sufficient, so streaming is left as a
  documented extension rather than carried as code that nothing consumes.
- State-machine-driven motion polling: `robot_sim.move_to` integrates position from
  wall-clock time and must be called repeatedly until motion completes. Each motion state
  owns an async loop that calls `move_to` until the target is reached (or `axis_speed`
  zeroes out), with a safety timeout, rather than trusting the simulator's internal
  completion check. `robot_sim.py` is used unmodified.
- Persistence: configuration (cube start, destination, home, travel height, speed) is
  stored via `vention-storage` in SQLite on a named Docker volume, so it survives restarts.
- camelCase JSON contract: the frontend gets an idiomatic camelCase API while the backend
  stays snake_case. The response models set a camelCase alias generator explicitly
  (`alias_generator=to_camel`, `populate_by_name=True`) so `model_dump(by_alias=True)`
  emits camelCase. We do this in our models rather than rely on the communication
  library's own post-hoc aliasing, which does not take effect under this pydantic version.
  Action names are declared camelCase directly (`@action(name="getStatus")`).

## Bonus items covered

- Persistence: config survives a backend restart via `vention-storage` SQLite on a named
  volume.
- Tests: backend pytest suite and frontend Vitest component tests.
- Containerization: a single `docker compose up` brings up the whole stack, with the
  frontend depending on the backend's health.
- Demo: a short screen recording of home, configure, run sequence, and fault/reset.
  Demo video: TODO (link to be added).

## Assumptions

- Coordinates are in millimeters; the workspace is a 2m x 2m footprint. Because the
  robot's hard limit is `±1000` mm per axis, the origin is the workspace center (robot
  home) and axes run `-1000..1000`. Table A is the upper-left quadrant, Table B the
  lower-right.
- Default positions: home `[0, 0, 0]`, cube start `[-600, 600, 0]`,
  destination `[600, -600, 0]`, travel height `200`, speed `90` mm/s.
- A single cube is picked and placed (no multi-cube batching).
- Axis positions are validated against `±1000` limits and speed against `0..100` before
  reaching the robot.

---

## Original exercise brief

# **Robot Pick & Place Simulation**

## **Problem Statement**

You are tasked with building a proof-of-concept for a 3-axis gantry robot solution. The goal is to implement a Python backend that controls a robotic arm using a State Machine and a React frontend to visualize and configure the operation.

You must simulate a "Pick and Place" sequence: picking a cube from **Table A** and placing it on **Table B** within the provided application footprint.

![image](https://github.com/VentionCoExperiments/MachineApps-take-home-public/raw/main/exercises/gantry-pick-and-place/figure1_application_footprint.png)

## **Checklist of Requirements**

### **Mandatory Requirements**

**Backend (Python & FastAPI)**

  - [ ] **Communication Framework:** Use the [`vention-communication`](https://pypi.org/project/vention-communication/) library to establish communication between the frontend and backend.
  - [ ] **State Machine Integration:** Implement the robot's control logic using the [`vention-state-machine`](https://pypi.org/project/vention-state-machine/) library.
  - [ ] **Robot Simulation:** Interface with the provided `robot_sim.py` class.
      - *Note:* The `move_to` method must be called repeatedly until motion is complete. This should be handled inside your state machine callbacks.
  - [ ] **API Endpoints:** Create endpoints to:
      - Get/Set robot, cube, and destination positions.
      - specific commands: `Home Robot`, `Start Sequence`, `Get Status`.
      - *Note:* The "Home" operation moves the robot to its home position (default: `[0, 0, 0]`). Review `robot_sim.py` to understand the `move_home()` method and the `home_position` parameter.
  - [ ] **Logic:** Implement the full Pick-and-Place sequence:
    1.  Move to Cube (Table A) $\rightarrow$ Lower $\rightarrow$ Close Gripper.
    2.  Lift $\rightarrow$ Move to Destination (Table B).
    3.  Lower $\rightarrow$ Open Gripper $\rightarrow$ Lift.

**Frontend (React & TypeScript)**

  - [ ] **Dashboard:** Display real-time telemetry:
      - Current Robot Position (X, Y, Z).
      - Cube Start Position & Destination.
      - Robot Status (Gripper open/closed, moving/idle).
      - Current State of the State Machine.
  - [ ] **Controls:** Allow the user to:
      - Configure the Cube's start coordinates and destination coordinates.
      - Trigger the "Home" operation (moves robot to home position, default: `[0, 0, 0]`).
      - Start the "Pick and Place" sequence.
  - [ ] **Visuals:** Provide a clear visual indication of errors and operational state.

### **Bonus Points**

  - [ ] **Persistence:** Use [`vention-storage`](https://pypi.org/project/vention-storage/) to save configuration (e.g., cube locations) between restarts.
  - [ ] **Testing:** Write unit tests for the backend logic or component tests for the frontend.
  - [ ] **Containerization:** Run the whole stack (Backend + Frontend) with a single command (e.g., Docker Compose).
  - [ ] **Demo:** Include a short video recording of your solution in action.

## **Technical Resources**

**Backend Setup**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Requirements include: fastapi, vention-communication==0.3.0, vention-state-machine==0.3.1, vention-storage==0.5.4
```

**Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

## **Submission**

  - [ ] Fork the repository and complete the work in your fork.
  - [ ] Include a **README** documenting:
      - Setup and run instructions.
      - Design decisions, assumptions, and trade-offs.
  - [ ] Push your changes and share the repository link.

-----

### **Questions?**

If you have any questions about the exercise, please contact [isaac.mills@vention.cc](mailto:isaac.mills@vention.cc). Happy coding\!
