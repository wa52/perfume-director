from __future__ import annotations

import json
import mimetypes
import subprocess
import sys
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from character_evolution.archive import available_versions, archive_version, rollback_version
from character_evolution.canon_adapter import apply_contract, contract_to_canon_profile, load_contract
from character_evolution.human_choice import apply_human_choice
from character_evolution.memory import CharacterMemory
from web_console.config_check import check_config
from web_console.jobs import JobManager
from web_console.registry import CharacterSpec, load_registry, registry_summary


ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
RUNS_ROOT = ROOT / "runs"
JOBS = JobManager()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def registry():
    return load_registry(ROOT)


def get_spec(character_id: str | None = None) -> CharacterSpec:
    reg = registry()
    target = character_id or reg.default_character
    if target not in reg.characters:
        raise ValueError(f"unknown character_id: {target}")
    return reg.characters[target]


def media_url(path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    candidate = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    root = RUNS_ROOT.resolve()
    if not (candidate == root or root in candidate.parents):
        return None
    try:
        rel = candidate.relative_to(ROOT)
    except ValueError:
        return None
    return "/media?path=" + urllib.parse.quote(rel.as_posix(), safe="")


def safe_media_path(raw: str) -> Path:
    decoded = urllib.parse.unquote(raw)
    candidate = (ROOT / decoded).resolve()
    base = RUNS_ROOT.resolve()
    if not (candidate == base or base in candidate.parents):
        raise ValueError("media path outside runs directory")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def _candidate_view(item: dict[str, Any]) -> dict[str, Any]:
    value = dict(item)
    value["media_url"] = media_url(str(item.get("image_ref", "")))
    return value


def build_dashboard(character_id: str | None = None) -> dict[str, Any]:
    reg = registry()
    spec = get_spec(character_id)
    contract = read_json(spec.contract, {}) or {}
    state = read_json(spec.current_state(), {}) or {}
    batch = read_json(spec.latest_batch, {}) or {}
    scene = read_json(spec.scene_report, {}) or {}
    candidates = batch.get("candidates") or batch.get("shortlist") or []
    shortlist = batch.get("shortlist") or []

    evidence_groups = []
    for feature, refs in state.get("evidence_refs", {}).items():
        evidence_groups.append({
            "feature": feature,
            "constraint": state.get("canon_constraints", {}).get(feature)
            or state.get("design_targets", {}).get(feature),
            "refs": refs,
        })

    versions = []
    for item in state.get("history", []):
        versions.append({
            "version": item.get("version"),
            "image_ref": item.get("image_ref"),
            "media_url": media_url(item.get("image_ref")),
            "score": item.get("score"),
            "accepted": item.get("accepted"),
            "human_feedback": item.get("human_feedback"),
        })

    archived = available_versions(spec.run_dir)
    for item in archived:
        item["identity_anchor_media_url"] = media_url(item.get("identity_anchor"))

    active_job = JOBS.active_for(spec.id)
    config_state = check_config(root=ROOT, spec=spec, check_connection=False)
    art_direction = None
    if spec.config.is_file():
        local_config = read_json(spec.config, {}) or {}
        art_raw = local_config.get("art_direction_path")
        if art_raw:
            art_path = Path(str(art_raw))
            art_path = art_path if art_path.is_absolute() else ROOT / art_path
            if art_path.is_file():
                art_direction = read_json(art_path, {})

    return {
        "character_id": spec.id,
        "character": state.get("character") or spec.name,
        "version": state.get("version", 0),
        "characters": registry_summary(reg),
        "default_character": reg.default_character,
        "state": state,
        "batch": {
            **batch,
            "candidates": [_candidate_view(x) for x in candidates],
            "shortlist": [_candidate_view(x) for x in shortlist],
        },
        "scene_validation": scene,
        "evidence_groups": evidence_groups,
        "versions": versions,
        "archived_versions": archived,
        "config_ready": config_state["ready"],
        "config_state": config_state,
        "art_direction": art_direction,
        "identity_anchor_media_url": media_url(state.get("identity_anchor")),
        "active_job": active_job.to_dict() if active_job else None,
    }


def apply_choice_payload(payload: dict[str, Any]) -> dict[str, Any]:
    character_id = str(payload.get("character_id", "")).strip() or None
    spec = get_spec(character_id)
    label = str(payload.get("label", "")).upper()
    if label not in {"A", "B", "C"}:
        raise ValueError("label must be A, B or C")

    contract = load_contract(spec.contract)
    canon = contract_to_canon_profile(contract)
    state = CharacterMemory(spec.current_state()).load(contract["character"]["name"])
    apply_contract(contract, state)
    batch = read_json(spec.latest_batch)
    if not batch:
        raise ValueError("latest_batch.json is missing; run a character round first")

    lock_features = payload.get("lock_features", [])
    rejects = payload.get("rejected", [])
    changes = payload.get("changes", [])
    if not isinstance(lock_features, list) or not isinstance(rejects, list) or not isinstance(changes, list):
        raise ValueError("lock_features, rejected and changes must be arrays")

    apply_human_choice(
        state=state,
        canon=canon,
        batch_report=batch,
        label=label,
        feedback=str(payload.get("feedback", "")).strip() or None,
        locks={str(x): f"keep-from-{label}" for x in lock_features if str(x).strip()},
        rejected=[str(x) for x in rejects if str(x).strip()],
        explicit_changes=[
            {"feature": str(x.get("feature", "")).strip(), "target": str(x.get("target", "")).strip()}
            for x in changes
            if isinstance(x, dict)
            and str(x.get("feature", "")).strip()
            and str(x.get("target", "")).strip()
        ],
    )
    spec.run_dir.mkdir(parents=True, exist_ok=True)
    CharacterMemory(spec.latest_state).save(state)
    archive_version(
        run_dir=spec.run_dir,
        state_path=spec.latest_state,
        batch_path=spec.latest_batch,
        scene_path=spec.scene_report,
    )
    return build_dashboard(spec.id)


def rollback_payload(payload: dict[str, Any]) -> dict[str, Any]:
    character_id = str(payload.get("character_id", "")).strip() or None
    spec = get_spec(character_id)
    active = JOBS.active_for(spec.id)
    if active and active.status in {"queued", "running"}:
        raise ValueError("cannot rollback while a character job is active")
    version = int(payload.get("version", -1))
    rollback_version(
        run_dir=spec.run_dir,
        version=version,
        latest_state=spec.latest_state,
        latest_batch=spec.latest_batch,
        latest_scene=spec.scene_report,
    )
    return build_dashboard(spec.id)


def _run_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=3600,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-5000:] or f"command failed: {command}")
    return {"stdout": result.stdout[-5000:]}


