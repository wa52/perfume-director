from __future__ import annotations

from .models import CanonProfile, CharacterState, Critique, RevisionPatch


class CharacterDirector:
    """Turns critic findings into a bounded revision patch instead of rewriting everything."""

    def __init__(self, max_changes: int = 3):
        if max_changes < 1:
            raise ValueError("max_changes must be >= 1")
        self.max_changes = max_changes

    def plan(
        self,
        canon: CanonProfile,
        state: CharacterState,
        critique: Critique,
    ) -> RevisionPatch:
        locked = set(state.locked)
        rejected = set(state.rejected)
        safe_changes: list[dict] = []
        reasons: list[str] = []

        for request in critique.change_requests:
            feature = str(request.get("feature", "")).strip()
            target = str(request.get("target", "")).strip()
            if not feature or feature in locked:
                continue
            if target and target in rejected:
                continue
            safe_changes.append(dict(request))
            if len(safe_changes) >= self.max_changes:
                break

        if critique.problems:
            reasons.extend(critique.problems[: self.max_changes])
        if canon.evidence:
            reasons.append("Revision must remain traceable to canon evidence.")
        if state.human_feedback:
            reasons.append("Preserve the user's accumulated character feedback.")

        return RevisionPatch(
            keep=list(state.locked),
            change=safe_changes,
            do_not_change=list(state.locked),
            rationale=reasons,
        )
