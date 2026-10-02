from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from ..models import CanonProfile, CharacterState, Critique, DirectorAdvice


HttpFn = Callable[[str, bytes | None, dict[str, str] | None, float], bytes]


@dataclass(slots=True)
class DirectorAgentConfig:
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: float = 120.0
    max_changes: int = 3
    system_prompt: str = (
        "You are the Character Director Agent for a novel-to-animation production. "
        "The Vision Critic has already inspected the image. Your job is to turn its findings, "
        "Canon constraints, character memory, and human feedback into a small actionable next-round plan. "
        "Never invent novel facts. Preserve identity. Human feedback outranks automatic aesthetics. "
        "Change at most three editable features. Return JSON only."
    )


def _http(
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _clean_advice(
    raw: dict[str, Any],
    *,
    candidate_id: str,
    state: CharacterState,
    max_changes: int,
) -> DirectorAdvice:
    editable = set(state.modifiable)
    locked = set(state.locked)
    rejected = set(state.rejected)

    changes = []
    for item in raw.get("changes", []):
        if not isinstance(item, dict):
            continue
        feature = str(item.get("feature", "")).strip()
        target = str(item.get("target", "")).strip()
        if not feature or not target or feature in locked:
            continue
        if editable and feature not in editable:
            continue
        if target in rejected:
            continue
        changes.append(
            {
                "feature": feature,
                "target": target,
                "why": str(item.get("why", "")).strip(),
                "priority": int(item.get("priority", len(changes) + 1)),
            }
        )
        if len(changes) >= max_changes:
            break

    issues = []
    for item in raw.get("priority_issues", [])[:max_changes]:
        if isinstance(item, dict):
            issues.append(
                {
                    "priority": int(item.get("priority", len(issues) + 1)),
                    "feature": str(item.get("feature", "")).strip() or "overall",
                    "diagnosis": str(item.get("diagnosis", "")).strip(),
                }
            )

    keep = [str(x) for x in raw.get("keep", []) if str(x).strip()]
    do_not_change = [str(x) for x in raw.get("do_not_change", []) if str(x).strip()]
    for feature in state.locked:
        if feature not in keep:
            keep.append(feature)
        if feature not in do_not_change:
            do_not_change.append(feature)

    return DirectorAdvice(
        candidate_id=candidate_id,
        summary=str(raw.get("summary", "")).strip(),
        strengths=[str(x) for x in raw.get("strengths", []) if str(x).strip()][:4],
        priority_issues=issues,
        keep=keep,
        changes=changes,
        do_not_change=do_not_change,
        next_round_goal=str(raw.get("next_round_goal", "")).strip(),
        evidence_notes=[str(x) for x in raw.get("evidence_notes", []) if str(x).strip()][:4],
    )


class OpenAICompatibleDirectorAgent:
    def __init__(self, config: DirectorAgentConfig, http_fn: HttpFn = _http):
        self.config = config
        self.http_fn = http_fn

    def advise(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        critique: Critique,
    ) -> DirectorAdvice:
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise ValueError(f"missing API key environment variable {self.config.api_key_env}")

        request_payload = {
            "character": state.character,
            "canon_hard_facts": canon.hard_facts,
            "canon_soft_traits": canon.soft_traits,
            "canon_constraints": state.canon_constraints,
            "design_targets": state.design_targets,
            "locked_features": state.locked,
            "editable_features": state.modifiable,
            "rejected_designs": state.rejected,
            "human_feedback": state.human_feedback,
            "forbidden_interpretations": state.forbidden_interpretations,
            "critic": {
                "scores": critique.scores,
                "problems": critique.problems,
                "change_requests": critique.change_requests,
                "locked_violations": critique.locked_violations,
                "evidence_alignment": critique.evidence_alignment,
            },
            "required_output": {
                "summary": "one concise director judgment",
                "strengths": ["what should be preserved"],
                "priority_issues": [
                    {"priority": 1, "feature": "eyes", "diagnosis": "observable problem"}
                ],
                "keep": ["features or qualities to preserve"],
                "changes": [
                    {
                        "priority": 1,
                        "feature": "eyes",
                        "target": "specific observable next state",
                        "why": "why this improves Canon/identity",
                    }
                ],
                "do_not_change": ["locked/stable features"],
                "next_round_goal": "single sentence target for the next batch",
                "evidence_notes": ["Canon/human-feedback guardrail"],
            },
            "rules": [
                f"Return at most {self.config.max_changes} changes.",
                "Only change editable features.",
                "Never contradict locked features.",
                "Do not turn soft context into invented hard appearance facts.",
                "Do not rewrite the whole character; use a bounded patch.",
            ],
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(request_payload, ensure_ascii=False),
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
        raw = json.loads(response["choices"][0]["message"]["content"])
        return _clean_advice(
            raw,
            candidate_id=critique.candidate_id,
            state=state,
            max_changes=self.config.max_changes,
        )
