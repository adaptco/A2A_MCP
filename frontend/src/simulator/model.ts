import {
  AgentState,
  PromptRecord,
  RuntimePipelineStatus,
  SimulatorMode,
  SimulatorState,
  ZoneTile,
} from '../types/simulator'

const GRID_COLUMNS = 4
const GRID_ROWS_BY_LAYER = [4, 4, 3]
const ZONE_SIZE = 100
const LAYER_HEIGHT = 40
const BASE_AGENT_ALTITUDE = 18

export const FRAME_MS = 1000 / 60

interface ControlState {
  up: boolean
  down: boolean
  left: boolean
  right: boolean
}

const AGENT_LIBRARY: Array<Pick<AgentState, 'id' | 'name' | 'role' | 'accent' | 'x' | 'z'>> = [
  { id: 'manager', name: 'Manager', role: 'Routing', accent: '#5fc8ff', x: 70, z: 70 },
  { id: 'conductor', name: 'Conductor', role: 'Orchestration', accent: '#7ad9a7', x: 170, z: 70 },
  { id: 'architect', name: 'Architect', role: 'Design', accent: '#ffb66e', x: 270, z: 70 },
  { id: 'coder', name: 'Coder', role: 'Execution', accent: '#8bc0ff', x: 370, z: 70 },
  { id: 'tester', name: 'Tester', role: 'Validation', accent: '#82f0d3', x: 70, z: 170 },
  { id: 'researcher', name: 'Researcher', role: 'Context', accent: '#f3d06b', x: 170, z: 170 },
  { id: 'physicist', name: 'Physicist', role: 'Invariants', accent: '#ff8f7a', x: 270, z: 170 },
  { id: 'ralph', name: 'Ralph', role: 'Runtime', accent: '#d2b4ff', x: 370, z: 170 },
]

export function createInitialSimulatorState(
  connectionMode: SimulatorMode = 'api',
): SimulatorState {
  const zones = createZones()
  const agents = createAgents(zones)
  const initialState: SimulatorState = {
    screen: 'menu',
    frame: 0,
    connectionMode,
    pipelineStatus: connectionMode === 'local' ? 'local-ready' : 'idle',
    apiAvailable: true,
    fullscreen: false,
    selectedAgentId: agents[0].id,
    zones,
    agents,
    promptHistory: [],
    activePrompt: '',
    runtime: {
      tenantId: null,
      clientKey: null,
      executionId: null,
      datasetCommit: null,
      verificationHash: null,
    },
    validationStatus: 'Corridor standing by.',
    lastError: null,
    lastScenarioSummary: null,
  }
  initialState.activePrompt = buildDefaultPrompt(initialState)
  return initialState
}

export function cloneSimulatorState(state: SimulatorState): SimulatorState {
  return {
    ...state,
    zones: state.zones.map((zone) => ({ ...zone })),
    agents: state.agents.map((agent) => ({ ...agent })),
    promptHistory: state.promptHistory.map((record) => ({ ...record })),
    runtime: { ...state.runtime },
  }
}

export function getSelectedAgent(state: SimulatorState): AgentState {
  return (
    state.agents.find((agent) => agent.id === state.selectedAgentId) ?? state.agents[0]
  )
}

export function cycleSelectedAgent(state: SimulatorState, direction = 1): void {
  const currentIndex = state.agents.findIndex((agent) => agent.id === state.selectedAgentId)
  const nextIndex =
    currentIndex === -1
      ? 0
      : (currentIndex + direction + state.agents.length) % state.agents.length
  state.selectedAgentId = state.agents[nextIndex].id
  state.activePrompt = buildDefaultPrompt(state)
  state.validationStatus = `${getSelectedAgent(state).name} selected for corridor control.`
}

export function setConnectionMode(state: SimulatorState, mode: SimulatorMode): void {
  state.connectionMode = mode
  state.pipelineStatus = mode === 'local' ? 'local-ready' : 'idle'
  state.lastError = null
  state.validationStatus =
    mode === 'local'
      ? 'Local deterministic corridor armed.'
      : 'API corridor armed. Dispatch a prompt to negotiate runtime.'
}

export function resetSimulatorState(
  state: SimulatorState,
  mode: SimulatorMode = state.connectionMode,
): SimulatorState {
  return createInitialSimulatorState(mode)
}

export function tickSimulator(
  state: SimulatorState,
  controls: ControlState,
  deltaSeconds: number,
): void {
  state.frame += 1

  const selected = getSelectedAgent(state)
  const movement = {
    x: (controls.right ? 1 : 0) - (controls.left ? 1 : 0),
    z: (controls.down ? 1 : 0) - (controls.up ? 1 : 0),
  }
  const magnitude = Math.hypot(movement.x, movement.z)

  if (state.screen === 'running' && magnitude > 0) {
    const moveSpeed = 82
    const normalizedX = movement.x / magnitude
    const normalizedZ = movement.z / magnitude

    selected.x = clamp(selected.x + normalizedX * moveSpeed * deltaSeconds, 50, 350)
    selected.z = clamp(selected.z + normalizedZ * moveSpeed * deltaSeconds, 50, 350)
    selected.speedMph = 20 + magnitude * 26
    selected.fuelGal = clamp(selected.fuelGal - deltaSeconds * 0.12, 0, 13.2)
    selected.headingDeg = (Math.atan2(normalizedX, normalizedZ) * 180) / Math.PI
    state.validationStatus = `${selected.name} holding ${lookupZoneLabel(
      state.zones,
      selected.currentZoneId,
    )}.`
  } else {
    selected.speedMph = Math.max(0, selected.speedMph * 0.88)
  }

  for (const [index, agent] of state.agents.entries()) {
    const phase = (state.frame + index * 11) * 0.05
    agent.y =
      agent.id === selected.id && state.screen === 'running'
        ? BASE_AGENT_ALTITUDE + 3.2
        : BASE_AGENT_ALTITUDE + Math.sin(phase) * 1.8
    agent.score = clamp(0.68 + (Math.sin(phase) + 1) * 0.12, 0.5, 0.97)
    agent.currentZoneId = getZoneForPosition(state.zones, agent.x, agent.z)?.id ?? null
  }
}

