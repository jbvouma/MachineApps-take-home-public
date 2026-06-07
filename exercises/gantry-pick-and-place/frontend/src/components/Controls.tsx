import { useHome } from '../hooks/useHome'
import { useStart } from '../hooks/useStart'
import type { Vec3 } from '../api/types'

interface ControlsProps {
  state: string
  moving: boolean
  home: Vec3
}

const Controls = ({ state, moving, home: homePos }: ControlsProps) => {
  const home = useHome()
  const start = useStart()

  const isReady = state === 'ready'
  const isFault = state === 'fault'
  const busy = moving || home.isPending || start.isPending

  return (
    <div className="controls">
      <div className="controls__buttons">
        <button
          type="button"
          className="btn btn--secondary"
          onClick={() => home.mutate()}
          data-tooltip={`Move to home: X=${homePos[0]}, Y=${homePos[1]}, Z=${homePos[2]}`}
          disabled={busy || isFault || !isReady}
        >
          {home.isPending ? 'Homing...' : 'Home'}
        </button>

        <button
          type="button"
          className="btn btn--primary"
          onClick={() => start.mutate()}
          disabled={!isReady || busy}
        >
          {start.isPending ? 'Starting...' : 'Start sequence'}
        </button>
      </div>
      <p className="controls__hint">
        {isReady
          ? 'Robot is ready. Start a pick-and-place cycle or send it home.'
          : isFault
            ? 'Clear the fault before issuing commands.'
            : 'Robot is busy. Controls are disabled until it returns to ready.'}
      </p>
    </div>
  )
}

export default Controls
