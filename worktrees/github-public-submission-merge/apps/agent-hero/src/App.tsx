import React, { useState } from 'react';
import HeroShotHUD from './components/HeroShotHUD';
import RacingGame from './components/RacingGame';

export default function App() {
  const [mode, setMode] = useState<'hero' | 'race'>('hero');

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden text-white font-mono">
      {/* Mode Toggle */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 flex gap-4 p-2 bg-gray-900/80 backdrop-blur rounded-lg border border-cyan-500/30">
        <button
          onClick={() => setMode('hero')}
          className={`px-4 py-1 rounded transition-all ${
            mode === 'hero'
              ? 'bg-cyan-500 text-black font-bold shadow-[0_0_10px_cyan]'
              : 'text-cyan-400 hover:bg-cyan-900/50'
          }`}
        >
          HERO HUD
        </button>
        <button
          onClick={() => setMode('race')}
          className={`px-4 py-1 rounded transition-all ${
            mode === 'race'
              ? 'bg-orange-500 text-black font-bold shadow-[0_0_10px_orange]'
              : 'text-orange-400 hover:bg-orange-900/50'
          }`}
        >
          RACE PROTOTYPE
        </button>
      </div>

      {mode === 'hero' ? <HeroShotHUD /> : <RacingGame />}
    </div>
  );
}
