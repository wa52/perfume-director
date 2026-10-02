import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web_console import server


def make_workspace(root: Path) -> tuple[Path, Path]:
    examples = root / "examples"
    config = root / "config"
    runs = root / "runs" / "character_evolution"
    examples.mkdir(parents=True)
    config.mkdir()
    runs.mkdir(parents=True)

    (examples / "lu_xin_state_v01.json").write_text(
        json.dumps(
            {
                "character": "陆辛",
                "version": 1,
                "locked": {"age": 23},
                "evidence_refs": {},
                "history": [],
                "modifiable": ["eyes"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (examples / "lu_xin_canon_contract.json").write_text(
        json.dumps({"character": {"name": "陆辛"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (config / "characters.example.json").write_text(
        json.dumps(
            {
                "default_character": "lu_xin",
                "characters": [
                    {
                        "id": "lu_xin",
                        "name": "陆辛",
                        "contract": "examples/lu_xin_canon_contract.json",
                        "base_state": "examples/lu_xin_state_v01.json",
                        "config": "config/character_v01.local.json",
                        "run_dir": "runs/character_evolution",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return runs, config


class WebConsoleTests(unittest.TestCase):
    def test_media_url_rejects_external_path(self):
        self.assertIsNone(server.media_url("/tmp/outside.png"))

    def test_safe_media_path_blocks_traversal(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            server.safe_media_path("../../etc/passwd")

    def test_dashboard_uses_registry_and_candidate_media_urls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runs, _ = make_workspace(root)
            image = runs / "candidate.png"
            image.write_bytes(b"png")
            (runs / "latest_batch.json").write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "rank": 1,
                                "label": "A",
                                "image_ref": str(image),
                                "scores": {"canon": 90},
                            }
                        ],
                        "shortlist": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(server, "ROOT", root), patch.object(server, "RUNS_ROOT", root / "runs"):
                payload = server.build_dashboard("lu_xin")

            self.assertEqual(payload["character_id"], "lu_xin")
            self.assertEqual(payload["character"], "陆辛")
            self.assertEqual(payload["batch"]["candidates"][0]["label"], "A")
            self.assertTrue(
                payload["batch"]["candidates"][0]["media_url"].startswith("/media?path=")
            )
            self.assertEqual(payload["characters"][0]["id"], "lu_xin")

    def test_unknown_character_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            make_workspace(root)
            with patch.object(server, "ROOT", root):
                with self.assertRaises(ValueError):
                    server.get_spec("missing")


if __name__ == "__main__":
    unittest.main()
