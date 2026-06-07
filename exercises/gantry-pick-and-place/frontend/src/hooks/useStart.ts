import { rpc } from '../api/client'
import type { CommandResponse } from '../api/types'
import { useInvalidatingMutation } from './useInvalidatingMutation'

export const useStart = () =>
  useInvalidatingMutation(() => rpc<CommandResponse>('startSequence'))
