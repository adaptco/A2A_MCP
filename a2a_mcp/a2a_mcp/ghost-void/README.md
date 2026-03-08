# Ghost Void & Agentic Runtime

A hybrid ecosystem combining the **Ghost Void Engine** (procedural C++ simulation) with the **Agentic Runtime Middleware** (Python-based lifecycle management and MLOps tickers).

## Architecture

This project consists of four main components:

1. **Engine Core (`src/`)**: C++ logic for physics, entity management, and procedural level generation.
2. **Agentic Middleware (`middleware/`)**: Python package for agent lifecycle management, state persistence, and external notifications.
3. **Orchestrator (`orchestrator/`)**: High-level agent coordination and self-healing loops.
4. **WebSocket Shell (`server/`)**: A Node.js server that spawns the engine process and bridges communication via WebSockets.
5. **React Frontend (`server/react-client/`)**: HTML5 Canvas SPA for visual interaction and game client rendering.

## Agentic Runtime Middleware

The middleware provides a unified interface for agent state management and real-time MLOps tracking.

### Features

- **Deterministic State Space**: Track agent lifecycle from `INIT` to `CONVERGED`.
- **WhatsApp MLOps Ticker**: Settlement-grade notifications for critical pipeline events.
- **Tetris Scoring Aggregator**: High-frequency gaming telemetry summarized via WhatsApp.
- **Persistence Layer**: SQL-backed artifact and event storage.

### Installation

```bash
# Install core dependencies and the middleware package
pip install -e .
```

### Usage

```python
from middleware import AgenticRuntime, WhatsAppEventObserver

# Initialize runtime with observers
runtime = AgenticRuntime(observers=[WhatsAppEventObserver()])

# Emit events
await runtime.emit_event(model_artifact)
```

## Repository Structure

```text
root/
├── src/                # C++ Source Code
├── include/            # C++ Headers
├── server/             # Node.js Server
│   ├── server.js       # Entry Point
│   └── react-client/   # React Source
├── agency_hub/         # Agent Normalization Layer
├── agents/             # Agent Implementations
└── Makefile            # Build Configuration
```

## How to Run

### Prerequisites

- C++ Compiler (GCC/Clang/MSVC)
- Node.js & npm
- Python 3.11+

### 1. Build the Engine

```sh
make all
```

### 2. Start the Orchestrator

```sh
python -m orchestrator.main
```

### 3. Start the Server

```sh
cd server
npm install
node server.js
```

Visit `http://localhost:8080` to interact with the system.
