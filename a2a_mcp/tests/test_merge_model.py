from __future__ import annotations

import unittest
from pathlib import Path

from app.merge_model import MergeModel


class MergeModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        model_path = Path(__file__).resolve().parents[1] / "specs" / "branch-merge-model.v1.json"
        cls.model = MergeModel.from_file(model_path)

    def test_branches_summary_contains_expected_ids(self) -> None:
        summary = self.model.branches_summary()
        branch_ids = [branch["id"] for branch in summary]
        self.assertIn("ssot", branch_ids)
        self.assertIn("core", branch_ids)
        # Branch order should be stable according to the model definition.
        self.assertEqual(branch_ids[0], "ssot")

    def test_plan_summary_is_sorted_and_resolves_sources(self) -> None:
        waves = self.model.plan_summary()
        orders = [wave["order"] for wave in waves]
        self.assertEqual(orders, sorted(orders))
        first_wave = waves[0]
        self.assertGreater(len(first_wave["sources"]), 0)
        for source in first_wave["sources"]:
            self.assertIn("id", source)
            self.assertIn("primary_branch", source)

    def test_automation_summary_contains_hooks_and_notifications(self) -> None:
        automation = self.model.automation_summary()
        self.assertGreaterEqual(len(automation["hooks"]), 1)
        self.assertGreaterEqual(len(automation["notifications"]), 1)
        self.assertIn("triggers", automation["hooks"][0])
        self.assertIn("channel", automation["notifications"][0])

    def test_to_dict_round_trip_preserves_merge_plan(self) -> None:
        document = self.model.to_dict()
        round_trip = MergeModel.from_dict(document)
        original_wave_ids = [wave["id"] for wave in self.model.plan_summary()]
        round_trip_wave_ids = [wave["id"] for wave in round_trip.plan_summary()]
        self.assertEqual(round_trip_wave_ids, original_wave_ids)
        self.assertEqual(round_trip.version, self.model.version)

    def test_middleware_contract_includes_merge_model_route(self) -> None:
        contract = self.model.middleware_summary()
        routes = [route["path"] for route in contract["routes"]]
        self.assertIn("/merge/model", routes)


if __name__ == "__main__":
    unittest.main()

