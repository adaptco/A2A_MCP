from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from codex_qernel import CodexQernel, QernelConfig
from codex_qernel.capsules import CapsuleManifest, discover_capsule_manifests


class CodexQernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        base = Path(self.tempdir.name)
        self.capsules_dir = base / "capsules"
        self.events_log = base / "events.ndjson"
        self.capsules_dir.mkdir(parents=True, exist_ok=True)
        valid_manifest = {
            "id": "capsule.test.v1",
            "version": "1.0.0",
            "name": "Test Capsule",
            "description": "Used by tests",
        }
        invalid_manifest = {
            "id": "capsule.invalid",
            "name": "Broken Capsule",
        }
        (self.capsules_dir / "valid.json").write_text(json.dumps(valid_manifest), encoding="utf-8")
        (self.capsules_dir / "invalid.json").write_text(json.dumps(invalid_manifest), encoding="utf-8")
        self.config = QernelConfig(
            os_name="TestOS",
            qernel_version="9.9.9",
            capsules_dir=self.capsules_dir,
            events_log=self.events_log,
            auto_refresh=True,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_discover_capsule_manifests_filters_invalid_files(self) -> None:
        manifests = discover_capsule_manifests(self.capsules_dir)
        self.assertEqual(len(manifests), 1)
        manifest = manifests[0]
        self.assertIsInstance(manifest, CapsuleManifest)
        self.assertEqual(manifest.capsule_id, "capsule.test.v1")
        self.assertEqual(manifest.name, "Test Capsule")

    def test_qernel_refresh_and_events(self) -> None:
        qernel = CodexQernel(self.config)
        health = qernel.health_status()
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["os"], "TestOS")
        self.assertEqual(health["capsules_loaded"], 1)

        capsules = qernel.list_capsules()
        self.assertEqual(len(capsules), 1)
        self.assertEqual(capsules[0]["id"], "capsule.test.v1")

        manifest = qernel.get_capsule("capsule.test.v1")
        self.assertEqual(manifest["name"], "Test Capsule")
        self.assertIsNone(qernel.get_capsule("missing"))

        qernel.refresh()
        events = qernel.read_events(limit=5)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[-1].event, "codex.qernel.refreshed")
        self.assertEqual(events[-1].payload["capsule_count"], 1)

        extra_event = qernel.record_event("codex.test.event", {"key": "value"})
        self.assertEqual(extra_event.payload["key"], "value")
        all_events = qernel.read_events(limit=10)
        self.assertEqual(all_events[-1].event, "codex.test.event")

    def test_scrollstream_rehearsal_cycle(self) -> None:
        qernel = CodexQernel(self.config)
        timestamps = iter(
            [
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
            ]
        )

        def fake_clock() -> datetime:
            return next(timestamps)

        entries = qernel.emit_scrollstream_rehearsal(clock=fake_clock)
        self.assertEqual(len(entries), 3)
        self.assertTrue(all(entry["capsule_id"] == "capsule.rehearsal.scrollstream.v1" for entry in entries))
        self.assertTrue(all(entry["training_mode"] for entry in entries))
        self.assertEqual([entry["cycle"] for entry in entries], ["audit.summary", "audit.proof", "audit.execution"])
        ledger = qernel.read_scrollstream_ledger(limit=5)
        self.assertEqual(len(ledger), 3)
        self.assertEqual(ledger[0]["agent"], "celine.architect")
        self.assertEqual(ledger[-1]["signals"]["replay_glyph"], "pulse")
        last_event = qernel.read_events(limit=1)[-1]
        self.assertEqual(last_event.event, "codex.scrollstream.rehearsal")
        self.assertTrue(Path(self.config.scrollstream_ledger).exists())

    def test_geodesic_terminal_modeling(self) -> None:
        qernel = CodexQernel(self.config)
        model = qernel.model_geodesic_terminal(
            bridge_name="AxQxOS test bridge",
            anchors=["north", "mid", "south"],
            span=90.0,
            tension=0.75,
        )

        self.assertEqual(model["bridge_name"], "AxQxOS test bridge")
        self.assertEqual(model["anchors"], ["north", "mid", "south"])
        self.assertEqual(len(model["segments"]), 2)
        self.assertAlmostEqual(model["span"], 90.0)
        self.assertGreater(model["lattice_frequency"], 0)

        last_event = qernel.read_events(limit=1)[-1]
        self.assertEqual(last_event.event, "codex.bridge.geodesic.modeled")
        self.assertEqual(last_event.payload["segments"], 2)
        self.assertEqual(last_event.payload["anchors"], ["north", "mid", "south"])

    def test_psm_gaussian_action(self) -> None:
        qernel = CodexQernel(self.config)
        result = qernel.synthesize_gaussian_action(
            axqos_flow="audit>query>action: bridge integrity sweep",
            state_id="cfm.qf4",
        )

        self.assertIn("predicted_action", result)
        self.assertIn(result["predicted_action"], {"Commit_Structural_Lock", "Policy_Audit_Required"})
        self.assertAlmostEqual(result["divergence_score"], 0.069, places=3)
        self.assertGreaterEqual(result["confidence"], 0.8)

        last_event = qernel.read_events(limit=1)[-1]
        self.assertEqual(last_event.event, "codex.psm.gaussian_action_synthesized")
        self.assertEqual(last_event.payload["state_id"], "cfm.qf4")
        self.assertEqual(last_event.payload["predicted_action"], result["predicted_action"])


class ConfigFromEnvTests(unittest.TestCase):
    def test_environment_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            os.environ["AXQXOS_NAME"] = "EnvOS"
            os.environ["CODEX_QERNEL_VERSION"] = "2.3.4"
            os.environ["CODEX_CAPSULE_DIR"] = "relative_capsules"
            os.environ["CODEX_EVENTS_LOG"] = "logs/events.ndjson"
            os.environ["CODEX_AUTO_REFRESH"] = "false"
            os.environ["CODEX_SCROLLSTREAM_LEDGER"] = "logs/scrollstream.ndjson"
            config = QernelConfig.from_env(base_dir=base)
            self.assertEqual(config.os_name, "EnvOS")
            self.assertEqual(config.qernel_version, "2.3.4")
            self.assertEqual(config.capsules_dir, base / "relative_capsules")
            self.assertEqual(config.events_log, base / "logs/events.ndjson")
            self.assertFalse(config.auto_refresh)
            self.assertEqual(config.scrollstream_ledger, base / "logs/scrollstream.ndjson")
        for var in [
            "AXQXOS_NAME",
            "CODEX_QERNEL_VERSION",
            "CODEX_CAPSULE_DIR",
            "CODEX_EVENTS_LOG",
            "CODEX_AUTO_REFRESH",
            "CODEX_SCROLLSTREAM_LEDGER",
        ]:
            os.environ.pop(var, None)


if __name__ == "__main__":
    unittest.main()
