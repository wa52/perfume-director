import copy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import commercial
import poster


class CommercialTests(unittest.TestCase):
    def test_rejected_diversity_can_retain_only_quality_held_drafts(self):
        value={'brand_analysis':{'observed_brand':'Actual','evidence':'source','expression_hypothesis':'hypothesis','unknowns':'history unknown'},
            'concepts':[{key:(f'id{i}' if key=='id' else f'{key} event {i}') for key in ('id','name','proposition','visual_mechanism','audience','brand_connection','source_constraints')} for i in range(4)]}
        reject={'distinct':False,'evidence':'same event','collapse_groups':[['id0','id1']],'required_revision':'different events'}
        config={'retain_rejected_creative_drafts':True}
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',side_effect=[value,reject,value,reject,value,reject]):
            self.assertEqual(commercial.creative_stage(poster,config,'product','brief',Path(f),{}),value)
            self.assertEqual(config['creative_diversity_veto'],reject)
            self.assertTrue(poster.read(Path(f)/'CreativeDraftHold.json')['commercial_pass_forbidden'])
            self.assertFalse(poster.read(Path(f)/'CreativeGate.json')['pass'])

    def test_invalid_creative_contract_never_becomes_a_draft_hold(self):
        config={'retain_rejected_creative_drafts':True}
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',return_value={'concepts':[]}):
            with self.assertRaises(ValueError):commercial.creative_stage(poster,config,'product','brief',Path(f),{})
            self.assertFalse((Path(f)/'CreativeConcepts.json').exists())

    def test_creative_veto_blocks_high_scoring_image_and_final_approval(self):
        config={'commercial_v2':True,'font':'font','creative_diversity_veto':{'evidence':'same event','distinct':False}}
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'review_poster',return_value=self.approved()),patch.object(poster,'layout_issues',return_value=[]),patch.object(commercial,'final_art_review') as final:
            result=poster.review_validated(config,{},'product','poster',[],Path(f),None)
            self.assertFalse(result['pass']);final.assert_not_called()
            self.assertIn('creative_diversity:unresolved',poster.read(Path(f)/'CommercialGate.json')['failures'])

    def test_creative_writer_and_reviewer_receive_references_without_mutating_settings(self):
        value={'brand_analysis':{'observed_brand':'Actual','evidence':'source','expression_hypothesis':'hypothesis','unknowns':'history unknown'},
            'concepts':[{key:(f'id{i}' if key=='id' else f'{key} event {i}') for key in ('id','name','proposition','visual_mechanism','audience','brand_connection','source_constraints')} for i in range(4)]}
        review={'distinct':True,'evidence':'four feasible events','collapse_groups':[],'required_revision':''}
        config={'vision_options':{'temperature':.2},'creative_references':[{'image':f'references/test{i}.png'} for i in range(3)],'product_category':'menswear','garment_type':'tshirt'}
        original=copy.deepcopy(config)
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',side_effect=[value,review]) as model:
            commercial.creative_stage(poster,config,'product','brief',Path(f),{})
            self.assertEqual(config,original)
            for call in model.call_args_list:self.assertEqual(len(call.args[2]),4)
            self.assertEqual(model.call_args_list[0].args[0]['vision_options']['temperature'],.8)
            self.assertEqual(model.call_args_list[1].args[0]['vision_options']['temperature'],.2)
            self.assertIn('No ground shadow at the hem',model.call_args_list[0].args[1])

    def approved(self):
        return {'pass':True,'score':99,'problems':[],'changes':[],
            'dimensions':{name:99 for name in poster.CRITIC_DIMENSIONS}|{'brand_alignment':99},
            'commercial_checks':{name:{'ok':True,'evidence':'Visible in actual render'} for name in commercial.CHECKS}}

    def test_high_average_cannot_override_identity_failure(self):
        value=self.approved();value['dimensions']['product_fidelity']=94
        self.assertFalse(commercial.gate(value)['pass'])
        self.assertTrue(value['pass'])

    def test_each_veto_and_missing_evidence_blocks(self):
        for name in commercial.CHECKS:
            for bad in ({'ok':False,'evidence':'defect'},{'ok':True,'evidence':''},{'ok':1,'evidence':'guessed'},None):
                with self.subTest(name=name,bad=bad):
                    value=self.approved();value['commercial_checks'][name]=bad
                    self.assertFalse(commercial.gate(value)['pass'])

    def test_geometry_and_unresolved_review_block(self):
        self.assertFalse(commercial.gate(self.approved(),['title_overlaps_product'])['pass'])
        value=self.approved();value['changes']=[{'path':'title.x','op':'add','value':1}]
        self.assertFalse(commercial.gate(value)['pass'])
        self.assertTrue(commercial.gate(self.approved())['pass'])

    def test_missing_brand_score_and_nan_fail_closed(self):
        for score in (None,float('nan'),True,101):
            value=self.approved();value['dimensions']['brand_alignment']=score
            self.assertFalse(commercial.gate(value)['pass'])

    def test_legacy_critic_cannot_claim_commercial_pass(self):
        value=self.approved();del value['commercial_checks']
        self.assertFalse(commercial.gate(value)['pass'])

    def test_directional_shadow_requires_known_source_light(self):
        plan={'source_key_light':'unknown','ground_material':'matte stone','cast_length_ratio':.1,'cast_opacity':.15,'cast_blur':8}
        with self.assertRaises(ValueError):commercial.validate_integration(plan)
        plan['cast_opacity']=0
        commercial.validate_integration(plan)

    def test_projected_shadow_does_not_change_product_and_stays_below_base(self):
        product=Image.new('RGBA',(20,60),(200,90,50,255));original=product.tobytes()
        canvas=Image.new('RGBA',(160,180),'white')
        plan={'source_key_light':'left','ground_material':'matte stone','cast_length_ratio':.15,'cast_opacity':.2,'cast_blur':2}
        output=commercial.cast_shadow(canvas,product,60,40,plan)
        self.assertEqual(product.tobytes(),original)
        self.assertEqual(output.getpixel((65,60)),canvas.getpixel((65,60)))
        self.assertLess(output.getpixel((76,113))[0],255)
        self.assertEqual(output.size,canvas.size)

    def test_frontal_light_casts_away_from_viewer(self):
        product=Image.new('RGBA',(20,60),(200,90,50,255));canvas=Image.new('RGBA',(160,180),'white')
        plan={'source_key_light':'front','ground_material':'matte stone','cast_length_ratio':.15,'cast_opacity':.2,'cast_blur':2}
        output=commercial.cast_shadow(canvas,product,60,40,plan)
        self.assertEqual(output.getpixel((70,115)),canvas.getpixel((70,115)))
        self.assertLess(output.getpixel((70,85))[0],255)

    def test_creative_contract_forbids_layout_and_duplicate_mechanisms(self):
        fields={'name':'concept','proposition':'campaign idea','audience':'new audience','brand_connection':'observed colors','source_constraints':'unaltered photograph'}
        value={'brand_analysis':{name:'Observed or unknown' for name in ('observed_brand','evidence','expression_hypothesis','unknowns')},'concepts':[{**fields,'id':f'idea{i}','visual_mechanism':f'mechanism{i}'} for i in range(4)]}
        commercial.validate_creative(value)
        modified=copy.deepcopy(value);modified['concepts'][0]['x']=.5
        with self.assertRaises(ValueError):commercial.validate_creative(modified)
        modified=copy.deepcopy(value);modified['concepts'][1]['visual_mechanism']=' mechanism0 '
        with self.assertRaises(ValueError):commercial.validate_creative(modified)

    def test_critic_contract_reaches_fresh_and_direct_reviews(self):
        self.assertIn('Commercial V2',poster.concept_context({'commercial_v2':True}))
        self.assertEqual(poster.concept_context({}),'')

    def test_live_review_uses_gate_and_persists_veto(self):
        value=self.approved();value['commercial_checks']['lighting_consistent']['ok']=False
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'review_poster',return_value=value),patch.object(poster,'layout_issues',return_value=[]):
            result=poster.review_validated({'commercial_v2':True,'font':'font'}, {},'product','poster',[],Path(folder),None)
            self.assertFalse(result['pass'])
            saved=poster.read(Path(folder)/'CommercialGate.json')
            self.assertIn('check:lighting_consistent',saved['failures'])

    def test_final_art_director_can_reject_high_scoring_generic_work(self):
        final={'tier':'draft','evidence':'generic circles and weak brand typography','problems':[]}
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'review_poster',return_value=self.approved()),patch.object(poster,'layout_issues',return_value=[]),patch.object(commercial,'final_art_review',return_value=final):
            result=poster.review_validated({'commercial_v2':True,'font':'font'}, {},'product','poster',[],Path(folder),None)
            self.assertFalse(result['pass'])
            self.assertEqual(result['commercial_gate']['final_tier'],'draft')

    def test_unavailable_final_review_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'review_poster',return_value=self.approved()),patch.object(poster,'layout_issues',return_value=[]),patch.object(commercial,'final_art_review',side_effect=TimeoutError):
            result=poster.review_validated({'commercial_v2':True,'font':'font'}, {},'product','poster',[],Path(folder),None)
            self.assertFalse(result['pass'])
            self.assertIn('final_art_director:unavailable',result['commercial_gate']['failures'])

    def test_directional_shadow_patches_cannot_change_observed_light(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        spec['integration_plan']={'source_key_light':'left','ground_material':'matte stone','cast_length_ratio':.1,'cast_opacity':.15,'cast_blur':8}
        changed=poster.apply_changes(spec,[{'path':'integration_plan.cast_opacity','op':'set','value':.1}])
        self.assertEqual(changed['integration_plan']['source_key_light'],'left')
        for path,value in [('integration_plan.source_key_light','right'),('integration_plan.cast_opacity',.9)]:
            with self.assertRaises(ValueError):poster.apply_changes(spec,[{'path':path,'op':'set','value':value}])

    def test_semantic_review_cannot_approve_explicit_collapse_groups(self):
        result={'distinct':True,'evidence':'different names','collapse_groups':[['c1','c2']]}
        with patch.object(poster,'vision',return_value=result):
            self.assertFalse(commercial.semantic_review(poster,{},'product',{},'trace')['distinct'])

    def test_repeated_creative_batch_is_repaired_before_art_director(self):
        fields={'name':'concept','proposition':'campaign idea','audience':'new audience','brand_connection':'observed colors','source_constraints':'unaltered photograph'}
        value={'brand_analysis':{name:'Observed or unknown' for name in ('observed_brand','evidence','expression_hypothesis','unknowns')},'concepts':[{**fields,'id':f'idea{i}','visual_mechanism':f'mechanism{i}'} for i in range(4)]}
        reject={'distinct':False,'evidence':'same isolated portrait','collapse_groups':[['idea0','idea1']],'required_revision':'different events'}
        accept={'distinct':True,'evidence':'different mechanisms','collapse_groups':[],'required_revision':''}
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'vision',side_effect=[value,reject,value,accept]) as model:
            commercial.creative_stage(poster,{},'product','brief',Path(folder),{})
            self.assertEqual(model.call_count,4)
            self.assertTrue(poster.read(Path(folder)/'CreativeGate.json')['pass'])
            self.assertIn('same isolated portrait',model.call_args_list[2].args[1])


if __name__=='__main__':unittest.main()
