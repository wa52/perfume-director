import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from character_evolution.archive import archive_version, available_versions, rollback_version
from web_console.jobs import JobManager


class ArchiveTests(unittest.TestCase):
    def test_archive_and_rollback_restore_state_batch_and_scene(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            state = run_dir / "latest_state.json"
            batch = run_dir / "latest_batch.json"
            scene = run_dir / "scene_validation.json"

            state.write_text(json.dumps({"version": 2, "character": "陆辛"}), encoding="utf-8")
            batch.write_text(json.dumps({"version": 2, "marker": "batch-v2"}), encoding="utf-8")
            scene.write_text(json.dumps({"version": 2, "marker": "scene-v2"}), encoding="utf-8")
            archive_version(
                run_dir=run_dir,
                state_path=state,
                batch_path=batch,
                scene_path=scene,
            )

            state.write_text(json.dumps({"version": 3, "character": "陆辛"}), encoding="utf-8")
            batch.write_text(json.dumps({"version": 3}), encoding="utf-8")
            scene.unlink()

            restored = rollback_version(
                run_dir=run_dir,
                version=2,
                latest_state=state,
                latest_batch=batch,
                latest_scene=scene,
            )
            self.assertEqual(restored["version"], 2)
            self.assertEqual(json.loads(batch.read_text())["marker"], "batch-v2")
            self.assertEqual(json.loads(scene.read_text())["marker"], "scene-v2")
            self.assertEqual([x["version"] for x in available_versions(run_dir)], [2])


class JobManagerTests(unittest.TestCase):
    def test_same_character_cannot_run_two_jobs_at_once(self):
        manager = JobManager()
        gate = threading.Event()

        def slow():
            gate.wait(timeout=1)
            return {"ok": True}

        first = manager.submit(kind="round", character_id="lu_xin", fn=slow)
        self.assertIn(first.status, {"queued", "running"})
        with self.assertRaises(ValueError):
            manager.submit(kind="scenes", character_id="lu_xin", fn=lambda: None)
        gate.set()

        deadline = time.time() + 2
        while manager.get(first.id).status in {"queued", "running"} and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(manager.get(first.id).status, "succeeded")

    def test_different_characters_can_run_independently(self):
        manager = JobManager()
        a = manager.submit(kind="round", character_id="a", fn=lambda: "A")
        b = manager.submit(kind="round", character_id="b", fn=lambda: "B")
        deadline = time.time() + 2
        while (
            manager.get(a.id).status in {"queued", "running"}
            or manager.get(b.id).status in {"queued", "running"}
        ) and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(manager.get(a.id).result, "A")
        self.assertEqual(manager.get(b.id).result, "B")


if __name__ == "__main__":
    unittest.main()
