import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from check_background import check


class BackgroundTests(unittest.TestCase):
    def test_catches_black_output_and_accepts_real_dark_variation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'background.png'
            image = Image.new('RGB', (32, 32))
            image.save(path)
            with self.assertRaisesRegex(ValueError, 'constant/black'):
                check(path)
            ImageDraw.Draw(image).rectangle((16, 0, 31, 31), fill=(20, 15, 10))
            image.save(path)
            self.assertGreater(check(path)['stddev'][0], 0)


if __name__ == '__main__':
    unittest.main()
