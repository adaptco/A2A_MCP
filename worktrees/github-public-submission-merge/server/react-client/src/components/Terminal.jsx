import React, { useState, useEffect, useRef } from 'react';

export function Terminal({ sendInput, logs = [] }) {
    const [input, setInput] = useState('');
    const [localLogs, setLocalLogs] = useState([]);
    const bottomRef = useRef(null);

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [localLogs, logs]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            processCommand(input);
            setInput('');
        }
    };

    const processCommand = (cmd) => {
        const timestamp = new Date().toLocaleTimeString();
        setLocalLogs(prev => [...prev, `[${timestamp}] > ${cmd}`]);

        const parts = cmd.trim().split(' ');
        const command = parts[0].toLowerCase();

        if (command === '/clear') {
            setLocalLogs([]);
            return;
        }

        if (command === '/deploy') {
            // Trigger Genesis
            // The server expects a raw string or JSON. 
            // Our server.js writes directly to stdin.
            // The Orchestrator expects "genesis_plane" in the string to trigger.
            // So we can just send that string directly or the JSON structure.
            // Let's send the JSON structure to be robust with the Grounding receptor logic if needed,
            // but Orchestrator.cpp does: if (line.find("genesis_plane") != std::string::npos)

            const msg = JSON.stringify({
                type: 'genesis_plane',
                origin: { x: 0, y: 500 },
                dimensions: { w: 1000, h: 50 }
            });
            // We need to send this via the socket.
            // sendInput in useGameSocket sends: { type: 'input', ...input }
            // valid if we change sendInput to be more generic OR we use a raw send.
            // useGameSocket's sendInput wraps in 'input'.
            // Orchestrator.cpp loop reads lines.
            // If we send through sendInput, it becomes {"type":"input", ...} which is a JSON string.
            // The orchestrator will see the whole line.
            // As long as "genesis_plane" is in there, it works.

            // However, to be cleaner, we might want a way to send raw messages.
            // But for now, relying on the substring match is "Hacktacular" enough for this shell.
            sendInput({ command: msg });
            return;
        }

        // Default: Send as raw input/chat
        sendInput({ message: cmd });
    };

    // Combine external logs (from engine) and local logs
    // For now, we only have local logs + what we might receive if we wire it up.
    // server.js sends engine stdout to client. useGameSocket puts it in 'gameState'.
    // If gameState is not a valid JSON state update, useGameSocket warns.
    // We might need to adjust useGameSocket to handle non-state log messages.
    // For now, let's just show local command history.

    return (
        <div className="terminal">
            <div className="terminal-header">GHOST VOID SHELL v1.0</div>
            <div className="terminal-log">
                {localLogs.map((log, i) => (
                    <div key={i} className="terminal-line">{log}</div>
                ))}
                <div ref={bottomRef} />
            </div>
            <div className="terminal-input-line">
                <span className="prompt">$</span>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="terminal-input"
                    autoFocus
                />
            </div>
        </div>
    );
}
