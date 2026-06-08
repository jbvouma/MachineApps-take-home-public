import { classifyState, humanizeState } from '../utils/state'

interface StateBadgeProps {
  state: string
  moving?: boolean
}

const StateBadge = ({ state, moving }: StateBadgeProps) => {
  const kind = classifyState(state)
  const animated = kind === 'busy' || moving

  return (
    <span
      className={`state-badge state-badge--${kind}${animated ? ' state-badge--pulse' : ''}`}
      role="status"
      aria-label={`State: ${humanizeState(state)}`}
    >
      <span className="state-badge__dot" aria-hidden="true" />
      {humanizeState(state)}
    </span>
  )
}

export default StateBadge
