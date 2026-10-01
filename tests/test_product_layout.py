import unittest
import poster


class CrossProductLayoutTests(unittest.TestCase):
    def test_real_tobacco_vanille_failure_fits_beside_wider_bottle(self):
        root=poster.ROOT
        spec=poster.read(root/'samples/cross-product/tobacco-vanille-20261001/baseline/botanical/Director-call.json')['output']
        product=root/'assets/products/tom-ford-tobacco-vanille-retailer.png'
        self.assertIn('title_overlaps_product',poster.layout_issues(spec,product,'C:/Windows/Fonts/msyh.ttc','botanical'))
        prepared,_=poster.prepare_layout({'font':'C:/Windows/Fonts/msyh.ttc','direction_id':'botanical'},spec,product)
        self.assertEqual(prepared['title']['text'],'TOBACCO VANILLE')
        self.assertEqual(prepared['title']['x'],90)
        self.assertLess(prepared['title']['size'],50)
        self.assertEqual(poster.layout_issues(prepared,product,'C:/Windows/Fonts/msyh.ttc','botanical'),[])

    def test_four_grids_fit_same_long_name_without_changing_product(self):
        product=poster.ROOT/'assets/products/tom-ford-tobacco-vanille-retailer.png'
        for direction in poster.DIRECTIONS:
            with self.subTest(direction=direction['id']):
                spec=poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),direction['id'])
                for layer,text in {'title':'TOBACCO VANILLE','logo':'TOM FORD','subtitle':'EAU DE PARFUM','price':''}.items():spec[layer]['text']=text
                prepared,_=poster.prepare_layout({'font':'C:/Windows/Fonts/msyh.ttc','direction_id':direction['id']},spec,product)
                self.assertEqual(prepared['product'],spec['product'])
                self.assertEqual(prepared['title']['text'],spec['title']['text'])
                self.assertEqual(poster.layout_issues(prepared,product,'C:/Windows/Fonts/msyh.ttc',direction['id']),[])
