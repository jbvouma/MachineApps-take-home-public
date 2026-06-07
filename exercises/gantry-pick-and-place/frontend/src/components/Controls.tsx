import { useHome } from '../hooks/useHome'
import { useStart } from '../hooks/useStart'
import { useStop, useResume, useDiscard } from '../hooks/useStop'
import type { Position } from '../api/types'

interface ControlsProps {
  state: string
  moving: boolean
  resumable: boolean
  home: Position
}

const Controls = ({ state, moving, resumable, home: homePos }: ControlsProps) => {
  const home = useHome()
  const start = useStart()
  const stop = useStop()
  const resume = useResume()
  const discard = useDiscard()

  const isReady = state === 'ready'
  const isFault = state === 'fault'
  // Running = a sequence is in progress (neither idle nor faulted). Stopped = a fault
  // that came from a deliberate operator stop, so it can be resumed or discarded.
  const isRunning = !isReady && !isFault
  const isStopped = isFault && resumable
  const busy = moving || home.isPending || start.isPending

  return (
    <div className="controls">
      <div className="controls__buttons">
        {!isStopped && (
          <>
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

            <button
              type="button"
              className="btn btn--danger"
              onClick={() => stop.mutate()}
              disabled={!isRunning || stop.isPending}
            >
              {stop.isPending ? 'Stopping...' : 'Stop'}
            </button>
          </>
        )}

        {isStopped && (
          <>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => resume.mutate()}
              disabled={resume.isPending || discard.isPending}
            >
              {resume.isPending ? 'Resuming...' : 'Resume'}
            </button>

            <button
              type="button"
              className="btn btn--danger"
              onClick={() => discard.mutate()}
              disabled={resume.isPending || discard.isPending}
            >
              {discard.isPending ? 'Discarding...' : 'Discard'}
            </button>
          </>
        )}
      </div>
      <p className="controls__hint">
        {isReady
          ? 'Robot is ready. Start a pick-and-place cycle or send it home.'
          : isStopped
            ? 'Sequence stopped. Resume to continue from where it halted, or discard it.'
            : isFault
              ? 'Clear the fault before issuing commands.'
              : 'Sequence running. Press Stop to halt; it can be resumed afterwards.'}
      </p>
    </div>
  )
}

export default Controls
