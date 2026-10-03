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


if __name__=='__main__':unittest.main()
