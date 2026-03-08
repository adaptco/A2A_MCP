# Avatar System & Judge Integration (Part E)

Complete agent-avatar binding system with Judge-based action evaluation integrated into orchestrator.

## Architecture

### Avatar System (avatars/)
- avatar.py: Avatar, AvatarProfile, AvatarStyle (Engineer/Designer/Driver)
- registry.py: AvatarRegistry singleton for agent bindings
- setup.py: Pre-configured avatars for 7-agent pipeline

### Judge System (judge/)
- decision.py: JudgmentModel (MCDA) with 4 criteria
- Loads weights from specs/judge_criteria.yaml
- Scores actions [0.0, 1.0] per frame

### Integration (orchestrator/)
- judge_orchestrator.py: JudgeOrchestrator singleton
- Injects avatar personality into agent prompts
- Evaluates agent actions via MCDA

## Agent Bindings (7 agents)

ManagingAgent -> Manager (Engineer)
OrchestrationAgent -> Conductor (Engineer)
ArchitectureAgent -> Architect (Designer)
CoderAgent -> Coder (Engineer)
TesterAgent -> Tester (Engineer)
ResearcherAgent -> Researcher (Designer)
PINNAgent -> Physicist (Engineer)

## Judge Criteria

Safety (1.0): bounds, collisions, overspeed, fuel, stability
Spec Alignment (0.8): acceleration, turning, braking, engine
Player Intent (0.7): objective progress, tactical fit, style
Latency (0.5): execution time, response quality

Formula: overall_score = sum(weight * criterion_score) / sum(weights)

## Integration Pipeline

Request -> Avatar System Context
         -> Agent Generates Response
         -> Judge MCDA Evaluation
         -> ActionScore [0.0, 1.0]
         -> Orchestrator Routes

## Testing

All modules compile. Integration tests pass:
- 7 avatars registered
- 4 criteria loaded from specs
- Correct weights per preset
- JudgeOrchestrator functional

## Files Created

avatars/: __init__.py, avatar.py, registry.py, setup.py
judge/: __init__.py, decision.py
orchestrator/: judge_orchestrator.py
tests/: test_avatar_integration.py

Status: Part E Complete
Version: 1.0.0-avatar-system
Date: 2026-02-12
