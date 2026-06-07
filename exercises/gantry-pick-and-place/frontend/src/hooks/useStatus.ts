import { useQuery } from '@tanstack/react-query'
import { rpc } from '../api/client'
import type { StatusResponse } from '../api/types'

export const statusKey = ['status'] as const

// Poll fast while the robot is doing something, back off to 1s when idle at ready/fault.
const pollInterval = (status: StatusResponse | undefined): number => {
  if (!status) return 250
  const active = status.moving || (status.state !== 'ready' && status.state !== 'fault')
  return active ? 250 : 1000
}

export const useStatus = () =>
  useQuery({
    queryKey: statusKey,
    queryFn: () => rpc<StatusResponse>('getStatus'),
    refetchInterval: (query) => pollInterval(query.state.data),
  })
