import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from PIL import Image
import reference_store as store


class ReferenceStoreTests(unittest.TestCase):
    def test_original_bytes_idempotent_import_and_analysis_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'references/candidates').mkdir(parents=True)
            downloads, curated = [], []
            for i, brand in enumerate(('A', 'A', 'B', 'C')):
                path = root/f'references/candidates/{i}.png'
                Image.new('RGB', (4, 4), (i*40, 0, 0)).save(path)
                content = path.read_bytes()
                downloads.append({'id': str(i), 'brand': brand, 'status': 'downloaded', 'path': str(path.relative_to(root)),
                    'sha256': hashlib.sha256(content).hexdigest(), 'width': 4, 'height': 4,
                    'source_url': 'https://example.com/source', 'image_url': 'https://example.com/image.png'})
                curated.append({'id': str(i), 'accepted': True, 'reference_kind': 'campaign', 'reason': 'test',
                    'analysis': {'perfume_suitability': 100-i}})
            for filename, data in (('downloads.json', downloads), ('curated.json', curated)):
                (root/'references'/filename).write_text(json.dumps(data), encoding='utf-8')
            store.import_curated(root)
            with closing(sqlite3.connect(root/'kb/design_kb.sqlite3')) as conn:
                rows = conn.execute('SELECT sha256,image_bytes FROM reference_images').fetchall()
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(hashlib.sha256(blob).hexdigest() == sha for sha, blob in rows))
            self.assertEqual([row['brand'] for row in store.select(root)], ['A', 'B', 'C'])
            store.update_analysis(root, 'references/luxury/0.png', {'perfume_suitability': 50})
            store.import_curated(root)
            entries = store.entries(root)
            self.assertEqual(len(entries), 4)
            first = next(row for row in entries if row['id'] == '0')
            self.assertEqual(first['analysis_origin'], 'vision_api')
            self.assertEqual(first['analysis']['perfume_suitability'], 50)


if __name__ == '__main__':
    unittest.main()
