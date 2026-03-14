import React, { useState, useEffect } from "react";
import { Zap, Gauge } from "lucide-react";

export default function HUD() {
  const [speed, setSpeed] = useState(0);
  const [boost, setBoost] = useState(0);

  useEffect(() => {
    // Mock speed loop for visual effect
    const interval = setInterval(() => {
      setSpeed(prev => Math.min(200, Math.max(80, prev + Math.random() * 20 - 10)));
      setBoost(prev => Math.min(100, Math.max(0, prev + (Math.random() > 0.5 ? 2 : -1))));
    }, 100);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none select-none flex flex-col justify-between p-6 z-10">

      {/* Top Bar: Lap Time & Pos */}
      <div className="flex justify-between items-start text-orange-400 font-black italic tracking-tighter drop-shadow-[2px_2px_0_black]">
        <div className="flex flex-col">
          <span className="text-4xl">POS 1/6</span>
          <span className="text-xl text-white">LAP 2/3</span>
        </div>
        <div className="text-4xl text-right">
          01:24.86
          <div className="text-sm text-white font-mono not-italic tracking-normal mt-1">+0.042</div>
        </div>
      </div>

      {/* Bottom Controls Area (Overlay) */}
      <div className="flex justify-between items-end w-full gap-8">

        {/* Speedo */}
        <div className="relative w-32 h-32 md:w-48 md:h-48 bg-black/60 backdrop-blur-sm rounded-full border-4 border-orange-500/50 flex items-center justify-center shadow-[0_0_20px_rgba(255,165,0,0.3)]">
          <div className="flex flex-col items-center">
            <span className="text-5xl md:text-7xl font-black text-white tracking-tighter">
              {Math.floor(speed)}
            </span>
            <span className="text-xs md:text-sm text-orange-400 font-bold tracking-widest">KM/H</span>
          </div>

          {/* Progress Circle (Visual) */}
          <svg className="absolute inset-0 w-full h-full -rotate-90">
            <circle
              className="text-gray-800"
              strokeWidth="4"
              stroke="currentColor"
              fill="transparent"
              r="40%"
              cx="50%"
              cy="50%"
            />
            <circle
              className="text-orange-500 transition-all duration-300"
              strokeWidth="4"
              strokeDasharray={251}
              strokeDashoffset={251 - (251 * (speed / 220))}
              strokeLinecap="round"
              stroke="currentColor"
              fill="transparent"
              r="40%"
              cx="50%"
              cy="50%"
            />
          </svg>
        </div>

        {/* Boost Meter */}
        <div className="flex-1 max-w-md">
          <div className="flex items-center justify-between mb-1 text-yellow-400 font-bold italic">
            <span className="flex items-center gap-1"><Zap size={16} fill="currentColor" /> NITRO</span>
            <span>{Math.floor(boost)}%</span>
          </div>
          <div className="h-4 w-full bg-gray-900 rounded-full overflow-hidden border border-gray-700 skew-x-[-12deg]">
            <div
              className="h-full bg-gradient-to-r from-yellow-600 via-yellow-400 to-white transition-all duration-200"
              style={{ width: `${boost}%` }}
            />
          </div>
        </div>

        {/* Mobile Controls Hint */}
        <div className="hidden md:flex flex-col items-center text-white/50 text-xs font-mono border border-white/20 p-2 rounded bg-black/40">
          <span>[SPACE] DRIFT</span>
          <span>[SHIFT] BOOST</span>
        </div>

      </div>
    </div>
  );
}
