import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, Activity, User, Grid } from "lucide-react";

type Status = "IDLE" | "WALK" | "INTERACT";

const statusColors = {
  IDLE: "text-cyan-400 border-cyan-400 shadow-[0_0_10px_cyan]",
  WALK: "text-purple-400 border-purple-400 shadow-[0_0_10px_purple]",
  INTERACT: "text-yellow-400 border-yellow-400 shadow-[0_0_10px_yellow]",
};

export default function HeroShotHUD() {
  const [status, setStatus] = useState<Status>("IDLE");
  const [coherence] = useState(0.999);

  return (
    <div className="flex flex-col md:flex-row justify-between items-center h-full w-full p-8 bg-[radial-gradient(circle_at_center,_#001018,_#000)] text-cyan-50">

      {/* Left Panel: Metadata */}
      <motion.div
        initial={{ x: -50, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="w-full md:w-64 p-6 border border-cyan-500/50 bg-black/40 backdrop-blur-md rounded-lg shadow-[0_0_15px_rgba(0,234,255,0.2)]"
      >
        <div className="flex items-center gap-2 mb-4 text-cyan-400 border-b border-cyan-500/30 pb-2">
          <User size={18} />
          <h3 className="font-bold tracking-widest">METADATA</h3>
        </div>
        <div className="space-y-3 font-mono text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">ID:</span>
            <span className="text-white drop-shadow-[0_0_5px_white]">AE-101-LA</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Rank:</span>
            <span className="text-purple-300">Lead Architect</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Token Wgt:</span>
            <span className="text-green-400">14.2k</span>
          </div>
        </div>
      </motion.div>

      {/* Center Stage */}
      <div className="relative flex flex-col items-center justify-center flex-1 h-full w-full">

        {/* Status Card */}
        <motion.div
          key={status}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className={`mb-8 px-6 py-3 border bg-black/60 backdrop-blur rounded-full flex items-center gap-3 ${statusColors[status]}`}
        >
          <Activity size={16} className="animate-pulse" />
          <h2 className="text-lg font-bold tracking-widest">STATUS: {status}</h2>
          <span className="w-px h-4 bg-white/20 mx-2" />
          <span className="text-xs font-mono opacity-80">COH: {coherence.toFixed(3)}</span>
        </motion.div>

        {/* Isometric Stage */}
        <div className="relative group perspective-[1000px]">
          {/* Sprite Placeholder */}
          <motion.div
            layoutId="sprite"
            className={`
              relative z-20 w-32 h-32 md:w-48 md:h-48 rounded-full
              flex items-center justify-center
              transition-all duration-500
              ${status === 'IDLE' ? 'bg-cyan-500/20 shadow-[0_0_50px_cyan]' : ''}
              ${status === 'WALK' ? 'bg-purple-500/20 shadow-[0_0_50px_purple]' : ''}
              ${status === 'INTERACT' ? 'bg-yellow-500/20 shadow-[0_0_50px_yellow]' : ''}
            `}
          >
            <div className={`
              w-24 h-24 md:w-32 md:h-32 rounded-lg border-2
              flex items-center justify-center text-4xl font-black
              ${status === 'IDLE' ? 'border-cyan-400 text-cyan-400 animate-pulse' : ''}
              ${status === 'WALK' ? 'border-purple-400 text-purple-400 animate-bounce' : ''}
              ${status === 'INTERACT' ? 'border-yellow-400 text-yellow-400 animate-spin' : ''}
            `}>
              {status[0]}
            </div>
          </motion.div>

          {/* Isometric Grid Floor */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] md:w-[400px] md:h-[400px] border border-cyan-500/20 bg-[linear-gradient(45deg,transparent_48%,rgba(0,234,255,0.1)_49%,rgba(0,234,255,0.1)_51%,transparent_52%)] [background-size:20px_20px] transform rotate-x-60 rotate-z-45 shadow-[0_0_100px_rgba(0,234,255,0.1)] rounded-full opacity-60 pointer-events-none" />
          <div className="absolute top-[60%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[200px] h-[200px] bg-cyan-500/5 blur-[40px] rounded-full pointer-events-none" />
        </div>

      </div>

      {/* Right Panel: Controls */}
      <motion.div
        initial={{ x: 50, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="w-full md:w-64 p-6 border border-cyan-500/50 bg-black/40 backdrop-blur-md rounded-lg shadow-[0_0_15px_rgba(0,234,255,0.2)]"
      >
        <div className="flex items-center gap-2 mb-4 text-cyan-400 border-b border-cyan-500/30 pb-2">
          <Grid size={18} />
          <h3 className="font-bold tracking-widest">ANIMATION</h3>
        </div>
        <div className="flex flex-col gap-2">
          {(["IDLE", "WALK", "INTERACT"] as Status[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`
                px-4 py-2 text-sm font-bold tracking-wider transition-all border
                hover:bg-cyan-500/20 hover:text-white
                ${status === s
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_8px_cyan]'
                  : 'bg-transparent text-gray-500 border-gray-700'}
              `}
            >
              {s}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
