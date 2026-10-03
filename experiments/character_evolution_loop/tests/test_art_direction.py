import json
import tempfile
import unittest
from pathlib import Path

from character_evolution.art_direction import load_art_direction
from character_evolution.generation_prompt import CharacterGenerationPrompt
from character_evolution.models import CanonProfile, CharacterState


class ArtDirectionTests(unittest.TestCase):
    def test_style_lock_is_added_without_locking_character_face(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "style.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "work-art-direction/1",
                        "name": "test style",
                        "prompt_rules": ["clean 2D animation"],
                        "negative_rules": ["photorealism"],
                        "locked_dimensions": {"medium": "2D animation"},
                        "editable_dimensions": ["scene_palette"],
                    }
                ),
                encoding="utf-8",
            )
            style = load_art_direction(path)
            state = CharacterState(
                character="角色A",
                modifiable=["face_shape", "eyes"],
            )
            prompt = CharacterGenerationPrompt(art_direction=style).render(
                canon=CanonProfile(character="角色A"),
                state=state,
            )
            self.assertIn("style lock medium: 2D animation", prompt)
            self.assertIn("avoid style drift: photorealism", prompt)
            self.assertIn("face_shape", prompt)
            self.assertNotIn("style lock face_shape", prompt)

    def test_style_dimension_overlap_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "style.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "work-art-direction/1",
                        "name": "bad",
                        "locked_dimensions": {"medium": "2D"},
                        "editable_dimensions": ["medium"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_art_direction(path)


if __name__ == "__main__":
    unittest.main()
