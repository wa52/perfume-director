import unittest

from character_evolution.generation_prompt import CharacterGenerationPrompt
from character_evolution.models import CanonProfile, CharacterState


class GenerationPromptTests(unittest.TestCase):
    def test_prompt_uses_canon_state_instead_of_hardcoded_character_facts(self):
        state = CharacterState(
            character="测试角色",
            locked={"age": 31, "daily_role_context": "researcher"},
            modifiable=["hairstyle", "eyes"],
            design_targets={
                "ordinary_presentation": {
                    "instruction": "保持低调，不做英雄化处理。",
                    "confidence": 0.8,
                }
            },
        )
        prompt = CharacterGenerationPrompt().render(
            canon=CanonProfile(character="测试角色"),
            state=state,
        )
        self.assertIn("single character: 测试角色", prompt)
        self.assertIn("canon age: 31", prompt)
        self.assertIn("canon daily role/context: researcher", prompt)
        self.assertNotIn("age: 23", prompt)
        self.assertNotIn("office-worker", prompt)
        self.assertIn("open visual exploration, not canon facts: hairstyle, eyes", prompt)


if __name__ == "__main__":
    unittest.main()
