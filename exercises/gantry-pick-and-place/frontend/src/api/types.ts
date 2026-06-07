export type Position = [number, number, number]

export type GripperState = 'open' | 'closed'

export interface StatusResponse {
  position: Position
  moving: boolean
  gripper: GripperState
  state: string
  lastState: string | null
  resumable: boolean
  cubeStart: Position
  destination: Position
  home: Position
  errorMessage: string
}

export interface CommandResponse {
  ok: boolean
  message: string
  state: string
}

export interface ConfigResponse {
  cubeStart: Position
  destination: Position
  home: Position
  travelZ: number
  speed: number
}

export interface ConfigPayload {
  cubeStart: Position
  destination: Position
  home?: Position
  travelZ?: number
  speed?: number
}

export interface RpcError {
  code: string
  message: string
  details: unknown[]
}
