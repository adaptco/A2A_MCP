import unittest
import sys
import os

# Add the project root to sys.path to resolve the module
# We need to go up from: qube_moemodel_v1/tests/test_agent.py
# 1. dirname -> qube_moemodel_v1/tests
# 2. .. -> qube_moemodel_v1
# 3. ../.. -> repo root (where qube_moemodel_v1 lives)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from qube_moemodel_v1.src.moe.agent import MoEAgent

class TestMoEAgent(unittest.TestCase):
    def setUp(self):
        # Define some simple experts
        self.expert_neg = lambda x: x * 2  # Handles negative well?
        self.expert_pos = lambda x: x + 10 # Handles positive well?
        self.expert_neutral = lambda x: 0

        self.experts = [self.expert_neg, self.expert_pos, self.expert_neutral]
        self.agent = MoEAgent(self.experts, expert_names=["NegX2", "PosPlus10", "Zero"])

    def test_routing_negative(self):
        # Input -5. Routing should pick first half (index 0).
        result = self.agent.process(-5.0)
        self.assertEqual(result["routing_indices"], [0])
        self.assertEqual(result["active_experts"], ["NegX2"])
        self.assertEqual(result["output"], -10.0)

    def test_routing_positive(self):
        # Input 5. Routing should pick second half [1, 2].
        result = self.agent.process(5.0)
        self.assertEqual(result["routing_indices"], [1, 2])
        self.assertEqual(result["active_experts"], ["PosPlus10", "Zero"])
        self.assertEqual(result["output"], 7.5)

    def test_routing_zero(self):
        # Input 0. All experts.
        result = self.agent.process(0.0)
        self.assertEqual(result["routing_indices"], [0, 1, 2])
        self.assertAlmostEqual(result["output"], 3.3333333, places=5)

    def test_initialization_error(self):
        with self.assertRaises(ValueError):
            MoEAgent([])

    def test_name_mismatch_error(self):
        with self.assertRaises(ValueError):
            MoEAgent([lambda x: x], expert_names=["A", "B"])

if __name__ == '__main__':
    unittest.main()
