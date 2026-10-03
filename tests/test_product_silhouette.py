import unittest
import tempfile
from pathlib import Path
from PIL import Image,ImageDraw
import graphic_shapes
import poster


class SilhouetteTests(unittest.TestCase):
    def test_original_alpha_exactly_determines_shape_not_label_rgb(self):
        source=Image.new('RGBA',(20,80),(255,0,0,0));d=ImageDraw.Draw(source)
        d.rectangle((6,0,13,29),fill=(255,0,0,255));d.rectangle((0,30,19,79),fill=(255,0,0,255))
        original=source.tobytes();shape={'kind':'product_silhouette','x':40,'y':10,'width':100,'height':80,'color':'#123456','opacity':1}
        out=graphic_shapes.compose(Image.new('RGBA',(180,150),'white'),[shape],source)
        self.assertEqual(source.tobytes(),original)
        self.assertEqual(out.getpixel((45,12))[:3],(255,255,255))
        self.assertEqual(out.getpixel((48,12))[:3],(18,52,86))
        self.assertEqual(out.getpixel((40,60))[:3],(18,52,86))
        self.assertEqual(out.getpixel((62,60))[:3],(255,255,255))

    def test_missing_or_empty_source_is_rejected(self):
        shape={'kind':'product_silhouette','x':0,'y':0,'width':50,'height':50,'color':'black','opacity':1}
        for source in [None,Image.new('RGB',(20,30)),Image.new('RGBA',(20,30))]:
            with self.assertRaises(ValueError):graphic_shapes.compose(Image.new('RGBA',(80,80)),[shape],source)

    def test_aspect_fit_and_transparent_opacity_are_preserved(self):
        source=Image.new('RGBA',(20,80),(200,10,20,128));shape={'kind':'product_silhouette','x':10,'y':10,'width':100,'height':100,'color':'black','opacity':.5}
        out=graphic_shapes.compose(Image.new('RGBA',(180,150),(0,0,0,0)),[shape],source)
        self.assertEqual(out.getpixel((20,50))[3],64)
        self.assertEqual(out.getpixel((36,50))[3],0)

    def test_renderer_and_critic_geometry_use_same_fitted_contour(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';source=Image.new('RGBA',(20,80),(200,90,20,255));source.save(path)
            spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
            spec['background'].update(color='#ffffff',shapes=[{'kind':'product_silhouette','x':10,'y':10,'width':100,'height':100,'color':'#123456','opacity':1}])
            for k in poster.TEXT_LAYERS:spec[k]['text']=''
            spec['decoration']['enabled']=False
            image=poster.render(spec,source,'C:/Windows/Fonts/msyh.ttc')
            self.assertEqual(image.getpixel((20,50)),(18,52,86));self.assertEqual(image.getpixel((36,50)),(255,255,255))
            geometry=poster.rendered_geometry(spec,path,'C:/Windows/Fonts/msyh.ttc')
            self.assertEqual(geometry['shape_geometry'][0]['bbox'],[10,10,35,110])


if __name__=='__main__':unittest.main()
