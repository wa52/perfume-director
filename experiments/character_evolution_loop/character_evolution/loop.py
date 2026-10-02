from __future__ import annotations

from dataclasses import asdict
from typing import Protocol, Sequence

from .director import CharacterDirector
from .memory import CharacterMemory
from .models import CanonProfile, CharacterState, Critique, IterationRecord, RevisionPatch


class ImageGenerator(Protocol):
    def generate(self, *, prompt: str, state: CharacterState, count: int) -> Sequence[str]: ...


class VisualCritic(Protocol):
    def review(
        self,
        *,
        image_ref: str,
        canon: CanonProfile,
        state: CharacterState,
    ) -> Critique: ...


class PromptRenderer(Protocol):
    def render(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        patch: RevisionPatch | None,
    ) -> str: ...


class CharacterEvolutionLoop:
    """One bounded iteration: render -> generate -> critique -> select -> patch -> remember."""

    def __init__(
        self,
        *,
        generator: ImageGenerator,
        critic: VisualCritic,
        prompt_renderer: PromptRenderer,
        memory: CharacterMemory,
        director: CharacterDirector | None = None,
    ):
        self.generator = generator
        self.critic = critic
        self.prompt_renderer = prompt_renderer
        self.memory = memory
        self.director = director or CharacterDirector()

    def run_round(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        candidates: int = 8,
        shortlist: int = 3,
    ) -> tuple[CharacterState, list[Critique]]:
        if candidates < 1 or shortlist < 1:
            raise ValueError("candidates and shortlist must be >= 1")

        prompt = self.prompt_renderer.render(canon=canon, state=state, patch=None)
        refs = list(self.generator.generate(prompt=prompt, state=state, count=candidates))
        if not refs:
            raise RuntimeError("generator returned no candidates")

        critiques = [
            self.critic.review(image_ref=ref, canon=canon, state=state) for ref in refs
        ]
        critiques.sort(key=self._rank_key, reverse=True)
        selected = critiques[0]
        selected_ref = (
            refs[next(i for i, ref in enumerate(refs) if ref == selected.candidate_id)]
            if selected.candidate_id in refs
            else selected.candidate_id
        )

        patch = self.director.plan(canon, state, selected)
        next_prompt = self.prompt_renderer.render(canon=canon, state=state, patch=patch)

        state.version += 1
        state.prompt = next_prompt
        for name, score in selected.scores.items():
            state.traits[name] = score
        state.history.append(
            IterationRecord(
                version=state.version,
                candidate_id=selected.candidate_id,
                image_ref=selected_ref,
                score=selected.overall,
                accepted=selected.eligible,
                critique=asdict(selected),
                patch=asdict(patch),
            )
        )
        self.memory.save(state)
        return state, critiques[: min(shortlist, len(critiques))]

    @staticmethod
    def _rank_key(critique: Critique) -> tuple[int, float, float]:
        # Any locked-feature violation loses to every lock-safe candidate.
        minimum = min(critique.scores.values()) if critique.scores else 0.0
        return (1 if critique.eligible else 0, critique.overall, minimum)
