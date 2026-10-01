import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import poster


class FourDirectionsTests(unittest.TestCase):
    def exercise(self, failed):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []
            events = []
            def child(config, product, brief, progress):
                index = len(calls)
                calls.append((config.copy(), brief))
                if index in failed:
                    raise ValueError('private provider details')
                folder = root/'runs/live'/str(index)
                poster.write(folder/'result.json', {'status': 'NEEDS_REVIEW', 'selected': {'version': 1, 'score': 75, 'poster': 'v1/poster.png'}, 'versions': []})
                return folder
            with patch.object(poster, 'ROOT', root), patch.object(poster, 'run', side_effect=child), patch.object(poster,'resolve_copy',return_value={'title':'actual name','logo':'actual brand','subtitle':'','price':''}):
                result = poster.read(poster.run_four({'vision_model': 'test','direction_mode':'curated'}, 'product', 'approved copy', progress=events.append)/'result.json')
            return result, calls, events

    def test_four_independent_briefs_seeds_and_results(self):
        result, calls, events = self.exercise(set())
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(len(result['directions']), 4)
        self.assertEqual(len({config['direction_seed_offset'] for config, brief in calls}), 4)
        self.assertEqual(len({brief for config, brief in calls}), 4)
        self.assertTrue(all('approved copy' in brief for config, brief in calls))
        self.assertTrue(all(config['approved_copy']['title']=='actual name' for config,brief in calls))
        self.assertEqual([item['id'] for item in result['directions']], [item['id'] for item in poster.DIRECTIONS])
        self.assertEqual(events[-1]['stage'], 'FINISHED')

    def test_failure_keeps_other_three_without_leaking_provider_message(self):
        result, calls, events = self.exercise({1})
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(len(calls), 4)
        self.assertEqual(sum('selected' in item for item in result['directions']), 3)
        self.assertEqual(result['directions'][1]['error'], 'ValueError')
        self.assertNotIn('private provider details', str(result))

    def test_curated_plans_have_distinct_grids_materials_and_type(self):
        template = poster.read(poster.ROOT/'examples/PosterSpec.json')
        plans = [poster.direction_template(template,item['id']) for item in poster.DIRECTIONS]
        self.assertEqual(len({(plan['product']['x'],plan['title']['x'],plan['title']['y']) for plan in plans}),4)
        self.assertEqual(len({plan['background']['prompt'] for plan in plans}),4)
        self.assertNotEqual(plans[0]['title']['font'],plans[2]['title']['font'])
        self.assertTrue(all(plan['product']['height'] >= 800 for plan in plans))

    def test_all_fail_does_not_claim_completion_or_pass(self):
        result, calls, events = self.exercise({0, 1, 2, 3})
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(len(calls), 4)


if __name__ == '__main__':
    unittest.main()
