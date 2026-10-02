from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from character_evolution.acceptance import AcceptancePolicy
from character_evolution.canon_adapter import apply_contract, contract_to_canon_profile, load_contract
from character_evolution.generation_prompt import CharacterGenerationPrompt
from character_evolution.loop import CharacterEvolutionLoop
from character_evolution.memory import CharacterMemory
from character_evolution.providers import (
    ComfyUICharacterGenerator,
    ComfyUIConfig,
    OpenAICompatibleVisionCritic,
    VisionCriticConfig,
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one real Character Evolution round: 8 images -> vision critic -> A/B/C -> next state."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/character_v01.local.json"),
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("examples/lu_xin_canon_contract.json"),
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("examples/lu_xin_state_v01.json"),
    )
    parser.add_argument(
        "--state-output",
        type=Path,
        default=Path("runs/character_evolution/latest_state.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("runs/character_evolution/latest_batch.json"),
    )
    args = parser.parse_args()

    root = Path.cwd()
    config = read_json(args.config)
    contract = load_contract(args.contract)

    state = CharacterMemory(args.state).load(contract["character"]["name"])
    apply_contract(contract, state)
    canon = contract_to_canon_profile(contract)

    comfy_raw = config["comfyui"]
    generator = ComfyUICharacterGenerator(
        ComfyUIConfig(
            base_url=comfy_raw["base_url"],
            workflow_path=resolve(root, comfy_raw["workflow_path"]),
            output_node=str(comfy_raw["output_node"]),
            prompt_node=str(comfy_raw["prompt_node"]),
            prompt_input=comfy_raw.get("prompt_input", "text"),
            seed_node=(
                str(comfy_raw["seed_node"])
                if comfy_raw.get("seed_node") is not None
                else None
            ),
            seed_input=comfy_raw.get("seed_input", "seed"),
            reference_image_node=(
                str(comfy_raw["reference_image_node"])
                if comfy_raw.get("reference_image_node") is not None
                else None
            ),
            reference_image_input=comfy_raw.get("reference_image_input", "image"),
            seed_start=int(comfy_raw.get("seed_start", 2026100201)),
            timeout_seconds=float(comfy_raw.get("timeout_seconds", 300)),
            poll_seconds=float(comfy_raw.get("poll_seconds", 1)),
            output_dir=resolve(
                root,
                comfy_raw.get("output_dir", "runs/character_evolution"),
            ),
        )
    )

    critic_raw = config["critic"]
    critic = OpenAICompatibleVisionCritic(
        VisionCriticConfig(
            base_url=critic_raw["base_url"],
            model=critic_raw["model"],
            api_key_env=critic_raw["api_key_env"],
            timeout_seconds=float(critic_raw.get("timeout_seconds", 180)),
        )
    )

    policy_raw = config.get("acceptance", {})
    policy = AcceptancePolicy(
        minimum_overall=float(policy_raw.get("minimum_overall", 78)),
        minimum_canon=float(policy_raw.get("minimum_canon", 85)),
        minimum_identity=float(policy_raw.get("minimum_identity", 72)),
    )

    batch = config.get("batch", {})
    candidates = int(batch.get("candidates", 8))
    shortlist_count = int(batch.get("shortlist", 3))

    output_memory = CharacterMemory(args.state_output)
    loop = CharacterEvolutionLoop(
        generator=generator,
        critic=critic,
        prompt_renderer=CharacterGenerationPrompt(),
        memory=output_memory,
        acceptance_policy=policy,
    )
    state, top = loop.run_round(
        canon=canon,
        state=state,
        candidates=candidates,
        shortlist=shortlist_count,
    )

    labels = ("A", "B", "C")
    report = {
        "character": state.character,
        "version": state.version,
        "accepted": state.history[-1].accepted,
        "selection_status": "PROVISIONAL_AUTO_RANKING",
        "selected_image": state.history[-1].image_ref,
        "selected_score": state.history[-1].score,
        "shortlist": [
            {
                "label": labels[index] if index < len(labels) else str(index + 1),
                "image_ref": critique.candidate_id,
                "overall": critique.overall,
                "scores": critique.scores,
                "problems": critique.problems,
                "locked_violations": critique.locked_violations,
                "evidence_alignment": critique.evidence_alignment,
                "change_requests": critique.change_requests,
            }
            for index, critique in enumerate(top)
        ],
        "human_choice_required": True,
        "next_patch": state.history[-1].patch,
        "next_prompt": state.prompt,
        "state_output": str(args.state_output),
    }
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
