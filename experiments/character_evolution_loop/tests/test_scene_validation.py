import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from character_evolution.models import CanonProfile, CharacterState
from character_evolution.providers.scene_validator import (
    OpenAICompatibleSceneValidator,
    SceneValidatorConfig,
    validate_scene_result,
)
from character_evolution.scene_validation import SceneAcceptancePolicy


class SceneValidationTests(unittest.TestCase):
    def test_scene_policy_rejects_identity_regression(self):
        result = validate_scene_result(
            {
                "scores": {
                    "identity_consistency": 95,
                    "canon": 95,
                    "scene_acting": 90,
                    "style_consistency": 90,
                },
                "scene_results": [
                    {"scene_id": "office", "identity_score": 95, "canon_score": 95, "problems": []},
                    {"scene_id": "home", "identity_score": 95, "canon_score": 95, "problems": []},
                    {"scene_id": "abnormal", "identity_score": 95, "canon_score": 95, "problems": []},
                ],
                "problems": [],
                "regression_features": ["face_shape"],
            }
        )
        self.assertFalse(SceneAcceptancePolicy().passes(result))

    def test_scene_validator_sends_anchor_plus_three_scenes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = {}
            for name in ("anchor", "office", "home", "abnormal"):
                path = root / f"{name}.png"
                path.write_bytes((name + "-bytes").encode())
                paths[name] = str(path)

            def fake_http(url, data=None, headers=None, timeout=60):
                payload = json.loads(data)
                content = payload["messages"][1]["content"]
                image_parts = [part for part in content if part.get("type") == "image_url"]
                self.assertEqual(len(image_parts), 4)
                raw = {
                    "scores": {
                        "identity_consistency": 88,
                        "canon": 90,
                        "scene_acting": 84,
                        "style_consistency": 85,
                    },
                    "scene_results": [
                        {"scene_id": "office", "identity_score": 90, "canon_score": 91, "problems": []},
                        {"scene_id": "home", "identity_score": 87, "canon_score": 90, "problems": []},
                        {"scene_id": "abnormal", "identity_score": 86, "canon_score": 88, "problems": []},
                    ],
                    "problems": [],
                    "regression_features": [],
                }
                return json.dumps({
                    "choices": [{"message": {"content": json.dumps(raw)}}]
                }).encode()

            validator = OpenAICompatibleSceneValidator(
                SceneValidatorConfig(
                    base_url="https://example.invalid/v1",
                    model="vision",
                    api_key_env="TEST_SCENE_KEY",
                ),
                http_fn=fake_http,
            )
            with patch.dict(os.environ, {"TEST_SCENE_KEY": "secret"}):
                result = validator.review(
                    anchor_image=paths["anchor"],
                    scene_images={
                        "office": paths["office"],
                        "home": paths["home"],
                        "abnormal": paths["abnormal"],
                    },
                    canon=CanonProfile(character="陆辛"),
                    state=CharacterState(character="陆辛"),
                )
            self.assertTrue(SceneAcceptancePolicy().passes(result))


if __name__ == "__main__":
    unittest.main()
