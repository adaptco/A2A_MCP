import unittest
from context.window import ContextWindow, Turn

class TestContextWindowBasic(unittest.TestCase):
    def test_turn_to_dict(self):
        turn = Turn(
            turn_id=1,
            agent_message="Hello",
            user_feedback="Hi",
            metadata={"key": "value"},
            is_pinned=True
        )
        expected = {
            "turn_id": 1,
            "agent": "Hello",
            "user": "Hi",
            "pinned": True,
            "metadata": {"key": "value"}
        }
        self.assertEqual(turn.to_dict(), expected)

    def test_context_window_init(self):
        cw = ContextWindow(window_size=5, compression_threshold=10)
        self.assertEqual(cw.window_size, 5)
        self.assertEqual(cw.compression_threshold, 10)
        self.assertEqual(len(cw._turns), 0)
        self.assertEqual(len(cw._all_turns), 0)
        self.assertEqual(cw._turn_count, 0)

    def test_add_turn(self):
        cw = ContextWindow()
        turn = cw.add_turn(agent_message="Agent msg", user_feedback="User fb", metadata={"meta": "data"}, pinned=True)

        self.assertEqual(turn.turn_id, 0)
        self.assertEqual(turn.agent_message, "Agent msg")
        self.assertEqual(turn.user_feedback, "User fb")
        self.assertEqual(turn.metadata, {"meta": "data"})
        self.assertTrue(turn.is_pinned)

        self.assertEqual(len(cw._turns), 1)
        self.assertEqual(len(cw._all_turns), 1)
        self.assertEqual(cw._turn_count, 1)
        self.assertEqual(cw._turns[0], turn)

    def test_pin_artifact(self):
        cw = ContextWindow()
        cw.pin_artifact(artifact_type="spec", content="new spec", reason="updated")

        self.assertEqual(len(cw._pinned_artifacts), 1)
        self.assertEqual(cw._pinned_artifacts[0], {
            "type": "spec",
            "content": "new spec",
            "reason": "updated"
        })

    def test_clear(self):
        cw = ContextWindow(window_size=2, compression_threshold=3)
        cw.add_turn("m1")
        cw.pin_artifact("type", "content")

        self.assertEqual(cw._turn_count, 1)
        self.assertEqual(len(cw._pinned_artifacts), 1)

        cw.clear()

        self.assertEqual(len(cw._turns), 0)
        self.assertEqual(len(cw._all_turns), 0)
        self.assertEqual(len(cw._compressed_summaries), 0)
        self.assertEqual(len(cw._pinned_artifacts), 0)
        self.assertEqual(cw._turn_count, 0)

    def test_repr(self):
        cw = ContextWindow()
        cw.add_turn("m1")
        cw.pin_artifact("type", "content")

        representation = repr(cw)
        self.assertIn("turns=1/1", representation)
        self.assertIn("pinned=1", representation)

class TestContextWindowAdvanced(unittest.TestCase):
    def test_compression_trigger(self):
        # window_size=2, threshold=3
        cw = ContextWindow(window_size=2, compression_threshold=3)
        cw.add_turn("m0")
        cw.add_turn("m1")
        self.assertEqual(len(cw._compressed_summaries), 0)

        # Adding 3rd turn should trigger compression of older turns (m0)
        cw.add_turn("m2")
        self.assertEqual(len(cw._compressed_summaries), 1)
        self.assertIn("m0", cw._compressed_summaries[0])
        self.assertIn("[SUMMARY: 1 turns]", cw._compressed_summaries[0])

    def test_compression_preserves_pinned_turns(self):
        cw = ContextWindow(window_size=1, compression_threshold=2)
        cw.add_turn("m0_pinned", pinned=True)
        cw.add_turn("m1_not_pinned")

        # When m1 is added, len(_all_turns) = 2, threshold reached.
        # cutoff = 2 - 1 = 1.
        # turns_to_compress = [t for t in _all_turns[:1] if not t.is_pinned]
        # _all_turns[:1] is m0_pinned. Since it IS pinned, turns_to_compress should be empty.

        self.assertEqual(len(cw._compressed_summaries), 0)

    def test_compression_logic_multi_turns(self):
        cw = ContextWindow(window_size=2, compression_threshold=5)
        for i in range(4):
            cw.add_turn(f"m{i}")

        self.assertEqual(len(cw._compressed_summaries), 0)

        # 5th turn
        cw.add_turn("m4")
        self.assertEqual(len(cw._compressed_summaries), 1)
        # cutoff = 5 - 2 = 3. Turns 0, 1, 2 should be compressed.
        self.assertIn("m0 m1 m2", cw._compressed_summaries[0])

    def test_get_context(self):
        cw = ContextWindow(window_size=2, compression_threshold=3)
        cw.pin_artifact("Policy", "Be helpful")
        cw.add_turn("m0", user_feedback="fb0")
        cw.add_turn("m1")
        cw.add_turn("m2", user_feedback="fb2")

        # m0 should be compressed
        context = cw.get_context()

        self.assertIn("=== Historical Context ===", context)
        self.assertIn("[SUMMARY: 1 turns] m0", context)

        self.assertIn("=== Critical Artifacts ===", context)
        self.assertIn("[Policy] Be helpful", context)

        self.assertIn("=== Recent Turns ===", context)
        self.assertIn("Agent (turn 1): m1", context)
        self.assertIn("Agent (turn 2): m2", context)
        self.assertIn("User: fb2", context)
        self.assertNotIn("Agent (turn 0): m0", context)

    def test_get_json_context(self):
        cw = ContextWindow(window_size=2, compression_threshold=3)
        cw.add_turn("m0")
        cw.add_turn("m1")
        cw.add_turn("m2")

        json_ctx = cw.get_json_context()
        self.assertEqual(json_ctx["turn_count"], 3)
        self.assertEqual(json_ctx["window_size"], 2) # Length of deque
        self.assertEqual(len(json_ctx["recent_turns"]), 2)
        self.assertEqual(len(json_ctx["compressed_summaries"]), 1)

if __name__ == '__main__':
    unittest.main()
