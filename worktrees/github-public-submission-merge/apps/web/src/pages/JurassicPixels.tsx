import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/**
 * BAEK-CHEON-2026: Kinetic Manifold Prototype v0.6
 * INTEGRATION: Gemini API Neural Audit & Strategy
 * ARCHITECTURE: MVP (Model-View-Presenter)
 */

type IconName =
  | "Leaf"
  | "Shield"
  | "Heart"
  | "Zap"
  | "Play"
  | "Pause"
  | "RotateCcw"
  | "ShieldAlert"
  | "Sparkles"
  | "MessageSquare"
  | "Database";

type IconProps = {
  name: IconName;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
};

const Icon = ({ name, size = 24, className = "", style }: IconProps) => {
  const iconPaths: Record<IconName, JSX.Element> = {
    Leaf: (
      <>
        <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1 9.8a7 7 0 0 1-9 8.2Z" />
        <path d="M11 20v-5a4 4 0 0 1 4-4h5" />
      </>
    ),
    Shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
    Heart: <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />,
    Zap: <path d="M13 2 L3 14 L12 14 L11 22 L21 10 L12 10 L13 2 Z" />,
    Play: <polygon points="5 3 19 12 5 21 5 3" />,
    Pause: (
      <>
        <rect x="6" y="4" width="4" height="16" />
        <rect x="14" y="4" width="4" height="16" />
      </>
    ),
    RotateCcw: (
      <>
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
        <path d="M3 3v5h5" />
      </>
    ),
    ShieldAlert: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </>
    ),
    Sparkles: (
      <>
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        <path d="M5 3v4" />
        <path d="M19 17v4" />
        <path d="M3 5h4" />
        <path d="M17 19h4" />
      </>
    ),
    MessageSquare: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
    Database: (
      <>
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
      </>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
    >
      {iconPaths[name]}
    </svg>
  );
};

const ENTITY_CAPACITY = 32;
const STRIDE = 8; // [x, y, type, state, health, vx, vy, timer]

const TYPE_SPROUTLING = 1;
const TYPE_TRAP = 2;
const TYPE_THREAT = 3;

const TILES = {
  0: { name: "VOID", color: "#020617" },
  1: { name: "MOSS_DIRT", color: "#14532d" },
  2: { name: "CYAN_RAMP", color: "#0e7490" },
  3: { name: "OBSIDIAN", color: "#0f172a" },
};

const INCIDENT_TABLE = {
  RAPTOR_SURGE: { safety: -0.15, happiness: -0.1, color: "#ef4444" },
  FROST_WILT: { happiness: -0.2, finances: -0.05, color: "#60a5fa" },
  SPORE_BLOOM: { finances: 0.1, safety: -0.05, color: "#f59e0b" },
};

type IncidentKey = keyof typeof INCIDENT_TABLE | null;

type CapsuleEntry = {
  tick: number;
  type: string;
  data: Record<string, number>;
};

const apiKey = "";

const callGemini = async (
  metrics: { finances: string; safety: string; happiness: string },
  incident: IncidentKey,
) => {
  const systemPrompt = `You are the MoE Strategic Coach for Jurassic Pixels. Analyze the current 2.5D simulation state. \n            Metrics: Finances: ${metrics.finances}, Safety: ${metrics.safety}, Happiness: ${metrics.happiness}. \n            Active Incident: ${incident || "NONE"}. \n            Provide a 1-sentence chunky strategy tip in a Bubble-Bobble aesthetic tone.`;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;
  const payload = {
    contents: [{ parts: [{ text: "Provide strategic audit." }] }],
    systemInstruction: { parts: [{ text: systemPrompt }] },
  };

  const backoff = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
  let delay = 1000;
  for (let i = 0; i < 5; i += 1) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("API_ERROR");
      const data = await response.json();
      return data.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    } catch {
      if (i === 4) return "NEURAL_LINK_ERR: Check connectivity.";
      await backoff(delay);
      delay *= 2;
    }
  }
  return "";
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

