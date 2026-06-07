import { rpc } from '../api/client'
import type { CommandResponse } from '../api/types'
import { useInvalidatingMutation } from './useInvalidatingMutation'

export const useStop = () =>
  useInvalidatingMutation(() => rpc<CommandResponse>('stopSequence'))

export const useResume = () =>
  useInvalidatingMutation(() => rpc<CommandResponse>('resumeSequence'))

export const useDiscard = () =>
  useInvalidatingMutation(() => rpc<CommandResponse>('discardSequence'))
