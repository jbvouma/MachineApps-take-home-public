import axios from 'axios'
import type { RpcError } from './types'

export const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const SERVICE = 'vention.app.v1.GantryPickAndPlaceService'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// The backend returns HTTP 200 even on handler errors, with an {error} envelope.
// Detect it and throw so React Query treats the call as a failure.
export const rpc = async <TRes, TReq = Record<string, never>>(
  action: string,
  body?: TReq,
): Promise<TRes> => {
  const { data } = await api.post(`/rpc/${SERVICE}/${action}`, body ?? {})

  if (data && typeof data === 'object' && 'error' in data) {
    const err = (data as { error: RpcError }).error
    throw new Error(err?.message || `RPC ${action} failed`)
  }

  return data as TRes
}
