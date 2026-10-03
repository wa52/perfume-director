from __future__ import annotations

from .models import CanonProfile, CharacterState, RevisionPatch


class CanonPromptRenderer:
    """Render a structured brief that keeps Canon, human feedback, and patches distinct."""

    def render(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        patch: RevisionPatch | None,
    ) -> str:
        lines = [f"CHARACTER: {state.character}"]

        if state.locked:
            lines.append("CANON_LOCKS:")
            for feature, value in state.locked.items():
                lines.append(f"- {feature}: {value}")

        if state.design_targets:
            lines.append("SOFT_DIRECTION:")
            for feature, payload in state.design_targets.items():
                instruction = payload.get("instruction", "")
                confidence = payload.get("confidence")
                suffix = f" [confidence={confidence}]" if confidence is not None else ""
                lines.append(f"- {feature}: {instruction}{suffix}")
        elif canon.soft_traits:
            lines.append("SOFT_DIRECTION:")
            lines.extend(f"- {item}" for item in canon.soft_traits)

        if state.modifiable:
            lines.append("EDITABLE_VISUAL_FEATURES:")
            lines.append("- " + ", ".join(state.modifiable))

        if state.rejected:
            lines.append("REJECTED_DESIGN_CHOICES:")
            lines.append("- " + ", ".join(state.rejected))

        forbidden = state.forbidden_interpretations or canon.forbidden_interpretations
        if forbidden:
            lines.append("DO_NOT_INFER:")
            lines.extend(f"- {item}" for item in forbidden)

        if state.human_feedback:
            lines.append("HUMAN_FEEDBACK:")
            lines.extend(f"- {item}" for item in state.human_feedback)

        if patch is not None:
            lines.append("REVISION_PATCH:")
            if patch.keep:
                lines.append("- KEEP: " + ", ".join(patch.keep))
            for change in patch.change:
                feature = change.get("feature", "")
                target = change.get("target", "")
                lines.append(f"- CHANGE {feature}: {target}")
            if patch.do_not_change:
                lines.append("- DO_NOT_CHANGE: " + ", ".join(patch.do_not_change))

        lines.append(
            "RULE: Canon locks are facts. Soft direction guides performance/design but must not be converted into unsupported literal appearance facts."
        )
        return "\n".join(lines)
