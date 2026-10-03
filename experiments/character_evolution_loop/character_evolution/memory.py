from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from .models import CharacterState, IterationRecord


class CharacterMemory:
    """JSON-backed long-term character state with explicit feature locking."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self, character: str) -> CharacterState:
        if not self.path.exists():
            return CharacterState(character=character)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        allowed = {f.name for f in fields(CharacterState)}
        clean = {k: v for k, v in raw.items() if k in allowed}
        clean["history"] = [IterationRecord(**item) for item in clean.get("history", [])]
        clean.setdefault("character", character)
        return CharacterState(**clean)

    def save(self, state: CharacterState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def lock(state: CharacterState, feature: str, value: Any) -> None:
        state.locked[feature] = value
        if feature in state.modifiable:
            state.modifiable.remove(feature)

    @staticmethod
    def unlock(state: CharacterState, feature: str) -> None:
        state.locked.pop(feature, None)
        if feature not in state.modifiable:
            state.modifiable.append(feature)

    @staticmethod
    def add_feedback(state: CharacterState, feedback: str) -> None:
        feedback = feedback.strip()
        if feedback and feedback not in state.human_feedback:
            state.human_feedback.append(feedback)
