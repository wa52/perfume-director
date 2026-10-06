import unittest

from character_evolution.human_choice import apply_human_choice
from character_evolution.models import CanonProfile, CharacterState, IterationRecord


class HumanDirectorAdviceTests(unittest.TestCase):
    def test_human_change_has_priority_over_agent_change(self):
        batch = {
            "shortlist": [
                {
                    "label": "B",
                    "image_ref": "b.png",
                    "scores": {
                        "canon": 90,
                        "ordinary": 80,
                        "office_worker": 80,
                        "restraint": 80,
                        "identity_clarity": 80,
                        "overbeautification_control": 80,
                    },
                    "problems": ["eyes too sharp"],
                    "change_requests": [
                        {"feature": "eyes", "target": "slightly softer"}
                    ],
                    "locked_violations": [],
                    "evidence_alignment": [],
                    "director_advice": {
                        "candidate_id": "b.png",
                        "summary": "Preserve face, refine gaze.",
                        "strengths": ["face identity is stable"],
                        "priority_issues": [
                            {
                                "priority": 1,
                                "feature": "eyes",
                                "diagnosis": "gaze is too sharp",
                            }
                        ],
                        "keep": ["face_shape"],
                        "changes": [
                            {
                                "priority": 1,
                                "feature": "eyes",
                                "target": "softer gaze",
                                "why": "less aggressive",
                            }
                        ],
                        "do_not_change": ["face_shape"],
                        "next_round_goal": "Keep identity and soften gaze.",
                        "evidence_notes": [],
                    },
                }
            ]
        }
        state = CharacterState(
            character="陆辛",
            version=2,
            modifiable=["eyes", "clothing"],
            history=[
                IterationRecord(
                    version=2,
                    candidate_id="a.png",
                    image_ref="a.png",
                    score=80,
                    accepted=False,
                    critique={},
                    patch={},
                )
            ],
        )

        apply_human_choice(
            state=state,
            canon=CanonProfile(character="陆辛"),
            batch_report=batch,
            label="B",
            feedback="眼神再自然一点。",
            explicit_changes=[
                {"feature": "eyes", "target": "neutral, relaxed, not staring"}
            ],
        )

        changes = state.history[-1].patch["change"]
        self.assertEqual(changes[0]["feature"], "eyes")
        self.assertEqual(changes[0]["target"], "neutral, relaxed, not staring")
        self.assertEqual(
            state.history[-1].director_advice["next_round_goal"],
            "Keep identity and soften gaze.",
        )
        self.assertIn("眼神再自然一点。", state.human_feedback)


if __name__ == "__main__":
    unittest.main()
