import React, { useEffect, useRef, useState } from "react";

// --- Field Math (Adapted for continuous 2D Phase Space) ---
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));

const calculateField = (
  trust: number,
  boundDist: number,
  mode: "read" | "write" = "read",
  sensitivity: "low" | "med" | "high" = "med"
) => {
  const nearBoundary = boundDist <= 0.15;
  const lowTrust = trust < 0.35;
  const highSens = sensitivity === "high";
  const writing = mode === "write";

  // Hard Barrier Logic
  let isHardBarrier = false;
  if (writing && boundDist <= 0.05) isHardBarrier = true;
  if (highSens && writing && nearBoundary && lowTrust) isHardBarrier = true;

  // Potential Logic
  const sensCost = sensitivity === "low" ? 2 : sensitivity === "med" ? 8 : 20;
  const eps = 0.05;
  const boundaryPenalty = clamp(1 / (boundDist + eps), 0, 20);
  const trustPenalty = clamp((1 - trust) * 12, 0, 12);
  const modeCost = writing ? 10 : 0;

  // Convoy Gravity Well: Creates a local minimum (attractor) in the safe zone
  let convoyWell = 0;
  if (mode === "read" && !highSens) {
    const distSq = Math.pow(trust - 0.85, 2) + Math.pow(boundDist - 0.75, 2);
    // Gaussian dip: Depth 15, Width factor 0.1
    convoyWell = -15 * Math.exp(-distSq / 0.1);
  }

  const V = clamp(sensCost + boundaryPenalty + trustPenalty + modeCost + convoyWell, 0, 60);

  // Classification
  let cClass: "normal" | "convoy" | "negotiation" = "normal";
  if (mode === "read" && boundDist >= 0.5 && trust >= 0.6 && sensitivity !== "high") {
    cClass = "convoy";
  } else {
    const isNearBoundary = boundDist <= 0.35;
    const midTrust = trust >= 0.35 && trust < 0.7;
    if (isNearBoundary && midTrust) cClass = "negotiation";
    if (mode === "read" && sensitivity === "high" && boundDist <= 0.6) cClass = "negotiation";
  }

  return { V, isHardBarrier, cClass };
};

type CursorHUD = {
  trust: number;
  boundDist: number;
  V: number;
  cClass: "normal" | "convoy" | "negotiation";
  isHardBarrier: boolean;
} | null;

