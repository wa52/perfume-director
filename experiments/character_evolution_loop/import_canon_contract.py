from __future__ import annotations

import argparse
from pathlib import Path

from character_evolution.canon_adapter import apply_contract, load_contract
from character_evolution.memory import CharacterMemory


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge a passage-free Canon contract into character state.")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--state", type=Path, default=Path("examples/lu_xin_state.json"))
    parser.add_argument("--output", type=Path, default=Path("examples/lu_xin_state_v01.json"))
    args = parser.parse_args()

    contract = load_contract(args.contract)
    memory = CharacterMemory(args.state)
    state = memory.load(contract["character"]["name"])
    apply_contract(contract, state)
    CharacterMemory(args.output).save(state)
    print(args.output)


if __name__ == "__main__":
    main()
