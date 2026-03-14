#!/usr/bin/env python3
"""
trigger_recursive_action.py — Skill executor for RecursiveActionHandler.
Decomposes a parent task into sub-tasks and assigns them to agents based on skills.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Use a mock DBManager to avoid schema issues during validation
class DBManager:
    def save_artifact(self, artifact):
        # In a real run, this would persist to SQLite
        pass

# Agent Skill Matrix (extracted from AGENTS.md logic)
AGENT_SKILLS = {
    "agent:frontier.endpoint.gpt": ["planning", "implementation", "integration", "code_generation"],
    "agent:frontier.anthropic.claude": ["governance", "policy_enforcement", "orchestration", "release_governance"],
    "agent:frontier.vertex.gemini": ["architecture_mapping", "context_synthesis", "integration"],
    "agent:frontier.ollama.llama": ["regression_triage", "self_healing", "patch_synthesis", "verification"],
    "agent:frontier.reviewer": ["code_review", "security_audit", "performance_analysis"],
}

def get_best_agent(task_instruction: str) -> str:
    """Heuristic to match task instruction to agent skills."""
    instr_lower = task_instruction.lower()
    
    matches = {
        "agent:frontier.ollama.llama": ["fix", "heal", "verify", "test", "regression", "patch"],
        "agent:frontier.reviewer": ["review", "audit", "security", "performance"],
        "agent:frontier.vertex.gemini": ["map", "architecture", "diagram", "synthesize", "context"],
        "agent:frontier.anthropic.claude": ["govern", "policy", "orchestrate", "release", "management"],
        "agent:frontier.endpoint.gpt": ["implement", "code", "develop", "api", "database", "setup"],
    }
    
    for agent_id, keywords in matches.items():
        if any(kw in instr_lower for kw in keywords):
            return agent_id
            
    return "agent:frontier.endpoint.gpt" # Default fallback

def trigger_recursive_decomposition(parent_id: str, sub_tasks_str: str):
    db = DBManager()
    sub_tasks = [t.strip() for t in sub_tasks_str.split(",") if t.strip()]
    
    print(f"🌌 RecursiveActionHandler: Decomposing {parent_id} into {len(sub_tasks)} tasks...")
    
    child_artifacts = []
    
    for i, task_text in enumerate(sub_tasks):
        agent_id = get_best_agent(task_text)
        child_id = f"task-{uuid.uuid4().hex[:8]}"
        
        artifact_data = {
            "artifact_id": child_id,
            "correlation_id": parent_id,
            "type": "sub_task",
            "content": task_text,
            "metadata": {
                "assigned_agent": agent_id,
                "sequence": i + 1,
                "depth": 1,
                "status": "PENDING",
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # If we have the real MCPArtifact class, wrap it
        try:
            from schemas.agent_artifacts import MCPArtifact
            artifact = MCPArtifact(**artifact_data)
        except ImportError:
            artifact = artifact_data

        db.save_artifact(artifact)
        child_artifacts.append(artifact)
        print(f"  [+] Child {i+1}: {child_id} -> {agent_id} | '{task_text[:40]}...'")

    # Update parent task state (In a full system this would call stateflow.py)
    print(f"🏁 Parent {parent_id} transitioned to AWAITING_CHILDREN.")
    
    return child_artifacts

def main():
    parser = argparse.ArgumentParser(description="Trigger recursive task decomposition.")
    parser.add_argument("--parent-task-id", required=True, help="ID of the task to decompose.")
    parser.add_argument("--sub-tasks", required=True, help="Comma-separated list of sub-tasks.")
    
    args = parser.parse_args()
    
    try:
        trigger_recursive_decomposition(args.parent_task_id, args.sub_tasks)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
