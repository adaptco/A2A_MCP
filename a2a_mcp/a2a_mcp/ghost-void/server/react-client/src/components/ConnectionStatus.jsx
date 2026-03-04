import React from 'react';

export function ConnectionStatus({ status }) {
    const color = status === 'Connected' ? '#0f0' : '#f00';
    return (
        <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)' }}>
            Status: <span style={{ color, fontWeight: 'bold' }}>{status}</span>
        </div>
    );
}
