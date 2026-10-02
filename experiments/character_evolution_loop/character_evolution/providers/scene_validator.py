from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..models import CanonProfile, CharacterState
from ..scene_validation import DEFAULT_SCENES, SceneValidationResult


HttpFn = Callable[[str, bytes | None, dict[str, str] | None, float], bytes]
SCENE_DIMENSIONS = (
    "identity_consistency",
    "canon",
    "scene_acting",
    "style_consistency",
)


@dataclass(slots=True)
class SceneValidatorConfig:
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: float = 180.0


def _http(url: str, data=None, headers=None, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _image_part(path: str | Path) -> dict:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{encoded}"},
    }


def validate_scene_result(raw: dict) -> SceneValidationResult:
    if not isinstance(raw, dict) or not isinstance(raw.get("scores"), dict):
        raise ValueError("scene validator requires scores object")
    scores = {}
    for name in SCENE_DIMENSIONS:
        value = raw["scores"].get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError(f"scene score {name!r} must be 0..100")
        scores[name] = float(value)

    scene_results = raw.get("scene_results", [])
    if not isinstance(scene_results, list):
        raise ValueError("scene_results must be a list")
    known = {scene.scene_id for scene in DEFAULT_SCENES}
    seen = set()
    for item in scene_results:
        if not isinstance(item, dict) or item.get("scene_id") not in known:
            raise ValueError("scene_results contains unknown scene_id")
        seen.add(item["scene_id"])
    if seen != known:
        raise ValueError("scene_results must cover office, home and abnormal scenes")

    problems = raw.get("problems", [])
    regression = raw.get("regression_features", [])
    if not isinstance(problems, list) or not isinstance(regression, list):
        raise ValueError("problems and regression_features must be lists")

    return SceneValidationResult(
        scores=scores,
        scene_results=[dict(item) for item in scene_results],
        problems=[str(x) for x in problems],
        regression_features=[str(x) for x in regression],
    )


class OpenAICompatibleSceneValidator:
    def __init__(self, config: SceneValidatorConfig, http_fn: HttpFn = _http):
        self.config = config
        self.http_fn = http_fn

    def review(
        self,
        *,
        anchor_image: str,
        scene_images: dict[str, str],
        canon: CanonProfile,
        state: CharacterState,
    ) -> SceneValidationResult:
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise ValueError(f"missing API key environment variable {self.config.api_key_env}")
        expected = {scene.scene_id for scene in DEFAULT_SCENES}
        if set(scene_images) != expected:
            raise ValueError("scene_images must contain exactly office, home and abnormal")

        instructions = {
            "character": state.character,
            "canon_locks": state.locked,
            "soft_direction": state.design_targets or canon.soft_traits,
            "forbidden_interpretations": state.forbidden_interpretations,
            "scenes": [
                {
                    "scene_id": scene.scene_id,
                    "title": scene.title,
                    "identity_rule": scene.identity_rule,
                    "canon_rule": scene.canon_rule,
                }
                for scene in DEFAULT_SCENES
            ],
            "scoring": {
                "identity_consistency": "Same person as anchor across all three scenes.",
                "canon": "No contradiction with locked Canon or forbidden interpretations.",
                "scene_acting": "Scene-dependent acting is appropriate without changing core identity.",
                "style_consistency": "Same 2D production design language across scenes.",
            },
            "response_schema": {
                "scores": {name: 0 for name in SCENE_DIMENSIONS},
                "scene_results": [
                    {
                        "scene_id": "office",
                        "identity_score": 0,
                        "canon_score": 0,
                        "problems": [],
                    },
                    {
                        "scene_id": "home",
                        "identity_score": 0,
                        "canon_score": 0,
                        "problems": [],
                    },
                    {
                        "scene_id": "abnormal",
                        "identity_score": 0,
                        "canon_score": 0,
                        "problems": [],
                    },
                ],
                "problems": [],
                "regression_features": [],
            },
        }
        content = [
            {
                "type": "text",
                "text": (
                    "Image 1 is the human-selected identity anchor. "
                    "Images 2-4 are office, home, abnormal scenes in that order. "
                    "Judge identity continuity, not identical expression or pose. "
                    "Return one JSON object only.\n"
                    + json.dumps(instructions, ensure_ascii=False)
                ),
            },
            _image_part(anchor_image),
            _image_part(scene_images["office"]),
            _image_part(scene_images["home"]),
            _image_part(scene_images["abnormal"]),
        ]
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a character continuity supervisor for animation adaptation. "
                        "The selected anchor defines visual identity. Novel Canon defines facts. "
                        "Do not demand identical pose/expression across scenes, and do not invent appearance Canon."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "response_format": {"type": "json_object"},
        }
        response = json.loads(
            self.http_fn(
                self.config.base_url.rstrip("/") + "/chat/completions",
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                {
                    "Authorization": "Bearer " + key,
                    "Content-Type": "application/json",
                },
                self.config.timeout_seconds,
            )
        )
        raw = json.loads(response["choices"][0]["message"]["content"])
        return validate_scene_result(raw)
