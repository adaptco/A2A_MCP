import React, { useState } from 'react';
import { useGameSocket } from './hooks/useGameSocket';
import { GameCanvas } from './components/GameCanvas';
import { WebGLCanvas } from './components/WebGLCanvas';
import { HUD } from './components/HUD';
import { ConnectionStatus } from './components/ConnectionStatus';
import { Terminal } from './components/Terminal';

function App() {
    const { status, gameState, sendInput } = useGameSocket('ws://localhost:8080');
    const [renderMode, setRenderMode] = useState('WebGL');

    return (
        <div style={{ position: 'relative', width: '800px', height: '600px', margin: '0 auto', fontFamily: 'monospace' }}>
            <ConnectionStatus status={status} />
            
            <div style={{ position: 'absolute', top: 10, right: 10, zIndex: 100 }}>
                <button 
                    onClick={() => setRenderMode(prev => prev === '2D' ? 'WebGL' : '2D')}
                    style={{ padding: '5px 10px', cursor: 'pointer', background: '#333', color: '#fff', border: '1px solid #666' }}
                >
                    Mode: {renderMode}
                </button>
            </div>

            {renderMode === 'WebGL' ? (
                <WebGLCanvas gameState={gameState} sendInput={sendInput} />
            ) : (
                <GameCanvas gameState={gameState} sendInput={sendInput} />
            )}
            
            <HUD score={0} energy={100} />
            <Terminal sendInput={sendInput} />
        </div>
    );
}

export default App;
