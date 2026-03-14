import { useEffect, useRef, useState } from "react";

type MissionModel = "claude" | "gemini" | "square";

type Mission = {
  id: string;
  phase: string;
  lane: string;
  title: string;
  summary: string;
  deliverable: string;
  source: string;
  model: MissionModel;
  zone: string;
  promptTokens: number;
  completionTokens: number;
  toolTokens: number;
  value: number;
  chaosDelta: number;
  tools: string[];
  avatarCue: string;
};

type LedgerEntry = {
  receiptId: string;
  missionId: string;
  missionTitle: string;
  totalTokens: number;
  estimatedCost: number;
  deliverable: string;
  model: MissionModel;
};

type GameMode = "briefing" | "play";

type GameState = {
  mode: GameMode;
  activeIndex: number;
  completedIds: string[];
  ledger: LedgerEntry[];
  backgroundTokens: number;
  runtimeMs: number;
  budgetCap: number;
  reserve: number;
  campaignName: string;
  notes: string;
  chaos: number;
  lastAction: string;
};

declare global {
  interface Window {
    render_game_to_text?: () => string;
    advanceTime?: (ms: number) => void;
  }
}

const MODEL_RATES: Record<MissionModel, { prompt: number; completion: number }> = {
  claude: { prompt: 0.003, completion: 0.015 },
  gemini: { prompt: 0.00125, completion: 0.005 },
  square: { prompt: 0, completion: 0 },
};

const TOOL_RATE = 0.0008;
const AMBIENT_RATE = 0.0024;

const MISSIONS: Mission[] = [
  {
    id: "notes-raid",
    phase: "Collect",
    lane: "Meeting notes",
    title: "Decision Raid",
    summary: "Run the `workspace-assistant-stack` overlay on fresh meetings so Charley starts from decisions, not noise.",
    deliverable: "Decision memo with owners, dates, and blocked items.",
    source: "skill.zip overlay",
    model: "claude",
    zone: "A / Planning",
    promptTokens: 2200,
    completionTokens: 1200,
    toolTokens: 360,
    value: 14,
    chaosDelta: -6,
    tools: ["meeting-intelligence", "decision tagging", "owner extraction"],
    avatarCue: "Pull the signal out first. Clean notes are cheaper than creative rework.",
  },
  {
    id: "ticket-forge",
    phase: "Scope",
    lane: "Ticket triage",
    title: "Acceptance Forge",
    summary: "Convert rough feature asks into sharp tickets before the burn rate touches the reserve pool.",
    deliverable: "Ticket pack with repro steps, acceptance criteria, and risk flags.",
    source: "skill.zip overlay",
    model: "claude",
    zone: "A / Planning",
    promptTokens: 2480,
    completionTokens: 1380,
    toolTokens: 410,
    value: 16,
    chaosDelta: -4,
    tools: ["triage planner", "criteria generator", "scope limiter"],
    avatarCue: "Write the handoff so Parker never has to guess the shape of the feature.",
  },
  {
    id: "insight-sift",
    phase: "Story",
    lane: "Interview insights",
    title: "Insight Sift",
    summary: "Mine customer interviews into themes, hypotheses, and launch hooks that Charley can actually market.",
    deliverable: "Insight board with themes, evidence lines, and next-bet hypotheses.",
    source: "skill.zip overlay",
    model: "claude",
    zone: "A / Planning",
    promptTokens: 2660,
    completionTokens: 1540,
    toolTokens: 480,
    value: 20,
    chaosDelta: -3,
    tools: ["theme clustering", "quote tagging", "hypothesis ladder"],
    avatarCue: "Good campaigns are just sharp taste translated into proof.",
  },
  {
    id: "brand-rollout",
    phase: "Compose",
    lane: "Brand strategy",
    title: "Foxfire Rollout Board",
    summary: "Use Charley's avatar brief from `Agents.pdf` to shape a six-month rollout board, copy direction, and creative spread.",
    deliverable: "Brand rollout board with hooks, channels, and calendar wedges.",
    source: "Agents.pdf / Charley-Fox",
    model: "claude",
    zone: "A / Planning",
    promptTokens: 3120,
    completionTokens: 1760,
    toolTokens: 560,
    value: 24,
    chaosDelta: 5,
    tools: ["brand generator", "content planner", "creative spread"],
    avatarCue: "Creative chaos is allowed. Ledger chaos is not.",
  },
  {
    id: "square-sync",
    phase: "Sync",
    lane: "POS embed",
    title: "Square Signal Sync",
    summary: "Attach the rollout to store reality: POS, embed hooks, and the AGENT UI layer that lives inside the sales flow.",
    deliverable: "POS sync contract and embedded widget handoff notes.",
    source: "Agents.pdf / Charley-Fox",
    model: "square",
    zone: "A to D bridge",
    promptTokens: 1600,
    completionTokens: 900,
    toolTokens: 1320,
    value: 22,
    chaosDelta: -2,
    tools: ["square sdk", "embed contract", "web builder"],
    avatarCue: "If the campaign cannot touch checkout, it is only decoration.",
  },
  {
    id: "parker-handoff",
    phase: "Ship",
    lane: "Parker sandbox",
    title: "Sandbox Handoff",
    summary: "Pass a clean token ledger and launch brief into Parker's sandbox so the artifact ships as a playable web app instead of a loose concept.",
    deliverable: "Parker-ready artifact brief with budget guardrails and launch state.",
    source: "Agents.pdf / Parker sandbox",
    model: "gemini",
    zone: "D / Sandbox",
    promptTokens: 2340,
    completionTokens: 1260,
    toolTokens: 520,
    value: 30,
    chaosDelta: -10,
    tools: ["game generation", "asset manager", "sandbox attestation"],
    avatarCue: "Ship the brief with enough discipline that Parker can move fast without lighting the budget on fire.",
  },
];

