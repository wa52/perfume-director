import tempfile
import unittest
from pathlib import Path

from character_evolution.acceptance import AcceptancePolicy
from character_evolution.loop import CharacterEvolutionLoop
from character_evolution.memory import CharacterMemory
from character_evolution.models import CanonProfile, CharacterState, Critique
from character_evolution.prompt_renderer import CanonPromptRenderer


class FakeGenerator:
    def generate(self, *, prompt, state, count):
        return ["img-a.png", "img-b.png"][:count]


class FakeCritic:
    def review(self, *, image_ref, canon, state):
        if image_ref == "img-a.png":
            return Critique(
                candidate_id="critic-A",
                scores={
                    "canon": 90,
                    "ordinary": 82,
                    "office_worker": 80,
                    "restraint": 83,
                    "identity_clarity": 76,
                    "overbeautification_control": 85,
                },
            )
        return Critique(
            candidate_id="critic-B",
            scores={
                "canon": 100,
                "ordinary": 99,
                "office_worker": 99,
                "restraint": 99,
                "identity_clarity": 99,
                "overbeautification_control": 99,
            },
            locked_violations=["age"],
        )


class LoopAcceptanceTests(unittest.TestCase):
    def test_selected_image_ref_tracks_generator_ref_not_critic_id(self):
        with tempfile.TemporaryDirectory() as td:
            memory = CharacterMemory(Path(td) / "state.json")
            loop = CharacterEvolutionLoop(
                generator=FakeGenerator(),
                critic=FakeCritic(),
                prompt_renderer=CanonPromptRenderer(),
                memory=memory,
                acceptance_policy=AcceptancePolicy(),
            )
            state, top = loop.run_round(
                canon=CanonProfile(character="陆辛"),
                state=CharacterState(character="陆辛"),
                candidates=2,
                shortlist=2,
            )
            self.assertEqual(state.history[-1].candidate_id, "critic-A")
            self.assertEqual(state.history[-1].image_ref, "img-a.png")
            self.assertTrue(state.history[-1].accepted)
            self.assertEqual(top[0].candidate_id, "critic-A")


if __name__ == "__main__":
    unittest.main()
