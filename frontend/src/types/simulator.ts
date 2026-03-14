export type SimulatorMode = 'local' | 'api'

export type RuntimePipelineStatus =
  | 'idle'
  | 'local-ready'
  | 'connecting'
  | 'running'
  | 'fallback'
  | 'verified'
  | 'error'

export type SimulatorScreen = 'menu' | 'running'

export interface ZoneTile {
  id: string
  label: string
  layer: number
  color: string
  x: number
  y: number
  z: number
  width: number
  depth: number
}

export interface AgentState {
  id: string
  name: string
  role: string
  accent: string
  x: number
  y: number
  z: number
  headingDeg: number
  speedMph: number
  fuelGal: number
  score: number
  currentZoneId: string | null
}

export interface PromptRecord {
  id: string
  prompt: string
  mode: SimulatorMode
  status: RuntimePipelineStatus
  response: string
  timestamp: string
  executionId?: string
  datasetCommit?: string
  verificationHash?: string
  error?: string
}

export interface RuntimeIdentifiers {
  tenantId: string | null
  clientKey: string | null
  executionId: string | null
  datasetCommit: string | null
  verificationHash: string | null
}

export interface SimulatorState {
  screen: SimulatorScreen
  frame: number
  connectionMode: SimulatorMode
  pipelineStatus: RuntimePipelineStatus
  apiAvailable: boolean
  fullscreen: boolean
  selectedAgentId: string
  zones: ZoneTile[]
  agents: AgentState[]
  promptHistory: PromptRecord[]
  activePrompt: string
  runtime: RuntimeIdentifiers
  validationStatus: string
  lastError: string | null
  lastScenarioSummary: string | null
}
