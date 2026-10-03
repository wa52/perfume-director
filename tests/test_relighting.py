import unittest
from PIL import Image,ImageDraw
import relighting


class RelightingTests(unittest.TestCase):
    def inputs(self):
        source=Image.new('RGB',(80,100),(100,110,120))
        raw=Image.new('RGB',source.size,(210,200,190))
        alpha=Image.new('L',source.size);ImageDraw.Draw(alpha).rectangle((20,10,59,89),fill=255)
        protected=Image.new('L',source.size);ImageDraw.Draw(protected).rectangle((20,40,59,60),fill=255)
        editable=Image.new('L',source.size);draw=ImageDraw.Draw(editable)
        draw.rectangle((23,13,56,37),fill=255);draw.rectangle((23,63,56,86),fill=255)
        return source,raw,alpha,protected,editable

    def test_label_pixels_are_exact_while_material_pixels_change(self):
        source,raw,alpha,protected,editable=self.inputs()
        result,metrics=relighting.protect(source,raw,alpha,protected,editable)
        self.assertEqual(metrics['protected_max_rgb_error'],0)
        self.assertGreater(metrics['editable_mean_rgb_change'],20)
        self.assertEqual(result.getpixel((30,50)),source.getpixel((30,50)))
        self.assertNotEqual(result.getpixel((35,25)),source.getpixel((35,25)))

    def test_source_boundary_is_retained_without_global_original_copy(self):
        source,raw,alpha,protected,editable=self.inputs()
        result,metrics=relighting.protect(source,raw,alpha,protected,editable)
        self.assertEqual(result.getpixel((20,30)),source.getpixel((20,30)))
        self.assertNotEqual(result.getpixel((0,0)),source.getpixel((0,0)))
        self.assertGreater(metrics['editable_pixels'],0)

    def test_mismatched_geometry_is_rejected(self):
        values=list(self.inputs());values[1]=Image.new('RGB',(79,100))
        with self.assertRaises(ValueError):relighting.protect(*values)

    def test_background_transfer_is_bounded_even_for_extreme_edit(self):
        source,raw,alpha,protected,editable=self.inputs()
        raw=Image.new('RGB',source.size,'white')
        output,_=relighting.protect(source,raw,alpha,protected,editable)
        self.assertLessEqual(output.getpixel((0,0))[0],125)

    def test_illumination_transfer_does_not_copy_invented_lettering(self):
        source,raw,alpha,protected,editable=self.inputs()
        ImageDraw.Draw(source).rectangle((30,45,35,55),fill=(240,240,240))
        ImageDraw.Draw(raw).rectangle((40,45,45,55),fill=(0,0,0))
        result,metrics=relighting.transfer_illumination(source,raw,alpha)
        self.assertGreater(result.getpixel((32,50))[0],result.getpixel((42,50))[0])
        self.assertFalse(metrics['generated_product_pixels_used'])
        self.assertFalse(metrics['exact_identity_rgb_lock'])

    def test_foreground_highlights_do_not_leak_into_background_light(self):
        source,raw,alpha,_,_=self.inputs()
        raw=source.copy();ImageDraw.Draw(raw).rectangle((20,10,59,89),fill='white')
        result,_=relighting.transfer_illumination(source,raw,alpha)
        self.assertEqual(result.getpixel((19,50)),source.getpixel((19,50)))

    def test_unobservable_background_and_empty_mask_fail(self):
        source,raw,alpha,_,_=self.inputs()
        for mask in (Image.new('L',source.size),Image.new('L',source.size,255)):
            with self.assertRaises(ValueError):relighting.transfer_illumination(source,raw,mask)


if __name__=='__main__':unittest.main()
