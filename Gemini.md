# Gemini CLI - A2A_MCP Agent Template

This document defines the foundational mandates, architectural principles, and operational workflows for Gemini CLI within the `A2A_MCP` workspace. These instructions take absolute precedence over general defaults.

## Core Architectural Mandates: The Digital Weave

The A2A_MCP system operates on the "Digital Weave" architecture, where the database is the central orchestrator and all agent outputs are immutable artifacts.

1.  **Artifact-First Persistence:** Every significant output (code, designs, test results) MUST be registered as an `MCPArtifact` in the persistence layer. Use `orchestrator/storage.py` (DBManager) for all state and artifact operations.
2.  **FSM-Driven Workflows:** All complex operations must align with the thread-safe Finite State Machine (FSM) defined in `orchestrator/stateflow.py`. Do not bypass the state transitions for project lifecycle management.
3.  **Self-Healing Feedback Loops:** Implement implementation-validation loops. Any "Coder" action should be followed by a "Tester" action, with automated retries for identified failures as seen in the core pipeline.
4.  **Contractual Communication:** Use the Pydantic schemas in `schemas/` for all inter-agent and inter-component communication to ensure type safety and consistent data structures.
5.  **Agent Ralph as Investigator:** For all codebase investigations and research tasks, utilize the `ResearcherAgent` (embedded as Agent Ralph). This agent employs a persistent, iterative loop ("Ralph Loop") to ensure thoroughness.

## Engineering Standards & Conventions

-   **Concurrency:** Use `asyncio` for the orchestration loop. For blocking I/O (database writes, heavy LLM calls), utilize `asyncio.to_thread` to maintain system responsiveness.
-   **Telemetry:** Every major agent action must emit a telemetry event via the `TelemetryEventModel` to track latency, quality scores, and structural integrity.
-   **Skill-Based Extensibility:** Agents are treated as "embedded skills" within the fabric. When adding functionality, define it as a modular skill that can be registered and invoked by the `Orchestrator`.

## Development Workflows

### 1. Research Phase
-   Validate changes against the `AGENTIC_CORE_STRUCTURE.md` and `architecture.md`.
-   Verify how the change impacts the FSM state transitions.

### 2. Strategy Phase
-   Propose how artifacts will be stored and tracked in the `DBManager`.
-   Define the validation criteria (automated tests) that will close the self-healing loop.

### 3. Execution Phase
-   **Act:** Perform surgical updates to the agents or orchestrator logic.
-   **Validate:** Run the full 5-agent pipeline simulation if possible, or use `pytest` to verify the specific logic. Use the existing `conftest.py` for fixture management.

## Project-Specific Tools
-   **MCP Integration:** Ensure any new tools or resources are exposed via the Model Context Protocol (MCP) as defined in `mcp_server.py`.
-   **State Management:** Always check the current `PlanState` before initiating transitions.

## A2A ADK for MCP
Specialized workflows and tool integrations for the A2A Unified Code-Generating ADK (v1.0.0).
Activate the skill with `activate_skill a2a-adk-mcp` to use the specialized agent development and validation commands.
