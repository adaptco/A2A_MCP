"""
Universal LLM Router — agents/runner.py

Entrypoint for all agent task execution inside GitHub Actions.
Reads TASK_ID, AGENT_CARD, LLM_TARGET from env, loads the agent's
system prompt, calls the appropriate LLM, and writes output to
artifacts/{task_id}/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# LLM Adapter — single interface, any backend
# ---------------------------------------------------------------------------

LLM_TARGET = os.environ.get("LLM_TARGET", "gemini")


def call_llm(system_prompt: str, user_message: str) -> str:
    """Route to the correct LLM backend based on LLM_TARGET env var."""
    if LLM_TARGET == "claude":
        return _call_claude(system_prompt, user_message)
    elif LLM_TARGET == "openai":
        return _call_openai(system_prompt, user_message)
    elif LLM_TARGET == "gemini":
        return _call_gemini(system_prompt, user_message)
    elif LLM_TARGET == "ollama":
        return _call_ollama(system_prompt, user_message)
    else:
        raise ValueError(f"Unknown LLM target: {LLM_TARGET}")


def _call_claude(system_prompt: str, user_message: str) -> str:
    """Call Anthropic Claude API."""

    api_key = os.environ["ANTHROPIC_API_KEY"]
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _call_openai(system_prompt: str, user_message: str) -> str:
    """Call OpenAI ChatCompletion API."""

    api_key = os.environ["OPENAI_API_KEY"]
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 4096,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini(system_prompt: str, user_message: str) -> str:
    """Call Google Gemini API."""
    api_key = os.environ["GEMINI_API_KEY"]
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    resp = httpx.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(system_prompt: str, user_message: str) -> str:
    """Call local Ollama instance."""

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    resp = httpx.post(
        f"{host}/api/generate",
        json={
            "model": os.environ.get("OLLAMA_MODEL", "mistral"),
            "system": system_prompt,
            "prompt": user_message,
            "stream": False,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["response"]


# ---------------------------------------------------------------------------
# Agent Task Runner — GitHub Actions entrypoint
# ---------------------------------------------------------------------------


def load_system_prompt(agent_card_path: str) -> str:
    """Load the system prompt for an agent from its prompts/ directory."""
    agent_dir = Path(agent_card_path).parent
    prompt_file = agent_dir / "prompts" / "system.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return f"You are a coding agent executing task as defined by {agent_card_path}."


def run_task(tid: str, agent_card_path: str, user_prompt: str = "") -> str:
    """Execute a single agent task and write output to artifacts/."""
    system_prompt = load_system_prompt(agent_card_path)

    # Read user prompt from env or file
    if not user_prompt:
        prompt_file = Path("artifacts") / tid / "input.txt"
        if prompt_file.exists():
            user_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            user_prompt = os.environ.get("USER_PROMPT", "Execute the assigned task.")

    # Call LLM
    print(f"[runner] Task={tid} Agent={agent_card_path} LLM={LLM_TARGET}")
    result = call_llm(system_prompt, user_prompt)

    # Write output artifact
    output_dir = Path("artifacts") / tid
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "output.txt"
    output_file.write_text(result, encoding="utf-8")

    # Write receipt
    receipt_dir = Path("receipts")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "task_id": tid,
        "agent_card": agent_card_path,
        "llm_target": LLM_TARGET,
        "status": "completed",
        "output_path": str(output_file),
    }
    receipt_file = receipt_dir / f"{tid}.json"
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    print(f"[runner] ✅ Task {tid} completed. Output: {output_file}")
    return result


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    task_id = os.environ.get("TASK_ID", "T-000")
    agent_card = os.environ.get("AGENT_CARD", "agents/runner.py")
    prompt = os.environ.get("USER_PROMPT", "")

    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    if len(sys.argv) > 2:
        agent_card = sys.argv[2]

    run_task(task_id, agent_card, prompt)
