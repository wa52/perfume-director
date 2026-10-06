import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from character_evolution.loop import CharacterEvolutionLoop
from character_evolution.memory import CharacterMemory
from character_evolution.models import CanonProfile, CharacterState, Critique
from character_evolution.providers.director_agent import (
    DirectorAgentConfig,
    OpenAICompatibleDirectorAgent,
)


class FakeGenerator:
    def __init__(self, root: Path):
        self.root = root

    def generate(self, *, prompt, state, count):
        refs = []
        for index in range(count):
            path = self.root / f"candidate-{index}.png"
            path.write_bytes(b"png")
            refs.append(str(path))
        return refs


class FakeCritic:
    def review(self, *, image_ref, canon, state):
        return Critique(
            candidate_id=image_ref,
            scores={
                "canon": 90,
                "context_fit": 80,
                "identity_clarity": 82,
                "character_specificity": 78,
                "design_coherence": 80,
                "overbeautification_control": 85,
            },
            problems=["eyes are too sharp", "clothing feels too fashionable"],
            change_requests=[
                {"feature": "eyes", "target": "softer and more neutral"},
                {"feature": "clothing", "target": "more practical"},
            ],
            evidence_alignment=["work context is plausible"],
        )


class FakeRenderer:
    def render(self, *, canon, state, patch=None):
        changes = [] if patch is None else patch.change
        return json.dumps(changes, ensure_ascii=False)


class BrokenDirector:
    def advise(self, *, canon, state, critique):
        raise RuntimeError("director unavailable")


class DirectorAgentTests(unittest.TestCase):
    def test_llm_director_filters_locked_and_limits_changes(self):
        def fake_http(url, data=None, headers=None, timeout=60):
            payload = json.loads(data)
            self.assertIn("human_feedback", json.loads(payload["messages"][1]["content"]))
            raw = {
                "summary": "Keep the face, soften the eyes.",
                "strengths": ["identity reads clearly"],
                "priority_issues": [
                    {"priority": 1, "feature": "eyes", "diagnosis": "too sharp"}
                ],
                "keep": ["face_shape"],
                "changes": [
                    {"priority": 1, "feature": "face_shape", "target": "sharper", "why": "bad"},
                    {"priority": 2, "feature": "eyes", "target": "softer", "why": "better restraint"},
                    {"priority": 3, "feature": "clothing", "target": "simpler", "why": "better context"},
                    {"priority": 4, "feature": "posture", "target": "neutral", "why": "less theatrical"},
                ],
                "do_not_change": [],
                "next_round_goal": "Preserve identity and remove sharpness.",
                "evidence_notes": ["Respect Canon and human feedback."],
            }
            return json.dumps({
                "choices": [{"message": {"content": json.dumps(raw)}}]
            }).encode()

        agent = OpenAICompatibleDirectorAgent(
            DirectorAgentConfig(
                base_url="https://example.invalid/v1",
                model="director-model",
                api_key_env="TEST_DIRECTOR_KEY",
                max_changes=2,
            ),
            http_fn=fake_http,
        )
        state = CharacterState(
            character="陈菁",
            locked={"face_shape": "keep"},
            modifiable=["eyes", "clothing", "posture"],
            human_feedback=["眼神不要太凶"],
        )
        with patch.dict(os.environ, {"TEST_DIRECTOR_KEY": "secret"}):
            advice = agent.advise(
                canon=CanonProfile(character="陈菁"),
                state=state,
                critique=FakeCritic().review(
                    image_ref="candidate.png",
                    canon=CanonProfile(character="陈菁"),
                    state=state,
                ),
            )

        self.assertEqual([x["feature"] for x in advice.changes], ["eyes", "clothing"])
        self.assertIn("face_shape", advice.do_not_change)
        self.assertNotIn("face_shape", [x["feature"] for x in advice.changes])
        self.assertEqual(advice.next_round_goal, "Preserve identity and remove sharpness.")

    def test_loop_falls_back_to_rule_director_if_agent_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = CharacterState(
                character="陈菁",
                version=1,
                modifiable=["eyes", "clothing"],
            )
            loop = CharacterEvolutionLoop(
                generator=FakeGenerator(root),
                critic=FakeCritic(),
                prompt_renderer=FakeRenderer(),
                memory=CharacterMemory(root / "state.json"),
                director_agent=BrokenDirector(),
            )
            state, top = loop.run_round(
                canon=CanonProfile(character="陈菁"),
                state=state,
                candidates=3,
                shortlist=3,
            )

            self.assertEqual(len(top), 3)
            self.assertEqual(len(loop.last_advice), 3)
            self.assertEqual(len(loop.last_advice_errors), 3)
            self.assertTrue(state.history[-1].director_advice)
            self.assertIn("eyes", [x["feature"] for x in state.history[-1].patch["change"]])


if __name__ == "__main__":
    unittest.main()
