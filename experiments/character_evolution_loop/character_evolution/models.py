from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CanonProfile:
    character: str
    hard_facts: dict[str, Any] = field(default_factory=dict)
    soft_traits: list[str] = field(default_factory=list)
    forbidden_interpretations: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Critique:
    candidate_id: str
    scores: dict[str, float]
    problems: list[str] = field(default_factory=list)
    change_requests: list[dict[str, Any]] = field(default_factory=list)
    locked_violations: list[str] = field(default_factory=list)
    evidence_alignment: list[str] = field(default_factory=list)

    @property
    def overall(self) -> float:
        if not self.scores:
            return 0.0
        return round(sum(self.scores.values()) / len(self.scores), 2)

    @property
    def eligible(self) -> bool:
        return not self.locked_violations


@dataclass(slots=True)
class RevisionPatch:
    keep: list[str] = field(default_factory=list)
    change: list[dict[str, Any]] = field(default_factory=list)
    do_not_change: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IterationRecord:
    version: int
    candidate_id: str
    image_ref: str
    score: float
    accepted: bool
    critique: dict[str, Any]
    patch: dict[str, Any]
    human_feedback: str | None = None


@dataclass(slots=True)
class CharacterState:
    character: str
    version: int = 0
    prompt: str = ""
    traits: dict[str, float] = field(default_factory=dict)

    # Features that future revisions must not change.
    locked: dict[str, Any] = field(default_factory=dict)
    # Visual features still open for design exploration.
    modifiable: list[str] = field(default_factory=list)
    # Human/design choices that should not be reintroduced.
    rejected: list[str] = field(default_factory=list)
    human_feedback: list[str] = field(default_factory=list)

    # Canon is kept separate from image scores so evidence confidence is never
    # confused with a visual-quality score.
    canon_constraints: dict[str, Any] = field(default_factory=dict)
    design_targets: dict[str, Any] = field(default_factory=dict)
    evidence_refs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    canon_source: dict[str, Any] = field(default_factory=dict)
    forbidden_interpretations: list[str] = field(default_factory=list)

    history: list[IterationRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
