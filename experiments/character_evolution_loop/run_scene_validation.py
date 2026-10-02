from __future__ import annotations

import argparse
import json
from pathlib import Path

from character_evolution.canon_adapter import apply_contract, contract_to_canon_profile, load_contract
from character_evolution.generation_prompt import CharacterGenerationPrompt
from character_evolution.memory import CharacterMemory
from character_evolution.providers import (
    ComfyUICharacterGenerator,
    ComfyUIConfig,
    OpenAICompatibleSceneValidator,
    SceneValidatorConfig,
)
from character_evolution.scene_validation import DEFAULT_SCENES, SceneAcceptancePolicy


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def comfy_config(root: Path, raw: dict, *, output_dir: Path) -> ComfyUIConfig:
    return ComfyUIConfig(
        base_url=raw["base_url"],
        workflow_path=resolve(root, raw["workflow_path"]),
        output_node=str(raw["output_node"]),
        prompt_node=str(raw["prompt_node"]),
        prompt_input=raw.get("prompt_input", "text"),
        seed_node=str(raw["seed_node"]) if raw.get("seed_node") is not None else None,
        seed_input=raw.get("seed_input", "seed"),
        reference_image_node=(
            str(raw["reference_image_node"])
            if raw.get("reference_image_node") is not None
            else None
        ),
        reference_image_input=raw.get("reference_image_input", "image"),
        seed_start=int(raw.get("seed_start", 2026100201)),
        timeout_seconds=float(raw.get("timeout_seconds", 300)),
        poll_seconds=float(raw.get("poll_seconds", 1)),
        output_dir=output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and validate office/home/abnormal identity-consistency scenes."
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
        default=Path("runs/character_evolution/latest_state.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/character_evolution/scene_validation.json"),
    )
    args = parser.parse_args()

    root = Path.cwd()
    config = read_json(args.config)
    contract = load_contract(args.contract)
    canon = contract_to_canon_profile(contract)
    state = CharacterMemory(args.state).load(contract["character"]["name"])
    apply_contract(contract, state)

    if not state.identity_anchor:
        raise ValueError("human identity_anchor is required before scene validation")

    scene_raw = config.get("scene_comfyui", config["comfyui"])
    if scene_raw.get("reference_image_node") is None:
        raise ValueError(
            "scene generation requires reference_image_node so the human-selected identity anchor is actually supplied to ComfyUI"
        )

    base_prompt = CharacterGenerationPrompt().render(canon=canon, state=state)
    scene_images: dict[str, str] = {}
    for scene in DEFAULT_SCENES:
        output_dir = resolve(
            root,
            scene_raw.get("output_dir", "runs/character_evolution/scenes"),
        ) / scene.scene_id
        generator = ComfyUICharacterGenerator(
            comfy_config(root, scene_raw, output_dir=output_dir)
        )
        prompt = ", ".join(
            [
                base_prompt,
                f"SCENE: {scene.prompt}",
                f"IDENTITY RULE: {scene.identity_rule}",
                f"CANON RULE: {scene.canon_rule}",
            ]
        )
        scene_images[scene.scene_id] = generator.generate(
            prompt=prompt,
            state=state,
            count=1,
        )[0]

    critic_raw = config["critic"]
    validator = OpenAICompatibleSceneValidator(
        SceneValidatorConfig(
            base_url=critic_raw["base_url"],
            model=critic_raw["model"],
            api_key_env=critic_raw["api_key_env"],
            timeout_seconds=float(critic_raw.get("timeout_seconds", 180)),
        )
    )
    result = validator.review(
        anchor_image=state.identity_anchor,
        scene_images=scene_images,
        canon=canon,
        state=state,
    )

    thresholds = config.get("scene_acceptance", {})
    policy = SceneAcceptancePolicy(
        minimum_identity=float(thresholds.get("minimum_identity", 82)),
        minimum_canon=float(thresholds.get("minimum_canon", 80)),
        minimum_overall=float(thresholds.get("minimum_overall", 80)),
    )
    report = {
        "character": state.character,
        "version": state.version,
        "identity_anchor": state.identity_anchor,
        "scene_images": scene_images,
        "pass": policy.passes(result),
        "overall": result.overall,
        "scores": result.scores,
        "scene_results": result.scene_results,
        "problems": result.problems,
        "regression_features": result.regression_features,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
