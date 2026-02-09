🚀 A2A-MCP: Agent-to-Agent Model Context Protocol
A robust, self-healing orchestrator for multi-agent collaboration, built on the Model Context Protocol (MCP) and persistent artifact-driven state management.

🏗️ System State Model
This project follows a three-phase evolution to transition from basic linear tasking to an intelligent, self-correcting agent ecosystem.

Phase 1: Persistence & Foundation (Completed)
Durable Storage: Transitioned from in-memory state to a persistent SQLAlchemy/PostgreSQL back-end.

Traceability: Every agent action produces an immutable MCPArtifact, creating a clear "Chain of Custody" for all data.

Automation: Established GitHub Actions for integration testing of the persistence layer.

Phase 2: Self-Healing Feedback Loop (Completed)
Iterative Logic: The orchestrator now detects agent failures and routes them back for correction.

Actionable Testing: The Tester Agent provides structured critique instead of binary pass/fail results.

Heuristic Fixes: Agents can process feedback to automatically resolve common syntax and documentation errors.

Phase 3: Intelligent LLM Integration (Active)
Reasoning Layer: Centralized LLM utility enables agents to "think" through complex fixes using Gemini/Claude.

Contextual Awareness: Agents ingest full historical artifact traces from the database to inform their next generation cycle.

MCP Control Plane: External tools can now trigger and monitor the entire A2A pipeline via the Model Context Protocol.

🔄 The Self-Healing Flow
Researcher: Analyzes input and generates research_doc.

Coder (v1): Generates initial code based on research.

Tester: Validates code and generates a test_report with detailed critiques.

Orchestrator: Evaluates the report; if failed, it triggers a Self-Correction Loop.

Coder (v2+): Uses the LLM utility to intelligently refactor code based on the Tester's feedback.

Verification
To verify the current system state, ensure your Docker containers are running and execute:

Bash
python test_api.py
python inspect_db.py