export default function JurassicPixels() {
  const [buffer] = useState(() => new Float32Array(10 + ENTITY_CAPACITY * STRIDE));
  const [tick, setTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [activeIncident, setActiveIncident] = useState<IncidentKey>(null);
  const [aiTip, setAiTip] = useState("Initializing MoE Council...");
  const [capsule, setCapsule] = useState<CapsuleEntry[]>([]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const spawnEntity = useCallback(
    (type: number, x?: number, y?: number) => {
      for (let i = 0; i < ENTITY_CAPACITY; i += 1) {
        const ptr = 10 + i * STRIDE;
        if (buffer[ptr + 2] === 0) {
          buffer[ptr] = x ?? Math.random() * 400;
          buffer[ptr + 1] = y ?? Math.random() * 300 + 50;
          buffer[ptr + 2] = type;
          buffer[ptr + 3] = 1;
          buffer[ptr + 4] = 1.0;
          buffer[ptr + 5] = (Math.random() - 0.5) * 2;
          buffer[ptr + 6] = (Math.random() - 0.5) * 2;
          buffer[ptr + 7] = 0;
          break;
        }
      }
    },
    [buffer],
  );

  const logInteraction = useCallback(
    (type: string, data: Record<string, number>) => {
      setCapsule((prev) => [...prev, { tick: buffer[0], type, data }].slice(-20));
    },
    [buffer],
  );

  const emitBubble = useCallback(
    (event: React.MouseEvent<HTMLCanvasElement>) => {
      if (!canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      spawnEntity(TYPE_TRAP, x, y);
      logInteraction("EMIT_BUBBLE", { x, y });
    },
    [spawnEntity, logInteraction],
  );

  const updateAiCoaching = useCallback(async () => {
    const metrics = {
      finances: buffer[4].toFixed(0),
      safety: buffer[2].toFixed(2),
      happiness: buffer[3].toFixed(2),
    };
    const response = await callGemini(metrics, activeIncident);
    setAiTip(response);
  }, [activeIncident, buffer]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, 600, 400);

    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1;
    for (let i = 0; i < 600; i += 40) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, 400);
      ctx.stroke();
    }

    for (let i = 0; i < ENTITY_CAPACITY; i += 1) {
      const ptr = 10 + i * STRIDE;
      const type = buffer[ptr + 2];
      if (type === 0) continue;

      const x = buffer[ptr];
      const y = buffer[ptr + 1];

      if (type === TYPE_SPROUTLING) {
        ctx.fillStyle = "#22c55e";
        ctx.fillRect(x - 10, y - 10, 20, 20);
        ctx.strokeStyle = "#fff";
        ctx.strokeRect(x - 10, y - 10, 20, 20);
      } else if (type === TYPE_TRAP) {
        ctx.beginPath();
        ctx.arc(x, y, 20, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(6, 182, 212, 0.3)";
        ctx.fill();
        ctx.strokeStyle = "#06b6d4";
        ctx.lineWidth = 2;
        ctx.stroke();
      } else if (type === TYPE_THREAT) {
        ctx.fillStyle = "#ef4444";
        ctx.beginPath();
        ctx.moveTo(x, y - 15);
        ctx.lineTo(x + 15, y + 15);
        ctx.lineTo(x - 15, y + 15);
        ctx.fill();
      }
    }
  }, [buffer]);

  const simulate = useCallback(() => {
    buffer[0] += 1;

    for (let i = 0; i < ENTITY_CAPACITY; i += 1) {
      const ptr = 10 + i * STRIDE;
      if (buffer[ptr + 2] === 0) continue;

      buffer[ptr] += buffer[ptr + 5];
      buffer[ptr + 1] += buffer[ptr + 6];

      if (buffer[ptr] < 20 || buffer[ptr] > 580) buffer[ptr + 5] *= -1;
      if (buffer[ptr + 1] < 20 || buffer[ptr + 1] > 380) buffer[ptr + 6] *= -1;

      if (buffer[ptr + 2] === TYPE_TRAP) {
        buffer[ptr + 7] += 1;
        if (buffer[ptr + 7] > 180) buffer[ptr + 2] = 0;

        for (let j = 0; j < ENTITY_CAPACITY; j += 1) {
          const target = 10 + j * STRIDE;
          if (buffer[target + 2] === TYPE_THREAT) {
            const dx = buffer[ptr] - buffer[target];
            const dy = buffer[ptr + 1] - buffer[target + 1];
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 30) {
              buffer[target + 2] = 0;
              buffer[ptr + 2] = 0;
              buffer[1] += 50;
            }
          }
        }
      }
    }

    if (buffer[0] % 600 === 0) {
      const keys = Object.keys(INCIDENT_TABLE) as Array<keyof typeof INCIDENT_TABLE>;
      const choice = keys[Math.floor(Math.random() * keys.length)] ?? "RAPTOR_SURGE";
      setActiveIncident(choice);
      spawnEntity(TYPE_THREAT);
    }

    if (buffer[0] % 3000 === 0) {
      void updateAiCoaching();
    }

    setTick(buffer[0]);
  }, [buffer, spawnEntity, updateAiCoaching]);

  useEffect(() => {
    buffer[2] = 0.85;
    buffer[3] = 0.9;
    buffer[4] = 1000;

    for (let i = 0; i < 6; i += 1) {
      spawnEntity(TYPE_SPROUTLING);
    }
  }, [buffer, spawnEntity]);

  useEffect(() => {
    let frame = 0;
    const loop = () => {
      if (isPlaying) {
        simulate();
        render();
      }
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [isPlaying, render, simulate, activeIncident]);

  const metrics = useMemo(
    () => ({
      safety: clamp(buffer[2] * 100, 0, 100).toFixed(0),
      happiness: clamp(buffer[3] * 100, 0, 100).toFixed(0),
      finances: buffer[4].toFixed(0),
    }),
    [buffer, tick],
  );

  return (
    <div className="flex min-h-screen flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col items-start justify-between gap-4 rounded-[2rem] border border-slate-800 bg-slate-900/50 p-6 shadow-2xl md:flex-row md:items-center">
        <div className="flex items-center gap-4">
          <div className="pixel-border rounded-2xl bg-green-600 p-3">
            <Icon name="Leaf" className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-black italic uppercase tracking-tighter">
              Jurassic Pixels <span className="text-green-500">v0.6</span>
            </h1>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
              Axiomatic Deterministic Runtime
            </p>
          </div>
        </div>

        <div className="flex gap-6">
          <div className="text-center">
            <span className="mb-1 block text-[10px] font-black uppercase text-slate-500">Safety</span>
            <div className="flex items-center gap-2">
              <Icon name="Shield" size={14} className="text-blue-500" />
              <span className="text-lg font-black text-blue-400">{metrics.safety}%</span>
            </div>
          </div>
          <div className="border-l border-slate-800 pl-6 text-center">
            <span className="mb-1 block text-[10px] font-black uppercase text-slate-500">
              Happiness
            </span>
            <div className="flex items-center gap-2">
              <Icon name="Heart" size={14} className="text-red-500" />
              <span className="text-lg font-black text-red-400">{metrics.happiness}%</span>
            </div>
          </div>
          <div className="border-l border-slate-800 pl-6 text-center">
            <span className="mb-1 block text-[10px] font-black uppercase text-slate-500">Finances</span>
            <div className="flex items-center gap-2">
              <Icon name="Zap" size={14} className="text-yellow-500" />
              <span className="text-lg font-black text-yellow-400">${metrics.finances}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid flex-grow grid-cols-1 gap-6 overflow-hidden lg:grid-cols-12">
        <div className="flex flex-col space-y-6 lg:col-span-3">
          <section className="group relative overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-900 p-6 shadow-xl">
            <div className="absolute -right-4 -top-4 opacity-5 transition-transform duration-1000 group-hover:rotate-12">
              <Icon name="Sparkles" size={120} />
            </div>
            <h3 className="mb-4 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-purple-400">
              <Icon name="MessageSquare" size={14} /> Neural MoE Coaching
            </h3>
            <div className="flex min-h-[100px] items-center rounded-2xl border border-purple-500/20 bg-slate-950 p-4">
              <p className="text-xs font-medium italic leading-relaxed text-slate-300">"{aiTip}"</p>
            </div>
            <button
              onClick={updateAiCoaching}
              className="mt-4 w-full rounded-xl border border-purple-500/30 bg-purple-600/10 py-2 text-[10px] font-bold uppercase tracking-widest text-purple-400 transition-all hover:bg-purple-600 hover:text-white"
            >
              Force Logic Refresh
            </button>
          </section>

          <section className="flex flex-grow flex-col overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="mb-4 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-500">
              <Icon name="Database" size={14} /> Capsule Event Log
            </h3>
            <div className="custom-scrollbar flex-grow space-y-2 overflow-y-auto pr-2">
              {capsule.map((entry, index) => (
                <div
                  key={`${entry.tick}-${index}`}
                  className="flex justify-between rounded-lg border border-white/5 bg-black/40 p-2 font-mono text-[9px]"
                >
                  <span className="text-slate-600">T-{entry.tick}</span>
                  <span className="text-green-500">{entry.type}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-6">
          <div className="group relative overflow-hidden rounded-[3rem] border-4 border-slate-800 bg-black shadow-2xl">
            <canvas
              ref={canvasRef}
              width={600}
              height={400}
              onClick={emitBubble}
              className="h-full w-full"
            />
            <div className="pointer-events-none absolute left-6 top-6 flex flex-col gap-2">
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 backdrop-blur">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
                <span className="text-[9px] font-black uppercase tracking-widest text-white">
                  Live: {activeIncident || "IDLE"}
                </span>
              </div>
            </div>
            <div className="pointer-events-none absolute bottom-8 right-8">
              <div className="text-right">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Score</p>
                <p className="text-4xl font-black italic leading-none text-white">
                  {(buffer[1] || 0).toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-3xl border border-slate-800 bg-slate-900/50 p-4">
            <div className="flex gap-2">
              <button
                onClick={() => setIsPlaying((prev) => !prev)}
                className="rounded-xl bg-slate-800 p-3 transition-colors hover:bg-slate-700"
              >
                {isPlaying ? <Icon name="Pause" size={18} /> : <Icon name="Play" size={18} />}
              </button>
              <button
                className="rounded-xl bg-slate-800 p-3 transition-colors hover:bg-slate-700"
                onClick={() => window.location.reload()}
              >
                <Icon name="RotateCcw" size={18} />
              </button>
            </div>
            <div className="text-right font-mono text-[10px] text-slate-500">
              VECTOR_TICK: {tick.toString().padStart(8, "0")}
            </div>
          </div>
        </div>

        <div className="space-y-6 lg:col-span-3">
          <section className="rounded-[2rem] border border-slate-800 bg-slate-900 p-6 shadow-xl">
            <h3 className="mb-4 text-[10px] font-black uppercase tracking-widest text-slate-500">
              Active Tileset Spec
            </h3>
            <div className="space-y-3">
              {Object.entries(TILES).map(([id, tile]) => (
                <div
                  key={id}
                  className="flex items-center justify-between rounded-xl border border-white/5 bg-black/20 p-2"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="h-6 w-6 rounded-md shadow-inner"
                      style={{ backgroundColor: tile.color }}
                    />
                    <span className="text-[10px] font-bold text-slate-300">{tile.name}</span>
                  </div>
                  <span className="text-[9px] font-mono text-slate-600">v1.0</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-800 bg-slate-900 p-6 shadow-xl">
            <h3 className="mb-4 text-[10px] font-black uppercase tracking-widest text-slate-500">
              Threat Table
            </h3>
            <div className="space-y-4">
              {Object.entries(INCIDENT_TABLE).map(([key, data]) => (
                <div
                  key={key}
                  className="group relative overflow-hidden rounded-2xl border border-white/5 bg-black/40 p-3"
                >
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase text-white">
                      {key.replace("_", " ")}
                    </span>
                    <Icon name="ShieldAlert" size={14} style={{ color: data.color }} />
                  </div>
                  <div className="mt-2 flex gap-2">
                    {Object.entries(data).map(([metric, value]) =>
                      metric !== "color" ? (
                        <span key={metric} className="text-[8px] font-bold uppercase text-slate-600">
                          {metric}: {value}
                        </span>
                      ) : null,
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      <footer className="mt-auto text-center text-[10px] font-black uppercase tracking-[0.5em] text-slate-700">
        Caretaker Protocol // 211,734 Vector Space // Bath House Simulations
      </footer>
    </div>
  );
}