const INITIAL_STATE: GameState = {
  mode: "briefing",
  activeIndex: 0,
  completedIds: [],
  ledger: [],
  backgroundTokens: 480,
  runtimeMs: 0,
  budgetCap: 72000,
  reserve: 9000,
  campaignName: "Charley Fox Token Accountant",
  notes:
    "Sandbox objective: keep the planning-layer burn readable, then hand the clean artifact to Parker with budget headroom still intact.",
  chaos: 38,
  lastAction: "Open the briefing, then hit Start Shift.",
};

function calculateMissionCost(mission: Mission): number {
  const pricing = MODEL_RATES[mission.model];
  const promptCost = (mission.promptTokens / 1000) * pricing.prompt;
  const completionCost = (mission.completionTokens / 1000) * pricing.completion;
  const toolCost = (mission.toolTokens / 1000) * TOOL_RATE;

  return round2(promptCost + completionCost + toolCost);
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function totalMissionTokens(mission: Mission): number {
  return mission.promptTokens + mission.completionTokens + mission.toolTokens;
}

function tick(state: GameState, ms: number): GameState {
  if (state.mode !== "play") {
    return state;
  }

  const steps = Math.max(1, Math.round(ms / 250));
  let runtimeMs = state.runtimeMs;
  let backgroundTokens = state.backgroundTokens;
  let chaos = state.chaos;

  for (let index = 0; index < steps; index += 1) {
    runtimeMs += 250;
    backgroundTokens += 4 + state.completedIds.length;
    chaos = clamp(chaos + 0.18, 0, 100);
  }

  return {
    ...state,
    runtimeMs,
    backgroundTokens,
    chaos: round2(chaos),
    lastAction: `Clock advanced ${Math.round(ms)}ms through the sandbox.`,
  };
}

function createReceipt(mission: Mission, sequence: number): LedgerEntry {
  return {
    receiptId: `CF-${String(sequence).padStart(3, "0")}`,
    missionId: mission.id,
    missionTitle: mission.title,
    totalTokens: totalMissionTokens(mission),
    estimatedCost: calculateMissionCost(mission),
    deliverable: mission.deliverable,
    model: mission.model,
  };
}

function buildSnapshot(state: GameState) {
  const activeMission = MISSIONS[state.activeIndex];
  const missionTokensSpent = state.ledger.reduce((sum, entry) => sum + entry.totalTokens, 0);
  const spentTokens = missionTokensSpent + state.backgroundTokens;
  const remainingBudget = state.budgetCap - state.reserve - spentTokens;
  const missionValue = state.ledger.reduce((sum, entry) => {
    const mission = MISSIONS.find((item) => item.id === entry.missionId);
    return sum + (mission?.value ?? 0);
  }, 0);
  const costSpent = round2(
    state.ledger.reduce((sum, entry) => sum + entry.estimatedCost, 0) +
      (state.backgroundTokens / 1000) * AMBIENT_RATE,
  );
  const signal = clamp(18 + missionValue + state.completedIds.length * 4, 0, 100);
  const sandboxReadiness = clamp(
    Math.round(
      (state.completedIds.length / MISSIONS.length) * 72 +
        (remainingBudget > 0 ? 18 : -24) +
        (state.chaos < 52 ? 10 : -8),
    ),
    0,
    100,
  );
  const handoffReady =
    state.completedIds.length === MISSIONS.length && remainingBudget > 0 && state.chaos < 55;

  return {
    activeMission,
    costSpent,
    handoffReady,
    remainingBudget,
    sandboxReadiness,
    signal,
    snapshot: {
      mode: state.mode,
      coordinateSystem: "mission_index origin=0 left_to_right across the rail",
      activeMission: {
        index: state.activeIndex,
        id: activeMission.id,
        title: activeMission.title,
        lane: activeMission.lane,
        totalTokens: totalMissionTokens(activeMission),
      },
      budget: {
        cap: state.budgetCap,
        reserve: state.reserve,
        spent: spentTokens,
        remaining: remainingBudget,
      },
      scores: {
        signal,
        chaos: state.chaos,
        sandboxReadiness,
      },
      completedMissionIds: state.completedIds,
      ledgerCount: state.ledger.length,
      lastAction: state.lastAction,
      controls:
        state.mode === "briefing"
          ? ["Space", "Enter"]
          : ["ArrowLeft", "ArrowRight", "Space", "R"],
    },
    spentTokens,
  };
}

function FoxAvatar() {
  return (
    <svg className="fox-svg" viewBox="0 0 280 280" role="img" aria-label="Charley Fox avatar">
      <defs>
        <linearGradient id="fur" x1="0%" x2="100%" y1="0%" y2="100%">
          <stop offset="0%" stopColor="#ffbf84" />
          <stop offset="55%" stopColor="#ff8c3c" />
          <stop offset="100%" stopColor="#ef5b22" />
        </linearGradient>
        <linearGradient id="visor" x1="0%" x2="100%" y1="0%" y2="0%">
          <stop offset="0%" stopColor="#7ce0c3" stopOpacity="0.92" />
          <stop offset="100%" stopColor="#9ef6ff" stopOpacity="0.6" />
        </linearGradient>
      </defs>
      <circle cx="140" cy="140" r="110" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.08)" />
      <path d="M82 88 L112 30 L128 92 Z" fill="url(#fur)" />
      <path d="M198 88 L168 30 L152 92 Z" fill="url(#fur)" />
      <path d="M78 108 Q140 48 202 108 L184 204 Q140 230 96 204 Z" fill="url(#fur)" />
      <path d="M96 118 Q140 82 184 118 L172 186 Q140 208 108 186 Z" fill="#fff2e7" />
      <path d="M92 118 Q140 148 188 118" fill="none" stroke="#1e1310" strokeWidth="10" strokeLinecap="round" />
      <ellipse cx="116" cy="138" rx="20" ry="14" fill="#1a0e09" />
      <ellipse cx="164" cy="138" rx="20" ry="14" fill="#1a0e09" />
      <rect x="92" y="120" width="96" height="32" rx="16" fill="url(#visor)" opacity="0.75" />
      <circle cx="116" cy="138" r="6" fill="#fffaf5" />
      <circle cx="164" cy="138" r="6" fill="#fffaf5" />
      <path d="M128 170 Q140 182 152 170" fill="none" stroke="#1e1310" strokeWidth="8" strokeLinecap="round" />
      <path d="M126 158 Q140 150 154 158" fill="#1e1310" />
      <circle cx="68" cy="120" r="14" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="6" />
      <circle cx="212" cy="120" r="14" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="6" />
      <path d="M78 120 H62" stroke="rgba(255,255,255,0.12)" strokeWidth="6" strokeLinecap="round" />
      <path d="M218 120 H202" stroke="rgba(255,255,255,0.12)" strokeWidth="6" strokeLinecap="round" />
      <path d="M112 214 Q140 228 168 214" fill="none" stroke="rgba(255,255,255,0.24)" strokeWidth="8" strokeLinecap="round" />
    </svg>
  );
}

