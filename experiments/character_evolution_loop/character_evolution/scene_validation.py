from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SceneSpec:
    scene_id: str
    title: str
    prompt: str
    identity_rule: str
    canon_rule: str


DEFAULT_SCENES = (
    SceneSpec(
        scene_id="office",
        title="普通办公室",
        prompt=(
            "ordinary company office scene, seated or standing near a workstation, "
            "routine workday, understated office-worker presence, no heroic staging"
        ),
        identity_rule="Keep the selected identity anchor's face, age impression and body identity stable.",
        canon_rule="Preserve the ordinary office-worker context and low protagonist aura.",
    ),
    SceneSpec(
        scene_id="home",
        title="家庭关系场景",
        prompt=(
            "modest home interior, relational family scene, restrained calm reaction, "
            "natural domestic acting, no glamour portrait composition"
        ),
        identity_rule="Keep the same person; expression may soften but identity must not change.",
        canon_rule="Use restrained scene acting without interpreting calmness as emotionlessness.",
    ),
    SceneSpec(
        scene_id="abnormal",
        title="异常高压场景",
        prompt=(
            "high-stress abnormal incident, tense atmosphere, alert reaction, "
            "same everyday character under pressure, not a permanent warrior makeover"
        ),
        identity_rule="Stress may change expression/posture, never the stable face/body identity.",
        canon_rule="Do not turn scene-specific danger into the character's default aggressive identity.",
    ),
)


@dataclass(slots=True)
class SceneValidationResult:
    scores: dict[str, float]
    scene_results: list[dict[str, Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    regression_features: list[str] = field(default_factory=list)

    @property
    def overall(self) -> float:
        if not self.scores:
            return 0.0
        return round(sum(self.scores.values()) / len(self.scores), 2)


@dataclass(slots=True)
class SceneAcceptancePolicy:
    minimum_identity: float = 82.0
    minimum_canon: float = 80.0
    minimum_overall: float = 80.0

    def passes(self, result: SceneValidationResult) -> bool:
        return (
            not result.regression_features
            and result.overall >= self.minimum_overall
            and result.scores.get("identity_consistency", 0.0) >= self.minimum_identity
            and result.scores.get("canon", 0.0) >= self.minimum_canon
        )
