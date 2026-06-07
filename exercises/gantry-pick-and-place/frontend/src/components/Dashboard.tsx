import type { StatusResponse } from '../api/types'
import { humanizeState } from '../lib/state'

const round = (n: number) => Math.round(n)

interface DashboardProps {
  status: StatusResponse
}

const Dashboard = ({ status }: DashboardProps) => {
  const [x, y, z] = status.position.map(round)

  const stateTone =
    status.state === 'fault' ? 'fault' : status.moving ? 'busy' : 'ready'

  return (
    <section className="card dashboard">
      <h2 className="card__title">Telemetry</h2>

      <div className="dashboard__grid">
        <div className="metric">
          <span className="metric__label">Position X</span>
          <span className="metric__value">{x} mm</span>
        </div>
        <div className="metric">
          <span className="metric__label">Position Y</span>
          <span className="metric__value">{y} mm</span>
        </div>
        <div className="metric">
          <span className="metric__label">Position Z</span>
          <span className="metric__value">{z} mm</span>
        </div>

        <div className={`metric metric--${status.moving ? 'busy' : 'ready'}`}>
          <span className="metric__label">Motion</span>
          <span className="metric__value">{status.moving ? 'Moving' : 'Idle'}</span>
        </div>
        <div className={`metric metric--${status.gripper === 'closed' ? 'warn' : 'ready'}`}>
          <span className="metric__label">Gripper</span>
          <span className="metric__value">
            {status.gripper === 'closed' ? 'Closed' : 'Open'}
          </span>
        </div>
        <div className={`metric metric--${stateTone}`}>
          <span className="metric__label">State</span>
          <span className="metric__value">{humanizeState(status.state)}</span>
        </div>
      </div>
    </section>
  )
}

export default Dashboard
