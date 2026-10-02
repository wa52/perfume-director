import copy
from pathlib import Path
import tempfile
import unittest
from urllib.error import URLError
from unittest.mock import patch

from PIL import Image
import concepts
import poster


class FreshConceptTests(unittest.TestCase):
    product=poster.ROOT/'assets/products/tom-ford-tobacco-vanille-retailer.png'
    config={'font':'C:/Windows/Fonts/msyh.ttc'}
    words={'title':'SCENT','logo':'BRAND','subtitle':'EAU','price':''}
    refs=[{'id':str(i),'brand':str(i),'image':str(poster.ROOT/'assets/products/tom-ford-tobacco-vanille-retailer.png')} for i in range(3)]

    def setUp(self):
        history=patch.object(concepts,'recent',return_value=[])
        history.start();self.addCleanup(history.stop)

    def plans(self):
        result=[]
        for index,d in enumerate(poster.DIRECTIONS):
            spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),d['id'])
            spec['background']['prompt']='Empty colored paper surface, broad diffused frontal illumination'
            for n,t in self.words.items():spec[n]['text']=t
            if index==0:
                spec['logo'].update(x=76,y=65)
                spec['title'].update(x=76,y=150)
                spec['subtitle'].update(x=76,y=280)
            elif index==1:
                spec['product'].update(x=540,y=580,width=326,height=720)
                spec['logo'].update(x=100,y=1010)
                spec['title'].update(x=100,y=1090)
                spec['subtitle'].update(x=100,y=1220)
            elif index==2:
                spec['product'].update(x=750,y=720,width=326,height=720)
                spec['logo'].update(x=70,y=540)
                spec['title'].update(x=70,y=620,size=64)
                spec['subtitle'].update(x=70,y=750)
            result.append({'name':'New idea '+str(index),'brief':'Fresh concept '+str(index),
                'material':'material '+str(index),'lighting':'diffuse frontal light','reference_ids':['0','1','2'],'spec':spec})
        return {'directions':result}

    def test_all_upper_titles_are_rejected_despite_other_geometry_changes(self):
        value=self.plans()
        for item in value['directions']:
            spec=item['spec']
            spec['logo'].update(x=76,y=65,size=24)
            spec['title'].update(x=76,y=150,size=64)
            spec['subtitle'].update(x=76,y=260,size=22)
        with self.assertRaisesRegex(ValueError,'topology'):
            concepts.validate_plans(poster,self.config,value,self.product,self.refs,self.words)

    def test_campaign_typography_reference_is_required_when_available(self):
        refs=copy.deepcopy(self.refs)
        refs.append({'id':'type-ref','brand':'TYPE','analysis':{'has_campaign_typography':True}})
        with self.assertRaisesRegex(ValueError,'actual campaign typography'):
            concepts.validate_plans(poster,self.config,self.plans(),self.product,refs,self.words)
        plans=self.plans()
        for item in plans['directions']:item['reference_ids'][0]='type-ref'
        self.assertEqual(len(concepts.validate_plans(poster,self.config,plans,self.product,refs,self.words)),4)

    def test_short_reference_aliases_resolve_exactly_without_guessing_unknown_ids(self):
        value=self.plans()
        for item in value['directions']:item['reference_ids']=['R1','R2','R3']
        resolved=concepts.resolve_reference_ids(value,self.refs)
        self.assertEqual(resolved['directions'][0]['reference_ids'],['0','1','2'])
        self.assertEqual(value['directions'][0]['reference_ids'],['R1','R2','R3'])
        value['directions'][0]['reference_ids'][0]='R9'
        with self.assertRaisesRegex(ValueError,'supplied reference IDs'):
            concepts.validate_plans(poster,self.config,concepts.resolve_reference_ids(value,self.refs),self.product,self.refs,self.words)

    def test_relationship_uses_actual_visible_bboxes_not_declared_names(self):
        plans=concepts.validate_plans(poster,self.config,self.plans(),self.product,self.refs,self.words)
        self.assertEqual({p['layout_relation'] for p in plans},{'above','below','beside'})
        self.assertEqual(concepts.title_relationship({'product_bbox':[400,400,800,1100],'text_bbox':{'title':[60,200,300,250]}}),'above')

    def test_critic_cannot_collapse_a_lower_title_into_an_upper_layout(self):
        spec=self.plans()['directions'][1]['spec']
        changes=[{'path':'title.y','op':'set','value':140},{'path':'title.size','op':'set','value':52}]
        with self.assertRaisesRegex(ValueError,'concept drift'):
            poster.apply_safe_changes(spec,changes,self.product,self.config['font'],'concept-2')
        candidate,audit=poster.recover_safe_groups(spec,changes+[{'path':'shadow.opacity','op':'set','value':.6}],self.product,self.config['font'],'concept-2')
        self.assertEqual(candidate['title'],spec['title'])
        self.assertEqual(candidate['shadow']['opacity'],.6)
        self.assertEqual(audit['rejected_groups'][0]['group'],'typography')

    def test_critic_preserves_title_family_but_can_refine_font_within_it(self):
        spec=self.plans()['directions'][0]['spec'];spec['title']['font']='C:/Windows/Fonts/times.ttf'
        with self.assertRaisesRegex(ValueError,'serif/sans'):
            poster.apply_safe_changes(spec,[{'path':'title.font','op':'set','value':'C:/Windows/Fonts/arial.ttf'}],self.product,self.config['font'],'concept-1')
        candidate=poster.apply_safe_changes(spec,[{'path':'title.font','op':'set','value':'C:/Windows/Fonts/georgia.ttf'}],self.product,self.config['font'],'concept-1')
        self.assertEqual(candidate['title']['font'],'C:/Windows/Fonts/georgia.ttf')

    def test_two_serif_fonts_do_not_count_as_distinct_type_families(self):
        value=self.plans()
        for index,item in enumerate(value['directions']):item['spec']['title']['font']='C:/Windows/Fonts/'+('times.ttf' if index%2 else 'georgia.ttf')
        with self.assertRaisesRegex(ValueError,'serif and sans'):
            concepts.validate_plans(poster,self.config,value,self.product,self.refs,self.words)

    def test_observed_bottle_width_background_patch_is_rejected_before_render(self):
        spec=self.plans()['directions'][0]['spec']
        changes=[{'path':'background.prompt','op':'set','value':'Copper dimples calming within one bottle-width of the center pool'},
                 {'path':'subtitle.y','op':'set','value':270}]
        with self.assertRaisesRegex(ValueError,'Concept background'):
            poster.apply_safe_changes(spec,changes,self.product,self.config['font'],'concept-1')
        candidate,audit=poster.recover_safe_groups(spec,changes,self.product,self.config['font'],'concept-1')
        self.assertEqual(candidate['background'],spec['background'])
        self.assertEqual(candidate['subtitle']['y'],270)
        self.assertEqual(audit['rejected_groups'][0]['group'],'background')

    def test_observed_prose_changes_are_rejected_without_crashing_recovery(self):
        spec=self.plans()['directions'][0]['spec'];changes=['Re-render the shadow layer exactly per spec']
        with self.assertRaisesRegex(ValueError,'prose'):
            poster.apply_changes(spec,changes)
        candidate,audit=poster.recover_safe_groups(spec,changes,self.product,self.config['font'],'concept-1')
        self.assertEqual(candidate,spec)
        self.assertEqual(audit['accepted'],[])
        critique={'pass':False,'score':67,'dimensions':{d:67 for d in poster.CRITIC_DIMENSIONS},'problems':['floating'],'changes':changes}
        with self.assertRaisesRegex(ValueError,'prose'):poster.validate_critique(critique,strict=True)

    def test_malformed_critic_and_failed_repair_keep_a_previewable_result(self):
        spec=self.plans()['directions'][0]['spec']
        raw={'pass':False,'score':67,'dimensions':{d:67 for d in poster.CRITIC_DIMENSIONS},'problems':['floating'],'changes':['Re-render the shadow']}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);poster.write(root/'examples/PosterSpec.json',spec)
            config={**self.config,'direction_id':'concept-4','initial_spec':spec,'references':self.refs,
                'creative_direction':{'name':'Side concept'},'planning_trace':'Concepts-call.json',
                'approved_copy':self.words,'max_rounds':1,'vision_model':'test'}
            def draw(c,s,p,d,b):Image.new('RGB',(1080,1440)).save(d)
            with patch.object(poster,'ROOT',root),patch.object(poster,'vision',side_effect=[raw,URLError('connection lost')]) as model,patch.object(poster,'comfy_render',side_effect=draw):
                folder=poster.run(config,self.product,'brief')
            result=poster.read(folder/'result.json')
            self.assertEqual(model.call_count,2)
            self.assertEqual(result['status'],'NEEDS_REVIEW')
            self.assertEqual(result['selected']['review_error'],'URLError')
            self.assertTrue((folder/result['selected']['poster']).exists())

    def test_duplicate_layouts_are_rejected_even_with_different_names_and_colors(self):
        value=self.plans()
        for item in value['directions']:
            original=item['spec']['background']['color']
            item['spec']=copy.deepcopy(value['directions'][0]['spec'])
            item['spec']['background']['color']=original
        with self.assertRaisesRegex(ValueError,'repeat'):
            concepts.validate_plans(poster,self.config,value,self.product,self.refs,self.words)

    def test_four_specs_keep_planned_coordinates_and_truthful_copy(self):
        value=self.plans()
        planned=concepts.validate_plans(poster,self.config,value,self.product,self.refs,self.words)
        self.assertEqual(len(planned),4)
        for actual,raw in zip(planned,value['directions']):
            self.assertEqual(actual['initial_spec']['product'],raw['spec']['product'])
            self.assertEqual(actual['initial_spec']['title']['text'],'SCENT')
            self.assertTrue(actual['id'].startswith('concept-'))

    def test_compact_model_geometry_becomes_spec_without_a_grid_lookup(self):
        item={'product':[.62,.57,.5],'palette':['#4B6280','#F8F2E8','#FFB647'],
            'lighting':'soft frontal illumination','background_prompt':'Empty slate blue paper with diagonal folds',
            'type':{'font':'C:/Windows/Fonts/georgia.ttf','title':[.1,.12,56],'logo':[.1,.06,24],'subtitle':[.1,.19,20]},
            'line':[.1,.24,.2]}
        with patch.object(poster,'direction_template',side_effect=AssertionError('Not a curated plan')):
            spec=concepts.build_spec(poster,self.config,item,self.product,self.words)
            prepared,_=poster.prepare_layout({**self.config,'direction_id':'concept-1'},spec,self.product)
        self.assertEqual(prepared['product']['x'],round(.62*1080))
        self.assertEqual(prepared['product']['y'],round(.57*1440))
        self.assertEqual(prepared['product']['height'],720)
        self.assertEqual(prepared['title']['x'],108)
        self.assertEqual(prepared['background']['color'],'#4B6280')
        self.assertTrue(prepared['decoration']['enabled'])
        self.assertEqual(prepared['title']['text'],'SCENT')

    def test_bad_geometry_is_rejected_without_a_curated_fallback(self):
        spec=self.plans()['directions'][0]['spec'];spec['product']['y']=300
        with patch.object(poster,'direction_template',side_effect=AssertionError('Must not use a template')):
            with self.assertRaisesRegex(ValueError,'unsafe'):
                poster.prepare_layout({**self.config,'direction_id':'concept-1'},spec,self.product)

    def test_recent_signature_cannot_be_reused_with_new_names_or_seeds(self):
        with patch.object(concepts,'recent',return_value=[]):
            plans=concepts.validate_plans(poster,self.config,self.plans(),self.product,self.refs,self.words)
        value=self.plans()
        for item in value['directions']:
            item['name']+=' renamed';item['spec']['seed']+=99
        with patch.object(concepts,'recent',return_value=plans),self.assertRaisesRegex(ValueError,'recent'):
            concepts.validate_plans(poster,self.config,value,self.product,self.refs,self.words)

    def test_unknown_reference_or_forbidden_background_is_not_accepted(self):
        for mutation in ('reference','background'):
            with self.subTest(mutation=mutation):
                value=self.plans()
                if mutation=='reference':value['directions'][0]['reference_ids'][0]='invented'
                else:value['directions'][0]['spec']['background']['prompt']='perfume on a pedestal'
                with self.assertRaises(ValueError):
                    concepts.validate_plans(poster,self.config,value,self.product,self.refs,self.words)

    def test_dynamic_text_safety_checks_collisions_without_forcing_one_alignment(self):
        spec=self.plans()['directions'][0]['spec'];spec['logo'].update(x=160,y=120);spec['title'].update(x=90,y=230)
        self.assertEqual(poster.layout_issues(spec,self.product,self.config['font'],'concept-1'),[])
        spec['logo'].update(x=spec['title']['x'],y=spec['title']['y'])
        self.assertTrue(any('text_overlap' in i for i in poster.layout_issues(spec,self.product,self.config['font'],'concept-1')))

    def test_initial_spec_is_rendered_without_a_second_director_or_reset(self):
        spec=self.plans()['directions'][0]['spec']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);poster.write(root/'examples/PosterSpec.json',spec)
            config={**self.config,'direction_id':'concept-1','initial_spec':spec,'references':self.refs,
                'creative_direction':{'name':'New concept'},'planning_trace':'Concepts-call.json',
                'approved_copy':self.words,'max_rounds':1,'vision_model':'test','direction_seed_offset':91}
            critique={'pass':True,'score':86,'dimensions':{d:86 for d in poster.CRITIC_DIMENSIONS},'problems':[],'changes':[]}
            def draw(c,s,p,d,b):Image.new('RGB',(1080,1440)).save(d)
            with patch.object(poster,'ROOT',root),patch.object(poster,'vision',return_value=critique) as model,patch.object(poster,'comfy_render',side_effect=draw):
                run=poster.run(config,self.product,'brief')
            actual=poster.read(run/'v1/PosterSpec.json')
            self.assertEqual(model.call_count,1)
            self.assertEqual(actual['product'],spec['product'])
            self.assertEqual(actual['seed'],spec['seed']+91)
            self.assertTrue((run/'Director-plan.json').exists())

    def test_default_four_mode_uses_new_plans_and_fresh_batch_seeds(self):
        with patch.object(concepts,'recent',return_value=[]):
            plans=concepts.validate_plans(poster,self.config,self.plans(),self.product,self.refs,self.words)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);calls=[]
            def child(config,product,brief,progress):
                calls.append(config)
                folder=root/'runs/live'/str(len(calls))
                poster.write(folder/'result.json',{'status':'NEEDS_REVIEW','selected':{'poster':'v1.png'},'versions':[]})
                return folder
            with patch.object(poster,'ROOT',root),patch.object(concepts,'plan_four',return_value=(plans,self.refs)) as planner,patch.object(poster,'run',side_effect=child):
                for _ in range(2):poster.run_four({**self.config,'approved_copy':self.words,'vision_model':'test'},self.product,'brief')
            self.assertEqual(planner.call_count,2)
            self.assertEqual([c['direction_id'] for c in calls[:4]],['concept-1','concept-2','concept-3','concept-4'])
            self.assertEqual(calls[0]['initial_spec'],plans[0]['initial_spec'])
            self.assertNotEqual(calls[0]['direction_seed_offset'],calls[4]['direction_seed_offset'])
            self.assertEqual(calls[0]['creative_direction']['name'],plans[0]['name'])


if __name__=='__main__':unittest.main()
