import { useMutation, useQueryClient } from '@tanstack/react-query'
import { statusKey } from './useStatus'
import { configKey } from './useConfig'

// Shared base: any command mutation refreshes status + config on success.
// Keys are imported from the query hooks that own them, so no central key file.
export const useInvalidatingMutation = <TRes, TVars = void>(
  fn: (vars: TVars) => Promise<TRes>,
) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: statusKey })
      qc.invalidateQueries({ queryKey: configKey })
    },
  })
}
