import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import poster
from PIL import Image, ImageDraw


class QualitySelectionTests(unittest.TestCase):
    def test_critic_sees_actual_ink_correction_and_rejected_previous_changes(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'black-gold')
        spec['title']['text']="J'adore"
        product=poster.ROOT/'assets/products/dior-jadore-retailer.png'
        with tempfile.TemporaryDirectory() as directory,patch.object(poster,'vision',return_value={}) as model:
            folder=Path(directory);current=folder/'v2';older=folder/'v1'
            current.mkdir();older.mkdir()
            poster.render(spec,Image.open(product),'C:/Windows/Fonts/msyh.ttc').save(current/'poster.png')
            poster.write(current/'Background-audit.json',{'ink_changes':[{'path':'title.color','old':'#FFFFFF','value':'#111111','reason':'text_background_contrast_below_3'}]})
            poster.write(older/'Critic-safe-groups.json',{'accepted':[],'rejected_groups':[{'group':'typography','changes':[{'path':'title.y','value':600}]}]})
            poster.review_poster({'font':'C:/Windows/Fonts/msyh.ttc'},spec,product,current/'poster.png',['r1','r2','r3'],current/'Critic-call.json',previous={'poster':older/'poster.png','critique':{}})
            prompt=model.call_args.args[1]
            self.assertIn('text_background_contrast_below_3',prompt)
            self.assertIn('Critic-safe-groups',prompt)
            self.assertIn('fit text size and product position together',prompt)

    def test_review_gets_contact_detail_without_changing_reference_order(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'black-gold')
        spec['title']['text']="J'adore"
        product=poster.ROOT/'assets/products/dior-jadore-retailer.png'
        with tempfile.TemporaryDirectory() as directory, patch.object(poster,'vision',return_value={}) as model:
            folder=Path(directory)
            poster.render(spec,Image.open(product),'C:/Windows/Fonts/msyh.ttc').save(folder/'poster.png')
            poster.review_poster({'font':'C:/Windows/Fonts/msyh.ttc'},spec,product,folder/'poster.png',['r1','r2','r3'],folder/'Critic-call.json')
            images=model.call_args.args[2]
            self.assertEqual(images[2:5],['r1','r2','r3'])
            self.assertEqual(images[5],folder/'Contact-detail.png')
            with Image.open(images[5]) as detail:
                self.assertEqual(detail.height,500)
                self.assertLessEqual(detail.width,960)
            self.assertIn('contact_detail_crop',model.call_args.args[1])

    def test_softbox_word_is_removed_before_background_generation(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'cream-minimal')
        spec['background']['prompt']='Empty ivory environment with softbox light from left'
        config=poster.read(poster.ROOT/'config.zhipu.example.json')
        config['direction_id']='cream-minimal'
        prompts=[]
        def execute(config,workflow,node,path):
            if str(node)=='10': prompts.append(workflow['5']['inputs']['text'])
            image=Image.new('RGB',(1080,1440),'#EEE0C0')
            ImageDraw.Draw(image).rectangle((600,0,1080,1440),fill='#D8CBB5')
            image.save(path)
            return Path(path)
        with tempfile.TemporaryDirectory() as directory, patch.object(poster,'execute',side_effect=execute), patch.object(poster,'upload',return_value='input'), patch.object(poster,'rendered_geometry',return_value={'text_bbox':{}}):
            poster.comfy_render(config,spec,'product',Path(directory)/'poster.png',None)
        self.assertEqual(len(prompts),1)
        self.assertNotIn('softbox',prompts[0])
        self.assertIn('diffused illumination',prompts[0])

    def test_cream_critic_cannot_confuse_left_anchor_with_center(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'cream-minimal')
        spec['title']['text']="J'adore"
        product=poster.ROOT/'assets/products/dior-jadore-retailer.png'
        config={'font':'C:/Windows/Fonts/msyh.ttc','direction_id':'cream-minimal'}
        spec,_=poster.prepare_layout(config,spec,product)
        with self.assertRaises(ValueError):
            poster.apply_safe_changes(spec,[{'path':'title.x','op':'set','value':540}],product,config['font'],'cream-minimal')

    def test_critic_cannot_create_small_gap_below_contact_shadow(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'black-gold')
        with self.assertRaises(ValueError):
            poster.apply_safe_changes(spec,[{'path':'shadow.offset_y','op':'set','value':5}],poster.ROOT/'assets/products/dior-jadore-retailer.png','C:/Windows/Fonts/msyh.ttc','black-gold')

    def test_unsafe_move_does_not_discard_independent_background_repair(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'black-gold')
        spec['title']['text']="J'adore"
        product=poster.ROOT/'assets/products/dior-jadore-retailer.png'
        changes=[{'path':'product.y','op':'set','value':1200},
                 {'path':'background.prompt','op':'set','value':'Continuous graphite floor with broad soft light'}]
        result,audit=poster.recover_safe_groups(spec,changes,product,'C:/Windows/Fonts/msyh.ttc','black-gold')
        self.assertEqual(result['product'],spec['product'])
        self.assertEqual(result['background']['revision'],1)
        self.assertEqual(audit['rejected_groups'][0]['group'],'product')
        self.assertEqual(len(audit['accepted']),1)
        self.assertEqual(poster.layout_issues(result,product,'C:/Windows/Fonts/msyh.ttc','black-gold'),[])

    def test_noop_background_set_does_not_spend_another_render(self):
        spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'black-gold')
        result,audit=poster.recover_safe_groups(spec,[{'path':'background.prompt','op':'set','value':spec['background']['prompt']}],poster.ROOT/'assets/products/dior-jadore-retailer.png','C:/Windows/Fonts/msyh.ttc','black-gold')
        self.assertEqual(result,spec)
        self.assertEqual(audit['accepted'],[])

    def test_copy_read_once_and_rejects_multiline(self):
        result = {'title': "J'adore", 'logo': 'Dior', 'subtitle': 'EAU DE PARFUM', 'price': '', 'evidence': 'Visible on bottle'}
        with tempfile.TemporaryDirectory() as folder, patch.object(poster,'vision',return_value=result) as model:
            accepted = poster.resolve_copy({},'product.png','no promotion',Path(folder))
            self.assertEqual(accepted['title'],"J'adore")
            self.assertNotIn('evidence',accepted)
            self.assertEqual(model.call_count,1)
            result['title']='unapproved\nsecond line'
            with self.assertRaises(ValueError):
                poster.resolve_copy({},'product.png','brief',Path(folder))

    def test_font_patch_cannot_read_arbitrary_file_or_lose_glyphs(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        original=copy.deepcopy(spec)
        for font in ('C:/Windows/Fonts/arial.ttf','config.local.json'):
            with self.assertRaises(ValueError):
                poster.apply_changes(spec,[{'path':'title.font','op':'set','value':font}])
        self.assertEqual(spec,original)
        spec['title']['text']="J'adore"
        self.assertEqual(poster.apply_changes(spec,[{'path':'title.font','op':'set','value':'C:/Windows/Fonts/georgia.ttf'}])['title']['font'],'C:/Windows/Fonts/georgia.ttf')

    def compare(self,verdict,versions):
        with tempfile.TemporaryDirectory() as folder, patch.object(poster,'vision',return_value=verdict) as model:
            selected=poster.select_final({'compare_final_versions':True},Path(folder),versions,'product', ['ref1','ref2','ref3'])
            audit=poster.read(Path(folder)/'Selection.json')
            return selected,audit,model

    def test_direct_comparison_can_choose_lower_scored_earlier_version(self):
        versions=[{'version':1,'score':78,'pass':False,'poster':'v1.png'},{'version':2,'score':83,'pass':False,'poster':'v2.png'}]
        selected,audit,model=self.compare({'selected_version':1,'evidence':'V1 has more coherent light','remaining_problems':['Generic typography']},versions)
        self.assertEqual(selected['version'],1)
        self.assertFalse(selected['pass'])
        self.assertTrue(audit['does_not_grant_pass'])
        self.assertNotIn('83',model.call_args.args[1])

    def test_invalid_comparison_falls_back_without_approval(self):
        versions=[{'version':1,'score':78,'pass':False,'poster':'v1.png'},{'version':2,'score':83,'pass':False,'poster':'v2.png'}]
        selected,audit,_=self.compare({'selected_version':99,'evidence':'Claim','remaining_problems':[]},versions)
        self.assertEqual(selected['version'],2)
        self.assertEqual(audit['method'],'score_fallback')
        self.assertFalse(selected['pass'])

    def test_unreviewed_image_is_not_eligible_to_replace_reviewed_work(self):
        versions=[{'version':1,'score':78,'pass':False,'poster':'v1.png'},{'version':2,'score':None,'pass':False,'poster':'v2.png'}]
        with patch.object(poster,'vision') as model:
            selected=poster.select_final({'compare_final_versions':True},Path('.'),versions,'product',[])
        self.assertEqual(selected['version'],1)
        model.assert_not_called()
