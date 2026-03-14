"""MCP server for GoldenEye AI Arena with governance/compliance topology.

Exposes playable match lifecycle tools and a compliance layer that models:
- Inspector: validates symmetry/material invariants and emits attestation beacons
- Corrector: remediates non-compliant agents back to invariants
- Negotiator: gates level progression using compliance receipts
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import sys
from dataclasses import dataclass, field
from typing import Any, Sequence
from uuid import uuid4

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, ImageContent, Resource, TextContent, Tool

LOGGER = logging.getLogger("goldeneye-ai-arena-mcp")


@dataclass(slots=True)
class AgentState:
    name: str
    x: float
    y: float
    heading: float
    hp: int = 100
    score: int = 0
    symmetry_spokes: int = 5
    material: str = "Obsidian Black"


@dataclass(slots=True)
class ComplianceBeacon:
    beacon_id: str
    tick: int
    agent_name: str
    status: str
    reason: str
    coordinate: dict[str, float]


@dataclass(slots=True)
class MatchState:
    match_id: str
    width: int = 960
    height: int = 540
    tick: int = 0
    level: int = 0
    required_material: str = "Obsidian Black"
    agents: dict[str, AgentState] = field(default_factory=dict)
    player_inputs: dict[str, dict[str, bool]] = field(default_factory=dict)
    beacons: list[ComplianceBeacon] = field(default_factory=list)


_MATCHES: dict[str, MatchState] = {}


def _spawn_agent(name: str, width: int, height: int) -> AgentState:
    return AgentState(
        name=name,
        x=random.uniform(30, width - 30),
        y=random.uniform(30, height - 30),
        heading=random.uniform(0, math.pi * 2),
    )


def create_match(seed: int | None = None) -> dict[str, Any]:
    if seed is not None:
        random.seed(seed)

    match_id = f"arena-{uuid4().hex[:8]}"
    state = MatchState(match_id=match_id)
    state.agents["alpha"] = _spawn_agent("alpha", state.width, state.height)
    state.agents["bravo"] = _spawn_agent("bravo", state.width, state.height)
    _MATCHES[match_id] = state
    return {"status": "ok", "match_id": match_id}


def join_match(match_id: str, player_name: str = "player") -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}
    if player_name in state.agents:
        return {"status": "error", "message": "player already exists"}

    state.agents[player_name] = _spawn_agent(player_name, state.width, state.height)
    state.player_inputs[player_name] = {"forward": False, "left": False, "right": False, "fire": False}
    return {"status": "ok", "player": player_name}


def set_player_input(match_id: str, player_name: str, controls: dict[str, bool]) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}
    if player_name not in state.player_inputs:
        return {"status": "error", "message": "player not controllable"}

    for key in ("forward", "left", "right", "fire"):
        state.player_inputs[player_name][key] = bool(controls.get(key, False))
    return {"status": "ok"}


def _update_agent_motion(agent: AgentState, controls: dict[str, bool], width: int, height: int) -> None:
    if controls.get("left"):
        agent.heading -= 0.1
    if controls.get("right"):
        agent.heading += 0.1
    if controls.get("forward"):
        agent.x += math.cos(agent.heading) * 3
        agent.y += math.sin(agent.heading) * 3

    agent.x = max(10, min(width - 10, agent.x))
    agent.y = max(10, min(height - 10, agent.y))


def _ai_controls(agent: AgentState, other: AgentState) -> dict[str, bool]:
    target_angle = math.atan2(other.y - agent.y, other.x - agent.x)
    delta = (target_angle - agent.heading + math.pi) % (2 * math.pi) - math.pi
    return {
        "forward": True,
        "left": delta < -0.2,
        "right": delta > 0.2,
        "fire": abs(delta) < 0.15,
    }


def _distance(a: AgentState, b: AgentState) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def tick_match(match_id: str, steps: int = 1) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}

    for _ in range(max(1, steps)):
        state.tick += 1

        names = list(state.agents)
        if len(names) < 2:
            continue

        for name, agent in state.agents.items():
            if name in state.player_inputs:
                controls = state.player_inputs[name]
            else:
                opponents = [state.agents[n] for n in names if n != name and state.agents[n].hp > 0]
                if not opponents:
                    continue
                nearest = min(opponents, key=lambda candidate: _distance(agent, candidate))
                controls = _ai_controls(agent, nearest)

            _update_agent_motion(agent, controls, state.width, state.height)

            if controls.get("fire"):
                opponents = [state.agents[n] for n in names if n != name and state.agents[n].hp > 0]
                if not opponents:
                    continue
                nearest = min(opponents, key=lambda candidate: _distance(agent, candidate))
                if _distance(agent, nearest) < 100:
                    nearest.hp = max(0, nearest.hp - 5)
                    if nearest.hp == 0:
                        agent.score += 1
                        nearest.hp = 100
                        nearest.x = random.uniform(30, state.width - 30)
                        nearest.y = random.uniform(30, state.height - 30)

    return {"status": "ok", "tick": state.tick}


def inspector_validate(match_id: str) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}

    receipts: list[dict[str, Any]] = []
    for agent in state.agents.values():
        symmetry_ok = agent.symmetry_spokes == 5
        material_ok = agent.material == state.required_material
        compliant = symmetry_ok and material_ok
        reason = "C5_SYMMETRY + material invariant satisfied" if compliant else (
            "symmetry break" if not symmetry_ok else "material drift"
        )
        beacon = ComplianceBeacon(
            beacon_id=f"beacon-{uuid4().hex[:8]}",
            tick=state.tick,
            agent_name=agent.name,
            status="green" if compliant else "red",
            reason=reason,
            coordinate={"x": round(agent.x, 2), "y": round(agent.y, 2)},
        )
        state.beacons.append(beacon)
        receipts.append(
            {
                "agent": agent.name,
                "compliant": compliant,
                "symmetry_spokes": agent.symmetry_spokes,
                "material": agent.material,
                "beacon_id": beacon.beacon_id,
                "status": beacon.status,
            }
        )

    return {
        "status": "ok",
        "match_id": state.match_id,
        "tick": state.tick,
        "receipts": receipts,
        "all_compliant": all(item["compliant"] for item in receipts),
    }


def corrector_remediate(match_id: str, target_agent: str | None = None) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}

    updated: list[str] = []
    names = [target_agent] if target_agent else list(state.agents)
    for name in names:
        if name not in state.agents:
            continue
        agent = state.agents[name]
        changed = False
        if agent.symmetry_spokes != 5:
            agent.symmetry_spokes = 5
            changed = True
        if agent.material != state.required_material:
            agent.material = state.required_material
            changed = True
        if changed:
            updated.append(name)

    return {
        "status": "ok",
        "match_id": state.match_id,
        "remediated_agents": updated,
        "count": len(updated),
    }


def negotiator_advance_level(match_id: str, target_level: int) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}

    report = inspector_validate(match_id)
    if report.get("status") != "ok":
        return report
    if not report["all_compliant"]:
        return {
            "status": "blocked",
            "message": "level advancement denied until all agents are compliant",
            "current_level": state.level,
            "target_level": target_level,
        }

    state.level = max(state.level, target_level)
    return {
        "status": "ok",
        "message": "level advanced",
        "new_level": state.level,
        "receipts": report["receipts"],
    }


def set_agent_drift(
    match_id: str,
    agent_name: str,
    symmetry_spokes: int | None = None,
    material: str | None = None,
) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}
    agent = state.agents.get(agent_name)
    if not agent:
        return {"status": "error", "message": "agent not found"}

    if symmetry_spokes is not None:
        agent.symmetry_spokes = int(symmetry_spokes)
    if material is not None:
        agent.material = material
    return {"status": "ok", "agent": agent_name}


def get_match_state(match_id: str) -> dict[str, Any]:
    state = _MATCHES.get(match_id)
    if not state:
        return {"status": "error", "message": "match not found"}

    return {
        "status": "ok",
        "match": {
            "match_id": state.match_id,
            "width": state.width,
            "height": state.height,
            "tick": state.tick,
            "level": state.level,
            "required_material": state.required_material,
            "agents": {
                key: {
                    "name": agent.name,
                    "x": round(agent.x, 2),
                    "y": round(agent.y, 2),
                    "heading": round(agent.heading, 3),
                    "hp": agent.hp,
                    "score": agent.score,
                    "symmetry_spokes": agent.symmetry_spokes,
                    "material": agent.material,
                }
                for key, agent in state.agents.items()
            },
            "beacons": [
                {
                    "beacon_id": beacon.beacon_id,
                    "tick": beacon.tick,
                    "agent_name": beacon.agent_name,
                    "status": beacon.status,
                    "reason": beacon.reason,
                    "coordinate": beacon.coordinate,
                }
                for beacon in state.beacons[-30:]
            ],
        },
    }


app = Server("goldeneye-ai-arena-mcp")


@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="goldeneye://matches",
            name="GoldenEye AI Arena matches",
            mimeType="application/json",
            description="Lists active GoldenEye AI Arena matches and compliance beacons",
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str | bytes:
    if uri != "goldeneye://matches":
        raise ValueError(f"Unknown resource: {uri}")
    payload = {
        "matches": [get_match_state(match_id) for match_id in _MATCHES],
        "count": len(_MATCHES),
    }
    return json.dumps(payload, indent=2)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_match",
            description="Create a new GoldenEye AI vs AI match.",
            inputSchema={"type": "object", "properties": {"seed": {"type": "integer"}}},
        ),
        Tool(
            name="join_match",
            description="Join a match with a user-controlled player.",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "player_name": {"type": "string"},
                },
                "required": ["match_id"],
            },
        ),
        Tool(
            name="set_player_input",
            description="Set control booleans for a player in a match.",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "player_name": {"type": "string"},
                    "controls": {
                        "type": "object",
                        "properties": {
                            "forward": {"type": "boolean"},
                            "left": {"type": "boolean"},
                            "right": {"type": "boolean"},
                            "fire": {"type": "boolean"},
                        },
                    },
                },
                "required": ["match_id", "player_name", "controls"],
            },
        ),
        Tool(
            name="tick_match",
            description="Advance simulation by one or many ticks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "steps": {"type": "integer", "minimum": 1, "maximum": 120},
                },
                "required": ["match_id"],
            },
        ),
        Tool(
            name="inspector_validate",
            description="Inspector role: emit attestation beacons and compliance receipts.",
            inputSchema={
                "type": "object",
                "properties": {"match_id": {"type": "string"}},
                "required": ["match_id"],
            },
        ),
        Tool(
            name="corrector_remediate",
            description="Corrector role: repair symmetry/material drift for one or all agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "target_agent": {"type": "string"},
                },
                "required": ["match_id"],
            },
        ),
        Tool(
            name="negotiator_advance_level",
            description="Negotiator role: gate level progression based on compliance receipts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "target_level": {"type": "integer", "minimum": 0, "maximum": 5},
                },
                "required": ["match_id", "target_level"],
            },
        ),
        Tool(
            name="set_agent_drift",
            description="Testing/admin helper to inject drift for validation and remediation loops.",
            inputSchema={
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "agent_name": {"type": "string"},
                    "symmetry_spokes": {"type": "integer", "minimum": 1, "maximum": 12},
                    "material": {"type": "string"},
                },
                "required": ["match_id", "agent_name"],
            },
        ),
        Tool(
            name="get_match_state",
            description="Read full match/game/compliance state.",
            inputSchema={
                "type": "object",
                "properties": {"match_id": {"type": "string"}},
                "required": ["match_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    args = arguments or {}
    if name == "create_match":
        result = create_match(seed=args.get("seed"))
    elif name == "join_match":
        result = join_match(args["match_id"], args.get("player_name", "player"))
    elif name == "set_player_input":
        result = set_player_input(args["match_id"], args["player_name"], args["controls"])
    elif name == "tick_match":
        result = tick_match(args["match_id"], int(args.get("steps", 1)))
    elif name == "inspector_validate":
        result = inspector_validate(args["match_id"])
    elif name == "corrector_remediate":
        result = corrector_remediate(args["match_id"], args.get("target_agent"))
    elif name == "negotiator_advance_level":
        result = negotiator_advance_level(args["match_id"], int(args["target_level"]))
    elif name == "set_agent_drift":
        result = set_agent_drift(
            args["match_id"],
            args["agent_name"],
            args.get("symmetry_spokes"),
            args.get("material"),
        )
    elif name == "get_match_state":
        result = get_match_state(args["match_id"])
    else:
        raise ValueError(f"Unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(result))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    asyncio.run(main())
