import copy
import unittest
from PIL import Image,ImageChops
import graphic_shapes
import poster


class GraphicShapesTests(unittest.TestCase):
    def shape(self,**changes):
        return {'kind':'rectangle','x':20,'y':30,'width':40,'height':50,
                'color':'#FF0000','opacity':1,**changes}

    def test_exact_geometry_and_transparency_leave_background_untouched(self):
        original=Image.new('RGB',(100,100),'white')
        result=graphic_shapes.compose(original,[self.shape(opacity=.5)]).convert('RGB')
        self.assertEqual(result.getpixel((20,30)),(255,127,127))
        self.assertEqual(result.getpixel((59,79)),(255,127,127))
        self.assertEqual(result.getpixel((60,80)),(255,255,255))
        self.assertEqual(original.getpixel((20,30)),(255,255,255))

    def test_shape_move_changes_only_its_old_and_new_regions(self):
        original=Image.new('RGB',(100,100),'white')
        a=graphic_shapes.compose(original,[self.shape()])
        b=graphic_shapes.compose(original,[self.shape(x=30)])
        self.assertEqual(ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox(),(20,30,70,80))

    def test_product_occludes_shape_and_retains_original_color(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json')
        for n in poster.TEXT_LAYERS:spec[n]['text']=''
        spec['decoration']['enabled']=False
        spec['shadow']['opacity']=0
        spec['product'].update(x=540,y=850,width=100,height=100)
        spec['background'].update(color='#FFFFFF',shapes=[self.shape(kind='ellipse',x=400,y=700,width=280,height=300)])
        result=poster.render(spec,Image.new('RGBA',(100,100),'#0000FF'),'C:/Windows/Fonts/arial.ttf')
        self.assertEqual(result.getpixel((540,850)),(0,0,255))
        self.assertEqual(result.getpixel((450,850)),(255,0,0))

    def test_graphic_patch_is_atomic_and_does_not_regenerate_background(self):
        spec=poster.read(poster.ROOT/'examples/PosterSpec.json');before=copy.deepcopy(spec)
        for shape in [self.shape(opacity=float('nan')),self.shape(width=-1),self.shape(x=-99999),self.shape(kind='script')]:
            with self.assertRaises(ValueError):
                poster.apply_changes(spec,[{'path':'title.size','op':'set','value':64},
                                           {'path':'background.shapes','op':'set','value':[shape]}])
            self.assertEqual(spec,before)
        fixed=poster.apply_changes(spec,[{'path':'background.shapes','op':'set','value':[self.shape()]}])
        self.assertEqual(fixed['background']['revision'],spec['background']['revision'])
        self.assertEqual(fixed['seed'],spec['seed'])
        with self.assertRaises(ValueError):poster.apply_changes(spec,[{'path':'background.shapes','op':'add','value':[]}])

    def test_bounded_bleed_and_list_order_are_supported(self):
        result=graphic_shapes.compose(Image.new('RGB',(100,100),'white'),
            [self.shape(x=-10,y=0),self.shape(x=0,y=0,width=10,height=10,color='#0000FF')])
        self.assertEqual(result.getpixel((1,1)),(0,0,255,255))
        self.assertEqual(result.getpixel((20,20)),(255,0,0,255))
        with self.assertRaises(ValueError):graphic_shapes.validate_shapes([self.shape()]*9,100,100)


if __name__=='__main__':unittest.main()
