import { FormEvent, startTransition, useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import {
  buildDefaultPrompt,
  buildLocalResponse,
  buildRenderGameText,
  cloneSimulatorState,
  createInitialSimulatorState,
  createPromptRecord,
  cycleSelectedAgent,
  FRAME_MS,
  getSelectedAgent,
  pushPromptRecord,
  promptToTokenVector,
  resetSimulatorState,
  setConnectionMode,
  tickSimulator,
} from '../simulator/model'
import {
  createRuntimeLoraDataset,
  createRuntimeRagContext,
  createRuntimeScenario,
  registerRuntimeClient,
  setRuntimeBaseline,
  verifyRuntimeExecution,
} from '../services/runtimeApi'
import { SimulatorMode, SimulatorState } from '../types/simulator'

type SceneRuntime = {
  renderer: THREE.WebGLRenderer
  scene: THREE.Scene
  camera: THREE.OrthographicCamera
  agentMeshes: Map<string, THREE.Mesh>
  selectionRing: THREE.Mesh
  resize: () => void
  dispose: () => void
}

type ControlsState = {
  up: boolean
  down: boolean
  left: boolean
  right: boolean
}

const FIXED_DELTA_SECONDS = FRAME_MS / 1000
const CAMERA_HALF_HEIGHT = 250
const CAMERA_POSITION = new THREE.Vector3(200, 310, 430)
const CAMERA_LOOK_AT = new THREE.Vector3(200, 30, 140)

function createSceneRuntime(
  canvas: HTMLCanvasElement,
  state: SimulatorState,
): SceneRuntime {
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#89c6ff')
  scene.fog = new THREE.Fog('#89c6ff', 360, 820)

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 2000)
  camera.position.copy(CAMERA_POSITION)
  camera.lookAt(CAMERA_LOOK_AT)

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.shadowMap.enabled = true

  const ambient = new THREE.AmbientLight('#ffffff', 1.15)
  scene.add(ambient)

  const keyLight = new THREE.DirectionalLight('#fff6d8', 1.25)
  keyLight.position.set(180, 320, 160)
  keyLight.castShadow = true
  scene.add(keyLight)

  const backLight = new THREE.DirectionalLight('#7ad9ff', 0.6)
  backLight.position.set(-120, 160, 240)
  scene.add(backLight)

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(330, 48),
    new THREE.MeshStandardMaterial({
      color: '#0f2740',
      transparent: true,
      opacity: 0.88,
      roughness: 0.85,
      metalness: 0.1,
    }),
  )
  floor.rotation.x = -Math.PI / 2
  floor.position.set(200, -6, 145)
  scene.add(floor)

  for (const zone of state.zones) {
    const tile = new THREE.Mesh(
      new THREE.BoxGeometry(zone.width * 0.92, 10, zone.depth * 0.92),
      new THREE.MeshStandardMaterial({
        color: zone.color,
        roughness: 0.55,
        metalness: 0.18,
      }),
    )
    tile.position.set(zone.x, zone.y, zone.z)
    tile.castShadow = true
    tile.receiveShadow = true
    scene.add(tile)
  }

  const strutMaterial = new THREE.MeshStandardMaterial({
    color: '#20354a',
    roughness: 0.82,
    metalness: 0.22,
  })
  for (const offset of [0, 400]) {
    const strut = new THREE.Mesh(new THREE.BoxGeometry(14, 140, 14), strutMaterial)
    strut.position.set(offset, 58, 145)
    scene.add(strut)
  }

  const agentMeshes = new Map<string, THREE.Mesh>()
  for (const agent of state.agents) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(14, 24, 24),
      new THREE.MeshStandardMaterial({
        color: agent.accent,
        roughness: 0.35,
        metalness: 0.22,
        emissive: new THREE.Color(agent.accent).multiplyScalar(0.06),
      }),
    )
    mesh.castShadow = true
    mesh.position.set(agent.x, agent.y, agent.z)
    scene.add(mesh)
    agentMeshes.set(agent.id, mesh)
  }

  const selectionRing = new THREE.Mesh(
    new THREE.TorusGeometry(20, 1.8, 10, 48),
    new THREE.MeshStandardMaterial({
      color: '#ffffff',
      emissive: new THREE.Color('#baf7ff'),
      emissiveIntensity: 0.6,
      roughness: 0.3,
      metalness: 0.4,
    }),
  )
  selectionRing.rotation.x = Math.PI / 2
  scene.add(selectionRing)

  const resize = () => {
    const width = canvas.clientWidth || canvas.parentElement?.clientWidth || window.innerWidth
    const height =
      canvas.clientHeight || canvas.parentElement?.clientHeight || window.innerHeight
    const aspect = width / Math.max(height, 1)
    camera.left = -CAMERA_HALF_HEIGHT * aspect
    camera.right = CAMERA_HALF_HEIGHT * aspect
    camera.top = CAMERA_HALF_HEIGHT
    camera.bottom = -CAMERA_HALF_HEIGHT
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
  }

  resize()
  renderer.render(scene, camera)

  return {
    renderer,
    scene,
    camera,
    agentMeshes,
    selectionRing,
    resize,
    dispose: () => {
      renderer.dispose()
      scene.traverse((node: THREE.Object3D) => {
        if (!(node instanceof THREE.Mesh)) {
          return
        }
        node.geometry.dispose()
        if (Array.isArray(node.material)) {
          node.material.forEach((material: THREE.Material) => material.dispose())
        } else {
          node.material.dispose()
        }
      })
    },
  }
}

