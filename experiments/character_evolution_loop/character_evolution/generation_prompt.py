from __future__ import annotations

from .art_direction import ArtDirection
from .models import CanonProfile, CharacterState


class CharacterGenerationPrompt:
    """Compile a visual prompt from Canon + work-level art direction + character state."""

    def __init__(self, art_direction: ArtDirection | None = None):
        self.art_direction = art_direction

    def render(self, *, canon: CanonProfile, state: CharacterState, patch=None) -> str:
        parts = [
            "character production concept art",
            f"single character: {state.character}",
            "character-focused half-body design, simple neutral background",
        ]

        if self.art_direction is not None:
            fragment = self.art_direction.prompt_fragment()
            if fragment:
                parts.append(fragment)
        else:
            parts.append("2D animation character design, clean production concept art")

        age = state.locked.get("age")
        if age is not None:
            parts.append(f"canon age: {age}")

        role = state.locked.get("daily_role_context")
        if role == "company_office_worker":
            parts.extend(
                [
                    "ordinary young office-worker daily presentation",
                    "understated everyday presence, low protagonist aura",
                    "restrained neutral expression and posture",
                    "practical non-fashion-forward daily styling",
                ]
            )
        elif role:
            parts.append(f"canon daily role/context: {role}")

        for feature, payload in state.design_targets.items():
            instruction = payload.get("instruction")
            if instruction:
                parts.append(f"soft direction {feature}: {instruction}")

        if state.human_feedback:
            parts.append("human direction: " + " ; ".join(state.human_feedback))
        if state.rejected:
            parts.append("avoid design choices: " + ", ".join(state.rejected))
        if state.forbidden_interpretations:
            parts.append("do not infer: " + " ; ".join(state.forbidden_interpretations))

        if patch is not None:
            for change in patch.change:
                parts.append(
                    f"revision {change.get('feature', '')}: {change.get('target', '')}"
                )

        if state.modifiable:
            parts.append(
                "open visual exploration, not canon facts: " + ", ".join(state.modifiable)
            )

        return ", ".join(part for part in parts if part)
