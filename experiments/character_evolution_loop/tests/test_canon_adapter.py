import unittest

from character_evolution.canon_adapter import apply_contract, contract_to_canon_profile
from character_evolution.models import CharacterState, RevisionPatch
from character_evolution.prompt_renderer import CanonPromptRenderer


CONTRACT = {
    "schema_version": "character-canon-contract/1",
    "character": {"id": "CHAR-LUXIN", "name": "陆辛"},
    "provenance": {
        "source_profile": "canon/lu_xin.profile.json",
        "source_profile_sha256": "fixture",
        "contains_novel_passages": False,
    },
    "locked_facts": [
        {
            "feature": "age",
            "value": 23,
            "source_fact_id": "age",
            "confidence": 1.0,
            "evidence": [
                {
                    "chapter_id": "ch-0006",
                    "chapter_title": "第五章",
                    "chunk_id": "ch-0006-ck-002",
                    "line_start": 481,
                    "line_end": 504,
                }
            ],
        },
        {
            "feature": "daily_role_context",
            "value": "company_office_worker",
            "source_fact_id": "office_work",
            "confidence": 0.99,
            "evidence": [
                {
                    "chapter_id": "ch-0034",
                    "chapter_title": "第三十三章",
                    "chunk_id": "ch-0034-ck-002",
                    "line_start": 2675,
                    "line_end": 2696,
                }
            ],
        },
    ],
    "soft_constraints": [
        {
            "feature": "ordinary_presentation",
            "instruction": "日常形象应保持普通、低主角光环。",
            "confidence": 0.82,
            "evidence": [
                {
                    "chapter_id": "ch-0201",
                    "chapter_title": "第一百九十九章",
                    "chunk_id": "ch-0201-ck-002",
                    "line_start": 18054,
                    "line_end": 18079,
                }
            ],
        }
    ],
    "unresolved_visual_features": [
        "face_shape",
        "hairstyle",
        "eye_shape",
        "default_clothing",
        "attractiveness",
    ],
    "forbidden_interpretations": ["不能因为主角身份自动强化成英雄式构图或强者脸。"],
}


class CanonAdapterTests(unittest.TestCase):
    def test_contract_preserves_human_feedback_and_separates_canon(self):
        state = CharacterState(
            character="陆辛",
            modifiable=["posture"],
            human_feedback=["不要主动往帅或强者方向设计。"],
        )
        apply_contract(CONTRACT, state)
        self.assertEqual(state.locked["age"], 23)
        self.assertEqual(state.locked["daily_role_context"], "company_office_worker")
        self.assertEqual(state.human_feedback, ["不要主动往帅或强者方向设计。"])
        self.assertEqual(state.traits, {})
        self.assertEqual(state.design_targets["ordinary_presentation"]["confidence"], 0.82)
        self.assertTrue(state.evidence_refs["age"])

    def test_unresolved_visual_features_remain_editable_with_aliases(self):
        state = apply_contract(CONTRACT, CharacterState(character="陆辛"))
        self.assertIn("face_shape", state.modifiable)
        self.assertIn("eyes", state.modifiable)
        self.assertIn("clothing", state.modifiable)
        self.assertNotIn("age", state.modifiable)

    def test_canon_conflict_is_rejected(self):
        state = CharacterState(character="陆辛", locked={"age": 29})
        with self.assertRaises(ValueError):
            apply_contract(CONTRACT, state)

    def test_prompt_renderer_keeps_hard_and_soft_constraints_separate(self):
        state = apply_contract(CONTRACT, CharacterState(character="陆辛"))
        state.human_feedback.append("更像普通上班族。")
        canon = contract_to_canon_profile(CONTRACT)
        rendered = CanonPromptRenderer().render(
            canon=canon,
            state=state,
            patch=RevisionPatch(change=[{"feature": "eyes", "target": "less sharp"}]),
        )
        self.assertIn("CANON_LOCKS:", rendered)
        self.assertIn("- age: 23", rendered)
        self.assertIn("SOFT_DIRECTION:", rendered)
        self.assertIn("日常形象应保持普通、低主角光环。", rendered)
        self.assertIn("EDITABLE_VISUAL_FEATURES:", rendered)
        self.assertIn("CHANGE eyes: less sharp", rendered)
        self.assertIn("HUMAN_FEEDBACK:", rendered)


if __name__ == "__main__":
    unittest.main()
