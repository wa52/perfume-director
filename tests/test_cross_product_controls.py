import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
import poster
import reference_store
import concepts


class CrossProductControlsTests(unittest.TestCase):
    def setUp(self):
        self.spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        self.font='C:/Windows/Fonts/arial.ttf'

    def test_observed_unsupported_critic_controls_are_now_executable(self):
        changes=[{'path':'title.tracking','op':'set','value':3},
                 {'path':'title.max_width','op':'set','value':400},
                 {'path':'decoration.enabled','op':'set','value':False},
                 {'path':'decoration.color','op':'set','value':'#E7C864'},
                 {'path':'shadow.width_scale','op':'multiply','value':1.15}]
        value=poster.apply_changes(self.spec,changes)
        self.assertEqual(value['title']['tracking'],3)
        self.assertFalse(value['decoration']['enabled'])
        self.assertEqual(value['shadow']['width_scale'],1.15)
        self.assertNotIn('tracking',self.spec['title'])

    def test_unsafe_decoration_tracking_and_shadow_patches_are_atomic(self):
        before=copy.deepcopy(self.spec)
        for path,value in [('decoration.width',5000),('decoration.enabled',1),('title.tracking',25),('shadow.width_scale',float('nan'))]:
            with self.subTest(path=path),self.assertRaises(ValueError):
                poster.apply_changes(self.spec,[{'path':'title.size','op':'set','value':45},{'path':path,'op':'set','value':value}])
            self.assertEqual(self.spec,before)

    def test_footprint_follows_narrow_offcentre_base_not_wide_cap(self):
        image=Image.new('RGBA',(200,300));draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,199,80),fill='red');draw.rectangle((120,81,159,299),fill='red')
        x,y,width=poster.contact_footprint(image)
        self.assertEqual((x,y,width),(140,300,40))

    def test_disconnected_toe_and_heel_keep_their_own_contact_heights(self):
        image=Image.new('RGBA',(200,300));draw=ImageDraw.Draw(image)
        draw.rectangle((10,0,190,200),fill='red')
        draw.rectangle((10,201,89,299),fill='red')
        draw.rectangle((180,201,189,290),fill='red')
        self.assertEqual(poster.contact_footprints(image),[(50,300,80),(185,291,10)])
        self.assertEqual(image.getpixel((100,299)),(0,0,0,0))

    def test_right_edge_title_is_translated_before_being_shrunk_to_unreadable_size(self):
        spec=copy.deepcopy(self.spec)
        spec['product'].update(x=540,y=850,width=520,height=720)
        spec['shadow'].update(kind='contact',offset_x=0,offset_y=0)
        for name in poster.TEXT_LAYERS:spec[name]['text']=''
        spec['title'].update(text='OMNIA CRYSTALLINE',x=950,y=170,size=64,font=self.font,align='right',max_width=0)
        fixed,issues=poster.prepare_layout({'font':self.font,'direction_id':'concept-test'},spec,
            poster.ROOT/'assets/products/bvlgari-omnia-crystalline-retailer.png')
        self.assertEqual(fixed['title']['size'],64)
        self.assertIn('title_horizontal_frame_fit',issues)
        self.assertLessEqual(poster.typography_module().text_layout(fixed['title'],self.font)['bbox'][2],1080*.96+1)
        self.assertEqual(spec['title']['x'],950)

    def test_background_receives_actual_base_and_reserved_text_regions(self):
        geo={'product_bbox':[200,300,600,1050],'text_bbox':{'title':[50,1100,800,1200]}}
        with patch.object(poster,'rendered_geometry',return_value=geo):
            prompt=poster.background_placement(self.spec,'unused',self.font)
        self.assertIn('middle left area',prompt)
        self.assertIn('lower central area',prompt)
        self.assertIn('from the middle',prompt)
        self.assertNotRegex(prompt,r'[\d\[\]]')
        poster.check_concept_background(prompt)

    def test_reference_sampler_has_brand_and_observed_language_diversity(self):
        rows=[]
        for i in range(12):
            rows.append({'id':str(i),'brand':str(i//2),'source_url':'https://source'+str(i%3)+'.test/a',
                'style':'minimal' if i%2 else 'editorial','analysis':{'perfume_suitability':90,
                'composition':'asymmetric' if i%2 else 'centered','typography':'serif' if i%3 else 'sans',
                'renderer_compatibility':90,'has_campaign_typography':bool(i%2)}})
        with patch.object(reference_store,'entries',return_value=rows):
            result=reference_store.planning_pool('unused',6)
        self.assertEqual(len({r['brand'] for r in result}),6)
        self.assertEqual({r['style'] for r in result},{'minimal','editorial'})

    def test_graphic_plan_is_not_forced_to_generate_photographic_floor(self):
        self.spec['scene_mode']='graphic'
        with patch.object(poster,'rendered_geometry',return_value={'product_bbox':[200,200,700,950],'text_bbox':{}}):
            prompt=poster.background_placement(self.spec,'unused',self.font)
        self.assertIn('Flat graphic',prompt)
        self.assertNotIn('ground plane must',prompt)

    def test_planning_pool_keeps_two_typography_examples_even_when_still_lifes_score_higher(self):
        rows=[]
        for i in range(12):
            rows.append({'id':str(i),'brand':str(i),'source_url':'https://example.test/'+str(i),
                         'style':'luxury','analysis':{'perfume_suitability':70 if i<2 else 100,
                         'renderer_compatibility':65 if i<2 else 100,'has_campaign_typography':i<2}})
        with patch.object(reference_store,'entries',return_value=rows):
            result=reference_store.planning_pool('unused',8)
        self.assertEqual(sum(r['analysis']['has_campaign_typography'] for r in result),2)
        self.assertEqual(len({r['brand'] for r in result}),8)

    def test_real_wide_triangle_cannot_overflow_using_tall_bottle_height(self):
        product=poster.ROOT/'assets/products/prada-paradoxe-retailer.png'
        item={'product':[.32,.55,.70],'palette':['#345678','#ffffff','#aaaaaa'],
            'lighting':'soft','background_prompt':'Empty blue surface','type':{
                'font':self.font,'title':[.1,.05,44],'logo':[.1,.10,24]},'line':None}
        spec=concepts.build_spec(poster,{'font':self.font},item,product,
            {'title':'Paradoxe','logo':'Prada','subtitle':'','price':''})
        poster.validate(spec)
        box=poster.rendered_geometry(spec,product,self.font)['product_bbox']
        self.assertGreaterEqual(box[0],1080*.05)
        self.assertLessEqual(box[2],1080*.95)
        self.assertIn('layout_fit',spec)
        self.assertLess(spec['product']['height'],round(.70*1440))

    def test_product_observation_is_forwarded_without_changing_approved_copy(self):
        result={'title':'Paradoxe','logo':'Prada','subtitle':'','price':'','evidence':'user brief',
            'product_profile':{'material':'clear pink glass','illumination':'broad pale reflections','view':'front'}}
        config={}
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'vision',return_value=result):
            copy_result=poster.resolve_copy(config,'unused','brief',Path(folder))
        self.assertEqual(copy_result,{k:result[k] for k in poster.TEXT_LAYERS})
        self.assertEqual(config['product_profile'],result['product_profile'])

if __name__=='__main__':unittest.main()
