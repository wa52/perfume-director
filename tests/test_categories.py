import copy
from contextlib import closing
import tempfile
from pathlib import Path
import unittest
from PIL import Image
import categories
import concepts
import poster
import quality
import reference_store


class CategoryTests(unittest.TestCase):
    def test_shoe_critic_is_not_given_a_conflicting_bottle_height_minimum(self):
        config={'product_category':'footwear','creative_direction':{'scene_mode':'graphic'}}
        self.assertNotIn('actual height 35-74%',poster.concept_context(config))
        spec=poster.read(poster.ROOT/'samples/categories/categories-recovery-20261003/footwear/concept-3/PosterSpec.json')
        geometry=poster.rendered_geometry(spec,poster.ROOT/'assets/products/categories/footwear.png',poster.FONT_CHOICES[0])
        self.assertGreater(geometry['product_width_ratio'],.55)
        self.assertLess(geometry['fresh_concept_size_policy']['minimum_height_ratio'],.35)
        self.assertTrue(geometry['fresh_concept_size_policy']['within_range'])

    def test_unsafe_side_column_patch_reports_measured_candidate_not_only_rejection(self):
        spec=poster.read(poster.ROOT/'samples/categories/categories-recovery-20261003/footwear/concept-3/PosterSpec.json')
        with self.assertRaises(ValueError) as raised:
            poster.apply_safe_changes(spec,[{'path':'title.size','op':'set','value':100}],poster.ROOT/'assets/products/categories/footwear.png',poster.FONT_CHOICES[0],'concept-3')
        self.assertIn('Proposed geometry:',str(raised.exception))
        self.assertIn('text_bbox',str(raised.exception))

    def test_wide_shoe_fits_without_bottle_height_rule(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'shoe.png'
            Image.new('RGBA',(900,280),(40,90,110,255)).save(path)
            item={'product':[.5,.56,.30],'palette':['#cce0e0','#153839'], 'lighting':'soft frontal',
                'background_prompt':'Empty teal paper with soft frontal illumination',
                'type':{'font':poster.FONT_CHOICES[0],'title':[.07,.13,60],'logo':[.07,.05,26],'subtitle':[.07,.85,24],'price':[.07,.92,20]}}
            config={'font':poster.FONT_CHOICES[0],'product_category':'footwear'}
            spec=concepts.build_spec(poster,config,item,path,{'title':'SHOE','logo':'BRAND','subtitle':'','price':''})
            geometry=poster.rendered_geometry(spec,path,config['font'])
            self.assertNotIn('product_scale_outside_hero_range',quality.layout_issues(spec,geometry,'concept-1'))
            self.assertGreater(geometry['product_bbox'][2]-geometry['product_bbox'][0],1080*.55)
            with self.assertRaisesRegex(ValueError,'too small'):
                concepts.build_spec(poster,{'font':config['font']},item,path,{'title':'SHOE','logo':'BRAND','subtitle':'','price':''})

    def test_category_pools_cannot_silently_use_perfume_references(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with closing(reference_store.connect(root)) as conn,conn:
                for index,category in enumerate(('perfume','footwear')):
                    conn.execute('INSERT INTO reference_images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (str(index),'Brand'+str(index),'editorial','commercial','https://example.org','https://example.org/image','image.png',800,1000,str(index),b'x','reviewed','{}','vision_api','research','today'))
                    if category!='perfume':conn.execute('INSERT INTO reference_categories VALUES (?,?)',(str(index),category))
            self.assertEqual([r['id'] for r in reference_store.entries(root,'perfume')],['0'])
            self.assertEqual([r['id'] for r in reference_store.entries(root,'footwear')],['1'])
            self.assertEqual(reference_store.planning_pool(root,category='beverage'),[])

    def test_unknown_category_and_curated_cross_category_are_rejected(self):
        with self.assertRaises(ValueError):categories.profile({'product_category':'arbitrary'})
        with self.assertRaisesRegex(ValueError,'dynamic'):
            poster.run_four({'product_category':'watches','direction_mode':'curated'},'missing.png','brief')

    def test_category_policy_is_specific_and_not_an_efficacy_claim(self):
        self.assertIn('heel',categories.context({'product_category':'footwear'}))
        self.assertIn('dial',categories.context({'product_category':'watches'}))
        self.assertIn('clinical efficacy',categories.context({'product_category':'skincare'}))
        self.assertIn('nutrition',categories.context({'product_category':'beverage'}))

    def test_critic_receives_intentional_empty_copy_and_actual_shape_edges(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        spec['price']['text']=''
        spec['background']['shapes']=[{'kind':'ellipse','x':713,'y':576,'width':324,'height':346,'color':'#D8402E','opacity':.9}]
        product=poster.ROOT/'assets/products/categories/watches.png'
        geometry=poster.rendered_geometry(spec,product,poster.FONT_CHOICES[0])
        self.assertIn('price',geometry['copy_policy']['intentional_empty_layers'])
        self.assertEqual(geometry['shape_geometry'][0]['bbox'],[713,576,1037,922])
        self.assertFalse(geometry['shape_geometry'][0]['crosses_canvas_edge'])
        self.assertIn('Never penalize',categories.context({'product_category':'watches'}))

    def test_cyrillic_fallback_preserves_serif_art_direction(self):
        spec=poster.read(poster.ROOT/'samples/categories/watch-first-iteration/v2/PosterSpec.json')
        spec['title'].update(text='РОССИЯ',font='C:/Windows/Fonts/BASKVILL.TTF',size=96)
        config={'font':'C:/Windows/Fonts/msyh.ttc','direction_id':'concept-1'}
        fitted,fixes=poster.prepare_layout(config,spec,poster.ROOT/'assets/products/categories/watches.png')
        self.assertEqual(categories.font_family(fitted['title']['font']),'serif')
        self.assertTrue(quality.font_supports_text(fitted['title']['font'],'РОССИЯ'))
        self.assertIn('title_font_fallback',fixes)

    def test_unreadable_shoe_name_gets_explicit_factual_headline(self):
        observed={'title':'','logo':'Nike','subtitle':'','price':'','evidence':'Swoosh only.'}
        result=categories.complete_copy(copy.deepcopy(observed),{'product_category':'footwear'})
        self.assertEqual(result['title'],'FOOTWEAR')
        self.assertEqual(result['observed_product_name'],'')
        self.assertEqual(result['copy_mode'],'factual_category_headline')
        self.assertEqual(result['price'],'')
        self.assertEqual(categories.complete_copy(copy.deepcopy(observed),{}),observed)


if __name__=='__main__':unittest.main()
