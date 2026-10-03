from __future__ import annotations

from dataclasses import asdict
from typing import Protocol, Sequence

from .acceptance import AcceptancePolicy
from .director import CharacterDirector
from .memory import CharacterMemory
from .models import (
    CanonProfile,
    CharacterState,
    Critique,
    DirectorAdvice,
    IterationRecord,
    RevisionPatch,
)


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


class DirectorAgent(Protocol):
    def advise(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        critique: Critique,
    ) -> DirectorAdvice: ...


class PromptRenderer(Protocol):
    def render(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        patch: RevisionPatch | None,
    ) -> str: ...


class CharacterEvolutionLoop:
    """One bounded iteration: render -> generate -> critique -> direct -> patch -> remember."""

    def __init__(
        self,
        *,
        generator: ImageGenerator,
        critic: VisualCritic,
        prompt_renderer: PromptRenderer,
        memory: CharacterMemory,
        director: CharacterDirector | None = None,
        director_agent: DirectorAgent | None = None,
        acceptance_policy: AcceptancePolicy | None = None,
    ):
        self.generator = generator
        self.critic = critic
        self.prompt_renderer = prompt_renderer
        self.memory = memory
        self.director = director or CharacterDirector()
        self.director_agent = director_agent
        self.acceptance_policy = acceptance_policy or AcceptancePolicy()
        self.last_reviewed: list[tuple[str, Critique]] = []
        self.last_advice: dict[str, DirectorAdvice] = {}
        self.last_advice_errors: dict[str, str] = {}

    def _advise(
        self,
        *,
        canon: CanonProfile,
        state: CharacterState,
        critique: Critique,
    ) -> DirectorAdvice:
        if self.director_agent is None:
            return self.director.advise(canon, state, critique)
        try:
            return self.director_agent.advise(
                canon=canon,
                state=state,
                critique=critique,
            )
        except Exception as error:
            self.last_advice_errors[critique.candidate_id] = (
                f"{type(error).__name__}: {error}"
            )
            return self.director.advise(canon, state, critique)

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
        self.last_advice = {}
        self.last_advice_errors = {}

        top_pairs = reviewed[: min(shortlist, len(reviewed))]
        for _, critique in top_pairs:
            self.last_advice[critique.candidate_id] = self._advise(
                canon=canon,
                state=state,
                critique=critique,
            )

        selected_ref, selected = reviewed[0]
        selected_advice = self.last_advice.get(selected.candidate_id)
        if selected_advice is None:
            selected_advice = self._advise(
                canon=canon,
                state=state,
                critique=selected,
            )
            self.last_advice[selected.candidate_id] = selected_advice

        patch = selected_advice.to_patch()
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
                director_advice=asdict(selected_advice),
            )
        )
        self.memory.save(state)
        return state, [item[1] for item in top_pairs]
