const WebSocket = require('ws');
const { spawn } = require('child_process');
const path = require('path');
const express = require('express');
const http = require('http');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Serve static files from 'public' directory
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json()); // Needed for body parsing? No, grounding uses raw/manual parse for simplicity logic

// Grounding Receptor Mount
// We use a proxy object to find the active engine
const engineProxy = {
    get stdin() { return global.activeEngine ? global.activeEngine.stdin : null; }
};
app.use('/webhook', require('./grounding')(engineProxy));
app.use('/valuation', require('./valuation')(engineProxy));

const PORT = 8080;
server.listen(PORT, () => {
    console.log(`Server started on http://localhost:${PORT}`);
});

// console.log('WebSocket Server started on port 8080'); // Removed separate log

// Path to the compiled engine executable
const isWin = process.platform === 'win32';
const enginePath = path.resolve(__dirname, `../bin/ghost-void_engine${isWin ? '.exe' : ''}`);
const groundingReceptor = require('./grounding');

wss.on('connection', (ws) => {
    console.log('Client connected');

    // Spawn the game engine process
    const engine = spawn(enginePath, [], {
        stdio: ['pipe', 'pipe', 'inherit'] // Pipe stdin/stdout, inherit stderr
    });

    // Attach Grounding Receptor (needs engine reference to pipe commands)
    // Note: In this simple architecture, we attach it per socket connection, which is a bit odd.
    // Ideally, the engine is singleton or managed globally. 
    // For this scaffolding, we'll let the most recent connection "own" the grounding receptor 
    // or just assume one user.
    // Better: Mount the route once, but update the engine reference. 
    // Hack for scaffolding: We'll re-mount or notify a global emitter.
    // Let's go with: Global Engine Reference for Grounding.

    global.activeEngine = engine;

    engine.stdout.on('data', (data) => {
        // Send engine output (state) to the client
        try {
            // Data might come in chunks, for this scaffolding we assume line-delimited JSON
            const lines = data.toString().split('\n');
            for (const line of lines) {
                if (line.trim()) {
                    // Validate JSON before broadcasting
                    try {
                        const json = JSON.parse(line.trim());
                        const payload = JSON.stringify(json);
                        // Broadcast to all connected clients (Frontend & Agent)
                        wss.clients.forEach((client) => {
                            if (client.readyState === WebSocket.OPEN) {
                                client.send(payload);
                            }
                        });
                    } catch (parseError) {
                        console.error('Invalid JSON from engine:', line.trim());
                    }
                }
            }
        } catch (e) {
            console.error('Error sending data to client:', e);
        }
    });

    ws.on('message', (message) => {
        // Forward client commands to the engine
        // Expected format: JSON string ending with newline
        engine.stdin.write(message + '\n');
    });

    // Start Game Loop (Drive the engine)
    const gameLoop = setInterval(() => {
        if (engine.exitCode === null) {
            engine.stdin.write('tick\n');
        }
    }, 1000 / 60); // 60 FPS

    ws.on('close', () => {
        console.log('Client disconnected');
        clearInterval(gameLoop);
        engine.kill();
    });

    engine.on('close', (code) => {
        console.log(`Engine process exited with code ${code}`);
        ws.close();
    });
});