export function App() {
  const [state, setState] = useState<GameState>(INITIAL_STATE);
  const stateRef = useRef<GameState>(state);
  const derived = buildSnapshot(state);
  const activeMission = derived.activeMission;

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    window.render_game_to_text = () => JSON.stringify(buildSnapshot(stateRef.current).snapshot);
    window.advanceTime = (ms: number) => {
      setState((current) => tick(current, ms));
    };

    return () => {
      delete window.render_game_to_text;
      delete window.advanceTime;
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === " " || event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault();
      }

      if (stateRef.current.mode === "briefing" && (event.key === "Enter" || event.key === " ")) {
        setState((current) => ({
          ...current,
          mode: "play",
          lastAction: "Shift started. Arrow keys move across the mission rail.",
        }));
        return;
      }

      if (stateRef.current.mode !== "play") {
        return;
      }

      if (event.key === "ArrowLeft") {
        setState((current) => ({
          ...current,
          activeIndex: (current.activeIndex + MISSIONS.length - 1) % MISSIONS.length,
          lastAction: "Moved left on the mission rail.",
        }));
      }

      if (event.key === "ArrowRight") {
        setState((current) => ({
          ...current,
          activeIndex: (current.activeIndex + 1) % MISSIONS.length,
          lastAction: "Moved right on the mission rail.",
        }));
      }

      if (event.key.toLowerCase() === "r") {
        setState(INITIAL_STATE);
      }

      if (event.key === " ") {
        executeMission(stateRef.current.activeIndex);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function executeMission(index: number) {
    const mission = MISSIONS[index];

    setState((current) => {
      if (current.mode !== "play") {
        return current;
      }

      if (current.completedIds.includes(mission.id)) {
        return {
          ...current,
          lastAction: `${mission.title} is already sealed in the ledger.`,
        };
      }

      const receipt = createReceipt(mission, current.ledger.length + 1);

      return {
        ...current,
        completedIds: [...current.completedIds, mission.id],
        ledger: [...current.ledger, receipt],
        chaos: round2(clamp(current.chaos + mission.chaosDelta, 0, 100)),
        lastAction: `${mission.title} posted ${receipt.totalTokens.toLocaleString()} tokens to the ledger.`,
      };
    });
  }

  function resetRun() {
    setState(INITIAL_STATE);
  }

  function setBudgetCap(value: number) {
    setState((current) => ({
      ...current,
      budgetCap: value,
      lastAction: `Budget cap tuned to ${value.toLocaleString()} tokens.`,
    }));
  }

  function setReserve(value: number) {
    setState((current) => ({
      ...current,
      reserve: value,
      lastAction: `Reserve tuned to ${value.toLocaleString()} tokens.`,
    }));
  }

  return (
    <div className="app-shell">
      <div className="topline">
        <span>Agents.pdf sandbox • Charley-Fox avatar • Parker handoff</span>
        <span>Controls: left/right move • space execute • r reset</span>
      </div>
      <section className="hero-grid">
        <article className="panel hero-panel">
          <div className="hero-copy">
            <div>
              <div className="eyebrow">
                <strong>Zone A</strong>
                Planning-layer fox with a live token ledger
              </div>
              <h1 className="hero-title">
                Charley Fox <em>Token Accountant</em>
              </h1>
              <p className="hero-body">
                A playable web app that turns Charley-Fox from the `Agents.pdf` swarm brief into a
                budget-disciplined avatar. The first three missions inherit the generic
                `workspace-assistant-stack` skill from `skill.zip`; the last three lock the output
                into Charley&apos;s brand-planning lane and hand the artifact to Parker&apos;s sandbox.
              </p>

              <div className="hero-actions">
                <button
                  id="start-btn"
                  className="action-button primary"
                  type="button"
                  onClick={() =>
                    setState((current) => ({
                      ...current,
                      mode: "play",
                      lastAction: "Shift started. Arrow keys move across the mission rail.",
                    }))
                  }
                >
                  {state.mode === "play" ? "Shift Live" : "Start Shift"}
                </button>
                <button className="action-button secondary" type="button" onClick={resetRun}>
                  Reset Ledger
                </button>
              </div>
            </div>

            <div className="avatar-shell">
              <h2>Avatar Brief</h2>
              <p>{activeMission.avatarCue}</p>
              <div className="avatar-figure">
                <div className="avatar-ring" />
                <div className="token-badge one">Spryte / Claude</div>
                <div className="token-badge two">Zone A planner</div>
                <div className="token-badge three">Creative chaos, clean books</div>
                <FoxAvatar />
              </div>
              <div className="avatar-meta">
                <div className="meta-row">
                  <strong>Boo binding</strong>
                  <span className="pill orange">Spryte</span>
                </div>
                <div className="meta-row">
                  <strong>Current lane</strong>
                  <span className="pill mint">{activeMission.lane}</span>
                </div>
                <div className="meta-row">
                  <strong>Parker sandbox</strong>
                  <span className={derived.handoffReady ? "pill mint" : "pill danger"}>
                    {derived.handoffReady ? "ready to ship" : "still balancing"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="hero-stats">
            <div className="stat-card">
              <div className="stat-label">Spent tokens</div>
              <div className="stat-value">{derived.spentTokens.toLocaleString()}</div>
              <div className="stat-meta">Ambient planning burn included</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Remaining budget</div>
              <div className="stat-value">{derived.remainingBudget.toLocaleString()}</div>
              <div className="stat-meta">Reserve already held back</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Estimated spend</div>
              <div className="stat-value">${derived.costSpent.toFixed(2)}</div>
              <div className="stat-meta">Prompt + completion + tool cost</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Sandbox score</div>
              <div className="stat-value">{derived.sandboxReadiness}</div>
              <div className="stat-meta">Handoff confidence to Parker</div>
            </div>
          </div>

          <div className="hero-form">
            <div className="field">
              <label htmlFor="campaign-name">Campaign / build name</label>
              <input
                id="campaign-name"
                value={state.campaignName}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    campaignName: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label htmlFor="active-brief">Active deliverable</label>
              <input id="active-brief" value={activeMission.deliverable} readOnly />
            </div>
            <div className="field wide">
              <label htmlFor="notes">Sandbox notes</label>
              <textarea
                id="notes"
                value={state.notes}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label htmlFor="budget-cap">Budget cap</label>
              <div className="range-field">
                <div className="range-header">
                  <span>{state.budgetCap.toLocaleString()} tokens</span>
                  <span>36k to 120k</span>
                </div>
                <input
                  id="budget-cap"
                  type="range"
                  min={36000}
                  max={120000}
                  step={1000}
                  value={state.budgetCap}
                  onChange={(event) => setBudgetCap(Number(event.target.value))}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="reserve-pool">Reserve pool</label>
              <div className="range-field">
                <div className="range-header">
                  <span>{state.reserve.toLocaleString()} tokens</span>
                  <span>4k to 24k</span>
                </div>
                <input
                  id="reserve-pool"
                  type="range"
                  min={4000}
                  max={24000}
                  step={500}
                  value={state.reserve}
                  onChange={(event) => setReserve(Number(event.target.value))}
                />
              </div>
            </div>
          </div>
        </article>

        <aside className="panel brief-panel">
          <div className="section-head">
            <div>
              <h3>Sandbox brief</h3>
              <p>
                Charley-Fox owns the planning layer. Parker owns the sandbox layer. The job of this
                app is to make their handoff accountable in tokens, not just vibes.
              </p>
            </div>
            <span className={derived.handoffReady ? "pill mint" : "pill orange"}>
              {derived.handoffReady ? "handoff sealed" : "briefing live"}
            </span>
          </div>

          <div className="insight-grid">
            <div className="insight-card">
              <h4>Charley-Fox from Agents.pdf</h4>
              <p>
                Boo binding: Spryte. LLM target: Claude. Avatar zone: A / Planning Layer. Role:
                creative brand strategist responsible for rollout boards, web builder outputs, and
                Square-linked sales surfaces.
              </p>
            </div>
            <div className="insight-card">
              <h4>`skill.zip` overlay</h4>
              <ul>
                <li>Meeting notes become decisions and action items.</li>
                <li>Feature asks become scoped tickets with acceptance criteria.</li>
                <li>Interview transcripts become themes and product hypotheses.</li>
              </ul>
            </div>
            <div className="insight-card">
              <h4>Readiness</h4>
              <div className="readiness-bar">
                <span style={{ width: `${derived.sandboxReadiness}%` }} />
              </div>
              <p style={{ marginTop: 12 }}>
                Signal score {derived.signal}. Chaos {state.chaos}. The sweet spot is high signal
                with chaos under fifty-five before Parker receives the artifact.
              </p>
            </div>
          </div>
        </aside>
      </section>
      <section className="dashboard-grid">
        <div className="stack">
          <article className="panel mission-panel">
            <div className="section-head">
              <div>
                <h3>Mission rail</h3>
                <p>
                  Select a lane with the arrow keys or by clicking. Press space or use the execute
                  button to post the mission to the token ledger.
                </p>
              </div>
              <span className="pill orange">{activeMission.zone}</span>
            </div>

            <div className="mission-rail">
              {MISSIONS.map((mission, index) => {
                const isActive = state.activeIndex === index;
                const isComplete = state.completedIds.includes(mission.id);

                return (
                  <button
                    key={mission.id}
                    className="mission-row"
                    data-active={isActive}
                    data-complete={isComplete}
                    type="button"
                    onClick={() =>
                      setState((current) => ({
                        ...current,
                        activeIndex: index,
                        lastAction: `Focused ${mission.title}.`,
                      }))
                    }
                  >
                    <div className="mission-phase">
                      <span>{mission.phase}</span>
                      <strong>{mission.lane}</strong>
                    </div>
                    <div className="mission-copy">
                      <strong>{mission.title}</strong>
                      <p>{mission.summary}</p>
                    </div>
                    <div className="mission-metrics">
                      <span>{totalMissionTokens(mission).toLocaleString()} tokens</span>
                      <span>${calculateMissionCost(mission).toFixed(2)}</span>
                      <span>{isComplete ? "sealed" : mission.source}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mission-detail">
              <div className="mission-grid">
                <div>
                  <span className="pill mint">{activeMission.source}</span>
                  <h4>{activeMission.title}</h4>
                  <p>{activeMission.summary}</p>
                  <ul>
                    <li>Deliverable: {activeMission.deliverable}</li>
                    <li>Tools: {activeMission.tools.join(", ")}</li>
                    <li>Avatar cue: {activeMission.avatarCue}</li>
                  </ul>
                </div>
                <div className="receipt-grid">
                  <div className="receipt-card">
                    <strong>Prompt tokens</strong>
                    <span>{activeMission.promptTokens.toLocaleString()}</span>
                  </div>
                  <div className="receipt-card">
                    <strong>Completion tokens</strong>
                    <span>{activeMission.completionTokens.toLocaleString()}</span>
                  </div>
                  <div className="receipt-card">
                    <strong>Tool tokens</strong>
                    <span>{activeMission.toolTokens.toLocaleString()}</span>
                  </div>
                  <div className="receipt-card">
                    <strong>Estimated cost</strong>
                    <span>${calculateMissionCost(activeMission).toFixed(2)}</span>
                  </div>
                  <button
                    id="run-btn"
                    className="action-button primary"
                    type="button"
                    onClick={() => executeMission(state.activeIndex)}
                    style={{ gridColumn: "1 / -1" }}
                  >
                    {state.completedIds.includes(activeMission.id)
                      ? "Mission sealed"
                      : `Execute ${activeMission.title}`}
                  </button>
                </div>
              </div>
            </div>
          </article>

          <article className="panel insight-panel">
            <div className="section-head">
              <div>
                <h3>Why this shape</h3>
                <p>
                  The original Charley Fox JRPG scaffold in this workspace already framed six
                  workday phases. This version keeps the same rhythm but converts the stakes from
                  pizza-shift throughput into token-accounting and artifact handoff.
                </p>
              </div>
            </div>

            <div className="insight-grid">
              <div className="insight-card">
                <h4>Mission mapping</h4>
                <ul>
                  <li>Collect / Scope / Story come from `workspace-assistant-stack`.</li>
                  <li>Compose / Sync come from Charley-Fox&apos;s `Agents.pdf` brief.</li>
                  <li>Ship is the Parker sandbox handoff gate.</li>
                </ul>
              </div>
              <div className="insight-card">
                <h4>Token accountant behavior</h4>
                <ul>
                  <li>Each mission mints an immutable receipt with tokens and estimated spend.</li>
                  <li>Ambient planning time burns background tokens through `advanceTime(ms)`.</li>
                  <li>Readiness depends on completion, remaining reserve, and controlled chaos.</li>
                </ul>
              </div>
            </div>
          </article>
        </div>

        <div className="stack">
          <article className="panel ledger-panel">
            <div className="section-head">
              <div>
                <h3>Ledger</h3>
                <p>
                  Receipts are immutable. The accounting view keeps mission burn, ambient drift, and
                  Parker handoff risk in one place.
                </p>
              </div>
              <span className={derived.remainingBudget > 0 ? "pill mint" : "pill danger"}>
                {derived.remainingBudget > 0 ? "within reserve" : "reserve breached"}
              </span>
            </div>

            {state.ledger.length === 0 ? (
              <div className="receipt-empty">
                No receipts yet. Start the shift, then execute a mission to post the first token
                entry into Charley&apos;s ledger.
              </div>
            ) : (
              <table className="ledger-table">
                <thead>
                  <tr>
                    <th>Receipt</th>
                    <th>Mission</th>
                    <th>Model</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {state.ledger.map((entry) => (
                    <tr key={entry.receiptId}>
                      <td>{entry.receiptId}</td>
                      <td>
                        {entry.missionTitle}
                        <div className="muted">{entry.deliverable}</div>
                      </td>
                      <td>{entry.model}</td>
                      <td>{entry.totalTokens.toLocaleString()}</td>
                      <td>${entry.estimatedCost.toFixed(2)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td>SYSTEM</td>
                    <td>
                      Ambient planning drift
                      <div className="muted">`advanceTime(ms)` background burn</div>
                    </td>
                    <td>blend</td>
                    <td>{state.backgroundTokens.toLocaleString()}</td>
                    <td>${((state.backgroundTokens / 1000) * AMBIENT_RATE).toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            )}
          </article>

          <article className="panel ledger-panel">
            <div className="section-head">
              <div>
                <h3>Live state</h3>
                <p>
                  This mirrors the deterministic state exported by `window.render_game_to_text()`.
                </p>
              </div>
            </div>
            <div className="insight-card">
              <p>
                <strong>Last action:</strong> {state.lastAction}
              </p>
              <p style={{ marginTop: 12 }}>
                <strong>Runtime:</strong> {(state.runtimeMs / 1000).toFixed(1)}s
              </p>
              <p style={{ marginTop: 12 }}>
                <strong>Completed:</strong> {state.completedIds.length} / {MISSIONS.length}
              </p>
              <p style={{ marginTop: 12 }}>
                <strong>Campaign:</strong> {state.campaignName}
              </p>
            </div>
          </article>
        </div>
      </section>

      <div className="footer-bar">
        <div>
          <strong>Snapshot contract:</strong> mission index is the playable coordinate system; the
          leftmost card is origin `0`, and rightward movement increments the cursor.
        </div>
        <div>
          <strong>Status:</strong>{" "}
          {derived.handoffReady ? "Parker can ship this." : "Charley is still balancing the ledger."}
        </div>
      </div>
    </div>
  );
}
