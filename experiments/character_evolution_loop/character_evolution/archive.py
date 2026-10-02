from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def version_dir(run_dir: Path, version: int) -> Path:
    return run_dir / "versions" / f"v{version:03d}"


def archive_version(
    *,
    run_dir: Path,
    state_path: Path,
    batch_path: Path | None = None,
    scene_path: Path | None = None,
) -> Path:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    version = int(state.get("version", 0))
    target = version_dir(run_dir, version)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(state_path, target / "state.json")
    if batch_path and batch_path.exists():
        shutil.copy2(batch_path, target / "batch.json")
    if scene_path and scene_path.exists():
        shutil.copy2(scene_path, target / "scene_validation.json")
    return target


def available_versions(run_dir: Path) -> list[dict[str, Any]]:
    root = run_dir / "versions"
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for folder in sorted(root.glob("v*")):
        state_path = folder / "state.json"
        if not state_path.exists():
            continue
        state = json.loads(state_path.read_text(encoding="utf-8"))
        out.append({
            "version": int(state.get("version", 0)),
            "path": str(state_path),
            "identity_anchor": state.get("identity_anchor"),
            "human_feedback": list(state.get("human_feedback", [])),
            "locked": dict(state.get("locked", {})),
        })
    return out


def rollback_version(
    *,
    run_dir: Path,
    version: int,
    latest_state: Path,
    latest_batch: Path,
    latest_scene: Path,
) -> dict[str, Any]:
    source = version_dir(run_dir, version)
    state_source = source / "state.json"
    if not state_source.exists():
        raise ValueError(f"archived version V{version:03d} does not exist")

    latest_state.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(state_source, latest_state)

    batch_source = source / "batch.json"
    if batch_source.exists():
        shutil.copy2(batch_source, latest_batch)
    elif latest_batch.exists():
        latest_batch.unlink()

    scene_source = source / "scene_validation.json"
    if scene_source.exists():
        shutil.copy2(scene_source, latest_scene)
    elif latest_scene.exists():
        latest_scene.unlink()

    return json.loads(latest_state.read_text(encoding="utf-8"))
