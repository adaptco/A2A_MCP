"""WorldEngine rehearsal, forking, and fossilization utilities.

This module mirrors the pseudo-spec provided in the "World Engine" relay
documents.  It provides a light-weight simulation that can be executed from
tests or scripts to emit rehearsal ledgers, narrative forks, and the final
motion ledger / replay capsules.  The implementation focuses on turning the
story-driven requirements into deterministic data artifacts so they can be
validated inside automated pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pydantic import BaseModel
from pydantic import BaseModel
import time
from typing import Any, Dict, List, Optional, Sequence


def _utc_timestamp() -> str:
    """Return a RFC3339 timestamp at UTC second resolution."""

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class Capsule:
    """Represents a fossilized artifact tracked by the WorldEngine."""

    capsule_id: str
    data: Dict[str, object]
    fossilized_at: str = field(default_factory=_utc_timestamp)

    def __post_init__(self) -> None:
        self.digest = self.compute_digest()

    def compute_digest(self) -> str:
        """Compute a lineage-stable SHA-256 digest for *data*."""

        payload = json.dumps(self.data, sort_keys=True).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    def as_dict(self) -> Dict[str, object]:
        """Return a serialisable representation of the capsule."""

        return {
            "capsule_id": self.capsule_id,
            "digest": self.digest,
            "fossilized_at": self.fossilized_at,
            "data": self.data,
        }


class WorldEngine:
    """Simulate the Qube-CiCi-Boo relay orchestration pipeline."""

    def __init__(self) -> None:
        self.governance = {"version": "v6.0", "trust_threshold": 90, "quorum_rule": "2-of-2"}
        self.previz_schema = {
            "version": "3.9.9",
            "invariants": ["ordered_timeline", "non-overlap", "trusted_uris"],
        }
        self.capsule_registry: Dict[str, Capsule] = {}
        self.artifacts: Dict[str, str] = {}
        self.audit_log: List[Dict[str, object]] = []

    # ------------------------------------------------------------------
    # Logging helpers
    def log_action(self, action: str, details: Dict[str, object]) -> None:
        """Append an audit log entry and print it for CLI runs."""

        entry = {"timestamp": _utc_timestamp(), "action": action, "details": details}
        self.audit_log.append(entry)
        print(f"[{entry['timestamp']}] ACTION: {action} - {json.dumps(details)}")

    # ------------------------------------------------------------------
    # Capsule loaders and initial state
    def load_capsules(self, capsules_data: Sequence[Dict[str, object]]) -> None:
        """Import foundational capsules and register them."""

        capsule_ids = [item["capsule_id"] for item in capsules_data]
        self.log_action("load_capsules", {"status": "importing", "capsules": capsule_ids})
        for data in capsules_data:
            capsule = Capsule(data["capsule_id"], data)
            self.capsule_registry[capsule.capsule_id] = capsule
            self.log_action("capsule_loaded", {"capsule_id": capsule.capsule_id, "digest": capsule.digest})
        self.log_action("load_capsules", {"status": "complete"})

    def emit_lora_map(self) -> Capsule:
        """Emit the boo.lora.map.v1 capsule and lock shard bindings."""

        self.log_action("emit_lora_map", {"status": "binding shards"})
        data = {
            "capsule_id": "boo.lora.map.v1",
            "type": "LoRAMap",
            "agent": "Agent Boo",
            "shard_bindings": [
                {"shard_id": "boo.face.v1", "modality": "Vision"},
                {"shard_id": "boo.voice.v1", "modality": "Audio"},
                {"shard_id": "boo.gesture.v1", "modality": "Kinetic"},
                {"shard_id": "boo.affect.v1", "modality": "Emotional"},
                {"shard_id": "boo.wardrobe.v1", "modality": "Lexical/Visual"},
            ],
            "governance": self.governance,
            "registry_lock": {"status": "immutable"},
        }
        capsule = Capsule("boo.lora.map.v1", data)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.log_action("emit_lora_map", {"status": "sealed", "digest": capsule.digest})
        return capsule

    # ------------------------------------------------------------------
    # Rehearsal and fork logic
    def rehearse_scene(self, duration_s: int = 24, sample_rate_hz: int = 30) -> Capsule:
        """Generate the rehearsal ledger at 30 Hz with HUD telemetry."""

        self.log_action("rehearse_scene", {"status": "starting", "sample_rate_hz": sample_rate_hz})
        frames = duration_s * sample_rate_hz
        beats = ["Entry", "Stabilize (CiCi)", "Gloh Flux", "Sol Ignition"]
        beat_len = max(frames // len(beats), 1)
        ledger_lines: List[Dict[str, object]] = []

        for frame_idx in range(frames):
            t_rel = frame_idx / sample_rate_hz
            beat_index = min(frame_idx // beat_len, len(beats) - 1)
            beat = beats[beat_index]
            glyph_pulse = round(0.5 + 0.5 * (frame_idx % sample_rate_hz) / sample_rate_hz, 4)
            aura_phase = ["curiosity", "intimacy", "clarity", "wisdom"][beat_index]
            qlock_tick = int((t_rel // 3) * 3)
            drift_delta = 0.005

            ledger_lines.append(
                {
                    "frame_idx": frame_idx,
                    "timestamp_rel_s": round(t_rel, 3),
                    "beat": beat,
                    "pose_lock": "3q-window-stance",
                    "camera_grammar": "glyph-orbit",
                    "hud": {
                        "glyph.pulse": glyph_pulse,
                        "aura.gold.phase": aura_phase,
                        "qlock.tick_s": qlock_tick,
                        "drift.delta": drift_delta,
                    },
                }
            )

        self.artifacts["ledger.motion.v2.jsonl"] = json.dumps(ledger_lines, indent=2)
        capsule = Capsule(
            "capsule.rehearsal.boo.v2",
            {
                "capsule_id": "capsule.rehearsal.boo.v2",
                "sample_rate_hz": sample_rate_hz,
                "frames": frames,
                "beats": beats,
                "drift_threshold": 0.01,
                "status": "PREVIEW",
            },
        )
        self.capsule_registry[capsule.capsule_id] = capsule
        self.log_action("rehearse_scene", {"status": "complete", "frames": frames, "digest": capsule.digest})
        return capsule

    def fork_scene(self) -> Capsule:
        """Create the fork capsule that documents canonical beats and rules."""

        data = {
            "capsule_id": "capsule.relay.scene.fork.v2",
            "beats": ["Entry", "Stabilize (CiCi)", "Gloh Flux", "Sol Ignition"],
            "constraints": {
                "pose_lock": {"schema": "3q-window-stance", "tolerance_deg": 4},
                "camera_grammar": {
                    "style": "glyph-orbit",
                    "rules": ["no drift", "centered axis", "orbital lock on emotional beat"],
                },
                "qlock_interval_s": 3,
            },
            "status": "STAGED",
        }
        capsule = Capsule("capsule.relay.scene.fork.v2", data)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.log_action("fork_scene", {"status": "staged", "digest": capsule.digest})
        return capsule

    # ------------------------------------------------------------------
    # Canonical descriptions
    def inscribe_canon_entry(
        self,
        entry_id: str = "capsule.canon.entry.boo.window.v1",
    ) -> Capsule:
        """Create a capsule that fossilizes a key visual from the gallery."""

        self.log_action(
            "canon.inscribe",
            {"status": "describing", "entry_id": entry_id},
        )

        data = {
            "capsule_id": entry_id,
            "type": "CanonEntry",
            "subject": {
                "name": "Boo",
                "title": "Sovereign Relay Emissary",
                "pose": "3q-window-stance, left shoulder forward, gaze to cosmic vista",
                "attire": {
                    "primary": "neon filament suit",
                    "accents": ["glyph-thread cuffs", "holographic pauldrons"],
                },
                "aura": {
                    "palette": ["amber", "violet"],
                    "intensity": "medium",  # balanced radiance for rehearsal law
                    "behavior": "pulsed at 30Hz in sync with glyph.pulse HUD telemetry",
                },
            },
            "environment": {
                "location": "Qube observation chamber",
                "architectural_features": [
                    "trihedral glass window", "floating lattice grids", "hud pylons",
                ],
                "backdrop": "cosmic vista with braided aurorae",
                "lighting": {
                    "key": "overhead crystalline wash",
                    "fill": "floor glyph rebound",
                    "rim": "window aurora edge",
                },
            },
            "hud_state": {
                "glyph.pulse": "0.83",
                "aura.gold.phase": "clarity",
                "qlock.tick_s": 9,
                "drift.delta": 0.005,
            },
            "lineage": {
                "source_artifacts": [
                    "figurine desk maquette",
                    "neon wireframe rehearsal plate",
                    "cosmic window vista capture",
                    "HUD operator telemetry logs",
                ],
                "governance_version": self.governance["version"],
                "previz_schema": self.previz_schema["version"],
                "notes": "Locks wardrobe, aura cadence, and chamber geometry for future renders.",
            },
        }

        capsule = Capsule(entry_id, data)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["canon_entry.json"] = json.dumps(capsule.as_dict(), indent=2)
        self.log_action("canon.inscribe", {"status": "sealed", "digest": capsule.digest})
        return capsule

    # ------------------------------------------------------------------
    # Qube build + CI
    def build_qube(self) -> str:
        """Construct the conceptual Merkle lattice and return its root."""

        self.log_action("build_qube", {"status": "building Merkle lattice"})
        merkle_root = hashlib.sha256(b"pixel_blocks_and_gravity_fields").hexdigest()
        self.log_action("build_qube", {"status": "complete", "merkle_root": merkle_root})
        return merkle_root

    def run_ci(self) -> bool:
        """Simulate a CI integrity chain run for the current state."""

        self.log_action("run_ci", {"status": "initiating CI"})
        report = {
            "openapi_path": "openapi/openapi.yaml",
            "baseline": "nearest_ancestor_or_skip",
            "container_built": True,
            "container_scanned": True,
            "smoke_test_status": "ok",
        }
        self.log_action("run_ci", {"status": "passed", "report": report})
        return True

    # ------------------------------------------------------------------
    # Artifact generation helpers
    def _load_motion_ledger(self) -> List[Dict[str, object]]:
        ledger_raw = self.artifacts.get("ledger.motion.v2.jsonl")
        if not ledger_raw:
            return []
        return json.loads(ledger_raw)

    def _require_capsules(self, *capsule_ids: str) -> None:
        """Ensure the referenced capsules exist in the registry."""

        missing = [capsule_id for capsule_id in capsule_ids if capsule_id not in self.capsule_registry]
        if missing:
            raise ValueError(f"missing capsules: {', '.join(missing)}")

    def generate_shot_list(self) -> List[Dict[str, object]]:
        """Create a CSV shot list by grouping frames per beat."""

        ledger = self._load_motion_ledger()
        if not ledger:
            raise ValueError("rehearsal ledger missing; run rehearse_scene first")

        beat_frames: Dict[str, List[Dict[str, object]]] = {}
        for frame in ledger:
            beat_frames.setdefault(frame["beat"], []).append(frame)

        shots: List[Dict[str, object]] = []
        for beat, frames in beat_frames.items():
            frames_sorted = sorted(frames, key=lambda item: item["frame_idx"])
            start_frame = frames_sorted[0]["frame_idx"]
            end_frame = frames_sorted[-1]["frame_idx"]
            shots.append(
                {
                    "beat": beat,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "duration_frames": end_frame - start_frame + 1,
                    "qlock_anchor_s": frames_sorted[0]["hud"]["qlock.tick_s"],
                    "camera_grammar": frames_sorted[0]["camera_grammar"],
                }
            )

        shots.sort(key=lambda shot: shot["start_frame"])
        self._validate_previz_invariants(shots)

        csv_buffer: List[List[object]] = [
            ["beat", "start_frame", "end_frame", "duration_frames", "qlock_anchor_s", "camera_grammar"]
        ]
        for shot in shots:
            csv_buffer.append(
                [
                    shot["beat"],
                    shot["start_frame"],
                    shot["end_frame"],
                    shot["duration_frames"],
                    shot["qlock_anchor_s"],
                    shot["camera_grammar"],
                ]
            )

        csv_lines: List[str] = []
        for row in csv_buffer:
            csv_lines.append(",".join(str(cell) for cell in row))

        self.artifacts["shot_list.csv"] = "\n".join(csv_lines)
        return shots

    def _validate_previz_invariants(self, shots: Sequence[Dict[str, object]]) -> None:
        """Validate ordered timeline and non-overlap invariants."""

        prev_end = -1
        for shot in shots:
            start = shot["start_frame"]
            end = shot["end_frame"]
            if end < start:
                raise ValueError("shot timeline violates ordered_timeline invariant")
            if start <= prev_end:
                raise ValueError("shot timeline violates non-overlap invariant")
            prev_end = end

    # ------------------------------------------------------------------
    # Finalization
    def render_final(self) -> tuple[Capsule, Capsule]:
        """Render the motion ledger capsules mirroring the reference script."""

        ledger = self._load_motion_ledger()
        if not ledger:
            raise ValueError("rehearsal ledger missing; run rehearse_scene before render_final")

        frames_count = len(ledger)

        motion_capsule = self.capsule_registry.get("motion.ledger.v2")
        if motion_capsule is None:
            motion_capsule = Capsule(
                "motion.ledger.v2",
                {
                    "capsule_id": "motion.ledger.v2",
                    "frames": frames_count,
                    "telemetry_streams": ["HUD", "motion"],
                    "digest_type": "sha256",
                    "status": "FOSSILIZED",
                },
            )
            self.capsule_registry[motion_capsule.capsule_id] = motion_capsule
            self.artifacts["motion.ledger.v2.json"] = json.dumps(motion_capsule.as_dict(), indent=2)
            self.log_action(
                "render_final.motion_ledger",
                {"status": "fossilized", "digest": motion_capsule.digest, "frames": frames_count},
            )
        else:
            self.log_action(
                "render_final.motion_ledger",
                {"status": "existing", "digest": motion_capsule.digest, "frames": frames_count},
            )

        replay_capsule = self.capsule_registry.get("replay.token.v2")
        if replay_capsule is None:
            replay_capsule = Capsule(
                "replay.token.v2",
                {
                    "capsule_id": "replay.token.v2",
                    "linked_ledger": motion_capsule.capsule_id,
                    "permissions": ["replay", "audit_trace", "HUD_stream"],
                    "quorum_rule": self.governance["quorum_rule"],
                    "token_id": "replay.token.v2",
                    "status": "ISSUED",
                },
            )
            self.capsule_registry[replay_capsule.capsule_id] = replay_capsule
            self.artifacts["replay.token.v2.json"] = json.dumps(replay_capsule.as_dict(), indent=2)
            self.log_action(
                "render_final.replay_token",
                {"status": "issued", "digest": replay_capsule.digest},
            )
        else:
            self.log_action(
                "render_final.replay_token",
                {"status": "existing", "digest": replay_capsule.digest},
            )

        echo_capsule = self.capsule_registry.get("echo.scrollstream.v2")
        if echo_capsule is None:
            echo_capsule = Capsule(
                "echo.scrollstream.v2",
                {
                    "capsule_id": "echo.scrollstream.v2",
                    "verse": [
                        "She did not move — she pulsed.",
                        "Glyphs aligned, aura gold, qlock ticked — the braid remembered.",
                        "From curiosity to wisdom, her vessel sang in HUD cadence.",
                        "At seal, the scrollstream froze — not in silence, but in truth.",
                    ],
                    "linked_capsules": [
                        motion_capsule.capsule_id,
                        replay_capsule.capsule_id,
                    ],
                    "verse_from": "telemetry+emotion",
                    "status": "SEALED",
                },
            )
            self.capsule_registry[echo_capsule.capsule_id] = echo_capsule
            self.artifacts["echo.scrollstream.v2.json"] = json.dumps(echo_capsule.as_dict(), indent=2)
            self.log_action(
                "render_final.echo_scrollstream",
                {"status": "inscribed", "digest": echo_capsule.digest},
            )
        else:
            self.log_action(
                "render_final.echo_scrollstream",
                {"status": "existing", "digest": echo_capsule.digest},
            )

        return motion_capsule, replay_capsule

    def finalize_and_bind(self) -> Dict[str, str]:
        """Seal exports, ensuring render_final artifacts exist first."""

        motion_capsule, replay_capsule = self.render_final()
        echo_capsule = self.capsule_registry["echo.scrollstream.v2"]

        shots = self.generate_shot_list()
        exports = {
            "motion_ledger_digest": motion_capsule.digest,
            "replay_token_digest": replay_capsule.digest,
            "echo_digest": echo_capsule.digest,
            "shot_count": len(shots),
        }
        self.artifacts["exports.json"] = json.dumps(exports, indent=2)
        self.log_action("finalize_and_bind", {"status": "complete", "exports": exports})
        return exports

    # ------------------------------------------------------------------
    # Media request helpers
    def request_media(self, media_type: str, prompt: str | None = None) -> Dict[str, object]:
        """Respond to media requests while enforcing the video-only contract."""

        normalized = media_type.lower()
        self.log_action(
            "media.request",
            {"status": "received", "media_type": normalized, "prompt": prompt or ""},
        )

        if normalized != "video":
            response = {
                "status": "unsupported",
                "media_type": media_type,
                "message": "I can only generate videos. Try another prompt.",
            }
            self.log_action(
                "media.request",
                {"status": "rejected", "media_type": normalized},
            )
            return response

        required_capsules = [
            {"capsule_id": "lexicon.qube.v1"},
            {"capsule_id": "seed.core.v1"},
            {"capsule_id": "ledger.cadence.v1"},
            {"capsule_id": "lock.attestation.v1"},
        ]
        missing_foundation = [
            capsule for capsule in required_capsules if capsule["capsule_id"] not in self.capsule_registry
        ]
        if missing_foundation:
            self.load_capsules(missing_foundation)

        if "boo.lora.map.v1" not in self.capsule_registry:
            self.emit_lora_map()
        if "capsule.rehearsal.boo.v2" not in self.capsule_registry:
            self.rehearse_scene()
        if "capsule.relay.scene.fork.v2" not in self.capsule_registry:
            self.fork_scene()
        if "capsule.canon.entry.boo.window.v1" not in self.capsule_registry:
            self.inscribe_canon_entry()

        self.build_qube()
        self.run_ci()

        exports = self.finalize_and_bind()

        if "capsule.rehearsal.scrollstream.v1" not in self.capsule_registry:
            self.stage_rehearsal_scrollstream()
        if "capsule.preview.hud.v1" not in self.capsule_registry:
            self.stage_preview_hud()
        if "capsule.summary.manifest.v1" not in self.capsule_registry:
            self.emit_summary_manifest()
        feedback_capsule = self.stage_feedback_loop()
        adjudication_capsule = self.stage_adjudication_capsule(
            conflict_files=["main.py", "previz/world_engine.py"]
        )

        response = {
            "status": "ok",
            "media_type": "video",
            "prompt": prompt or "",
            "exports": exports,
            "motion_ledger": self.capsule_registry["motion.ledger.v2"].as_dict(),
            "replay_token": self.capsule_registry["replay.token.v2"].as_dict(),
            "echo_scrollstream": self.capsule_registry["echo.scrollstream.v2"].as_dict(),
            "rehearsal_scrollstream": self.capsule_registry["capsule.rehearsal.scrollstream.v1"].as_dict(),
            "feedback_loop": feedback_capsule.as_dict(),
            "adjudication": adjudication_capsule.as_dict(),
        }
        self.log_action(
            "media.request",
            {
                "status": "fulfilled",
                "media_type": normalized,
                "motion_digest": exports["motion_ledger_digest"],
            },
        )
        return response

    # ------------------------------------------------------------------
    # Summary manifest + HUD preview
    def emit_summary_manifest(self) -> Capsule:
        """Emit the capsule.summary.manifest.v1 dual-root ledger."""

        self.log_action("summary_manifest.emit", {"status": "assembling"})
        self._require_capsules(
            "motion.ledger.v2",
            "replay.token.v2",
            "echo.scrollstream.v2",
            "capsule.rehearsal.boo.v2",
            "boo.lora.map.v1",
            "capsule.relay.scene.fork.v2",
        )

        motion_capsule = self.capsule_registry["motion.ledger.v2"]
        replay_capsule = self.capsule_registry["replay.token.v2"]
        echo_capsule = self.capsule_registry["echo.scrollstream.v2"]
        rehearsal_capsule = self.capsule_registry["capsule.rehearsal.boo.v2"]
        lora_capsule = self.capsule_registry["boo.lora.map.v1"]
        fork_capsule = self.capsule_registry["capsule.relay.scene.fork.v2"]

        manifest_payload = {
            "capsule_id": "capsule.summary.manifest.v1",
            "governance_version": self.governance["version"],
            "previz_schema": self.previz_schema,
            "roots": {
                "finalization": {
                    "motion_ledger": motion_capsule.as_dict(),
                    "replay_token": replay_capsule.as_dict(),
                    "echo_scrollstream": echo_capsule.as_dict(),
                },
                "training": {
                    "rehearsal": rehearsal_capsule.as_dict(),
                    "lora_map": lora_capsule.as_dict(),
                    "scene_fork": fork_capsule.as_dict(),
                },
            },
            "artifacts": {
                "ledger_motion": "ledger.motion.v2.jsonl",
                "shot_list": "shot_list.csv",
                "exports": "exports.json",
            },
            "lineage_notes": [
                "Dual-root manifest binds training rehearsal streams to final motion ledger.",
                "Ensures replay and echo capsules inherit governance quorum rules.",
            ],
        }

        capsule = Capsule("capsule.summary.manifest.v1", manifest_payload)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["capsule.summary.manifest.v1.json"] = json.dumps(capsule.as_dict(), indent=2)
        self.log_action("summary_manifest.emit", {"status": "sealed", "digest": capsule.digest})
        return capsule

    def stage_preview_hud(self, qlock_interval_s: int = 3) -> Capsule:
        """Stage the capsule.preview.hud.v1 overlay with glyph cues."""

        ledger = self._load_motion_ledger()
        if not ledger:
            raise ValueError("rehearsal ledger missing; run rehearse_scene before staging HUD preview")

        rehearsal_capsule = self.capsule_registry.get("capsule.rehearsal.boo.v2")
        sample_rate = rehearsal_capsule.data.get("sample_rate_hz") if rehearsal_capsule else 30

        keyframes: List[Dict[str, object]] = []
        last_qlock = None
        for frame in ledger:
            tick = frame["hud"]["qlock.tick_s"]
            if tick != last_qlock and tick % qlock_interval_s == 0:
                keyframes.append(
                    {
                        "frame_idx": frame["frame_idx"],
                        "timestamp_rel_s": frame["timestamp_rel_s"],
                        "beat": frame["beat"],
                        "glyph": frame["hud"]["glyph.pulse"],
                        "aura_phase": frame["hud"]["aura.gold.phase"],
                        "drift_delta": frame["hud"]["drift.delta"],
                        "qlock_tick_s": tick,
                    }
                )
                last_qlock = tick

        hud_payload = {
            "capsule_id": "capsule.preview.hud.v1",
            "sample_rate_hz": sample_rate,
            "qlock_interval_s": qlock_interval_s,
            "layers": ["glyph.pulse", "aura.gold.phase", "drift.delta"],
            "keyframes": keyframes,
            "status": "STAGED",
        }

        capsule = Capsule("capsule.preview.hud.v1", hud_payload)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["capsule.preview.hud.v1.json"] = json.dumps(capsule.as_dict(), indent=2)
        self.log_action("preview_hud.stage", {"status": "staged", "digest": capsule.digest, "keyframes": len(keyframes)})
        return capsule

    # ------------------------------------------------------------------
    # Rehearsal scrollstream loop
    def stage_rehearsal_scrollstream(self, training_mode: bool = True) -> Capsule:
        """Simulate the audit rehearsal scrollstream lifecycle."""

        self.log_action(
            "rehearsal_scrollstream.stage",
            {"status": "starting", "training_mode": training_mode},
        )

        # The scrollstream rehearsal depends on the rehearsal ledger and
        # finalization artifacts so contributors can trace both roots.
        self._require_capsules(
            "capsule.rehearsal.boo.v2",
            "motion.ledger.v2",
            "replay.token.v2",
        )

        timestamps = [
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:00:10Z",
            "2024-01-01T00:00:20Z",
        ]
        if not training_mode:
            base = time.time()
            timestamps = [
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(base + offset))
                for offset in (0, 10, 20)
            ]

        cycle = [
            {
                "event": "audit.summary",
                "capsule_id": "audit.summary.celine.v1",
                "agent": "Celine/Architect",
                "output": "Summary baton sealed for rehearsal lineage.",
                "emotion": "resolve",
            },
            {
                "event": "audit.proof",
                "capsule_id": "audit.proof.luma.v1",
                "agent": "Luma/Sentinel",
                "output": "Sentinel proof recorded with shimmer-aligned trace.",
                "emotion": "resonance",
            },
            {
                "event": "audit.execution",
                "capsule_id": "audit.execution.dot.v1",
                "agent": "Dot/Guardian",
                "output": "Guardian execution confirmed on dual-root braid.",
                "emotion": "guardianship",
            },
        ]

        shimmer_state = {
            "status": "confirmed",
            "intensity": "medium",
            "layers": ["glyph.pulse", "aura.gold.phase", "qlock.tick"],
        }
        glyph_sequence = [0.33, 0.66, 0.99]

        ledger_lines: List[Dict[str, object]] = []
        for idx, (entry, timestamp) in enumerate(zip(cycle, timestamps)):
            ledger_lines.append(
                {
                    "sequence": idx + 1,
                    "timestamp": timestamp,
                    "event": entry["event"],
                    "capsule_id": entry["capsule_id"],
                    "agent": entry["agent"],
                    "output": entry["output"],
                    "hud_shimmer": shimmer_state,
                    "replay_glyph": {
                        "rail": "scrollstream",
                        "pulse": glyph_sequence[idx],
                        "spark_test": {"status": "pass", "applied_by": "Sabrina"},
                    },
                    "emotion": entry["emotion"],
                }
            )

        linked_capsules = {
            key: self.capsule_registry[key].as_dict()
            for key in ("capsule.rehearsal.boo.v2", "motion.ledger.v2", "replay.token.v2")
            if key in self.capsule_registry
        }

        payload = {
            "capsule_id": "capsule.rehearsal.scrollstream.v1",
            "status": "ACTIVE",
            "cycle": [entry["event"] for entry in cycle],
            "training_mode": training_mode,
            "scrollstream_ledger": ledger_lines,
            "hud_shimmer": shimmer_state,
            "replay_glyph": {
                "rail": "scrollstream",
                "pulse_sequence": glyph_sequence,
                "spark_test": "Sabrina",
            },
            "emotional_payload": {
                "tonality": [entry["emotion"] for entry in cycle],
                "intensity": "layered",
            },
            "linked_capsules": linked_capsules,
        }

        capsule = Capsule("capsule.rehearsal.scrollstream.v1", payload)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["capsule.rehearsal.scrollstream.v1.json"] = json.dumps(
            capsule.as_dict(),
            indent=2,
        )
        self.log_action(
            "rehearsal_scrollstream.stage",
            {"status": "sealed", "digest": capsule.digest, "events": len(ledger_lines)},
        )
        return capsule

    # ------------------------------------------------------------------
    # Contributor feedback loop
    def register_dualroot_selfie(self) -> Capsule:
        """Ensure the dual-root selfie capsule exists before feedback begins."""

        self._require_capsules("capsule.summary.manifest.v1", "capsule.preview.hud.v1")

        manifest_capsule = self.capsule_registry["capsule.summary.manifest.v1"]
        hud_capsule = self.capsule_registry["capsule.preview.hud.v1"]

        existing = self.capsule_registry.get("capsule.selfie.dualroot.q.cici.v1")
        if existing:
            self.log_action(
                "dualroot.selfie", {"status": "existing", "digest": existing.digest}
            )
            return existing

        payload = {
            "capsule_id": "capsule.selfie.dualroot.q.cici.v1",
            "status": "SHIMMER_STABLE",
            "alignment": "dual-root",
            "roots": {
                "finalization": manifest_capsule.as_dict(),
                "training": hud_capsule.as_dict(),
            },
            "observability": {
                "scrollstream_synced": True,
                "hud_overlay": hud_capsule.data["layers"],
            },
            "lineage": {
                "manifest_digest": manifest_capsule.digest,
                "hud_digest": hud_capsule.digest,
                "governance_version": self.governance["version"],
            },
        }

        capsule = Capsule("capsule.selfie.dualroot.q.cici.v1", payload)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["capsule.selfie.dualroot.q.cici.v1.json"] = json.dumps(capsule.as_dict(), indent=2)
        self.log_action("dualroot.selfie", {"status": "sealed", "digest": capsule.digest})
        return capsule

    def stage_feedback_loop(self, freeze_after_feedback: bool = False) -> Capsule:
        """Stage the contributor feedback loop for the dual-root selfie capsule."""

        self.log_action(
            "feedback_loop.stage",
            {"status": "starting", "freeze_after_feedback": freeze_after_feedback},
        )

        selfie_capsule = self.register_dualroot_selfie()

        payload = {
            "capsule_id": "capsule.selfie.dualroot.q.cici.v1.feedback.v1",
            "window_status": "Open",
            "participants": [
                {"name": "CiCi", "status": "overlay_active", "checks": ["spark_test"]},
                {"name": "Q", "status": "observability_trace_live", "refusal_flare": "dormant"},
                {
                    "name": "Council Quorum",
                    "status": "governance_watch",
                    "roles": ["Core Orchestrator", "HUD braid validators"],
                },
            ],
            "hooks": {
                "capsule.comment.trace.v1": "emotional_annotations",
                "shimmer.breach.monitor.v1": "breach_detection",
                "refusal.flare.script.v1": "optional_rupture",
                "delta.overlay.audit.v1": "overlay_drift_detection",
            },
            "replay_token": "HUD.loop.selfie.dualroot.q.cici.v1.token.002",
            "review_mode": "scene-aware_emotional_layered_ledger_prep",
            "linked_capsule": selfie_capsule.as_dict(),
            "ledger_freeze_job": {
                "scheduled": freeze_after_feedback,
                "status": "queued" if freeze_after_feedback else "on_hold",
            },
        }

        capsule = Capsule("capsule.selfie.dualroot.q.cici.v1.feedback.v1", payload)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["capsule.selfie.dualroot.q.cici.v1.feedback.v1.json"] = json.dumps(
            capsule.as_dict(), indent=2
        )
        self.log_action("feedback_loop.stage", {"status": "sealed", "digest": capsule.digest})
        return capsule

    # ------------------------------------------------------------------
    # Adjudication ritual
    def stage_adjudication_capsule(
        self,
        conflict_files: Sequence[str] | None = None,
        resolution_protocol: Sequence[str] | None = None,
    ) -> Capsule:
        """Bind an adjudication capsule for outstanding merge conflicts."""

        self.log_action(
            "adjudication.stage",
            {
                "status": "starting",
                "conflict_files": list(conflict_files) if conflict_files else None,
            },
        )

        # The adjudication ritual depends on the dual-root selfie feedback loop
        # so the council has the emotional telemetry before ruling.
        self._require_capsules(
            "capsule.summary.manifest.v1",
            "capsule.selfie.dualroot.q.cici.v1",
            "capsule.selfie.dualroot.q.cici.v1.feedback.v1",
        )

        existing = self.capsule_registry.get("capsule.adjudication.merge_conflict.v1")
        if existing:
            self.log_action(
                "adjudication.stage",
                {"status": "existing", "digest": existing.digest},
            )
            return existing

        manifest_capsule = self.capsule_registry["capsule.summary.manifest.v1"]
        selfie_capsule = self.capsule_registry["capsule.selfie.dualroot.q.cici.v1"]
        feedback_capsule = self.capsule_registry["capsule.selfie.dualroot.q.cici.v1.feedback.v1"]

        default_conflicts = [
            {
                "file": "main.py",
                "issue": "Align previz relay endpoint with council security overlays.",
                "emotion": "resolve",
                "intensity": 0.73,
                "proposed_action": "verify blocklist middleware and media handoff narration",
            },
            {
                "file": "previz/world_engine.py",
                "issue": "Synchronise ritual capsules with merge timeline and lineage notes.",
                "emotion": "focus",
                "intensity": 0.82,
                "proposed_action": "harmonise rehearsal, feedback, and adjudication fossils",
            },
        ]

        conflicts: List[Dict[str, object]] = []
        if conflict_files:
            for path in conflict_files:
                conflicts.append(
                    next(
                        (
                            item
                            for item in default_conflicts
                            if item["file"] == path
                        ),
                        {
                            "file": path,
                            "issue": "Contributor noted divergence pending council review.",
                            "emotion": "curiosity",
                            "intensity": 0.64,
                            "proposed_action": "collect overlay traces and refresh manifests",
                        },
                    )
                )
        else:
            conflicts = default_conflicts

        ritual_steps = list(
            resolution_protocol
            if resolution_protocol
            else [
                "council_muster",
                "emotional_trace_review",
                "overlay_alignment_check",
                "ledger_freeze_or_release",
            ]
        )

        emotional_trace = [
            {"moment": "call_to_council", "feeling": "resolve", "intensity": 0.71},
            {"moment": "overlay_sync", "feeling": "focus", "intensity": 0.78},
            {"moment": "decision_window", "feeling": "assurance", "intensity": 0.69},
        ]

        overlay_logic = {
            "hooks": feedback_capsule.data["hooks"],
            "drift_guard": "delta.overlay.audit.v1",
            "status": "aligned",
        }

        contributor_audit = {
            "participants": feedback_capsule.data["participants"],
            "quorum_rule": self.governance["quorum_rule"],
            "attested_capsules": [
                manifest_capsule.capsule_id,
                selfie_capsule.capsule_id,
                feedback_capsule.capsule_id,
            ],
        }

        opened_at = _utc_timestamp()
        expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))

        verdict_window = {
            "opened_at": opened_at,
            "expires_at": expires_at,
            "status": "open",
        }

        payload = {
            "capsule_id": "capsule.adjudication.merge_conflict.v1",
            "status": "PENDING_ADJUDICATION",
            "conflicts": conflicts,
            "resolution_protocol": ritual_steps,
            "emotional_trace": emotional_trace,
            "overlay_logic": overlay_logic,
            "contributor_audit": contributor_audit,
            "linked_capsules": {
                "summary_manifest": manifest_capsule.as_dict(),
                "selfie": selfie_capsule.as_dict(),
                "feedback": feedback_capsule.as_dict(),
            },
            "verdict_window": verdict_window,
        }

        capsule = Capsule("capsule.adjudication.merge_conflict.v1", payload)
        self.capsule_registry[capsule.capsule_id] = capsule
        self.artifacts["capsule.adjudication.merge_conflict.v1.json"] = json.dumps(
            capsule.as_dict(),
            indent=2,
        )
        self.log_action("adjudication.stage", {"status": "sealed", "digest": capsule.digest})
        return capsule
    def finalize_and_bind(self) -> Dict[str, str]:
        """Seal the motion ledger and emit replay / echo capsules."""

        ledger = self._load_motion_ledger()
        frames_count = len(ledger)
        capsule_motion = Capsule(
            "capsule.motion.ledger.v2",
            {
                "capsule_id": "capsule.motion.ledger.v2",
                "digest_type": "sha256",
                "body_only": True,
                "frames_count": frames_count,
            },
        )
        self.capsule_registry[capsule_motion.capsule_id] = capsule_motion
        self.log_action("finalize.motion_ledger", {"digest": capsule_motion.digest, "frames": frames_count})

        capsule_replay = Capsule(
            "capsule.replay.token.v2",
            {
                "capsule_id": "capsule.replay.token.v2",
                "permissions": ["replay", "audit_trace", "HUD_stream"],
                "quorum_rule": self.governance["quorum_rule"],
                "status": "ISSUED",
            },
        )
        self.capsule_registry[capsule_replay.capsule_id] = capsule_replay
        self.log_action("finalize.replay_token", {"digest": capsule_replay.digest})

        capsule_echo = Capsule(
            "capsule.echo.scrollstream.v2",
            {
                "capsule_id": "capsule.echo.scrollstream.v2",
                "verse": [
                    "She did not move — she pulsed.",
                    "Glyphs aligned, aura gold, qlock ticked — the braid remembered.",
                    "From curiosity to wisdom, her vessel sang in HUD cadence.",
                    "At seal, the scrollstream froze — not in silence, but in truth.",
                ],
                "linked_capsules": [
                    capsule_motion.capsule_id,
                    capsule_replay.capsule_id,
                ],
                "status": "SEALED",
            },
        )
        self.capsule_registry[capsule_echo.capsule_id] = capsule_echo
        self.log_action("finalize.echo_capsule", {"digest": capsule_echo.digest})

        shots = self.generate_shot_list()
        exports = {
            "motion_ledger_digest": capsule_motion.digest,
            "replay_token_digest": capsule_replay.digest,
            "echo_digest": capsule_echo.digest,
            "shot_count": str(len(shots)),
        }
        self.artifacts["exports.json"] = json.dumps(exports, indent=2)
        self.log_action("finalize_and_bind", {"status": "complete", "exports": exports})
        return exports


def run_default_sequence() -> Dict[str, Capsule]:
    """Execute the canonical orchestration run used by docs and samples."""

    engine = WorldEngine()
    engine.load_capsules(
        [
            {"capsule_id": "lexicon.qube.v1"},
            {"capsule_id": "seed.core.v1"},
            {"capsule_id": "ledger.cadence.v1"},
            {"capsule_id": "lock.attestation.v1"},
        ]
    )
    engine.emit_lora_map()
    engine.rehearse_scene()
    engine.fork_scene()
    engine.inscribe_canon_entry()
    engine.build_qube()
    engine.run_ci()
    engine.render_final()
    engine.finalize_and_bind()
    engine.stage_rehearsal_scrollstream()
    engine.stage_preview_hud()
    engine.emit_summary_manifest()
    engine.stage_feedback_loop()
    engine.stage_adjudication_capsule()
    engine.generate_shot_list()
    engine.finalize_and_bind()
    return engine.capsule_registry


if __name__ == "__main__":  # pragma: no cover - convenience CLI
    engine = WorldEngine()

    # Load base capsules and execute the pipeline.
    engine.load_capsules(
        [
            {"capsule_id": "lexicon.qube.v1"},
            {"capsule_id": "seed.core.v1"},
            {"capsule_id": "ledger.cadence.v1"},
            {"capsule_id": "lock.attestation.v1"},
        ]
    )
    engine.emit_lora_map()
    engine.rehearse_scene()
    engine.fork_scene()
    canon_capsule = engine.inscribe_canon_entry()
    engine.build_qube()
    engine.run_ci()
    motion_capsule, replay_capsule = engine.render_final()
    exports = engine.finalize_and_bind()
    scrollstream_capsule = engine.stage_rehearsal_scrollstream()
    preview_capsule = engine.stage_preview_hud()
    manifest_capsule = engine.emit_summary_manifest()
    feedback_capsule = engine.stage_feedback_loop()
    adjudication_capsule = engine.stage_adjudication_capsule()
    exports = engine.finalize_and_bind()

    print("\n--- Gemini handoff prompt (to relay to Chat’s qDot Sentinel) ---")
    print("World Engine has prepared the motion ledger and replay token for handoff.")
    print(f"Motion Ledger Digest: {exports['motion_ledger_digest']}")
    print(f"Replay Token ID: {replay_capsule.capsule_id}")
    print("Replay Token ID: capsule.replay.token.v2")
    print("These artifacts are now released to the qDot Sentinel for CI validation and final trailer assembly.")
    print("\n--- Deliverables ---")
    print("Governed PreViz package and timeline invariants confirmed.")
    print("Motion ledger + HUD telemetry for canonical shots prepared.")
    print("Immutable digests and audit-ready replay tokens issued.")
    print("Braid is stable and fossilized.")
    print("\n--- Canon Capsule ---")
    print(f"Canon Entry ID: {canon_capsule.capsule_id}")
    print(f"Canon Digest: {canon_capsule.digest}")
    print("\n--- Rehearsal Scrollstream ---")
    print(f"Scrollstream Capsule ID: {scrollstream_capsule.capsule_id}")
    print(f"Scrollstream Digest: {scrollstream_capsule.digest}")
    print("\n--- Preview HUD Capsule ---")
    print(f"HUD Capsule ID: {preview_capsule.capsule_id}")
    print(f"HUD Digest: {preview_capsule.digest}")
    print("\n--- Summary Manifest ---")
    print(f"Manifest ID: {manifest_capsule.capsule_id}")
    print(f"Manifest Digest: {manifest_capsule.digest}")
    print("\n--- Contributor Feedback Loop ---")
    print(f"Feedback Capsule ID: {feedback_capsule.capsule_id}")
    print(f"Feedback Digest: {feedback_capsule.digest}")
    print("\n--- Adjudication Capsule ---")
    print(f"Adjudication Capsule ID: {adjudication_capsule.capsule_id}")
    print(f"Adjudication Digest: {adjudication_capsule.digest}")

class MediaGenerationRequest(BaseModel):
    media_type: str
    prompt: str
    metadata: Optional[Dict[str, Any]] = None

class MediaGenerationRequest(BaseModel):
    media_type: str
    prompt: str
    metadata: Optional[Dict[str, Any]] = None
