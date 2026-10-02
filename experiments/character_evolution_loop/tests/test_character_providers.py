import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from character_evolution.acceptance import AcceptancePolicy, shortlist
from character_evolution.models import CanonProfile, CharacterState, Critique
from character_evolution.providers.comfyui import ComfyUICharacterGenerator, ComfyUIConfig
from character_evolution.providers.vision_critic import (
    OpenAICompatibleVisionCritic,
    VisionCriticConfig,
)


class CharacterProviderTests(unittest.TestCase):
    def test_comfyui_generator_patches_prompt_and_seed_and_downloads_image(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workflow = {
                "3": {"inputs": {"seed": 0}, "class_type": "KSampler"},
                "6": {"inputs": {"text": "old"}, "class_type": "CLIPTextEncode"},
                "9": {"inputs": {}, "class_type": "SaveImage"},
            }
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            submitted = []

            def fake_http(url, data=None, headers=None, timeout=60):
                if url.endswith("/prompt"):
                    body = json.loads(data)
                    submitted.append(body["prompt"])
                    return json.dumps({"prompt_id": f"p{len(submitted)}"}).encode()
                if "/history/" in url:
                    prompt_id = url.rsplit("/", 1)[-1]
                    return json.dumps({
                        prompt_id: {
                            "status": {"completed": True},
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": prompt_id + ".png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            },
                        }
                    }).encode()
                if "/view?" in url:
                    return b"fake-png"
                raise AssertionError(url)

            generator = ComfyUICharacterGenerator(
                ComfyUIConfig(
                    base_url="http://127.0.0.1:8190",
                    workflow_path=workflow_path,
                    output_node="9",
                    prompt_node="6",
                    seed_node="3",
                    seed_start=100,
                    poll_seconds=0,
                    output_dir=root / "runs",
                ),
                http_fn=fake_http,
            )
            refs = generator.generate(
                prompt="character prompt",
                state=CharacterState(character="陆辛", version=1),
                count=2,
            )

            self.assertEqual(len(refs), 2)
            self.assertEqual(submitted[0]["6"]["inputs"]["text"], "character prompt")
            self.assertEqual(submitted[0]["3"]["inputs"]["seed"], 1100)
            self.assertEqual(submitted[1]["3"]["inputs"]["seed"], 1101)
            self.assertEqual(Path(refs[0]).read_bytes(), b"fake-png")

    def test_identity_anchor_is_uploaded_and_mapped_into_reference_node(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            anchor = root / "anchor.png"
            anchor.write_bytes(b"anchor-bytes")
            workflow = {
                "3": {"inputs": {"seed": 0}, "class_type": "KSampler"},
                "6": {"inputs": {"text": "old"}, "class_type": "CLIPTextEncode"},
                "10": {"inputs": {"image": "old.png"}, "class_type": "LoadImage"},
                "9": {"inputs": {}, "class_type": "SaveImage"},
            }
            workflow_path = root / "workflow.json"
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            submitted = []

            def fake_http(url, data=None, headers=None, timeout=60):
                if url.endswith("/upload/image"):
                    return json.dumps({"name": "uploaded-anchor.png", "subfolder": ""}).encode()
                if url.endswith("/prompt"):
                    body = json.loads(data)
                    submitted.append(body["prompt"])
                    return json.dumps({"prompt_id": "p1"}).encode()
                if "/history/" in url:
                    return json.dumps({
                        "p1": {
                            "status": {"completed": True},
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "p1.png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            },
                        }
                    }).encode()
                if "/view?" in url:
                    return b"scene-png"
                raise AssertionError(url)

            generator = ComfyUICharacterGenerator(
                ComfyUIConfig(
                    base_url="http://127.0.0.1:8190",
                    workflow_path=workflow_path,
                    output_node="9",
                    prompt_node="6",
                    seed_node="3",
                    reference_image_node="10",
                    output_dir=root / "runs",
                    poll_seconds=0,
                ),
                http_fn=fake_http,
            )
            generator.generate(
                prompt="next version",
                state=CharacterState(
                    character="陆辛",
                    version=2,
                    identity_anchor=str(anchor),
                ),
                count=1,
            )
            self.assertEqual(
                submitted[0]["10"]["inputs"]["image"],
                "uploaded-anchor.png",
            )

    def test_vision_critic_returns_structured_critique(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "candidate.png"
            image.write_bytes(b"png-bytes")

            def fake_http(url, data=None, headers=None, timeout=60):
                payload = json.loads(data)
                self.assertEqual(payload["model"], "vision-model")
                self.assertEqual(headers["Authorization"], "Bearer secret")
                result = {
                    "candidate_id": "ignored",
                    "scores": {
                        "canon": 92,
                        "ordinary": 80,
                        "office_worker": 78,
                        "restraint": 84,
                        "identity_clarity": 76,
                        "overbeautification_control": 88,
                    },
                    "problems": ["eyes are too sharp"],
                    "change_requests": [{"feature": "eyes", "target": "less sharp"}],
                    "locked_violations": [],
                    "evidence_alignment": ["office-worker context is plausible"],
                }
                return json.dumps({
                    "choices": [{"message": {"content": json.dumps(result)}}]
                }).encode()

            critic = OpenAICompatibleVisionCritic(
                VisionCriticConfig(
                    base_url="https://example.invalid/v1",
                    model="vision-model",
                    api_key_env="TEST_CHARACTER_VISION_KEY",
                ),
                http_fn=fake_http,
            )
            with patch.dict(os.environ, {"TEST_CHARACTER_VISION_KEY": "secret"}):
                review = critic.review(
                    image_ref=str(image),
                    canon=CanonProfile(character="陆辛"),
                    state=CharacterState(character="陆辛"),
                )
            self.assertEqual(review.candidate_id, str(image))
            self.assertEqual(review.scores["canon"], 92)
            self.assertEqual(review.change_requests[0]["feature"], "eyes")

    def test_acceptance_rejects_lock_violation_even_with_high_scores(self):
        scores = {
            "canon": 99,
            "ordinary": 99,
            "office_worker": 99,
            "restraint": 99,
            "identity_clarity": 99,
            "overbeautification_control": 99,
        }
        critique = Critique(
            candidate_id="A",
            scores=scores,
            locked_violations=["age presentation contradicts lock"],
        )
        self.assertFalse(AcceptancePolicy().passes(critique))

    def test_shortlist_prioritizes_lock_safe_candidates(self):
        unsafe = Critique(
            candidate_id="unsafe",
            scores={
                "canon": 100,
                "ordinary": 100,
                "office_worker": 100,
                "restraint": 100,
                "identity_clarity": 100,
                "overbeautification_control": 100,
            },
            locked_violations=["lock violation"],
        )
        safe = Critique(
            candidate_id="safe",
            scores={
                "canon": 80,
                "ordinary": 70,
                "office_worker": 70,
                "restraint": 70,
                "identity_clarity": 70,
                "overbeautification_control": 70,
            },
        )
        self.assertEqual(shortlist([unsafe, safe], 1)[0].candidate_id, "safe")


if __name__ == "__main__":
    unittest.main()
