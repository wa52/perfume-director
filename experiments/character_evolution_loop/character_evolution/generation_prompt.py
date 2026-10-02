from __future__ import annotations

from .models import CanonProfile, CharacterState


class CharacterGenerationPrompt:
    """Compile a generation prompt without inventing unresolved Canon appearance."""

    def render(self, *, canon: CanonProfile, state: CharacterState, patch=None) -> str:
        parts = [
            "2D animation character design, clean production concept art",
            "single Chinese male character",
            "age 23",
            "ordinary young office worker presentation",
            "low protagonist aura, understated everyday presence",
            "restrained neutral expression and posture",
            "natural believable proportions",
            "plain practical contemporary office-casual impression",
            "character-focused half-body design, simple neutral background",
            "not a fashion illustration, not an idol portrait, not a heroic poster",
        ]

        if state.human_feedback:
            parts.append("human direction: " + " ; ".join(state.human_feedback))
        if state.rejected:
            parts.append("avoid: " + ", ".join(state.rejected))
        if state.forbidden_interpretations:
            parts.append("do not infer: " + " ; ".join(state.forbidden_interpretations))
        if patch is not None:
            for change in patch.change:
                parts.append(
                    f"revision {change.get('feature', '')}: {change.get('target', '')}"
                )

        # Explicitly state that unresolved features should vary between seeds rather
        # than being silently invented as Canon.
        if state.modifiable:
            parts.append(
                "explore without locking as canon: " + ", ".join(state.modifiable)
            )
        return ", ".join(part for part in parts if part)
