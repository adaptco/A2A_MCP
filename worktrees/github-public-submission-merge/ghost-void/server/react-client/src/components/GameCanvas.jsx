import React, { useRef, useEffect } from 'react';

export function GameCanvas({ gameState, sendInput }) {
    const canvasRef = useRef(null);

    // Input Handling
    useEffect(() => {
        const keys = {};

        const handleDown = (e) => {
            keys[e.code] = true;
            pushInput();
        };

        const handleUp = (e) => {
            keys[e.code] = false;
            pushInput();
        };

        const pushInput = () => {
            sendInput({
                left: keys['ArrowLeft'] || false,
                right: keys['ArrowRight'] || false,
                jump: keys['Space'] || keys['ArrowUp'] || false,
                shoot: keys['KeyZ'] || false
            });
        };

        window.addEventListener('keydown', handleDown);
        window.addEventListener('keyup', handleUp);

        return () => {
            window.removeEventListener('keydown', handleDown);
            window.removeEventListener('keyup', handleUp);
        };
    }, [sendInput]);

    // Render Loop (mostly reactive to gameState, but could act as loop)
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !gameState) return;
        const ctx = canvas.getContext('2d');

        // Clear
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Debug Text
        ctx.fillStyle = '#444';
        ctx.font = '14px Courier New';
        ctx.fillText("React Renderer", 10, 580);

        // Mock Avatar
        if (gameState.avatar) {
            ctx.fillStyle = '#00f'; // Mega Man Blue
            ctx.fillRect(gameState.avatar.x, gameState.avatar.y, 30, 30);
        }

        // Draw Level (Simplified)
        // In real app, iterate over gameState.tiles
        ctx.fillStyle = '#666';
        ctx.fillRect(0, 500, 800, 100); // Floor

    }, [gameState]);

    return (
        <canvas
            ref={canvasRef}
            width={800}
            height={600}
            style={{
                border: '4px solid #444',
                boxShadow: '0 0 20px rgba(0,0,0,0.5)',
                imageRendering: 'pixelated'
            }}
        />
    );
}
