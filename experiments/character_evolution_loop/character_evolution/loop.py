from __future__ import annotations

from dataclasses import asdict
from typing import Protocol, Sequence

from .acceptance import AcceptancePolicy
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
        acceptance_policy: AcceptancePolicy | None = None,
    ):
        self.generator = generator
        self.critic = critic
        self.prompt_renderer = prompt_renderer
        self.memory = memory
        self.director = director or CharacterDirector()
        self.acceptance_policy = acceptance_policy or AcceptancePolicy()
        self.last_reviewed: list[tuple[str, Critique]] = []

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

        reviewed: list[tuple[str, Critique]] = []
        for ref in refs:
            critique = self.critic.review(image_ref=ref, canon=canon, state=state)
            reviewed.append((ref, critique))

        reviewed.sort(
            key=lambda item: self.acceptance_policy.rank(item[1]),
            reverse=True,
        )
        self.last_reviewed = list(reviewed)
        selected_ref, selected = reviewed[0]

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
                accepted=self.acceptance_policy.passes(selected),
                critique=asdict(selected),
                patch=asdict(patch),
            )
        )
        self.memory.save(state)
        return state, [item[1] for item in reviewed[: min(shortlist, len(reviewed))]]