function syncScene(runtime: SceneRuntime, state: SimulatorState): void {
  const selected = getSelectedAgent(state)

  for (const agent of state.agents) {
    const mesh = runtime.agentMeshes.get(agent.id)
    if (!mesh) {
      continue
    }
    mesh.position.set(agent.x, agent.y, agent.z)
    mesh.scale.setScalar(agent.id === selected.id ? 1.18 : 1)

    const material = mesh.material as THREE.MeshStandardMaterial
    material.color.set(agent.accent)
    material.emissive
      .set(agent.accent)
      .multiplyScalar(agent.id === selected.id ? 0.18 : 0.06 + agent.score * 0.05)
  }

  runtime.selectionRing.position.set(selected.x, selected.y - 12, selected.z)
  runtime.selectionRing.visible = state.screen === 'running'

  runtime.camera.position.lerp(
    new THREE.Vector3(selected.x, CAMERA_POSITION.y, selected.z + 255),
    0.08,
  )
  runtime.camera.lookAt(new THREE.Vector3(selected.x, 20, selected.z - 20))
  runtime.renderer.render(runtime.scene, runtime.camera)
}

function summarizeApiPrompt(
  state: SimulatorState,
  prompt: string,
  ragChunkCount: number,
  loraCandidateCount: number,
): string {
  const selected = getSelectedAgent(state)
  return [
    `${selected.name} negotiated the live corridor for "${prompt}".`,
    `Retrieved ${ragChunkCount} RAG chunks and exported ${loraCandidateCount} LoRA candidates.`,
    `Verification head: ${state.runtime.verificationHash ?? 'pending'}.`,
  ].join(' ')
}

