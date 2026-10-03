import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import campaign_copy
import concepts
import poster
import commercial


class CampaignCopyTests(unittest.TestCase):
    def setUp(self):
        self.concepts=[{'id':f'c{i}'} for i in range(4)]
        self.identity={'title':'Product','subtitle':'Category','logo':'Real Brand','price':'99'}
        self.proposal={'directions':[{'creative_id':f'c{i}','title':f'Idea {i}','subtitle':f'Event {i}','rationale':'Visual relationship'} for i in range(4)]}
        self.review={'directions':[{'creative_id':f'c{i}','concept_fit':True,'brand_fit':True,'claim_safe':True,'memory_clear':True,'evidence':'Visible event expressed'} for i in range(4)]}

    def test_identity_cannot_be_modified_by_model(self):
        words=campaign_copy.validate(self.proposal,self.concepts,self.identity)
        for row in words.values():
            self.assertEqual(row['logo'],'Real Brand');self.assertEqual(row['price'],'99')
        bad=copy.deepcopy(self.proposal);bad['directions'][0]['price']='0'
        with self.assertRaises(ValueError):campaign_copy.validate(bad,self.concepts,self.identity)

    def test_optional_subtitle_does_not_force_generic_body_copy(self):
        proposal=copy.deepcopy(self.proposal)
        for row in proposal['directions']:row['subtitle']=''
        words=campaign_copy.validate(proposal,self.concepts,self.identity)
        self.assertTrue(all(row['subtitle']=='' for row in words.values()))
        self.assertTrue(all(row['logo']=='Real Brand' and row['price']=='99' for row in words.values()))

    def test_overlong_copy_retries_with_measured_limit_and_records_rejection(self):
        long=copy.deepcopy(self.proposal);long['directions'][0]['subtitle']='x'*110
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'vision',side_effect=[long,self.proposal,self.review]) as model:
            words=campaign_copy.stage(poster,{},'product','中文用户需求',Path(folder),self.concepts,self.identity)
            self.assertEqual(words['c0']['logo'],'Real Brand')
            feedback=model.call_args_list[1].args[1]
            self.assertIn('maximum 96 characters; received length 110',feedback)
            self.assertTrue((Path(folder)/'CampaignCopyRejected-1.json').exists())
            self.assertTrue((Path(folder)/'CampaignCopy.json').exists())

    def test_missing_repeated_and_unbounded_copy_rejected(self):
        for change in ('id','title','length','newline'):
            bad=copy.deepcopy(self.proposal)
            if change=='id':bad['directions'][1]['creative_id']='c0'
            if change=='title':bad['directions'][1]['title']=' Idea 0 '
            if change=='length':bad['directions'][0]['title']='a'*65
            if change=='newline':bad['directions'][0]['title']='new\nline'
            with self.assertRaises(ValueError):campaign_copy.validate(bad,self.concepts,self.identity)

    def test_rejected_copy_is_automatically_rewritten_with_evidence(self):
        rejected=copy.deepcopy(self.review);rejected['directions'][0].update(memory_clear=False,evidence='Generic slogan unrelated to scene')
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'vision',side_effect=[self.proposal,rejected,self.proposal,self.review]) as model:
            words=campaign_copy.stage(poster,{},'product','brief',Path(folder),self.concepts,self.identity)
            self.assertEqual(len(words),4);self.assertEqual(model.call_count,4)
            self.assertIn('Generic slogan',model.call_args_list[2].args[1])
            self.assertTrue(poster.read(Path(folder)/'CampaignCopy.json')['identity_locked'])

    def test_string_true_or_missing_memory_evidence_never_accepted(self):
        review=copy.deepcopy(self.review);review['directions'][0]['memory_clear']='true'
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'vision',side_effect=[self.proposal,review]*3):
            with self.assertRaises(ValueError):campaign_copy.stage(poster,{},'product','brief',Path(folder),self.concepts,self.identity)
            self.assertFalse((Path(folder)/'CampaignCopy.json').exists())

    def test_concept_copy_is_used_in_actual_poster_spec(self):
        base=poster.read(poster.ROOT/'examples/PosterSpec.json');base['title']['text']='Product'
        words=campaign_copy.validate(self.proposal,self.concepts,self.identity)
        item={'creative_id':'c2','palette':['#ffffff','#111111'],'product':[.5,.5,.5],
              'type':{'font':poster.FONT_CHOICES[0],'title':[.1,.1,24],'subtitle':[.1,.15,16],'logo':[.1,.9,16],'price':[.1,.95,16]},'background_prompt':'plain wall','scene_mode':'graphic','lighting':'soft frontal'}
        spec=concepts.build_spec(poster,{'font':poster.FONT_CHOICES[0],'campaign_copy_by_id':words},item,poster.ROOT/'samples/harmonization/beverage-clean-20261003/product.png',self.identity)
        self.assertEqual(spec['title']['text'],'Idea 2');self.assertEqual(spec['logo']['text'],'Real Brand')

    def test_new_visual_checks_are_hard_gate_vetoes(self):
        result={'pass':True,'dimensions':{k:99 for k in commercial.THRESHOLDS},'commercial_checks':{k:{'ok':True,'evidence':'Visible'} for k in commercial.CHECKS},'problems':[],'changes':[]}
        for key in ['copy_concept_specific','visual_memory_visible']:
            bad=copy.deepcopy(result);bad['commercial_checks'][key]['ok']=False
            self.assertFalse(commercial.gate(bad)['pass'])


if __name__=='__main__':unittest.main()