def run_character_job(spec: CharacterSpec, kind: str) -> dict[str, Any]:
    if not spec.config.exists():
        raise ValueError(f"missing local config: {spec.config}")
    spec.run_dir.mkdir(parents=True, exist_ok=True)

    if kind == "round":
        command = [
            sys.executable,
            str(ROOT / "run_character_round.py"),
            "--config", str(spec.config),
            "--contract", str(spec.contract),
            "--state", str(spec.current_state()),
            "--state-output", str(spec.latest_state),
            "--report-output", str(spec.latest_batch),
        ]
    elif kind == "scenes":
        if not spec.latest_state.exists():
            raise ValueError("scene validation requires a generated/human-reviewed latest_state")
        command = [
            sys.executable,
            str(ROOT / "run_scene_validation.py"),
            "--config", str(spec.config),
            "--contract", str(spec.contract),
            "--state", str(spec.latest_state),
            "--output", str(spec.scene_report),
        ]
    else:
        raise ValueError(f"unsupported job kind: {kind}")

    output = _run_command(command)
    return {
        "kind": kind,
        "character_id": spec.id,
        "output": output,
        "dashboard": build_dashboard(spec.id),
    }


def submit_job(payload: dict[str, Any]) -> dict[str, Any]:
    character_id = str(payload.get("character_id", "")).strip() or None
    kind = str(payload.get("kind", "")).strip()
    if kind not in {"round", "scenes"}:
        raise ValueError("kind must be round or scenes")
    spec = get_spec(character_id)
    job = JOBS.submit(
        kind=kind,
        character_id=spec.id,
        fn=lambda: run_character_job(spec, kind),
    )
    return {"status": "accepted", "job": job.to_dict()}


def config_payload(character_id: str | None, connection: bool) -> dict[str, Any]:
    spec = get_spec(character_id)
    return check_config(root=ROOT, spec=spec, check_connection=connection)


class Handler(BaseHTTPRequestHandler):
    server_version = "CharacterDirector/0.7"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[web] " + fmt % args + "\n")

    def _json(self, value: Any, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        character_id = params.get("character_id", [None])[0]

        try:
            if parsed.path == "/api/dashboard":
                self._json(build_dashboard(character_id))
                return
            if parsed.path == "/api/config-check":
                connection = params.get("connection", ["0"])[0] == "1"
                self._json(config_payload(character_id, connection))
                return
            if parsed.path.startswith("/api/jobs/"):
                job_id = parsed.path.rsplit("/", 1)[-1]
                self._json({"job": JOBS.get(job_id).to_dict()})
                return
            if parsed.path == "/api/jobs":
                self._json({"jobs": [job.to_dict() for job in JOBS.list_recent()]})
                return
            if parsed.path == "/media":
                raw = params.get("path", [""])[0]
                self._serve_file(safe_media_path(raw))
                return
            if parsed.path in {"/", "/index.html"}:
                self._serve_file(STATIC / "index.html")
                return
            if parsed.path.startswith("/assets/"):
                name = Path(parsed.path).name
                if name in {"app.js", "styles.css"}:
                    self._serve_file(STATIC / name)
                    return
            self.send_error(HTTPStatus.NOT_FOUND)
        except KeyError as error:
            self._json({"status": "error", "message": f"job not found: {error.args[0]}"}, 404)
        except (ValueError, FileNotFoundError) as error:
            self._json({"status": "error", "message": str(error)}, 400)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be an object")

            if self.path == "/api/choice":
                self._json(apply_choice_payload(payload))
            elif self.path == "/api/rollback":
                self._json(rollback_payload(payload))
            elif self.path == "/api/jobs":
                self._json(submit_job(payload), 202)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as error:
            self._json(
                {
                    "status": "error",
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
                400,
            )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Local Character Director Web Console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Character Director: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
