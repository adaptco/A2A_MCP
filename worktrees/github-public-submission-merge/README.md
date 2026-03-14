## MCP Remote Containers (/mcp)

To merge remote MCP container definitions into this repository, use the `/mcp` contract under `fieldengine-cfo-mcp/mcp` together with the Docker MCP catalog at `mcp_servers/docker_mcp_catalog/docker-mcp-catalog.json`.

### Merge flow

1. Fetch remote updates for the container source repository.
2. Copy or reconcile capability changes into:
   - `fieldengine-cfo-mcp/mcp/server.json`
   - `fieldengine-cfo-mcp/mcp/capabilities.md`
3. If image references changed, update `mcp_servers/docker_mcp_catalog/docker-mcp-catalog.json` in the same commit.
4. Validate JSON formatting and run targeted checks before opening a PR.

### Suggested verification commands

```bash
python -m json.tool fieldengine-cfo-mcp/mcp/server.json >/dev/null
python -m json.tool mcp_servers/docker_mcp_catalog/docker-mcp-catalog.json >/dev/null
python scripts/check_invariants.py
```

### PR scope

Keep MCP container merges focused to metadata, capability docs, and catalog entries so reviewers can audit container provenance and behavior deltas in one place.

## Minimal template you can adapt

- Short window in memory or persistent index (Redis or DB recommended for multi‑process).  
- `envelope_id` + `vanguard_jti` uniqueness enforced.

**Operational Hardening**

Expected behavior:
- `git rev-parse --is-inside-work-tree` returns `true`.
- `git remote -v` lists your configured remote repositories (e.g., `origin`).
- `git fetch <remote-name>` updates remote refs from the specified remote.
- `git log ... <remote-name>/main..<your-branch>` prints commits that are on `<your-branch>` and not on `<remote-name>/main`.

---

## Developer Guide (Core Orchestrator)

**Local Setup**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Run Tests**

```bash
pytest -q
```

**Run Merkle Anchor Locally**

```bash
export WITNESS_LOG_PATH=./witness.ndjson
export ANCHOR_LOG_PATH=./anchor.ndjson
python -m core_orchestrator.services.merkle_anchor
```

**Run Handshake Unit Test Flow**

- Use the test harness in `tests/test_handshake.py` which mocks external keys and writes witness lines to a temp file.

---

## Contribution Guidelines

**Code Style**

- Follow repository linting rules: `black`, `ruff`, `mypy`.
- Keep canonicalization deterministic and avoid nondeterministic fields in receipts.

**Pull Request Requirements**

- All PRs must include tests for new deterministic behavior.
- Schema changes require sample updates and CI schema validation.
- Security changes must include threat model notes and key rotation plan.

**Release Process**

- Anchors produced by CI can be used to create signed release tags.
- Maintain an audit trail of anchor metadata and witness snapshots for each release.

---

**Verified for World OS v1.0.0-foundation**

## GoldenEye AI Arena (Web + MCP)

This repository now includes a lightweight multiplayer-style browser FPS arena artifact and an MCP server for CLI agents/users.

### Web artifact

- Open `public/goldeneye-ai-arena.html` in a browser (or serve `public/` with a static server).
- The arena starts in AI-vs-AI mode (`alpha` vs `bravo`).
- Press `J` to join as a player, then use:
  - `W` move forward
  - `A/D` rotate
  - `Space` fire
- Governance controls in-browser:
  - `I` Inspector (emit compliance beacons)
  - `C` Corrector (remediate drift to invariant)
  - `N` Negotiator (attempt L0→L5 ascension)

### MCP server

Run the dedicated MCP server:

```bash
python server/goldeneye_mcp_server.py
```

Available MCP tools:

- `create_match` → creates a match and returns `match_id`
- `join_match` → adds a user-controlled player in an existing match
- `set_player_input` → sends input booleans (`forward`, `left`, `right`, `fire`)
- `tick_match` → advances simulation ticks
- `inspector_validate` → emits attestation beacons and compliance receipts
- `corrector_remediate` → restores drifted agents to invariants
- `negotiator_advance_level` → gates level advancement based on receipts
- `set_agent_drift` → helper for injecting drift in tests/admin scenarios
- `get_match_state` → returns match state + compliance payload

### API JSON shape for A2A backend integration

`get_match_state` returns a JSON envelope suitable for downstream A2A/MCP adapters:

```json
{
  "status": "ok",
  "match": {
    "match_id": "arena-1234abcd",
    "width": 960,
    "height": 540,
    "tick": 42,
    "level": 2,
    "required_material": "Obsidian Black",
    "agents": {
      "alpha": {"name": "alpha", "x": 123.4, "y": 88.1, "heading": 1.1, "hp": 100, "score": 0, "symmetry_spokes": 5, "material": "Obsidian Black"}
    },
    "beacons": [{"beacon_id": "beacon-a1b2c3d4", "status": "green"}]
  }
}
```
