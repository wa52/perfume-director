import unittest

from character_evolution.human_choice import apply_human_choice
from character_evolution.models import CanonProfile, CharacterState, IterationRecord


def batch():
    return {
        "shortlist": [
            {
                "label": "A",
                "image_ref": "a.png",
                "scores": {
                    "canon": 90,
                    "ordinary": 80,
                    "office_worker": 80,
                    "restraint": 80,
                    "identity_clarity": 80,
                    "overbeautification_control": 80,
                },
                "problems": [],
                "change_requests": [],
                "locked_violations": [],
                "evidence_alignment": [],
            },
            {
                "label": "B",
                "image_ref": "b.png",
                "scores": {
                    "canon": 88,
                    "ordinary": 84,
                    "office_worker": 82,
                    "restraint": 84,
                    "identity_clarity": 86,
                    "overbeautification_control": 90,
                },
                "problems": ["eyes are too sharp"],
                "change_requests": [{"feature": "eyes", "target": "softer"}],
                "locked_violations": [],
                "evidence_alignment": [],
            },
        ]
    }


class HumanChoiceTests(unittest.TestCase):
    def test_human_choice_promotes_non_auto_candidate_and_keeps_feedback(self):
        state = CharacterState(
            character="陆辛",
            version=2,
            modifiable=["eyes", "face_shape"],
            history=[
                IterationRecord(
                    version=2,
                    candidate_id="a.png",
                    image_ref="a.png",
                    score=82,
                    accepted=True,
                    critique={},
                    patch={},
                )
            ],
        )
        apply_human_choice(
            state=state,
            canon=CanonProfile(character="陆辛"),
            batch_report=batch(),
            label="B",
            feedback="B最接近，但眼睛不对。",
            explicit_changes=[{"feature": "eyes", "target": "less sharp and more neutral"}],
        )
        self.assertEqual(state.identity_anchor, "b.png")
        self.assertIn("B最接近，但眼睛不对。", state.human_feedback)
        self.assertEqual(state.history[-1].image_ref, "b.png")
        self.assertEqual(state.history[-1].human_feedback, "B最接近，但眼睛不对。")
        self.assertIn("less sharp", state.prompt)

    def test_human_lock_is_preserved(self):
        state = CharacterState(character="陆辛", modifiable=["face_shape"])
        apply_human_choice(
            state=state,
            canon=CanonProfile(character="陆辛"),
            batch_report=batch(),
            label="A",
            locks={"face_shape": "keep-from-A"},
        )
        self.assertEqual(state.locked["face_shape"], "keep-from-A")
        self.assertNotIn("face_shape", state.modifiable)

    def test_canon_violation_cannot_be_promoted(self):
        bad = batch()
        bad["shortlist"][0]["locked_violations"] = ["age"]
        with self.assertRaises(ValueError):
            apply_human_choice(
                state=CharacterState(character="陆辛"),
                canon=CanonProfile(character="陆辛"),
                batch_report=bad,
                label="A",
            )


if __name__ == "__main__":
    unittest.main()