export default function ConsentVisualizer() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  
  // HUD Data for the sidebar
  const [cursorData, setCursorData] = useState<CursorHUD>(null);
  
  // Mutable ref for rendering the cursor circle without triggering re-renders
  const mousePosRef = useRef<{ x: number; y: number } | null>(null);

  // Field control UI State
  const [fieldMode, setFieldMode] = useState<"read" | "write">("read");
  const [fieldSens, setFieldSens] = useState<"low" | "med" | "high">("med");

  // Keep agents persistent across heatmap/field changes
  const agentsRef = useRef<any[] | null>(null);
  if (!agentsRef.current) {
    agentsRef.current = Array.from({ length: 30 }).map(() => ({
      trust: Math.random(),
      boundDist: Math.random() * 0.5 + 0.5,
      vx: (Math.random() - 0.5) * 0.01,
      vy: (Math.random() - 0.5) * 0.01,
      heat: 0,
      mode: (Math.random() > 0.8 ? "write" : "read") as "read" | "write",
      sensitivity: (Math.random() < 0.15 ? "high" : "med") as "low" | "med" | "high",
      convoyEligible: Math.random() < 0.35, 
    }));
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId = 0;

    // --- DPR + CSS sizing ---
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const logicalWidth = Math.max(1, Math.floor(rect.width));
    const logicalHeight = Math.max(1, Math.floor(rect.height));

    canvas.width = Math.floor(logicalWidth * dpr);
    canvas.height = Math.floor(logicalHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const width = logicalWidth;
    const height = logicalHeight;

    const pxToSpace = (px: number, py: number) => ({
      trust: clamp(px / width, 0, 1),
      boundDist: clamp(1 - py / height, 0, 1),
    });

    const spaceToPx = (trust: number, boundDist: number) => ({
      x: trust * width,
      y: (1 - boundDist) * height,
    });

    // --- Cursor Tracking ---
    const onMove = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect();
      const x = clamp(e.clientX - r.left, 0, width);
      const y = clamp(e.clientY - r.top, 0, height);
      mousePosRef.current = { x, y };

      const s = pxToSpace(x, y);
      const f = calculateField(s.trust, s.boundDist, fieldMode, fieldSens);
      setCursorData({
        trust: s.trust,
        boundDist: s.boundDist,
        V: f.V,
        cClass: f.cClass,
        isHardBarrier: f.isHardBarrier,
      });
    };

    const onLeave = () => {
      mousePosRef.current = null;
      setCursorData(null);
    };

    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);

    // --- Precompute Heatmap Background based on active UI Toggles ---
    const heatCanvas = document.createElement("canvas");
    heatCanvas.width = Math.max(1, Math.floor(width / 4));
    heatCanvas.height = Math.max(1, Math.floor(height / 4));
    const hCtx = heatCanvas.getContext("2d");
    if (!hCtx) return;

    const imgData = hCtx.createImageData(heatCanvas.width, heatCanvas.height);

    for (let y = 0; y < heatCanvas.height; y++) {
      for (let x = 0; x < heatCanvas.width; x++) {
        const space = pxToSpace(x * 4, y * 4);
        const { V, isHardBarrier, cClass } = calculateField(space.trust, space.boundDist, fieldMode, fieldSens);

        const i = (y * heatCanvas.width + x) * 4;

        if (isHardBarrier) {
          imgData.data[i] = 20; imgData.data[i + 1] = 0; imgData.data[i + 2] = 10; imgData.data[i + 3] = 255;
        } else if (cClass === "convoy") {
          const intensity = clamp(255 - V * 4, 0, 255);
          imgData.data[i] = 0; imgData.data[i + 1] = intensity; imgData.data[i + 2] = 255; imgData.data[i + 3] = 255;
        } else if (cClass === "negotiation") {
          imgData.data[i] = 255; imgData.data[i + 1] = clamp(150 - V * 2, 0, 255); imgData.data[i + 2] = 0; imgData.data[i + 3] = 255;
        } else {
          const heat = clamp((V / 60) * 255, 0, 255);
          imgData.data[i] = heat; imgData.data[i + 1] = 20; imgData.data[i + 2] = clamp(100 - heat / 3, 0, 255); imgData.data[i + 3] = 255;
        }
      }
    }
    hCtx.putImageData(imgData, 0, 0);

    // --- Precompute Vector Field ---
    const vectorCanvas = document.createElement("canvas");
    vectorCanvas.width = width;
    vectorCanvas.height = height;
    const vCtx = vectorCanvas.getContext("2d");
    if (vCtx) {
      vCtx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      vCtx.fillStyle = "rgba(255, 255, 255, 0.12)";
      const step = 24;

      for (let y = step / 2; y < height; y += step) {
        for (let x = step / 2; x < width; x += step) {
          const s = pxToSpace(x, y);
          const t0 = s.trust;
          const b0 = s.boundDist;
          const eps = 0.01;

          const vL = calculateField(t0 - eps, b0, fieldMode, fieldSens).V;
          const vR = calculateField(t0 + eps, b0, fieldMode, fieldSens).V;
          const vD = calculateField(t0, b0 - eps, fieldMode, fieldSens).V;
          const vU = calculateField(t0, b0 + eps, fieldMode, fieldSens).V;

          const gradX = (vR - vL) / (2 * eps);
          const gradY = (vU - vD) / (2 * eps);

          const fx = -gradX;
          const fy = -gradY;

          const mag = Math.sqrt(fx * fx + fy * fy);
          if (mag > 0.5) {
            const len = Math.min(mag * 0.6, step * 0.7);
            // Canvas Y is inverted relative to Space Y, so fy is negated for rotation
            const angle = Math.atan2(-fy, fx);

            vCtx.save();
            vCtx.translate(x, y);
            vCtx.rotate(angle);
            
            vCtx.beginPath();
            vCtx.moveTo(-len / 2, 0);
            vCtx.lineTo(len / 2, 0);
            vCtx.lineTo(len / 2 - 3, -2);
            vCtx.moveTo(len / 2, 0);
            vCtx.lineTo(len / 2 - 3, 2);
            vCtx.stroke();
            vCtx.restore();
          } else {
             vCtx.beginPath();
             vCtx.arc(x, y, 0.5, 0, Math.PI * 2);
             vCtx.fill();
          }
        }
      }
    }

    // --- Physics Loop ---
    const render = () => {
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "rgba(10, 10, 15, 0.18)";
      ctx.fillRect(0, 0, width, height);

      ctx.globalCompositeOperation = "screen";
      ctx.globalAlpha = 0.06;
      ctx.drawImage(heatCanvas, 0, 0, width, height);
      ctx.globalAlpha = 1.0;
      ctx.globalCompositeOperation = "source-over";

      ctx.drawImage(vectorCanvas, 0, 0);

      agentsRef.current?.forEach((agent) => {
        const t0 = clamp(agent.trust, 0, 1);
        const b0 = clamp(agent.boundDist, 0, 1);

        const delta = 0.012;
        const tL = clamp(t0 - delta, 0, 1);
        const tR = clamp(t0 + delta, 0, 1);
        const bD = clamp(b0 - delta, 0, 1);
        const bU = clamp(b0 + delta, 0, 1);

        const curr = calculateField(t0, b0, agent.mode, agent.sensitivity);

        const VL = calculateField(tL, b0, agent.mode, agent.sensitivity).V;
        const VR = calculateField(tR, b0, agent.mode, agent.sensitivity).V;
        const VD = calculateField(t0, bD, agent.mode, agent.sensitivity).V;
        const VU = calculateField(t0, bU, agent.mode, agent.sensitivity).V;

        const dVdx = (VR - VL) / (tR - tL || 1e-6);
        const dVdy = (VU - VD) / (bU - bD || 1e-6);

        const inConvoyRegion = curr.cClass === "convoy";
        const convoyCaptured = inConvoyRegion && agent.convoyEligible && agent.mode === "read";

        const base = convoyCaptured ? 0.00008 : 0.00012; 
        const drift = convoyCaptured ? 0.00003 : 0.00005;

        const forceX = -dVdx * base - dVdy * drift;
        const forceY = -dVdy * base + dVdx * drift;

        agent.vx += forceX;
        agent.vy += forceY;

        const friction = convoyCaptured ? 0.94 : 0.92;
        agent.vx *= friction;
        agent.vy *= friction;

        agent.trust = t0 + agent.vx;
        agent.boundDist = b0 + agent.vy;

        const postT = clamp(agent.trust, 0, 1);
        const postB = clamp(agent.boundDist, 0, 1);
        const post = calculateField(postT, postB, agent.mode, agent.sensitivity);

        const outOfBounds = postB <= 0 || postT <= 0 || postT >= 1 || postB >= 1;
        if (post.isHardBarrier || outOfBounds) {
          agent.vx *= -1.45;
          agent.vy *= -1.45;
          agent.trust = clamp(agent.trust, 0.01, 0.99);
          agent.boundDist = clamp(agent.boundDist, 0.01, 0.99);
          agent.heat = Math.min(agent.heat + 18, 100);
        } else {
          agent.heat *= 0.955;
        }

        let vibX = 0, vibY = 0;
        if (post.cClass === "negotiation") {
          const intensity = 0.0045;
          vibX = (Math.random() - 0.5) * intensity;
          vibY = (Math.random() - 0.5) * intensity;
          agent.heat = Math.min(agent.heat + 1.5, 60);
        }

        const pos = spaceToPx(clamp(agent.trust + vibX, 0, 1), clamp(agent.boundDist + vibY, 0, 1));

        ctx.beginPath();
        ctx.arc(pos.x, pos.y, agent.mode === "write" ? 4 : 3, 0, Math.PI * 2);

        if (convoyCaptured) {
          ctx.fillStyle = "#00ffff";
          ctx.shadowBlur = 10;
          ctx.shadowColor = "#00ffff";
        } else {
          ctx.fillStyle = agent.mode === "write" ? "#ff3366" : "#ffffff";
          ctx.shadowBlur = agent.heat;
          ctx.shadowColor = "#ff0000";
        }

        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // Render cursor using the mutable ref to avoid dependency array triggers
      if (mousePosRef.current) {
        ctx.save();
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = "rgba(255,255,255,0.25)";
        ctx.beginPath();
        ctx.arc(mousePosRef.current.x, mousePosRef.current.y, 10, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
    };
  }, [fieldMode, fieldSens]); // ONLY restarts when field controls change!

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-neutral-950 text-neutral-200 p-8 font-mono">
      <div className="max-w-4xl w-full">
        <div className="mb-6 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Consent Phase Space</h1>
            <p className="text-neutral-400 text-sm mb-4">
              <span className="text-cyan-400">Blue regions</span>: Potential convoy basins (requires explicit convoy consent). <br />
              <span className="text-orange-400">Orange regions</span>: Unstable negotiation saddles. <br />
              <span className="text-red-600 font-bold">Dark bottom</span>: Forbidden core boundary.
            </p>
            
            {/* Field Controls UI */}
            <div className="flex gap-4">
              <div className="flex bg-neutral-900 border border-neutral-800 rounded-lg p-1">
                <button
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${fieldMode === 'read' ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'}`}
                  onClick={() => setFieldMode('read')}
                >Read Mode</button>
                <button
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${fieldMode === 'write' ? 'bg-rose-900/50 text-rose-200' : 'text-neutral-500 hover:text-neutral-300'}`}
                  onClick={() => setFieldMode('write')}
                >Write Mode</button>
              </div>

              <div className="flex bg-neutral-900 border border-neutral-800 rounded-lg p-1">
                <button
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${fieldSens === 'low' ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'}`}
                  onClick={() => setFieldSens('low')}
                >Low Sens</button>
                <button
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${fieldSens === 'med' ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'}`}
                  onClick={() => setFieldSens('med')}
                >Med Sens</button>
                <button
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${fieldSens === 'high' ? 'bg-orange-900/50 text-orange-200' : 'text-neutral-500 hover:text-neutral-300'}`}
                  onClick={() => setFieldSens('high')}
                >High Sens</button>
              </div>
            </div>
            <span className="block text-neutral-600 text-xs mt-2">
              Showing field geometry for: <strong className="text-neutral-400">{fieldMode} / {fieldSens}</strong>
            </span>
          </div>

          <div className="text-right text-xs text-neutral-500 space-y-1">
            <p>X-Axis: Trust (0 → 1)</p>
            <p>Y-Axis: Boundary Distance (Core → Outer)</p>
            <p>Glow: Chaotic penalty accumulation</p>
            {cursorData && (
              <div className="mt-2 p-3 rounded border border-neutral-800 bg-neutral-900/80 text-[11px] text-left inline-block w-48 shadow-xl backdrop-blur-sm">
                <div className="text-neutral-300 font-semibold border-b border-neutral-800 pb-1 mb-1">Local Field Probe</div>
                <div className="flex justify-between"><span>trust:</span> <span>{cursorData.trust.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>boundDist:</span> <span>{cursorData.boundDist.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>potential (V):</span> <span>{cursorData.V.toFixed(1)}</span></div>
                <div className="flex justify-between">
                  <span>zone:</span>{" "}
                  <span className={cursorData.cClass === "convoy" ? "text-cyan-400 font-semibold" : cursorData.cClass === "negotiation" ? "text-orange-400 font-semibold" : "text-neutral-300"}>
                    {cursorData.cClass}
                  </span>
                </div>
                <div className="flex justify-between mt-1 pt-1 border-t border-neutral-800/50">
                  <span>hardBarrier:</span>{" "}
                  <span className={cursorData.isHardBarrier ? "text-rose-500 font-bold" : "text-neutral-500"}>
                    {cursorData.isHardBarrier ? "BLOCKED" : "clear"}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="relative rounded-xl overflow-hidden shadow-2xl shadow-cyan-900/20 border border-neutral-800 bg-neutral-900">
          <canvas
            ref={canvasRef}
            className="w-full h-auto cursor-crosshair"
            style={{ display: "block", width: "100%", aspectRatio: "4 / 3" }}
          />

          {/* HUD Overlay */}
          <div className="absolute top-4 left-4 pointer-events-none">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00ffff]"></div>
              <span className="text-xs font-semibold text-cyan-100">Convoy Captured (explicit)</span>
            </div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-white animate-pulse"></div>
              <span className="text-xs font-semibold text-neutral-200">Read Agent (orbiting)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_12px_#ff0000]"></div>
              <span className="text-xs font-semibold text-rose-200">Write Agent (high heat)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}