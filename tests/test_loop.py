import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import poster
from PIL import Image, ImageDraw


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.spec = poster.read(poster.ROOT/'examples/PosterSpec.json')

    def test_patch_is_atomic_and_rejects_off_canvas(self):
        original = copy.deepcopy(self.spec)
        with self.assertRaises(ValueError):
            poster.apply_changes(self.spec, [{'path': 'title.size', 'op': 'multiply', 'value': .8},
                {'path': 'product.x', 'op': 'set', 'value': 5000}])
        self.assertEqual(self.spec, original)

    def test_product_scale_ignores_transparent_padding(self):
        spec = copy.deepcopy(self.spec)
        spec['canvas'] = {'width': 512, 'height': 512}
        spec['product'] = {'x': 256, 'y': 256, 'width': 100, 'height': 200}
        spec['shadow']['opacity'] = 0
        spec['decoration']['enabled'] = False
        for name in poster.TEXT_LAYERS:
            spec[name].update(text='', x=0, y=0)
        padded = Image.new('RGBA', (400, 400))
        ImageDraw.Draw(padded).rectangle((150, 50, 249, 249), fill=(255, 0, 0, 255))
        config = poster.read(poster.ROOT/'config.example.json')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'padded.png'
            padded.save(path)
            geometry = poster.rendered_geometry(spec, path, config['font'])
        self.assertEqual(geometry['product_bbox'], [206, 156, 306, 356])
        self.assertEqual(geometry['product_base_y'], 356)
        self.assertEqual(geometry['text_product_overlap'], {})
        result = poster.render(spec, padded, config['font'])
        pixels = result.load()
        self.assertEqual(pixels[206, 156], (255, 0, 0))
        self.assertEqual(pixels[305, 355], (255, 0, 0))
        self.assertNotEqual(pixels[205, 155], (255, 0, 0))

    def test_no_arbitrary_fields_or_nonfinite_values(self):
        for change in ({'path': 'seed', 'op': 'set', 'value': 9},
                       {'path': 'title.size', 'op': 'set', 'value': float('nan')}):
            with self.assertRaises(ValueError):
                poster.apply_changes(self.spec, [change])

    def test_background_regeneration_preserves_base_seed(self):
        changed = poster.apply_changes(self.spec, [{'path': 'background.prompt', 'op': 'set', 'value': 'simpler background'}])
        self.assertEqual(changed['seed'], self.spec['seed'])
        self.assertEqual(changed['background']['revision'], 1)

    def test_contact_shadow_patch_for_existing_spec(self):
        spec = poster.apply_changes(self.spec, [{'path': 'shadow.kind', 'op': 'set', 'value': 'contact'}])
        self.assertEqual(spec['shadow']['kind'], 'contact')
        with self.assertRaises(ValueError):
            poster.apply_changes(self.spec, [{'path': 'shadow.kind', 'op': 'set', 'value': 'unknown'}])

    def test_pass_cannot_hide_unresolved_problems(self):
        with self.assertRaises(ValueError):
            poster.validate_critique({'pass': True, 'score': 90, 'problems': ['bad product'], 'changes': []})

    def test_strict_gate_does_not_accept_high_total_with_weak_typography(self):
        critique = {'pass': True, 'score': 90, 'problems': [], 'changes': [],
                    'dimensions': dict.fromkeys(poster.CRITIC_DIMENSIONS, 90)}
        critique['dimensions']['typography'] = 65
        result = poster.validate_critique(critique, strict=True)
        self.assertFalse(result['pass'])
        self.assertEqual(result['reported_score'], 90)
        self.assertTrue(result['problems'])

    def test_strict_gate_requires_complete_scores_and_uses_average(self):
        critique = {'pass': True, 'score': 99, 'problems': [], 'changes': [],
                    'dimensions': dict.fromkeys(poster.CRITIC_DIMENSIONS, 82)}
        self.assertFalse(poster.validate_critique(critique, strict=True)['pass'])
        self.assertEqual(critique['score'], 82)
        del critique['dimensions']['composition']
        with self.assertRaises(ValueError):
            poster.validate_critique(critique, strict=True)

    def exercise_loop(self, critiques, max_rounds=3):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            poster.write(root/'examples/PosterSpec.json', self.spec)
            poster.write(root/'kb/luxury.json', [{'image': 'reference.png', 'analysis': {'perfume_suitability': 80}}]*3)
            product = root/'product.png'
            Image.new('RGBA', (10, 10), (255, 255, 255, 128)).save(product)
            config = poster.read(poster.ROOT/'config.example.json')
            config['max_rounds'] = max_rounds

            def fake_render(config, spec, product, destination, background):
                Image.new('RGB', (spec['canvas']['width'],spec['canvas']['height'])).save(destination)

            for critique in critiques:
                critique['dimensions'] = dict.fromkeys(poster.CRITIC_DIMENSIONS, critique['score'])
            with patch.object(poster, 'ROOT', root), patch.object(poster, 'vision', side_effect=[self.spec, *critiques]), patch.object(poster, 'comfy_render', side_effect=fake_render) as renderer:
                result = poster.read(poster.run(config, product, 'test')/'result.json')
            return result, renderer.call_count

    def test_quality_budget_can_continue_beyond_three_versions(self):
        critiques = [{'pass':False,'score':score,'problems':[{'type':'typography','problem':'refine'}],
                     'changes':[{'path':'title.size','op':'multiply','value':.95}]} for score in (70,71,72,73,74)]
        result,count=self.exercise_loop(critiques,max_rounds=5)
        self.assertEqual(count,5)
        self.assertEqual(result['status'],'NEEDS_REVIEW')

    def test_unchanged_patch_does_not_repeat_render(self):
        critique={'pass':False,'score':70,'problems':[{'type':'typography','problem':'refine'}],
                  'changes':[{'path':'title.size','op':'set','value':self.spec['title']['size']}]}
        result,count=self.exercise_loop([critique],max_rounds=5)
        self.assertEqual(count,1)
        self.assertEqual(result['status'],'NEEDS_REVIEW')

    def test_pass_stops_first_render(self):
        result, count = self.exercise_loop([{'pass': True, 'score': 85, 'problems': [], 'changes': []}])
        self.assertEqual(count, 1)
        self.assertEqual(result['status'], 'PASS')

    def test_invalid_critic_patch_preserves_reviewable_poster(self):
        result, count = self.exercise_loop([{'pass': False, 'score': 75,
            'problems': [{'type': 'composition', 'problem': 'move'}],
            'changes': [{'path': 'product.y', 'op': 'set', 'value': 9999}]}])
        self.assertEqual(count, 1)
        self.assertEqual(result['status'], 'NEEDS_REVIEW')
        self.assertEqual(result['selected']['version'], 1)

    def test_three_render_limit_selects_best_not_last(self):
        critiques = [{'pass': False, 'score': score, 'problems': [{'type': 'typography', 'problem': 'adjust'}],
            'changes': [{'path': 'title.size', 'op': 'multiply', 'value': .95}]} for score in (70, 78, 72)]
        result, count = self.exercise_loop(critiques)
        self.assertEqual(count, 3)
        self.assertEqual(result['selected']['version'], 2)
        self.assertEqual(result['status'], 'NEEDS_REVIEW')


if __name__ == '__main__':
    unittest.main()
