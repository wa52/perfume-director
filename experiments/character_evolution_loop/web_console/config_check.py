from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from .registry import CharacterSpec


def _resolve(base: Path, raw: str) -> Path:
    value = Path(raw)
    return value if value.is_absolute() else base / value


def check_config(
    *,
    root: Path,
    spec: CharacterSpec,
    check_connection: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("contract", spec.contract.is_file(), str(spec.contract))
    add("base_state", spec.base_state.is_file(), str(spec.base_state))
    add("local_config", spec.config.is_file(), str(spec.config))

    config: dict[str, Any] = {}
    if spec.config.is_file():
        try:
            config = json.loads(spec.config.read_text(encoding="utf-8"))
            add("config_json", True, "valid JSON")
        except Exception as error:
            add("config_json", False, str(error))
            config = {}

    comfy = config.get("comfyui") if isinstance(config, dict) else None
    if isinstance(comfy, dict):
        required = ("base_url", "workflow_path", "output_node", "prompt_node")
        missing = [key for key in required if not comfy.get(key)]
        add("comfyui_fields", not missing, "missing: " + ", ".join(missing) if missing else "required fields present")

        workflow_path = _resolve(root, str(comfy.get("workflow_path", "")))
        workflow: dict[str, Any] = {}
        if workflow_path.is_file():
            try:
                workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
                add("portrait_workflow", True, str(workflow_path))
            except Exception as error:
                add("portrait_workflow", False, f"{workflow_path}: {error}")
        else:
            add("portrait_workflow", False, str(workflow_path))

        if workflow:
            for label, node_key in (
                ("prompt_node", "prompt_node"),
                ("output_node", "output_node"),
                ("seed_node", "seed_node"),
                ("reference_image_node", "reference_image_node"),
            ):
                value = comfy.get(node_key)
                if value is None and node_key in {"seed_node", "reference_image_node"}:
                    continue
                add(label, str(value) in workflow, f"node {value}")

        if check_connection and comfy.get("base_url"):
            url = str(comfy["base_url"]).rstrip("/") + "/system_stats"
            try:
                with urllib.request.urlopen(url, timeout=2.5) as response:
                    add("comfyui_connection", 200 <= response.status < 300, url)
            except Exception as error:
                add("comfyui_connection", False, f"{url}: {error}")
    else:
        add("comfyui_fields", False, "missing comfyui object")

    critic = config.get("critic") if isinstance(config, dict) else None
    if isinstance(critic, dict):
        env_name = str(critic.get("api_key_env", "")).strip()
        add("critic_model", bool(critic.get("base_url") and critic.get("model")), str(critic.get("model", "")))
        add("critic_api_key", bool(env_name and os.environ.get(env_name)), env_name or "api_key_env missing")
    else:
        add("critic_model", False, "missing critic object")
        add("critic_api_key", False, "missing critic object")

    scene = config.get("scene_comfyui") if isinstance(config, dict) else None
    if isinstance(scene, dict):
        scene_path = _resolve(root, str(scene.get("workflow_path", "")))
        add("scene_workflow", scene_path.is_file(), str(scene_path))
        add(
            "scene_reference_node",
            scene.get("reference_image_node") is not None,
            f"node {scene.get('reference_image_node')}",
        )
    else:
        add("scene_workflow", False, "scene_comfyui not configured")
        add("scene_reference_node", False, "scene_comfyui not configured")

    return {
        "character_id": spec.id,
        "ready": all(item["ok"] for item in checks if item["name"] not in {"scene_workflow", "scene_reference_node", "comfyui_connection"}),
        "checks": checks,
    }
