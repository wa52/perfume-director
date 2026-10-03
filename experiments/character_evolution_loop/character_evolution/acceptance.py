from __future__ import annotations

from dataclasses import dataclass

from .models import Critique


@dataclass(slots=True)
class AcceptancePolicy:
    minimum_overall: float = 78.0
    minimum_canon: float = 85.0
    minimum_identity: float = 72.0

    def passes(self, critique: Critique) -> bool:
        if critique.locked_violations:
            return False
        return (
            critique.overall >= self.minimum_overall
            and critique.scores.get("canon", 0.0) >= self.minimum_canon
            and critique.scores.get("identity_clarity", 0.0) >= self.minimum_identity
        )

    def rank(self, critique: Critique) -> tuple[int, float, float, float]:
        minimum = min(critique.scores.values()) if critique.scores else 0.0
        return (
            1 if not critique.locked_violations else 0,
            critique.scores.get("canon", 0.0),
            critique.overall,
            minimum,
        )


def shortlist(critiques: list[Critique], count: int = 3) -> list[Critique]:
    if count < 1:
        raise ValueError("count must be >= 1")
    policy = AcceptancePolicy()
    ordered = sorted(critiques, key=policy.rank, reverse=True)
    return ordered[: min(count, len(ordered))]
