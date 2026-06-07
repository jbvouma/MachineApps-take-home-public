export type Vec3 = [number, number, number]

export type GripperState = 'open' | 'closed'

export interface StatusResponse {
  position: Vec3
  moving: boolean
  gripper: GripperState
  state: string
  lastState: string | null
  resumable: boolean
  cubeStart: Vec3
  destination: Vec3
  home: Vec3
  errorMessage: string
}

export interface CommandResponse {
  ok: boolean
  message: string
  state: string
}

export interface ConfigResponse {
  cubeStart: Vec3
  destination: Vec3
  home: Vec3
  travelZ: number
  speed: number
}

export interface ConfigPayload {
  cubeStart: Vec3
  destination: Vec3
  home?: Vec3
  travelZ?: number
  speed?: number
}

export interface RpcError {
  code: string
  message: string
  details: unknown[]
}
