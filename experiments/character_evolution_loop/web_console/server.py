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

from character_evolution.canon_adapter import apply_contract, contract_to_canon_profile, load_contract
from character_evolution.human_choice import apply_human_choice
from character_evolution.memory import CharacterMemory

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
RUNS = ROOT / "runs" / "character_evolution"
CONTRACT = ROOT / "examples" / "lu_xin_canon_contract.json"
V01_STATE = ROOT / "examples" / "lu_xin_state_v01.json"
LATEST_STATE = RUNS / "latest_state.json"
LATEST_BATCH = RUNS / "latest_batch.json"
SCENE_REPORT = RUNS / "scene_validation.json"
LOCAL_CONFIG = ROOT / "config" / "character_v01.local.json"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def current_state_path() -> Path:
    return LATEST_STATE if LATEST_STATE.exists() else V01_STATE


def media_url(path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    candidate = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    try:
        rel = candidate.relative_to(ROOT)
    except ValueError:
        return None
    if not (RUNS.resolve() == candidate or RUNS.resolve() in candidate.parents):
        return None
    return "/media?path=" + urllib.parse.quote(rel.as_posix(), safe="")


def _candidate_view(item: dict[str, Any]) -> dict[str, Any]:
    value = dict(item)
    value["media_url"] = media_url(str(item.get("image_ref", "")))
    return value


def build_dashboard() -> dict[str, Any]:
    contract = read_json(CONTRACT, {}) or {}
    state = read_json(current_state_path(), {}) or {}
    batch = read_json(LATEST_BATCH, {}) or {}
    scene = read_json(SCENE_REPORT, {}) or {}
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

    return {
        "character": state.get("character") or contract.get("character", {}).get("name"),
        "version": state.get("version", 0),
        "state": state,
        "batch": {
            **batch,
            "candidates": [_candidate_view(x) for x in candidates],
            "shortlist": [_candidate_view(x) for x in shortlist],
        },
        "scene_validation": scene,
        "evidence_groups": evidence_groups,
        "versions": versions,
        "config_ready": LOCAL_CONFIG.exists(),
        "identity_anchor_media_url": media_url(state.get("identity_anchor")),
    }


def safe_media_path(raw: str) -> Path:
    decoded = urllib.parse.unquote(raw)
    candidate = (ROOT / decoded).resolve()
    base = RUNS.resolve()
    if not (candidate == base or base in candidate.parents):
        raise ValueError("media path outside runs directory")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def apply_choice_payload(payload: dict[str, Any]) -> dict[str, Any]:
    label = str(payload.get("label", "")).upper()
    if label not in {"A", "B", "C"}:
        raise ValueError("label must be A, B or C")

    contract = load_contract(CONTRACT)
    canon = contract_to_canon_profile(contract)
    state = CharacterMemory(current_state_path()).load(contract["character"]["name"])
    apply_contract(contract, state)
    batch = read_json(LATEST_BATCH)
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
            if isinstance(x, dict) and str(x.get("feature", "")).strip() and str(x.get("target", "")).strip()
        ],
    )
    CharacterMemory(LATEST_STATE).save(state)
    return build_dashboard()


def run_fixed_script(script: str) -> dict[str, Any]:
    if not LOCAL_CONFIG.exists():
        raise ValueError("缺少 config/character_v01.local.json；请先复制 example 并填写本机 ComfyUI 节点。")
    if script not in {"run_character_round.py", "run_scene_validation.py"}:
        raise ValueError("unsupported script")
    result = subprocess.run(
        [sys.executable, str(ROOT / script), "--config", str(LOCAL_CONFIG)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=3600,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-4000:] or f"{script} failed")
    return {"status": "ok", "dashboard": build_dashboard()}


class Handler(BaseHTTPRequestHandler):
    server_version = "CharacterDirector/0.6"

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
        if parsed.path == "/api/dashboard":
            self._json(build_dashboard())
            return
        if parsed.path == "/media":
            try:
                raw = urllib.parse.parse_qs(parsed.query).get("path", [""])[0]
                self._serve_file(safe_media_path(raw))
            except (ValueError, FileNotFoundError) as error:
                self._json({"status": "error", "message": str(error)}, 404)
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

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/choice":
                self._json(apply_choice_payload(payload))
            elif self.path == "/api/run-round":
                self._json(run_fixed_script("run_character_round.py"))
            elif self.path == "/api/run-scenes":
                self._json(run_fixed_script("run_scene_validation.py"))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except subprocess.TimeoutExpired as error:
            self._json({"status": "error", "message": f"local process timed out: {error.cmd}"}, 504)
        except Exception as error:
            self._json({"status": "error", "error_type": type(error).__name__, "message": str(error)}, 400)


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
