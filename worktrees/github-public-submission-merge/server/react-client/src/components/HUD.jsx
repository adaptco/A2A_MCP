import React from 'react';

export function HUD({ score = 0, energy = 100 }) {
    return (
        <div style={{
            position: 'absolute',
            top: 10,
            left: 10,
            right: 10,
            display: 'flex',
            justifyContent: 'space-between',
            pointerEvents: 'none',
            color: '#fff',
            fontSize: '20px',
            textShadow: '2px 2px #000'
        }}>
            <div>SCORE: {score.toString().padStart(6, '0')}</div>
            <div style={{
                width: '20px',
                height: '100px',
                border: '2px solid #fff',
                position: 'relative',
                backgroundColor: '#444'
            }}>
                <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    width: '100%',
                    height: `${energy}%`,
                    backgroundColor: '#f0e68c',
                    transition: 'height 0.2s'
                }} />
            </div>
        </div>
    );
}
