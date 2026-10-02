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
    source = local if local.exists() else example
    raw = json.loads(source.read_text(encoding="utf-8"))

    items = raw.get("characters")
    if not isinstance(items, list) or not items:
        raise ValueError("character registry requires non-empty characters list")

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
        )

    default = str(raw.get("default_character", "")).strip() or next(iter(characters))
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
        }
        for spec in registry.characters.values()
    ]
