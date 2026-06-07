import { rpc } from '../api/client'
import type { ConfigPayload, ConfigResponse } from '../api/types'
import { useInvalidatingMutation } from './useInvalidatingMutation'

export const useSetConfig = () =>
  useInvalidatingMutation((payload: ConfigPayload) =>
    rpc<ConfigResponse, ConfigPayload>('setConfig', payload),
  )