export default function SimulatorPage() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const promptInputRef = useRef<HTMLInputElement | null>(null)
  const sceneRef = useRef<SceneRuntime | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const controlsRef = useRef<ControlsState>({
    up: false,
    down: false,
    left: false,
    right: false,
  })
  const stateRef = useRef<SimulatorState>(createInitialSimulatorState())
  const [uiState, setUiState] = useState<SimulatorState>(() =>
    cloneSimulatorState(stateRef.current),
  )

  const publishState = () => {
    const snapshot = cloneSimulatorState(stateRef.current)
    startTransition(() => {
      setUiState(snapshot)
    })
  }

  const renderFrame = () => {
    const runtime = sceneRef.current
    if (!runtime) {
      return
    }

    tickSimulator(stateRef.current, controlsRef.current, FIXED_DELTA_SECONDS)
    syncScene(runtime, stateRef.current)
    publishState()
  }

  const startCorridor = () => {
    stateRef.current.screen = 'running'
    if (stateRef.current.connectionMode === 'local') {
      stateRef.current.pipelineStatus = 'local-ready'
    }
    stateRef.current.validationStatus =
      'Corridor active. Use arrow keys to move, Enter to dispatch, Space to cycle.'
    publishState()
    promptInputRef.current?.focus()
  }

  const applyReset = () => {
    stateRef.current = resetSimulatorState(stateRef.current)
    publishState()
    if (sceneRef.current) {
      syncScene(sceneRef.current, stateRef.current)
    }
  }

  const handleToggleMode = () => {
    const nextMode: SimulatorMode =
      stateRef.current.connectionMode === 'api' ? 'local' : 'api'
    setConnectionMode(stateRef.current, nextMode)
    stateRef.current.apiAvailable = nextMode === 'api'
    publishState()
  }

  const handleCycleAgent = () => {
    cycleSelectedAgent(stateRef.current)
    publishState()
    if (sceneRef.current) {
      syncScene(sceneRef.current, stateRef.current)
    }
  }

  const handleToggleFullscreen = async () => {
    const container = containerRef.current
    if (!container) {
      return
    }

    if (document.fullscreenElement) {
      await document.exitFullscreen()
      return
    }

    await container.requestFullscreen()
  }

  const executePrompt = async (promptOverride?: string) => {
    const prompt = (promptOverride ?? stateRef.current.activePrompt).trim()
    if (!prompt) {
      stateRef.current.activePrompt = buildDefaultPrompt(stateRef.current)
      publishState()
      return
    }

    const selected = getSelectedAgent(stateRef.current)
    const tokens = promptToTokenVector(prompt, selected)
    stateRef.current.lastError = null

    if (stateRef.current.connectionMode === 'local') {
      stateRef.current.pipelineStatus = 'running'
      publishState()

      const response = buildLocalResponse(stateRef.current, prompt)
      pushPromptRecord(
        stateRef.current,
        createPromptRecord({
          prompt,
          mode: 'local',
          status: 'local-ready',
          response,
        }),
      )
      stateRef.current.pipelineStatus = 'local-ready'
      stateRef.current.validationStatus = 'Local deterministic corridor confirmed.'
      stateRef.current.activePrompt = buildDefaultPrompt(stateRef.current)
      publishState()
      return
    }

    try {
      stateRef.current.pipelineStatus = 'connecting'
      publishState()

      if (!stateRef.current.runtime.clientKey || !stateRef.current.runtime.tenantId) {
        const registration = await registerRuntimeClient()
        stateRef.current.runtime.clientKey = registration.client_key
        stateRef.current.runtime.tenantId = registration.tenant_id
      }

      await setRuntimeBaseline(stateRef.current.runtime.clientKey!, tokens)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'API setup failed.'
      stateRef.current.apiAvailable = false
      stateRef.current.connectionMode = 'local'
      stateRef.current.pipelineStatus = 'fallback'
      stateRef.current.validationStatus = 'API setup failed; falling back to local corridor.'
      stateRef.current.lastError = message
      const response = buildLocalResponse(stateRef.current, prompt)
      pushPromptRecord(
        stateRef.current,
        createPromptRecord({
          prompt,
          mode: 'local',
          status: 'fallback',
          response,
          error: message,
        }),
      )
      stateRef.current.activePrompt = buildDefaultPrompt(stateRef.current)
      publishState()
      return
    }

    try {
      stateRef.current.pipelineStatus = 'running'
      publishState()

      const runtimeHints = {
        preset: 'simulation',
        agent_name: selected.name,
        action: prompt,
        speed_mph: Number(selected.speedMph.toFixed(2)),
        heading_deg: Number(selected.headingDeg.toFixed(2)),
        fuel_gal: Number(selected.fuelGal.toFixed(2)),
      }

      const scenario = await createRuntimeScenario(stateRef.current.runtime.clientKey!, {
        tokens,
        runtime_hints: runtimeHints,
      })
      stateRef.current.runtime.executionId = scenario.execution_id
      stateRef.current.runtime.tenantId = scenario.tenant_id

      const rag = await createRuntimeRagContext(scenario.execution_id, 3)
      const lora = await createRuntimeLoraDataset(scenario.execution_id, tokens)
      const verification = await verifyRuntimeExecution(scenario.execution_id)

      stateRef.current.runtime.datasetCommit = lora.dataset_commit
      stateRef.current.runtime.verificationHash = verification.hash_head
      stateRef.current.pipelineStatus = verification.valid ? 'verified' : 'error'
      stateRef.current.validationStatus = verification.valid
        ? 'Live corridor verified through settlement lineage.'
        : 'Live corridor returned an invalid verification.'

      const response = summarizeApiPrompt(
        stateRef.current,
        prompt,
        rag.retrieval_context.chunks.length,
        lora.lora_dataset.length,
      )
      pushPromptRecord(
        stateRef.current,
        createPromptRecord({
          prompt,
          mode: 'api',
          status: verification.valid ? 'verified' : 'error',
          response,
          executionId: scenario.execution_id,
          datasetCommit: lora.dataset_commit,
          verificationHash: verification.hash_head,
        }),
      )
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Runtime pipeline failed.'
      stateRef.current.pipelineStatus = 'error'
      stateRef.current.validationStatus = 'Live corridor faulted after setup.'
      stateRef.current.lastError = message
      pushPromptRecord(
        stateRef.current,
        createPromptRecord({
          prompt,
          mode: 'api',
          status: 'error',
          response: `Runtime pipeline failed for "${prompt}".`,
          executionId: stateRef.current.runtime.executionId ?? undefined,
          error: message,
        }),
      )
    } finally {
      stateRef.current.activePrompt = buildDefaultPrompt(stateRef.current)
      publishState()
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) {
      return
    }

    const runtime = createSceneRuntime(canvas, stateRef.current)
    sceneRef.current = runtime
    syncScene(runtime, stateRef.current)
    publishState()

    const loop = () => {
      renderFrame()
      animationFrameRef.current = window.requestAnimationFrame(loop)
    }

    animationFrameRef.current = window.requestAnimationFrame(loop)

    const onResize = () => {
      runtime.resize()
      syncScene(runtime, stateRef.current)
    }

    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('resize', onResize)
      if (animationFrameRef.current !== null) {
        window.cancelAnimationFrame(animationFrameRef.current)
      }
      runtime.dispose()
      sceneRef.current = null
    }
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) {
        return
      }

      const inputFocused = document.activeElement === promptInputRef.current

      switch (event.key) {
        case 'ArrowUp':
          controlsRef.current.up = true
          break
        case 'ArrowDown':
          controlsRef.current.down = true
          break
        case 'ArrowLeft':
          controlsRef.current.left = true
          break
        case 'ArrowRight':
          controlsRef.current.right = true
          break
        case 'Enter':
          event.preventDefault()
          if (stateRef.current.screen === 'menu') {
            startCorridor()
          } else if (!inputFocused) {
            void executePrompt()
          }
          break
        case ' ':
          if (!inputFocused) {
            event.preventDefault()
            handleCycleAgent()
          }
          break
        case 'a':
        case 'A':
          if (!inputFocused) {
            event.preventDefault()
            handleToggleMode()
          }
          break
        case 'b':
        case 'B':
        case 'r':
        case 'R':
          if (!inputFocused) {
            event.preventDefault()
            applyReset()
          }
          break
        case 'f':
        case 'F':
          if (!inputFocused) {
            event.preventDefault()
            void handleToggleFullscreen()
          }
          break
        case 'Escape':
          if (document.fullscreenElement) {
            void document.exitFullscreen()
          }
          break
      }
    }

    const onKeyUp = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowUp':
          controlsRef.current.up = false
          break
        case 'ArrowDown':
          controlsRef.current.down = false
          break
        case 'ArrowLeft':
          controlsRef.current.left = false
          break
        case 'ArrowRight':
          controlsRef.current.right = false
          break
      }
    }

    const onFullscreenChange = () => {
      stateRef.current.fullscreen = Boolean(document.fullscreenElement)
      publishState()
      if (sceneRef.current) {
        sceneRef.current.resize()
        syncScene(sceneRef.current, stateRef.current)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    document.addEventListener('fullscreenchange', onFullscreenChange)

    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      document.removeEventListener('fullscreenchange', onFullscreenChange)
    }
  }, [])

  useEffect(() => {
    window.render_game_to_text = () => buildRenderGameText(stateRef.current)
    window.advanceTime = (ms: number) => {
      const steps = Math.max(1, Math.round(ms / FRAME_MS))
      for (let step = 0; step < steps; step += 1) {
        renderFrame()
      }
    }

    return () => {
      delete window.render_game_to_text
      delete window.advanceTime
    }
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await executePrompt()
  }

  return (
    <section className="simulator-shell">
      <header className="simulator-header">
        <div>
          <p className="eyebrow">A2A Simulator Corridor</p>
          <h1>Hybrid runtime loop with deterministic lattice stepping.</h1>
        </div>
        <div className="simulator-actions">
          <button
            className={`mode-pill ${uiState.connectionMode === 'api' ? 'active' : ''}`}
            type="button"
            onClick={handleToggleMode}
          >
            {uiState.connectionMode === 'api' ? 'API armed' : 'Local armed'}
          </button>
          <button className="ghost-button" type="button" onClick={handleCycleAgent}>
            Cycle agent
          </button>
          <button
            className="ghost-button"
            id="fullscreen-btn"
            type="button"
            onClick={() => void handleToggleFullscreen()}
          >
            {uiState.fullscreen ? 'Windowed' : 'Fullscreen'}
          </button>
          <button className="ghost-button" type="button" onClick={applyReset}>
            Reset corridor
          </button>
        </div>
      </header>

      <div className="simulator-layout">
        <div className="simulator-stage-card">
          <div className="simulator-stage" ref={containerRef}>
            <canvas
              ref={canvasRef}
              className="simulator-canvas"
              aria-label="A2A simulator canvas"
            />

            {uiState.screen === 'menu' ? (
              <div className="start-overlay">
                <div className="start-card">
                  <p className="eyebrow">44-zone corridor ready</p>
                  <h2>Launch the simulator route.</h2>
                  <p>
                    Arrow keys move the active agent. Enter dispatches the prompt.
                    Space cycles agents. A toggles API and local mode. B resets.
                  </p>
                  <button
                    className="primary-button"
                    id="start-btn"
                    type="button"
                    onClick={startCorridor}
                  >
                    Enter corridor
                  </button>
                </div>
              </div>
            ) : null}

            <div className="simulator-overlay">
              <div className="status-card">
                <div className="hud-row">
                  <span>Frame</span>
                  <strong>{uiState.frame}</strong>
                </div>
                <div className="hud-row">
                  <span>Zones</span>
                  <strong>{uiState.zones.length}</strong>
                </div>
                <div className="hud-row">
                  <span>Pipeline</span>
                  <strong>{uiState.pipelineStatus}</strong>
                </div>
                <div className="hud-row">
                  <span>Mode</span>
                  <strong>{uiState.connectionMode}</strong>
                </div>
              </div>

              <div className="telemetry-card">
                <p className="mini-label">Selected agent</p>
                <h3>{getSelectedAgent(uiState).name}</h3>
                <p>{getSelectedAgent(uiState).role}</p>
                <p>{uiState.validationStatus}</p>
              </div>
            </div>

            <div className="simulator-console">
              <form className="prompt-bar" onSubmit={handleSubmit}>
                <input
                  id="prompt-input"
                  ref={promptInputRef}
                  value={uiState.activePrompt}
                  onChange={(event) => {
                    stateRef.current.activePrompt = event.target.value
                    publishState()
                  }}
                  placeholder="Dispatch a simulator prompt"
                />
                <button className="primary-button" id="dispatch-btn" type="submit">
                  Dispatch
                </button>
              </form>
            </div>
          </div>
        </div>

        <aside className="simulator-sidebar">
          <section className="panel simulator-panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Runtime</p>
                <h2>Connection state</h2>
              </div>
            </div>
            <div className="simulator-runtime-grid">
              <div className="summary-card">
                <span className="summary-label">Client key</span>
                <span className="summary-value simulator-summary">
                  {uiState.runtime.clientKey ?? 'pending'}
                </span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Execution</span>
                <span className="summary-value simulator-summary">
                  {uiState.runtime.executionId ?? 'none'}
                </span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Dataset</span>
                <span className="summary-value simulator-summary">
                  {uiState.runtime.datasetCommit ?? 'none'}
                </span>
              </div>
            </div>
            {uiState.lastError ? (
              <div className="status-banner error simulator-banner">{uiState.lastError}</div>
            ) : null}
          </section>

          <section className="panel simulator-panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Agents</p>
                <h2>Corridor cast</h2>
              </div>
            </div>
            <div className="avatar-grid">
              {uiState.agents.map((agent) => (
                <article
                  className={`avatar-card ${agent.id === uiState.selectedAgentId ? 'is-selected' : ''}`}
                  key={agent.id}
                >
                  <p className="avatar-style">{agent.role}</p>
                  <h4>{agent.name}</h4>
                  <p>Zone: {agent.currentZoneId ?? 'unassigned'}</p>
                  <p>Fuel: {agent.fuelGal.toFixed(1)} gal</p>
                  <p>Score: {(agent.score * 100).toFixed(0)}%</p>
                </article>
              ))}
            </div>
          </section>

          <section className="panel simulator-panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Prompt ledger</p>
                <h2>Recent dispatches</h2>
              </div>
            </div>
            {uiState.promptHistory.length === 0 ? (
              <div className="empty-state compact">
                <p>Dispatch a prompt to populate the corridor ledger.</p>
              </div>
            ) : (
              <div className="shot-list simulator-shot-list">
                {uiState.promptHistory.map((record) => (
                  <article className="shot-card" key={record.id}>
                    <div className="shot-meta">
                      <span>{record.mode}</span>
                      <span>{record.status}</span>
                    </div>
                    <p className="shot-focus">{record.prompt}</p>
                    <p>{record.response}</p>
                    {record.executionId ? <p>Execution: {record.executionId}</p> : null}
                    {record.datasetCommit ? <p>Dataset: {record.datasetCommit}</p> : null}
                  </article>
                ))}
              </div>
            )}
          </section>
        </aside>
      </div>
    </section>
  )
}
