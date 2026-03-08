# Phase Space Bifurcation Analysis

Parallel orchestration framework comparing LangGraph and LangChain for multi-agent systems.

## Overview

This module implements two parallel orchestration approaches to observe how different frameworks model the same multi-agent system and where they bifurcate in phase space.

### Frameworks

1. **LangGraph**: Graph-based state machine with explicit conditional routing
2. **LangChain**: Sequential chain with memory-driven context accumulation

## Architecture

```
phase_space/
├── langgraph_orchestrator.py   # StateGraph implementation
├── langchain_orchestrator.py   # SequentialChain implementation
├── bifurcation_analyzer.py     # Parallel execution & analysis
└── requirements.txt            # Dependencies
```

## Usage

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Individual Orchestrators

```python
# LangGraph
from langgraph_orchestrator import run_langgraph_simulation
result = run_langgraph_simulation(steps=100)
print(result['metrics'])

# LangChain
from langchain_orchestrator import run_langchain_simulation
result = run_langchain_simulation(steps=100)
print(result['metrics'])
```

### Run Bifurcation Analysis

```bash
python bifurcation_analyzer.py
```

This will:

1. Execute both orchestrators in parallel
2. Compute trajectory divergence
3. Generate visualization (`phase_space_bifurcation.png`)
4. Create analysis report (`bifurcation_report.md`)

## Metrics

| Metric | Description |
|--------|-------------|
| `decision_entropy` | Shannon entropy of action distributions |
| `trajectory_divergence` | KL divergence between framework paths |
| `safety_violation_rate` | Frequency of SafetyLayer clips |
| `emergence_score` | Kawaii Score + Non-Euclidean Drift |

## Hypothesis

**LangGraph** exhibits more deterministic trajectories due to explicit state management and checkpointing.

**LangChain** shows higher variance from memory-based context accumulation and sequential execution.

## Results

Run the analyzer to observe where the models bifurcate in phase space and how their decision trajectories diverge over time.