export function buildDefaultPrompt(state: SimulatorState): string {
  const selected = getSelectedAgent(state)
  const zoneName = lookupZoneLabel(state.zones, selected.currentZoneId)
  return `Hold safe lane through ${zoneName} and report on drift integrity for ${selected.name}.`
}

export function buildLocalResponse(state: SimulatorState, prompt: string): string {
  const selected = getSelectedAgent(state)
  const zoneName = lookupZoneLabel(state.zones, selected.currentZoneId)
  return [
    `${selected.name} accepted the prompt in ${zoneName}.`,
    'Deterministic local corridor stayed inside the 44-zone lattice.',
    `Queued instruction: "${prompt}".`,
  ].join(' ')
}

export function pushPromptRecord(state: SimulatorState, record: PromptRecord): void {
  state.promptHistory = [record, ...state.promptHistory].slice(0, 6)
  state.lastScenarioSummary = record.response
}

export function createPromptRecord(args: {
  prompt: string
  mode: SimulatorMode
  status: RuntimePipelineStatus
  response: string
  executionId?: string
  datasetCommit?: string
  verificationHash?: string
  error?: string
}): PromptRecord {
  return {
    id: `prompt-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    prompt: args.prompt,
    mode: args.mode,
    status: args.status,
    response: args.response,
    timestamp: new Date().toISOString(),
    executionId: args.executionId,
    datasetCommit: args.datasetCommit,
    verificationHash: args.verificationHash,
    error: args.error,
  }
}

export function promptToTokenVector(prompt: string, agent: AgentState): number[] {
  const seed = `${prompt}|${agent.id}|${Math.round(agent.x)}|${Math.round(agent.z)}`
  const tokens: number[] = []
  for (let index = 0; index < 16; index += 1) {
    const charCode = seed.charCodeAt(index % seed.length)
    const nextCode = seed.charCodeAt((index * 3 + 7) % seed.length)
    const token = ((charCode + nextCode + index * 17) % 41) / 4 - 5
    tokens.push(Number(token.toFixed(4)))
  }
  return tokens
}

export function buildRenderGameText(state: SimulatorState): string {
  const selected = getSelectedAgent(state)
  return JSON.stringify({
    coordinate_system: 'x increases east, z increases south, y increases upward',
    screen: state.screen,
    connectionMode: state.connectionMode,
    pipelineStatus: state.pipelineStatus,
    fullscreen: state.fullscreen,
    selectedAgent: {
      id: selected.id,
      name: selected.name,
      role: selected.role,
      x: round(selected.x),
      y: round(selected.y),
      z: round(selected.z),
      headingDeg: round(selected.headingDeg),
      speedMph: round(selected.speedMph),
      fuelGal: round(selected.fuelGal),
      zone: lookupZoneLabel(state.zones, selected.currentZoneId),
    },
    visibleAgents: state.agents.map((agent) => ({
      id: agent.id,
      x: round(agent.x),
      y: round(agent.y),
      z: round(agent.z),
      zone: lookupZoneLabel(state.zones, agent.currentZoneId),
      score: round(agent.score),
    })),
    prompt: {
      draft: state.activePrompt,
      lastResponse: state.promptHistory[0]?.response ?? null,
    },
    runtime: state.runtime,
    validationStatus: state.validationStatus,
  })
}

function createZones(): ZoneTile[] {
  const colors = ['#4f9dff', '#ffb65c', '#ff7d9f']
  const zones: ZoneTile[] = []

  GRID_ROWS_BY_LAYER.forEach((rows, layer) => {
    for (let column = 0; column < GRID_COLUMNS; column += 1) {
      for (let row = 0; row < rows; row += 1) {
        const id = `zone-${layer}-${column}-${row}`
        zones.push({
          id,
          label: `Layer ${layer + 1} · Sector ${column + 1}.${row + 1}`,
          layer,
          color: colors[layer],
          x: column * ZONE_SIZE + ZONE_SIZE / 2,
          y: layer * LAYER_HEIGHT,
          z: row * ZONE_SIZE + ZONE_SIZE / 2,
          width: ZONE_SIZE,
          depth: ZONE_SIZE,
        })
      }
    }
  })

  return zones
}

function createAgents(zones: ZoneTile[]): AgentState[] {
  return AGENT_LIBRARY.map((agent, index) => ({
    ...agent,
    y: BASE_AGENT_ALTITUDE + (index % 2 === 0 ? 2 : -1),
    headingDeg: 0,
    speedMph: 0,
    fuelGal: 13.2 - index * 0.3,
    score: 0.76 - index * 0.02,
    currentZoneId: getZoneForPosition(zones, agent.x, agent.z)?.id ?? null,
  }))
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function round(value: number): number {
  return Number(value.toFixed(2))
}

function lookupZoneLabel(zones: ZoneTile[], zoneId: string | null): string {
  return zones.find((zone) => zone.id === zoneId)?.label ?? 'Unassigned sector'
}

export function getZoneForPosition(zones: ZoneTile[], x: number, z: number): ZoneTile | null {
  return (
    zones.find((zone) => {
      const halfWidth = zone.width / 2
      const halfDepth = zone.depth / 2
      return (
        x >= zone.x - halfWidth &&
        x < zone.x + halfWidth &&
        z >= zone.z - halfDepth &&
        z < zone.z + halfDepth
      )
    }) ?? null
  )
}
