from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from character_evolution.archive import archive_version
from character_evolution.canon_adapter import apply_contract, contract_to_canon_profile, load_contract
from character_evolution.human_choice import apply_human_choice
from character_evolution.memory import CharacterMemory


def parse_key_value(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected feature=value")
    key, raw = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("feature name cannot be empty")
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote an A/B/C shortlist candidate to the human identity anchor."
    )
    parser.add_argument("--choose", required=True, choices=("A", "B", "C", "a", "b", "c"))
    parser.add_argument("--feedback", default="")
    parser.add_argument("--lock", action="append", default=[], type=parse_key_value)
    parser.add_argument("--reject", action="append", default=[])
    parser.add_argument("--change", action="append", default=[], type=parse_key_value)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("examples/lu_xin_canon_contract.json"),
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("runs/character_evolution/latest_state.json"),
    )
    parser.add_argument(
        "--batch",
        type=Path,
        default=Path("runs/character_evolution/latest_batch.json"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    contract = load_contract(args.contract)
    canon = contract_to_canon_profile(contract)
    state = CharacterMemory(args.state).load(contract["character"]["name"])
    apply_contract(contract, state)
    batch = json.loads(args.batch.read_text(encoding="utf-8"))

    locks = dict(args.lock)
    changes = [{"feature": feature, "target": value} for feature, value in args.change]
    apply_human_choice(
        state=state,
        canon=canon,
        batch_report=batch,
        label=args.choose,
        feedback=args.feedback or None,
        locks=locks,
        rejected=args.reject,
        explicit_changes=changes,
    )

    output = args.output or args.state
    CharacterMemory(output).save(state)
    archive_version(
        run_dir=output.parent,
        state_path=output,
        batch_path=args.batch,
    )
    print(
        json.dumps(
            {
                "character": state.character,
                "version": state.version,
                "identity_anchor": state.identity_anchor,
                "human_feedback": state.human_feedback,
                "locked": state.locked,
                "rejected": state.rejected,
                "next_prompt": state.prompt,
                "state_output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
