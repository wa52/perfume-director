from __future__ import annotations

from .models import CanonProfile, CharacterState, Critique, DirectorAdvice, RevisionPatch


class CharacterDirector:
    """Deterministic fallback director that converts Critic findings into readable advice."""

    def __init__(self, max_changes: int = 3):
        if max_changes < 1:
            raise ValueError("max_changes must be >= 1")
        self.max_changes = max_changes

    def advise(
        self,
        canon: CanonProfile,
        state: CharacterState,
        critique: Critique,
    ) -> DirectorAdvice:
        locked = set(state.locked)
        rejected = set(state.rejected)
        safe_changes: list[dict] = []

        for request in critique.change_requests:
            feature = str(request.get("feature", "")).strip()
            target = str(request.get("target", "")).strip()
            if not feature or feature in locked:
                continue
            if target and target in rejected:
                continue
            safe_changes.append(
                {
                    "feature": feature,
                    "target": target,
                    "why": next(iter(critique.problems), "Improve the weakest reviewed visual dimension."),
                    "priority": len(safe_changes) + 1,
                }
            )
            if len(safe_changes) >= self.max_changes:
                break

        issues = [
            {
                "priority": index + 1,
                "feature": (
                    safe_changes[index]["feature"]
                    if index < len(safe_changes)
                    else "overall"
                ),
                "diagnosis": problem,
            }
            for index, problem in enumerate(critique.problems[: self.max_changes])
        ]
        if critique.locked_violations:
            issues = [
                {
                    "priority": 0,
                    "feature": "canon_lock",
                    "diagnosis": item,
                }
                for item in critique.locked_violations
            ] + issues

        strengths = list(critique.evidence_alignment[:3])
        if not strengths:
            best = sorted(critique.scores.items(), key=lambda x: x[1], reverse=True)[:2]
            strengths = [f"{name} score {score:.0f}" for name, score in best]

        next_goal = (
            "Fix the highest-priority visible deviation while preserving the current identity."
            if safe_changes
            else "Preserve the current identity and explore small variations without introducing new drift."
        )

        notes: list[str] = []
        if canon.evidence:
            notes.append("Keep every revision traceable to Canon evidence.")
        if state.human_feedback:
            notes.append("Human feedback has higher priority than automatic visual preference.")

        return DirectorAdvice(
            candidate_id=critique.candidate_id,
            summary=(
                f"Use this candidate as the next iteration base with {len(safe_changes)} bounded change(s)."
                if not critique.locked_violations
                else "Do not promote this candidate until Canon-lock regressions are removed."
            ),
            strengths=strengths,
            priority_issues=issues,
            keep=list(state.locked),
            changes=safe_changes,
            do_not_change=list(state.locked),
            next_round_goal=next_goal,
            evidence_notes=notes,
        )

    def plan(
        self,
        canon: CanonProfile,
        state: CharacterState,
        critique: Critique,
    ) -> RevisionPatch:
        return self.advise(canon, state, critique).to_patch()
