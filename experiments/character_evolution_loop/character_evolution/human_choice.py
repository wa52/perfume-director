from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .director import CharacterDirector
from .generation_prompt import CharacterGenerationPrompt
from .memory import CharacterMemory
from .models import CanonProfile, CharacterState, Critique


def _critique_from_entry(entry: dict[str, Any]) -> Critique:
    return Critique(
        candidate_id=str(entry["image_ref"]),
        scores={k: float(v) for k, v in entry.get("scores", {}).items()},
        problems=[str(x) for x in entry.get("problems", [])],
        change_requests=[dict(x) for x in entry.get("change_requests", [])],
        locked_violations=[str(x) for x in entry.get("locked_violations", [])],
        evidence_alignment=[str(x) for x in entry.get("evidence_alignment", [])],
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
) -> CharacterState:
    """Promote A/B/C to the human identity anchor and rebuild the next patch.

    Automatic ranking proposes a shortlist; only this function makes a human choice
    authoritative for the identity anchor.
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

    if feedback:
        CharacterMemory.add_feedback(state, feedback)

    for feature, value in (locks or {}).items():
        feature = feature.strip()
        if not feature:
            continue
        # Canon locks cannot be silently contradicted by a human visual lock.
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
    if explicit_changes:
        merged = [dict(x) for x in explicit_changes] + critique.change_requests
        critique.change_requests = merged

    director = director or CharacterDirector()
    patch = director.plan(canon, state, critique)
    next_prompt = CharacterGenerationPrompt().render(
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
            "patch": asdict(patch),
        }
    )

    # Replace the provisional auto-selection for the current version with the
    # human-authoritative selection. History remains one record per generated round.
    if state.history and state.history[-1].version == state.version:
        record = state.history[-1]
        record.candidate_id = critique.candidate_id
        record.image_ref = image_ref
        record.score = critique.overall
        record.critique = asdict(critique)
        record.patch = asdict(patch)
        record.human_feedback = feedback
        record.accepted = not critique.locked_violations

    return state
