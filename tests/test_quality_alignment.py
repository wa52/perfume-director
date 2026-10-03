import json
from pathlib import Path
import unittest
import categories
import commercial
import poster


class AlignmentTests(unittest.TestCase):
    def test_all_categories_and_clothing_subtypes_share_policy(self):
        for category in categories.PROFILES:
            types=categories.GARMENT_TYPES if category in categories.CLOTHING_CATEGORIES else ['auto']
            for subtype in types:
                original={'product_category':category,'garment_type':subtype,'commercial_v2':False,
                    'direction_mode':'curated','campaign_copy_mode':'identity','commercial_target':'social_ad',
                    'approved_copy':{'title':'Exact user text'},'max_rounds':5,'vision_model':'configured-model'}
                cfg=categories.aligned_config(original)
                self.assertTrue(cfg['commercial_v2']);self.assertEqual(cfg['direction_mode'],'dynamic')
                self.assertTrue(cfg['retain_rejected_creative_drafts'])
                self.assertEqual(cfg['campaign_copy_mode'],'creative');self.assertEqual(cfg['commercial_target'],'campaign_candidate')
                self.assertEqual(cfg['approved_copy'],original['approved_copy'])
                self.assertEqual(cfg['max_rounds'],5);self.assertEqual(cfg['vision_model'],'configured-model')
                self.assertIs(original['commercial_v2'],False)

    def test_catalog_covers_every_workflow_and_distinguishes_components(self):
        catalog=poster.read(poster.ROOT/'workflows/QUALITY_ALIGNMENT.json')
        expected={p.relative_to(poster.ROOT).as_posix() for p in (poster.ROOT/'workflows').rglob('*.json') if p.name!='QUALITY_ALIGNMENT.json'}
        self.assertEqual({x['path'] for x in catalog['workflows']},expected)
        for row in catalog['workflows']:
            graph=poster.read(poster.ROOT/row['path'])
            types={n['type'] for n in graph['nodes']} if 'nodes' in graph else {n['class_type'] for n in graph.values()}
            full=bool(types & {'PerfumeDirectorLoop','ProductDirectorLoop','ClothingDirectorLoop'})
            self.assertEqual(row['role'],'automatic_director' if full else 'render_component')
            self.assertEqual(row['quality_profile'],categories.QUALITY_PROFILE if full else None)
            self.assertFalse(row['commercial_visual_quality_verified'])
            if full:
                self.assertEqual(graph['extra']['director_quality_profile'],categories.QUALITY_PROFILE)
                director=next(n for n in graph['nodes'] if n['type'] in ('PerfumeDirectorLoop','ProductDirectorLoop','ClothingDirectorLoop'))
                if director['type']=='PerfumeDirectorLoop':self.assertNotIn('暖白',director['widgets_values'][0])
                if director['type']=='ProductDirectorLoop' and director['widgets_values'][1]=='beverage':
                    self.assertEqual(next(n for n in graph['nodes'] if n['type']=='LoadImage')['widgets_values'][0],'beverage-official-clean.png')
                if director['type']=='ClothingDirectorLoop':
                    category,kind=director['widgets_values'][1:3]
                    matching=(category=='menswear' and kind in ('auto','tshirt')) or (category=='womenswear' and kind in ('auto','dress'))
                    if not matching:self.assertEqual(next(n for n in graph['nodes'] if n['type']=='LoadImage')['widgets_values'][0],'')

    def test_shared_vetoes_include_identity_and_visible_concept(self):
        self.assertEqual(commercial.THRESHOLDS,{'product_fidelity':95,'physical_integration':88,
            'typography':88,'composition':88,'brand_alignment':85,'creative_coherence':88})
        for key in ('logo_correct','shape_preserved','lighting_consistent','copy_concept_specific','visual_memory_visible'):
            self.assertIn(key,commercial.CHECKS)


if __name__=='__main__':unittest.main()
