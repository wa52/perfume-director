from __future__ import annotations

import argparse
from pathlib import Path

from character_evolution.canon_adapter import apply_contract, load_contract
from character_evolution.memory import CharacterMemory
from character_evolution.models import CharacterState


def build_initial_state(contract: dict) -> CharacterState:
    state = CharacterState(
        character=contract["character"]["name"],
        version=1,
    )
    apply_contract(contract, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V01 Character State from a Canon contract.")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load_contract(args.contract)
    state = build_initial_state(contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    CharacterMemory(args.output).save(state)
    print(f"{state.character}: V{state.version:02d} -> {args.output}")


if __name__ == "__main__":
    main()
