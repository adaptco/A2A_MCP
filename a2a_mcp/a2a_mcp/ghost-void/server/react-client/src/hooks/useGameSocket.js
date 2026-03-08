import { useEffect, useState, useRef } from 'react';

export function useGameSocket(url = 'ws://localhost:8080') {
    const [status, setStatus] = useState('Disconnected');
    const [gameState, setGameState] = useState(null);
    const socketRef = useRef(null);

    useEffect(() => {
        const ws = new WebSocket(url);
        socketRef.current = ws;

        ws.onopen = () => setStatus('Connected');
        ws.onclose = () => setStatus('Disconnected');
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setGameState(data);
            } catch (e) {
                console.warn('Invalid JSON:', event.data);
            }
        };

        return () => {
            ws.close();
        };
    }, [url]);

    const sendInput = (input) => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({ type: 'input', ...input }));
        }
    };

    return { status, gameState, sendInput };
}
