import { useQuery } from '@tanstack/react-query'
import { rpc } from '../api/client'
import type { ConfigResponse } from '../api/types'

export const configKey = ['config'] as const

export const useConfig = () =>
  useQuery({
    queryKey: configKey,
    queryFn: () => rpc<ConfigResponse>('getConfig'),
  })
