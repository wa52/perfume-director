import json
import tempfile
import unittest
from pathlib import Path

from character_evolution.director import CharacterDirector
from character_evolution.memory import CharacterMemory
from character_evolution.models import CanonProfile, CharacterState, Critique


class CharacterEvolutionTests(unittest.TestCase):
    def test_locked_feature_is_never_revised(self):
        state = CharacterState(character="陆辛", locked={"face_shape": "ordinary-oval"})
        critique = Critique(
            candidate_id="A",
            scores={"ordinary": 70, "canon": 80},
            change_requests=[
                {"feature": "face_shape", "target": "sharp"},
                {"feature": "eyes", "target": "softer"},
            ],
        )
        patch = CharacterDirector().plan(CanonProfile(character="陆辛"), state, critique)
        self.assertEqual([c["feature"] for c in patch.change], ["eyes"])
        self.assertIn("face_shape", patch.do_not_change)

    def test_rejected_target_is_filtered_and_change_count_is_bounded(self):
        state = CharacterState(character="陆辛", rejected=["aggressive_gaze"])
        critique = Critique(
            candidate_id="A",
            scores={"canon": 60},
            change_requests=[
                {"feature": "eyes", "target": "aggressive_gaze"},
                {"feature": "clothing", "target": "office"},
                {"feature": "posture", "target": "reserved"},
                {"feature": "hair", "target": "plain"},
            ],
        )
        patch = CharacterDirector(max_changes=2).plan(CanonProfile(character="陆辛"), state, critique)
        self.assertEqual(len(patch.change), 2)
        self.assertNotIn("aggressive_gaze", [c.get("target") for c in patch.change])

    def test_memory_roundtrip_keeps_history_shape(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            memory = CharacterMemory(path)
            state = CharacterState(character="陆辛", version=4, locked={"hair": "plain-short"})
            memory.save(state)
            loaded = memory.load("陆辛")
            self.assertEqual(loaded.version, 4)
            self.assertEqual(loaded.locked["hair"], "plain-short")
            parsed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["character"], "陆辛")

    def test_lock_moves_feature_out_of_modifiable(self):
        state = CharacterState(character="陆辛", modifiable=["eyes", "hair"])
        CharacterMemory.lock(state, "hair", "plain-short")
        self.assertNotIn("hair", state.modifiable)
        self.assertEqual(state.locked["hair"], "plain-short")


if __name__ == "__main__":
    unittest.main()
