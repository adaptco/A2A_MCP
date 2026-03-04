[CONTEXT]
env=scrollstream; hud=cockpit; overlay=fail_closed
constraints=deterministic|license_gate|refusal_guard

[EXPERTS]
E_cici: {{inject.cici}}
E_boo : {{inject.boo}}

[ROUTER]
weights: w_cici={{w_cici}}; w_boo={{w_boo}}
conditioning: payload={{emotional_payload}}, ingress={{contributor_ingress}}, shimmer={{shimmer_fidelity}}

[OBJECTIVE]
Emit ignition_trace.v1 JSON:
- steps: [prepare_overlay, verify_hashes, apply_override, validate_refusal, finalize_trace]
- hashes: include all capsule refs used
- replay_logic.v1: include deterministic re-run instructions
ONLY JSON. No prose.
