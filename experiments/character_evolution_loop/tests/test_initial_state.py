import unittest

from build_initial_state import build_initial_state


class InitialStateTests(unittest.TestCase):
    def test_unresolved_features_enter_modifiable_without_fake_locks(self):
        contract = {
            "schema_version": "character-canon-contract/1",
            "character": {"id": "CHAR-X", "name": "角色X"},
            "provenance": {"contains_novel_passages": False},
            "locked_facts": [],
            "soft_constraints": [
                {
                    "feature": "recurring_work_context",
                    "instruction": "工作语境",
                    "confidence": 0.68,
                    "evidence": [],
                }
            ],
            "unresolved_visual_features": ["age", "face_shape", "eye_shape"],
            "forbidden_interpretations": [],
        }
        state = build_initial_state(contract)
        self.assertEqual(state.version, 1)
        self.assertEqual(state.locked, {})
        self.assertIn("age", state.modifiable)
        self.assertIn("face_shape", state.modifiable)
        self.assertIn("eyes", state.modifiable)
        self.assertIn("recurring_work_context", state.design_targets)


if __name__ == "__main__":
    unittest.main()
