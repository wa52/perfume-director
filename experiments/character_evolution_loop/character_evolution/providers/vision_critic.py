from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..models import CanonProfile, CharacterState, Critique


HttpFn = Callable[[str, bytes | None, dict[str, str] | None, float], bytes]

CRITIC_DIMENSIONS = (
    "canon",
    "ordinary",
    "office_worker",
    "restraint",
    "identity_clarity",
    "overbeautification_control",
)


@dataclass(slots=True)
class VisionCriticConfig:
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: float = 180.0
    minimum_dimension: float = 0.0
    system_prompt: str = (
        "You are a visual character adaptation critic. Return one JSON object only. "
        "Judge the supplied image against the structured Canon/Character State. "
        "Do not invent novel facts. Do not reward generic attractiveness, hero aura, "
        "aggression, or fashionability unless explicitly supported."
    )


def _http(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _image_data_url(path: str | Path) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _state_payload(canon: CanonProfile, state: CharacterState) -> dict[str, Any]:
    return {
        "character": state.character,
        "canon_locks": state.locked,
        "canon_constraints": state.canon_constraints,
        "soft_direction": state.design_targets or canon.soft_traits,
        "editable_visual_features": state.modifiable,
        "rejected_design_choices": state.rejected,
        "forbidden_interpretations": state.forbidden_interpretations
        or canon.forbidden_interpretations,
        "human_feedback": state.human_feedback,
    }


def validate_critic_result(result: dict[str, Any]) -> Critique:
    if not isinstance(result, dict):
        raise ValueError("critic response must be an object")
    scores = result.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("critic response requires scores")
    clean_scores: dict[str, float] = {}
    for name in CRITIC_DIMENSIONS:
        value = scores.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError(f"critic score {name!r} must be 0..100")
        clean_scores[name] = float(value)

    candidate_id = result.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("critic response requires candidate_id")

    for key in ("problems", "change_requests", "locked_violations", "evidence_alignment"):
        if not isinstance(result.get(key, []), list):
            raise ValueError(f"critic field {key!r} must be a list")

    requests = result.get("change_requests", [])
    for request in requests:
        if not isinstance(request, dict) or not request.get("feature") or "target" not in request:
            raise ValueError("each change_request requires feature and target")

    return Critique(
        candidate_id=candidate_id,
        scores=clean_scores,
        problems=[str(item) for item in result.get("problems", [])],
        change_requests=[dict(item) for item in requests],
        locked_violations=[str(item) for item in result.get("locked_violations", [])],
        evidence_alignment=[str(item) for item in result.get("evidence_alignment", [])],
    )


class OpenAICompatibleVisionCritic:
    def __init__(self, config: VisionCriticConfig, http_fn: HttpFn = _http):
        self.config = config
        self.http_fn = http_fn

    def review(
        self,
        *,
        image_ref: str,
        canon: CanonProfile,
        state: CharacterState,
    ) -> Critique:
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise ValueError(f"missing API key environment variable {self.config.api_key_env}")

        rubric = {
            "score_dimensions": {
                "canon": "Does the image avoid contradicting locked Canon facts?",
                "ordinary": "Does the daily presentation read as ordinary/low protagonist aura rather than glamorized?",
                "office_worker": "Does the everyday presentation plausibly fit the Canon office-worker context without turning it into a costume?",
                "restraint": "Is the default expression/posture restrained rather than aggressive or theatrically dangerous?",
                "identity_clarity": "Is this a coherent reusable character identity rather than a generic unstable face?",
                "overbeautification_control": "Does it avoid unnecessary idol/webtoon-model beautification when Canon does not require it?",
            },
            "rules": [
                "A locked violation is concrete contradiction with canon_locks, not merely an aesthetic preference.",
                "Do not lock unresolved appearance from this one image.",
                "Return at most 3 change_requests, targeting editable features only.",
                "Each change target must be observable and specific.",
            ],
            "response_schema": {
                "candidate_id": image_ref,
                "scores": {name: 0 for name in CRITIC_DIMENSIONS},
                "problems": [],
                "change_requests": [{"feature": "eyes", "target": "less sharp"}],
                "locked_violations": [],
                "evidence_alignment": [],
            },
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "state": _state_payload(canon, state),
                                    "rubric": rubric,
                                },
                                ensure_ascii=False,
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": _image_data_url(image_ref)},
                        },
                    ],
                },
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
        message = response["choices"][0]["message"]["content"]
        result = json.loads(message)
        result["candidate_id"] = image_ref
        return validate_critic_result(result)
