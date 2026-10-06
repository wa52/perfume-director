from __future__ import annotations

import copy
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from ..models import CharacterState


HttpFn = Callable[[str, bytes | None, dict[str, str] | None, float], bytes]


@dataclass(slots=True)
class ComfyUIConfig:
    base_url: str
    workflow_path: Path
    output_node: str
    prompt_node: str
    prompt_input: str = "text"
    seed_node: str | None = None
    seed_input: str = "seed"
    reference_image_node: str | None = None
    reference_image_input: str = "image"
    seed_start: int = 2026100201
    timeout_seconds: float = 300.0
    poll_seconds: float = 1.0
    output_dir: Path = Path("runs/character_evolution")


def _http(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class ComfyUICharacterGenerator:
    """Generic ComfyUI API workflow adapter for character candidates.

    It intentionally knows nothing about a specific checkpoint or node pack. The
    user exports an API-format workflow from ComfyUI and maps the positive prompt,
    optional seed, and image output node through ComfyUIConfig.
    """

    def __init__(self, config: ComfyUIConfig, http_fn: HttpFn = _http):
        self.config = config
        self.http_fn = http_fn

    def _load_workflow(self) -> dict[str, Any]:
        workflow = json.loads(self.config.workflow_path.read_text(encoding="utf-8"))
        if self.config.prompt_node not in workflow:
            raise ValueError(f"prompt node {self.config.prompt_node!r} not found in workflow")
        if self.config.output_node not in workflow:
            raise ValueError(f"output node {self.config.output_node!r} not found in workflow")
        if self.config.seed_node and self.config.seed_node not in workflow:
            raise ValueError(f"seed node {self.config.seed_node!r} not found in workflow")
        if self.config.reference_image_node and self.config.reference_image_node not in workflow:
            raise ValueError(f"reference image node {self.config.reference_image_node!r} not found in workflow")
        return workflow

    @staticmethod
    def _set_input(workflow: dict[str, Any], node_id: str, input_name: str, value: Any) -> None:
        node = workflow[node_id]
        inputs = node.setdefault("inputs", {})
        if input_name not in inputs:
            raise ValueError(f"workflow node {node_id!r} has no input {input_name!r}")
        inputs[input_name] = value


    def _upload_image(self, path: str | Path) -> str:
        path = Path(path)
        boundary = "----CharacterEvolutionBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
        result = json.loads(
            self.http_fn(
                self.config.base_url.rstrip("/") + "/upload/image",
                body,
                {"Content-Type": "multipart/form-data; boundary=" + boundary},
                min(self.config.timeout_seconds, 60.0),
            )
        )
        return "/".join(
            part for part in (result.get("subfolder"), result["name"]) if part
        )

    def _execute_one(self, workflow: dict[str, Any], destination: Path) -> Path:
        base = self.config.base_url.rstrip("/")
        body = json.dumps({"prompt": workflow}).encode("utf-8")
        result = json.loads(
            self.http_fn(
                base + "/prompt",
                body,
                {"Content-Type": "application/json"},
                min(self.config.timeout_seconds, 60.0),
            )
        )
        if result.get("node_errors") or "prompt_id" not in result:
            raise RuntimeError(f"ComfyUI rejected workflow: {result}")

        prompt_id = result["prompt_id"]
        deadline = time.monotonic() + self.config.timeout_seconds
        while time.monotonic() < deadline:
            history = json.loads(
                self.http_fn(
                    base + "/history/" + prompt_id,
                    None,
                    None,
                    min(self.config.timeout_seconds, 60.0),
                )
            ).get(prompt_id)
            if history:
                status = history.get("status", {})
                if status.get("status_str") == "error":
                    errors = [
                        message[1]
                        for message in status.get("messages", [])
                        if isinstance(message, list)
                        and len(message) > 1
                        and message[0] == "execution_error"
                    ]
                    error = errors[-1] if errors else {}
                    raise RuntimeError(
                        "ComfyUI execution failed at "
                        + str(error.get("node_type", "unknown"))
                        + ": "
                        + str(error.get("exception_message", "see server log"))
                    )

                images = (
                    history.get("outputs", {})
                    .get(str(self.config.output_node), {})
                    .get("images", [])
                )
                if images:
                    image = images[0]
                    query = urllib.parse.urlencode(
                        {key: image[key] for key in ("filename", "subfolder", "type")}
                    )
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(
                        self.http_fn(
                            base + "/view?" + query,
                            None,
                            None,
                            min(self.config.timeout_seconds, 60.0),
                        )
                    )
                    return destination
                if status.get("completed"):
                    raise RuntimeError("ComfyUI workflow completed without selected output image")
            time.sleep(self.config.poll_seconds)

        raise TimeoutError(f"ComfyUI render timed out for prompt {prompt_id}")

    def generate(self, *, prompt: str, state: CharacterState, count: int) -> Sequence[str]:
        if count < 1:
            raise ValueError("count must be >= 1")
        template = self._load_workflow()
        run_dir = self.config.output_dir / state.character / f"v{state.version + 1:03d}"
        refs: list[str] = []
        uploaded_reference = None
        if self.config.reference_image_node and state.identity_anchor:
            uploaded_reference = self._upload_image(state.identity_anchor)

        for index in range(count):
            workflow = copy.deepcopy(template)
            self._set_input(
                workflow,
                self.config.prompt_node,
                self.config.prompt_input,
                prompt,
            )
            if self.config.reference_image_node and uploaded_reference:
                self._set_input(
                    workflow,
                    self.config.reference_image_node,
                    self.config.reference_image_input,
                    uploaded_reference,
                )
            seed = self.config.seed_start + state.version * 1000 + index
            if self.config.seed_node:
                self._set_input(
                    workflow,
                    self.config.seed_node,
                    self.config.seed_input,
                    seed,
                )
            destination = run_dir / f"candidate-{index + 1:02d}-seed-{seed}.png"
            refs.append(str(self._execute_one(workflow, destination)))
        return refs
