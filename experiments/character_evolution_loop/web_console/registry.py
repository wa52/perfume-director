from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CharacterSpec:
    id: str
    name: str
    contract: Path
    base_state: Path
    config: Path
    run_dir: Path
    scene_validation_enabled: bool = False

    @property
    def latest_state(self) -> Path:
        return self.run_dir / "latest_state.json"

    @property
    def latest_batch(self) -> Path:
        return self.run_dir / "latest_batch.json"

    @property
    def scene_report(self) -> Path:
        return self.run_dir / "scene_validation.json"

    def current_state(self) -> Path:
        return self.latest_state if self.latest_state.exists() else self.base_state


@dataclass(frozen=True, slots=True)
class CharacterRegistry:
    default_character: str
    characters: dict[str, CharacterSpec]


def _inside(path: Path, root: Path) -> bool:
    path = path.resolve()
    root = root.resolve()
    return path == root or root in path.parents


def _resolve(root: Path, raw: str, *, run_dir: bool = False) -> Path:
    value = Path(raw)
    path = value.resolve() if value.is_absolute() else (root / value).resolve()
    allowed = (root / "runs").resolve() if run_dir else root.resolve()
    if not _inside(path, allowed):
        raise ValueError(f"path outside allowed workspace: {raw}")
    return path


def load_registry(root: Path) -> CharacterRegistry:
    local = root / "config" / "characters.local.json"
    example = root / "config" / "characters.example.json"
    base_raw = json.loads(example.read_text(encoding="utf-8"))
    local_raw = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}

    base_items = base_raw.get("characters")
    local_items = local_raw.get("characters", [])
    if not isinstance(base_items, list) or not base_items:
        raise ValueError("character registry requires non-empty built-in characters list")
    if not isinstance(local_items, list):
        raise ValueError("local character registry entries must be a list")

    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in [*base_items, *local_items]:
        if not isinstance(item, dict):
            raise ValueError("character registry entries must be objects")
        character_id = str(item.get("id", "")).strip()
        if not character_id:
            raise ValueError("each character requires id")
        if character_id not in merged:
            order.append(character_id)
            merged[character_id] = dict(item)
        else:
            merged[character_id].update(item)

    items = [merged[character_id] for character_id in order]

    characters: dict[str, CharacterSpec] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("character registry entries must be objects")
        character_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        if not character_id or not name:
            raise ValueError("each character requires id and name")
        if character_id in characters:
            raise ValueError(f"duplicate character id: {character_id}")
        characters[character_id] = CharacterSpec(
            id=character_id,
            name=name,
            contract=_resolve(root, str(item["contract"])),
            base_state=_resolve(root, str(item["base_state"])),
            config=_resolve(root, str(item["config"])),
            run_dir=_resolve(root, str(item["run_dir"]), run_dir=True),
            scene_validation_enabled=bool(item.get("scene_validation_enabled", False)),
        )

    default = str(local_raw.get("default_character", "")).strip() or str(base_raw.get("default_character", "")).strip() or next(iter(characters))
    if default not in characters:
        raise ValueError(f"default_character {default!r} is not registered")
    return CharacterRegistry(default_character=default, characters=characters)


def registry_summary(registry: CharacterRegistry) -> list[dict[str, Any]]:
    return [
        {
            "id": spec.id,
            "name": spec.name,
            "has_contract": spec.contract.is_file(),
            "has_base_state": spec.base_state.is_file(),
            "has_config": spec.config.is_file(),
            "run_dir": str(spec.run_dir),
            "scene_validation_enabled": spec.scene_validation_enabled,
        }
        for spec in registry.characters.values()
    ]
