import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web_console.config_check import check_config
from web_console.registry import load_registry


class RegistryAndConfigTests(unittest.TestCase):
    def test_registry_separates_character_run_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir()
            (root / "examples").mkdir()
            (root / "runs").mkdir()
            for cid in ("a", "b"):
                (root / "examples" / f"{cid}.json").write_text("{}", encoding="utf-8")
                (root / "examples" / f"{cid}.state.json").write_text("{}", encoding="utf-8")
            (root / "config" / "characters.example.json").write_text(
                json.dumps(
                    {
                        "default_character": "a",
                        "characters": [
                            {
                                "id": "a",
                                "name": "A",
                                "contract": "examples/a.json",
                                "base_state": "examples/a.state.json",
                                "config": "config/a.local.json",
                                "run_dir": "runs/a",
                                "scene_validation_enabled": True,
                            },
                            {
                                "id": "b",
                                "name": "B",
                                "contract": "examples/b.json",
                                "base_state": "examples/b.state.json",
                                "config": "config/b.local.json",
                                "run_dir": "runs/b",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            registry = load_registry(root)
            self.assertNotEqual(
                registry.characters["a"].latest_state,
                registry.characters["b"].latest_state,
            )
            self.assertTrue(registry.characters["a"].scene_validation_enabled)
            self.assertFalse(registry.characters["b"].scene_validation_enabled)

    def test_local_registry_overrides_without_hiding_builtin_characters(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir()
            (root / "examples").mkdir()
            (root / "runs").mkdir()
            for cid in ("a", "b"):
                (root / "examples" / f"{cid}.json").write_text("{}", encoding="utf-8")
                (root / "examples" / f"{cid}.state.json").write_text("{}", encoding="utf-8")

            (root / "config" / "characters.example.json").write_text(
                json.dumps(
                    {
                        "default_character": "a",
                        "characters": [
                            {
                                "id": "a",
                                "name": "A",
                                "contract": "examples/a.json",
                                "base_state": "examples/a.state.json",
                                "config": "config/a.local.json",
                                "run_dir": "runs/a",
                            },
                            {
                                "id": "b",
                                "name": "B",
                                "contract": "examples/b.json",
                                "base_state": "examples/b.state.json",
                                "config": "config/b.local.json",
                                "run_dir": "runs/b",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "config" / "characters.local.json").write_text(
                json.dumps(
                    {
                        "characters": [
                            {
                                "id": "a",
                                "run_dir": "runs/a-custom",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            registry = load_registry(root)
            self.assertEqual(set(registry.characters), {"a", "b"})
            self.assertTrue(str(registry.characters["a"].run_dir).endswith("runs/a-custom"))
            self.assertTrue(str(registry.characters["b"].run_dir).endswith("runs/b"))

    def test_config_check_validates_nodes_and_api_key_env(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir()
            (root / "examples").mkdir()
            (root / "runs").mkdir()
            (root / "workflows").mkdir()
            contract = root / "examples" / "c.json"
            state = root / "examples" / "s.json"
            contract.write_text("{}", encoding="utf-8")
            state.write_text("{}", encoding="utf-8")
            workflow = root / "workflows" / "portrait.json"
            workflow.write_text(
                json.dumps(
                    {
                        "3": {"inputs": {"seed": 0}},
                        "6": {"inputs": {"text": ""}},
                        "9": {"inputs": {}},
                    }
                ),
                encoding="utf-8",
            )
            config = root / "config" / "character.local.json"
            config.write_text(
                json.dumps(
                    {
                        "comfyui": {
                            "base_url": "http://127.0.0.1:8190",
                            "workflow_path": "workflows/portrait.json",
                            "output_node": "9",
                            "prompt_node": "6",
                            "seed_node": "3",
                        },
                        "critic": {
                            "base_url": "https://example.invalid/v1",
                            "model": "vision",
                            "api_key_env": "TEST_CHAR_KEY",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "config" / "characters.example.json").write_text(
                json.dumps(
                    {
                        "default_character": "c",
                        "characters": [
                            {
                                "id": "c",
                                "name": "C",
                                "contract": "examples/c.json",
                                "base_state": "examples/s.json",
                                "config": "config/character.local.json",
                                "run_dir": "runs/c",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            spec = load_registry(root).characters["c"]
            with patch.dict(os.environ, {"TEST_CHAR_KEY": "secret"}):
                result = check_config(root=root, spec=spec, check_connection=False)
            by_name = {x["name"]: x for x in result["checks"]}
            self.assertTrue(by_name["prompt_node"]["ok"])
            self.assertTrue(by_name["output_node"]["ok"])
            self.assertTrue(by_name["critic_api_key"]["ok"])


if __name__ == "__main__":
    unittest.main()
