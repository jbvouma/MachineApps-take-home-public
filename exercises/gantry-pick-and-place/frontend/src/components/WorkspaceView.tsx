import type { StatusResponse, Vec3 } from '../api/types'

// Origin at center, axes span -1000..1000 (robot hard limit), matching the backend.
const WORLD_MIN = -1000
const WORLD_SPAN = 2000
const PAD = 24
const SIZE = 420
const SCALE = (SIZE - PAD * 2) / WORLD_SPAN

// X grows right; world Y grows up while SVG y grows down, so flip Y.
const toX = (mm: number) => PAD + (mm - WORLD_MIN) * SCALE
const toY = (mm: number) => PAD + (WORLD_MIN + WORLD_SPAN - mm) * SCALE

interface WorkspaceViewProps {
  status: StatusResponse
}

const WorkspaceView = ({ status }: WorkspaceViewProps) => {
  const cube: Vec3 = status.cubeStart
  const dest: Vec3 = status.destination
  const [px, py] = status.position

  // Table A: 0.5m square centered in the upper-left quadrant (-600, 600).
  const tableASize = 500 * SCALE
  const tableAx = toX(-850)
  const tableAy = toY(850)

  // Table B: 0.5m square centered lower-right (600, -600), rotated ~45deg per the figure.
  const tableBcx = toX(600)
  const tableBcy = toY(-600)
  const tableBhalf = (500 * SCALE) / 2

  return (
    <section className="card workspace">
      <h2 className="card__title">Workspace (2m x 2m)</h2>
      <svg
        className="workspace__svg"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label="Top-down view of the robot workspace"
      >
        <rect
          x={PAD}
          y={PAD}
          width={SIZE - PAD * 2}
          height={SIZE - PAD * 2}
          className="ws-boundary"
        />

        <rect
          x={tableAx}
          y={tableAy}
          width={tableASize}
          height={tableASize}
          className="ws-table"
        />
        <text x={tableAx + tableASize / 2} y={tableAy + tableASize / 2} className="ws-label">
          Table A
        </text>

        <g transform={`rotate(45 ${tableBcx} ${tableBcy})`}>
          <rect
            x={tableBcx - tableBhalf}
            y={tableBcy - tableBhalf}
            width={tableBhalf * 2}
            height={tableBhalf * 2}
            className="ws-table"
          />
        </g>
        <text
          x={tableBcx}
          y={tableBcy}
          transform={`rotate(45 ${tableBcx} ${tableBcy})`}
          className="ws-label"
        >
          Table B
        </text>

        <circle cx={toX(0)} cy={toY(0)} r={34} className="ws-robot-zone" />
        <text x={toX(0)} y={toY(0)} className="ws-label ws-label--robot">
          Robot
        </text>

        {/* Cube start marker */}
        <rect
          x={toX(cube[0]) - 6}
          y={toY(cube[1]) - 6}
          width={12}
          height={12}
          className="ws-cube"
        />

        {/* Destination target marker */}
        <g className="ws-target">
          <circle cx={toX(dest[0])} cy={toY(dest[1])} r={9} />
          <line x1={toX(dest[0]) - 12} y1={toY(dest[1])} x2={toX(dest[0]) + 12} y2={toY(dest[1])} />
          <line x1={toX(dest[0])} y1={toY(dest[1]) - 12} x2={toX(dest[0])} y2={toY(dest[1]) + 12} />
        </g>

        {/* Live robot position */}
        <circle cx={toX(px)} cy={toY(py)} r={7} className="ws-tcp" />
      </svg>

      <ul className="workspace__legend">
        <li>
          <span className="legend-swatch legend-swatch--cube" /> Cube start
        </li>
        <li>
          <span className="legend-swatch legend-swatch--target" /> Destination
        </li>
        <li>
          <span className="legend-swatch legend-swatch--tcp" /> Live position
        </li>
      </ul>
    </section>
  )
}

export default WorkspaceView
