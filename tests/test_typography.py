import copy
import math
import unittest

from PIL import Image

import typography


class TypographyTests(unittest.TestCase):
    font = 'C:/Windows/Fonts/arial.ttf'

    def item(self, **changes):
        return {'x': 20, 'y': 30, 'size': 42, 'text': 'Amber Valley',
                'color': '#ffffff', **changes}

    def assert_ink_matches(self, item):
        canvas = Image.new('RGBA', (700, 500))
        layout = typography.text_layout(item, self.font)
        self.assertEqual(typography.draw_text(canvas, item, self.font), layout)
        actual = canvas.getchannel('A').getbbox()
        predicted = layout['bbox']
        self.assertIsNotNone(actual)
        self.assertLessEqual(predicted[0], actual[0])
        self.assertLessEqual(predicted[1], actual[1])
        self.assertGreaterEqual(predicted[2], actual[2])
        self.assertGreaterEqual(predicted[3], actual[3])
        # Font bearings may contain a one-pixel clear boundary, not a loose box.
        self.assertLessEqual(max(abs(a-b) for a,b in zip(actual, predicted)), 2)
        return layout

    def test_default_and_tracked_mixed_case_geometry_matches_ink(self):
        for tracking in (0, 2.5, -1):
            with self.subTest(tracking=tracking):
                self.assert_ink_matches(self.item(text='AV Amber gy, J!', tracking=tracking))

    def test_tracking_keeps_mixed_case_on_one_baseline(self):
        layout = typography.text_layout(self.item(text='Ag,j', tracking=4), self.font)
        self.assertEqual(len({op['xy'][1] for op in layout['ops']}), 1)

    def test_wrap_alignment_and_tracking_share_exact_draw_geometry(self):
        for align in ('left', 'center', 'right'):
            with self.subTest(align=align):
                item = self.item(text='Amber Valley Eau de Parfum', max_width=300,
                                 tracking=2, align=align, line_height=1.3)
                layout = self.assert_ink_matches(item)
                self.assertEqual(' '.join(layout['lines']).split(), item['text'].split())
                self.assertGreater(len(layout['lines']), 1)
                self.assertLessEqual(layout['bbox'][2], item['x'] + item['max_width'])

    def test_cjk_wrap_preserves_characters(self):
        item = self.item(text='清新花香淡香水', font='C:/Windows/Fonts/msyh.ttc', max_width=160)
        layout = self.assert_ink_matches(item)
        self.assertEqual(''.join(layout['lines']), item['text'])
        self.assertGreater(len(layout['lines']), 1)

    def test_long_latin_word_requires_font_or_frame_change(self):
        with self.assertRaisesRegex(ValueError, 'Unbreakable'):
            typography.text_layout(self.item(text='Extraordinary', max_width=60), self.font)

    def test_more_than_four_lines_rejected(self):
        with self.assertRaisesRegex(ValueError, 'four lines'):
            typography.text_layout(self.item(text='A\nB\nC\nD\nE'), self.font)

    def test_invalid_controls_rejected_without_mutation(self):
        invalid = [('tracking', math.nan), ('tracking', True), ('tracking', -5),
                   ('tracking', 41), ('max_width', -1), ('max_width', 701),
                   ('line_height', .9), ('line_height', math.inf),
                   ('align', 'justify')]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                item = self.item(**{key: value})
                before = copy.deepcopy(item)
                with self.assertRaises(ValueError):
                    typography.validate_style(item, 700)
                self.assertEqual(item, before)

    def test_empty_text_has_empty_ink_bounds(self):
        item = self.item(text='')
        canvas = Image.new('RGBA', (100, 100))
        layout = typography.draw_text(canvas, item, self.font)
        self.assertEqual(layout['bbox'], [20, 30, 20, 30])
        self.assertIsNone(canvas.getbbox())


if __name__ == '__main__':
    unittest.main()
