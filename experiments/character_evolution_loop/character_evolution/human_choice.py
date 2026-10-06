from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .director import CharacterDirector
from .generation_prompt import CharacterGenerationPrompt
from .memory import CharacterMemory
from .models import CanonProfile, CharacterState, Critique, DirectorAdvice


def _critique_from_entry(entry: dict[str, Any]) -> Critique:
    return Critique(
        candidate_id=str(entry["image_ref"]),
        scores={k: float(v) for k, v in entry.get("scores", {}).items()},
        problems=[str(x) for x in entry.get("problems", [])],
        change_requests=[dict(x) for x in entry.get("change_requests", [])],
        locked_violations=[str(x) for x in entry.get("locked_violations", [])],
        evidence_alignment=[str(x) for x in entry.get("evidence_alignment", [])],
    )


def _advice_from_entry(entry: dict[str, Any]) -> DirectorAdvice | None:
    raw = entry.get("director_advice")
    if not isinstance(raw, dict):
        return None
    return DirectorAdvice(
        candidate_id=str(raw.get("candidate_id") or entry.get("image_ref", "")),
        summary=str(raw.get("summary", "")),
        strengths=[str(x) for x in raw.get("strengths", [])],
        priority_issues=[dict(x) for x in raw.get("priority_issues", []) if isinstance(x, dict)],
        keep=[str(x) for x in raw.get("keep", [])],
        changes=[dict(x) for x in raw.get("changes", []) if isinstance(x, dict)],
        do_not_change=[str(x) for x in raw.get("do_not_change", [])],
        next_round_goal=str(raw.get("next_round_goal", "")),
        evidence_notes=[str(x) for x in raw.get("evidence_notes", [])],
    )


def apply_human_choice(
    *,
    state: CharacterState,
    canon: CanonProfile,
    batch_report: dict[str, Any],
    label: str,
    feedback: str | None = None,
    locks: dict[str, Any] | None = None,
    rejected: list[str] | None = None,
    explicit_changes: list[dict[str, Any]] | None = None,
    director: CharacterDirector | None = None,
    prompt_renderer: CharacterGenerationPrompt | None = None,
) -> CharacterState:
    """Promote A/B/C to the human identity anchor and rebuild the next patch.

    Automatic A/B/C and Director Agent advice are proposals. Human choice,
    explicit changes and locks become authoritative only here.
    """
    label = label.strip().upper()
    choices = {
        str(item.get("label", "")).upper(): item
        for item in batch_report.get("shortlist", [])
    }
    if label not in choices:
        raise ValueError(f"shortlist label {label!r} not found")

    selected = choices[label]
    image_ref = str(selected.get("image_ref", "")).strip()
    if not image_ref:
        raise ValueError("selected shortlist item has no image_ref")
    if selected.get("locked_violations"):
        raise ValueError("cannot promote a candidate with locked Canon violations")

    if feedback:
        CharacterMemory.add_feedback(state, feedback)

    for feature, value in (locks or {}).items():
        feature = feature.strip()
        if not feature:
            continue
        if feature in state.canon_constraints:
            canon_value = state.canon_constraints[feature].get("value")
            if canon_value != value:
                raise ValueError(
                    f"cannot override Canon lock {feature!r}: {canon_value!r}"
                )
        CharacterMemory.lock(state, feature, value)

    for item in rejected or []:
        item = item.strip()
        if item and item not in state.rejected:
            state.rejected.append(item)

    critique = _critique_from_entry(selected)
    advice = _advice_from_entry(selected)

    agent_changes = []
    if advice is not None:
        agent_changes = [
            {
                "feature": str(item.get("feature", "")),
                "target": str(item.get("target", "")),
            }
            for item in advice.changes
        ]

    # Human explicit edits outrank Director Agent suggestions, which outrank the
    # raw Vision Critic change_requests.
    critique.change_requests = [
        *[dict(x) for x in (explicit_changes or [])],
        *agent_changes,
        *critique.change_requests,
    ]

    director = director or CharacterDirector()
    patch = director.plan(canon, state, critique)
    prompt_renderer = prompt_renderer or CharacterGenerationPrompt()
    next_prompt = prompt_renderer.render(
        canon=canon,
        state=state,
        patch=patch,
    )

    state.identity_anchor = image_ref
    state.prompt = next_prompt
    state.human_selections.append(
        {
            "version": state.version,
            "label": label,
            "image_ref": image_ref,
            "feedback": feedback,
            "locks": dict(locks or {}),
            "rejected": list(rejected or []),
            "director_advice": asdict(advice) if advice else None,
            "patch": asdict(patch),
        }
    )

    if state.history and state.history[-1].version == state.version:
        record = state.history[-1]
        record.candidate_id = critique.candidate_id
        record.image_ref = image_ref
        record.score = critique.overall
        record.critique = asdict(critique)
        record.patch = asdict(patch)
        record.human_feedback = feedback
        record.director_advice = asdict(advice) if advice else {}
        record.accepted = True

    return state
