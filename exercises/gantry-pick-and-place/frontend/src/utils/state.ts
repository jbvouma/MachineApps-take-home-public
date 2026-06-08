export type StateKind = 'ready' | 'fault' | 'busy' | 'unknown'

// "Seq_movingToCube" -> "Moving To Cube"; "ready" -> "Ready"
export const humanizeState = (state: string): string => {
  if (!state) return 'Unknown'
  const withoutGroup = state.includes('_')
    ? state.slice(state.indexOf('_') + 1)
    : state
  return withoutGroup
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export const classifyState = (state: string): StateKind => {
  if (!state) return 'unknown'
  if (state === 'ready') return 'ready'
  if (state === 'fault') return 'fault'
  return 'busy'
}
