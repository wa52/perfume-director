import copy
import json
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
import categories
import poster
import reference_store


class ClothingTests(unittest.TestCase):
    def test_invalid_subtype_or_mode_cannot_enter_loop(self):
        for config in ({'product_category':'menswear','garment_type':'unknown'},
                       {'product_category':'womenswear','display_mode':'try_on'},
                       {'product_category':'perfume','garment_type':'dress'}):
            with self.assertRaises(ValueError):categories.profile(config)

    def test_hanging_dress_never_receives_bottle_floor_shadow(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        config={'product_category':'womenswear','garment_type':'dress','display_mode':'hanging'}
        spec['product_category']='womenswear'
        result=categories.spec_policy(spec,config)
        self.assertEqual(result['scene_mode'],'graphic')
        self.assertEqual(result['shadow']['opacity'],0)
        self.assertEqual(result['garment_type'],'dress')
        poster.validate(result)
        unsafe=copy.deepcopy(result);unsafe['shadow']['opacity']=.1
        with self.assertRaisesRegex(ValueError,'clothing|Clothing'):poster.validate(unsafe)
        self.assertIn('complete hem',categories.context(config))

    def test_original_model_preserves_original_photo_policy(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        before=copy.deepcopy(spec)
        result=categories.spec_policy(spec,{'product_category':'menswear','display_mode':'original_model'})
        self.assertEqual(result.get('scene_mode'),before.get('scene_mode'))
        self.assertEqual(result['shadow'],before['shadow'])
        self.assertIn('entire supplied person',categories.context({'product_category':'menswear','display_mode':'original_model'}))

    def test_subtype_retrieval_has_explicit_same_audience_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with closing(reference_store.connect(root)) as conn,conn:
                for index,kind in enumerate(('shirt','shirt','dress','dress')):
                    category='menswear' if index<3 else 'womenswear'
                    analysis=json.dumps({'garment_types':[kind],'quality_score':90})
                    conn.execute('INSERT INTO reference_images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (str(index),'Brand'+str(index),'editorial','commercial','https://example.org','https://example.org/image','image.png',800,1000,str(index),b'x','reviewed',analysis,'vision_api','research','today'))
                    conn.execute('INSERT INTO reference_categories VALUES (?,?)',(str(index),category))
            rows=reference_store.planning_pool(root,category='menswear',garment_type='shirt')
            self.assertEqual({row['id'] for row in rows},{'0','1','2'})
            self.assertEqual({row['retrieval_scope'] for row in rows},{'same_audience_style_fallback'})
            self.assertEqual(reference_store.planning_pool(root,category='perfume'),[])
            with closing(reference_store.connect(root)) as conn,conn:
                conn.execute('UPDATE reference_images SET analysis_json=? WHERE id=?',(json.dumps({'garment_types':['shirt']}),'2'))
            exact=reference_store.planning_pool(root,category='menswear',garment_type='shirt')
            self.assertEqual({row['retrieval_scope'] for row in exact},{'garment_match'})

    def test_all_clothing_workflow_widget_orders_match_node(self):
        files=list((poster.ROOT/'workflows/clothing').glob('*.ui.json'))
        self.assertEqual(len(files),18)
        for path in files:
            graph=poster.read(path);node=graph['nodes'][1]
            brief,category,kind,mode=node['widgets_values']
            self.assertEqual(node['type'],'ClothingDirectorLoop')
            categories.profile({'product_category':category,'garment_type':kind,'display_mode':mode})
            self.assertTrue(brief)


if __name__=='__main__':unittest.main()
