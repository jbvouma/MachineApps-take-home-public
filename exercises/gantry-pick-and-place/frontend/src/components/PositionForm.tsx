import { useState } from 'react'
import { useSetConfig } from '../hooks/useSetConfig'
import type { Position } from '../api/types'

const AXIS_MIN = -1000
const AXIS_MAX = 1000
const AXES = ['x', 'y', 'z'] as const
type Axis = (typeof AXES)[number]
type VecForm = Record<Axis, string>

interface PositionFormProps {
  cubeStart: Position
  destination: Position
  disabled?: boolean
}

const toForm = (v: Position): VecForm => ({
  x: String(v[0]),
  y: String(v[1]),
  z: String(v[2]),
})

const validateAxis = (raw: string): string | null => {
  if (raw.trim() === '') return 'Required'
  const n = Number(raw)
  if (!Number.isFinite(n)) return 'Must be a number'
  if (n < AXIS_MIN || n > AXIS_MAX) return `Must be ${AXIS_MIN}..${AXIS_MAX}`
  return null
}

const toPosition = (f: VecForm): Position => [Number(f.x), Number(f.y), Number(f.z)]

const VecFields = ({
  legend,
  values,
  errors,
  onChange,
  disabled,
}: {
  legend: string
  values: VecForm
  errors: Partial<VecForm>
  onChange: (axis: Axis, value: string) => void
  disabled?: boolean
}) => (
  <fieldset className="vec-fields" disabled={disabled}>
    <legend>{legend}</legend>
    {AXES.map((axis) => (
      <label key={axis} className="vec-fields__field">
        <span className="vec-fields__axis">{axis.toUpperCase()}</span>
        <input
          type="number"
          inputMode="numeric"
          value={values[axis]}
          aria-label={`${legend} ${axis.toUpperCase()}`}
          aria-invalid={Boolean(errors[axis])}
          onChange={(e) => onChange(axis, e.target.value)}
        />
        {errors[axis] && (
          <span className="vec-fields__error" role="alert">
            {errors[axis]}
          </span>
        )}
      </label>
    ))}
  </fieldset>
)

const PositionForm = ({ cubeStart, destination, disabled }: PositionFormProps) => {
  const setConfig = useSetConfig()
  const [cube, setCube] = useState<VecForm>(toForm(cubeStart))
  const [dest, setDest] = useState<VecForm>(toForm(destination))
  const [touched, setTouched] = useState(false)

  // Resync from server values until the user starts editing. Adjusting state
  // during render (rather than in an effect) avoids a cascading re-render.
  const serverKey = `${cubeStart.join()}|${destination.join()}`
  const [syncedKey, setSyncedKey] = useState(serverKey)
  if (!touched && serverKey !== syncedKey) {
    setCube(toForm(cubeStart))
    setDest(toForm(destination))
    setSyncedKey(serverKey)
  }

  const errorsFor = (f: VecForm): Partial<VecForm> => {
    const out: Partial<VecForm> = {}
    for (const axis of AXES) {
      const err = validateAxis(f[axis])
      if (err) out[axis] = err
    }
    return out
  }

  const cubeErrors = errorsFor(cube)
  const destErrors = errorsFor(dest)
  const hasErrors =
    Object.keys(cubeErrors).length > 0 || Object.keys(destErrors).length > 0

  const update =
    (setter: typeof setCube) => (axis: Axis, value: string) => {
      setTouched(true)
      setter((prev) => ({ ...prev, [axis]: value }))
    }

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (hasErrors) return
    setConfig.mutate(
      { cubeStart: toPosition(cube), destination: toPosition(dest) },
      { onSuccess: () => setTouched(false) },
    )
  }

  return (
    <div className="position-form">
      <h3 className="operations__subtitle">Positions</h3>
      <form onSubmit={onSubmit} noValidate>
        <VecFields
          legend="Cube start"
          values={cube}
          errors={cubeErrors}
          onChange={update(setCube)}
          disabled={disabled}
        />
        <VecFields
          legend="Destination"
          values={dest}
          errors={destErrors}
          onChange={update(setDest)}
          disabled={disabled}
        />

        <div className="position-form__actions">
          <button
            type="submit"
            className="btn btn--primary"
            disabled={disabled || hasErrors || setConfig.isPending}
          >
            {setConfig.isPending ? 'Saving...' : 'Save positions'}
          </button>
          {setConfig.isError && (
            <span className="position-form__status position-form__status--error" role="alert">
              {(setConfig.error as Error).message}
            </span>
          )}
          {setConfig.isSuccess && !touched && (
            <span className="position-form__status">Saved</span>
          )}
        </div>
      </form>
    </div>
  )
}

export default PositionForm
