import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import commercial
import poster


class CommercialRepairTests(unittest.TestCase):
    def test_veto_translates_to_valid_patch_without_granting_pass(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json');original=copy.deepcopy(spec)
        changes=[{'path':'title.size','op':'multiply','value':.9}]
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',return_value={'changes':changes}),patch.object(poster,'review_geometry',return_value={}):
            result=commercial.final_art_repair(poster,{},spec,'product','poster',[],Path(f),{'tier':'draft'})
            self.assertEqual(result,changes);self.assertEqual(spec,original)
            self.assertIs(poster.read(Path(f)/'CommercialRepair.json')['does_not_grant_pass'],True)

    def test_cannot_change_identity_or_unsupported_layers(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        for path,value in [('logo.text','Different brand'),('product.source','other.png'),('seed',42)]:
            with self.subTest(path=path),tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',return_value={'changes':[{'path':path,'op':'set','value':value}]}),patch.object(poster,'review_geometry',return_value={}):
                with self.assertRaises(ValueError):commercial.final_art_repair(poster,{},spec,'product','poster',[],Path(f),{})
                self.assertFalse((Path(f)/'CommercialRepair.json').exists())

    def test_no_supported_repair_remains_empty(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',return_value={'changes':[]}),patch.object(poster,'review_geometry',return_value={}):
            self.assertEqual(commercial.final_art_repair(poster,{},spec,'product','poster',[],Path(f),{}),[])

    def test_final_veto_returns_repairs_to_iteration(self):
        critique={'pass':True,'score':96,'dimensions':{k:96 for k in (*poster.CRITIC_DIMENSIONS,'brand_alignment')},
            'problems':[],'changes':[],'commercial_checks':{k:{'ok':True,'evidence':'visible'} for k in commercial.CHECKS}}
        changes=[{'path':'title.size','op':'multiply','value':.9}]
        final={'tier':'draft','evidence':'weak hierarchy','problems':[]}
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'review_poster',return_value=critique),patch.object(poster,'layout_issues',return_value=[]),patch.object(commercial,'final_art_review',return_value=final),patch.object(commercial,'final_art_repair',return_value=changes) as repair:
            result=poster.review_validated({'commercial_v2':True,'font':'font','direction_id':'concept-1'}, {},'product','poster',[],Path(f),None)
            self.assertFalse(result['pass']);self.assertEqual(result['changes'],changes);repair.assert_called_once()
            self.assertIn('final_art_director:below_target_or_unresolved',result['commercial_gate']['failures'])

    def test_invalid_identity_patch_is_rewritten_using_validation_error(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json');original=copy.deepcopy(spec)
        changes=[{'path':'title.size','op':'multiply','value':.9}]
        responses=[{'changes':[{'path':'logo.text','op':'set','value':''}]},{'changes':changes}]
        with tempfile.TemporaryDirectory() as f,patch.object(poster,'vision',side_effect=responses) as vision,patch.object(poster,'review_geometry',return_value={}):
            self.assertEqual(commercial.final_art_repair(poster,{},spec,'product','poster',[],Path(f),{}),changes)
            self.assertEqual(spec,original);self.assertIn('Unsupported patch: logo.text',vision.call_args.args[1])
            self.assertTrue((Path(f)/'CommercialRepairRejected-1.json').exists())


if __name__=='__main__':unittest.main()
