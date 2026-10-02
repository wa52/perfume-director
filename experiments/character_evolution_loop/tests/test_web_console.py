import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web_console import server


class WebConsoleTests(unittest.TestCase):
    def test_media_url_rejects_external_path(self):
        self.assertIsNone(server.media_url("/tmp/outside.png"))

    def test_safe_media_path_blocks_traversal(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            server.safe_media_path("../../etc/passwd")

    def test_dashboard_contains_candidate_media_urls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runs = root / "runs" / "character_evolution"
            examples = root / "examples"
            config = root / "config"
            runs.mkdir(parents=True)
            examples.mkdir()
            config.mkdir()
            image = runs / "candidate.png"
            image.write_bytes(b"png")
            (examples / "lu_xin_state_v01.json").write_text(json.dumps({"character":"陆辛","version":1,"locked":{"age":23},"evidence_refs":{},"history":[]}, ensure_ascii=False), encoding="utf-8")
            (examples / "lu_xin_canon_contract.json").write_text(json.dumps({"character":{"name":"陆辛"}}, ensure_ascii=False), encoding="utf-8")
            (runs / "latest_batch.json").write_text(json.dumps({"candidates":[{"rank":1,"label":"A","image_ref":str(image),"scores":{"canon":90}}],"shortlist":[]}, ensure_ascii=False), encoding="utf-8")
            with patch.object(server,"ROOT",root), patch.object(server,"RUNS",runs), patch.object(server,"CONTRACT",examples/"lu_xin_canon_contract.json"), patch.object(server,"V01_STATE",examples/"lu_xin_state_v01.json"), patch.object(server,"LATEST_STATE",runs/"latest_state.json"), patch.object(server,"LATEST_BATCH",runs/"latest_batch.json"), patch.object(server,"SCENE_REPORT",runs/"scene_validation.json"), patch.object(server,"LOCAL_CONFIG",config/"character_v01.local.json"):
                payload=server.build_dashboard()
            self.assertEqual(payload["character"],"陆辛")
            self.assertEqual(payload["batch"]["candidates"][0]["label"],"A")
            self.assertTrue(payload["batch"]["candidates"][0]["media_url"].startswith("/media?path="))


if __name__ == "__main__":
    unittest.main()
