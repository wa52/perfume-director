from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ArtDirection:
    schema_version: str
    name: str
    prompt_rules: list[str] = field(default_factory=list)
    negative_rules: list[str] = field(default_factory=list)
    locked_dimensions: dict[str, Any] = field(default_factory=dict)
    editable_dimensions: list[str] = field(default_factory=list)

    def prompt_fragment(self) -> str:
        parts = []
        if self.name:
            parts.append(f"work-level art direction: {self.name}")
        parts.extend(self.prompt_rules)
        for key, value in self.locked_dimensions.items():
            parts.append(f"style lock {key}: {value}")
        if self.negative_rules:
            parts.append("avoid style drift: " + " ; ".join(self.negative_rules))
        return ", ".join(parts)


def load_art_direction(path: str | Path | None) -> ArtDirection | None:
    if path is None:
        return None
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "work-art-direction/1":
        raise ValueError("unsupported art direction schema")
    locked = raw.get("locked_dimensions", {})
    editable = raw.get("editable_dimensions", [])
    if not isinstance(locked, dict) or not isinstance(editable, list):
        raise ValueError("invalid art direction dimensions")
    overlap = set(locked).intersection(str(x) for x in editable)
    if overlap:
        raise ValueError(f"style dimensions cannot be both locked and editable: {sorted(overlap)}")
    return ArtDirection(
        schema_version=raw["schema_version"],
        name=str(raw.get("name", "")),
        prompt_rules=[str(x) for x in raw.get("prompt_rules", [])],
        negative_rules=[str(x) for x in raw.get("negative_rules", [])],
        locked_dimensions=dict(locked),
        editable_dimensions=[str(x) for x in editable],
    )
