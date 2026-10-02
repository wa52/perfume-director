import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import random
from unittest.mock import patch
from PIL import Image
import reference_store as store


class ReferenceStoreTests(unittest.TestCase):
    def test_pool_explores_near_quality_examples_and_excludes_weak_ones(self):
        rows=[{'id':str(i),'brand':str(i),'source_url':'https://example.test/'+str(i),'style':'editorial',
               'analysis':{'perfume_suitability':90 if i<20 else 10,'renderer_compatibility':90 if i<20 else 10,
                           'has_campaign_typography':True}} for i in range(24)]
        with tempfile.TemporaryDirectory() as folder,patch.object(store,'entries',return_value=rows):
            draws=[store.planning_pool(Path(folder),2,rng=random.Random(seed)) for seed in range(20)]
        ids={row['id'] for draw in draws for row in draw}
        self.assertGreater(len(ids),10)
        self.assertTrue(all(int(ident)<20 for ident in ids))
        self.assertTrue(all(len({row['brand'] for row in draw})==2 for draw in draws))

    def test_recent_reference_usage_counts_distinct_ids_and_ignores_bad_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for i,data in enumerate([[{'id':'A'},{'id':'A'},{'id':'B'}],[{'id':'A'}]]):
                target=root/f'runs/batches/{i}/Planning-references.json'
                target.parent.mkdir(parents=True);target.write_text(json.dumps(data),encoding='utf-8')
            bad=root/'runs/batches/bad/Planning-references.json';bad.parent.mkdir();bad.write_text('{',encoding='utf-8')
            self.assertEqual(store.recent_reference_usage(root),{'A':2,'B':1})

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
            # A public checkout stores accepted files in their final folders,
            # not in an ignored download cache. Re-import must work there too.
            for row in downloads:row['path']='references/luxury/'+Path(row['path']).name
            (root/'references/downloads.json').write_text(json.dumps(downloads),encoding='utf-8')
            store.import_curated(root)
            self.assertEqual(len(store.entries(root)),4)


if __name__ == '__main__':
    unittest.main()
