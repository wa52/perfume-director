import unittest
import numpy as np
from PIL import Image, ImageDraw
import harmonization


class HarmonizationTests(unittest.TestCase):
    def test_linear_composite_has_no_dark_gamma_fringe(self):
        product=Image.new('RGBA',(1,1),(255,255,255,128))
        background=Image.new('RGB',(1,1),'black')
        result=harmonization.linear_composite(background,product)
        self.assertGreater(result.getpixel((0,0))[0],180)

    def test_matte_cleanup_changes_rgb_but_never_alpha_or_opaque_label(self):
        image=Image.new('RGBA',(9,9),(255,255,255,0))
        ImageDraw.Draw(image).rectangle((2,2,6,6),fill=(30,40,50,255))
        image.putpixel((1,4),(220,230,240,80))
        cleaned=harmonization.clean_matte(image)
        self.assertEqual(cleaned.getchannel('A').tobytes(),image.getchannel('A').tobytes())
        self.assertEqual(cleaned.getpixel((4,4)),image.getpixel((4,4)))
        self.assertLess(cleaned.getpixel((1,4))[0],60)

    def test_guided_field_cannot_copy_generated_lettering(self):
        before=Image.new('RGB',(80,100),(90,100,110));guide=before.copy()
        ImageDraw.Draw(guide).text((30,40),'FAKE',fill='white')
        alpha=Image.new('L',before.size);ImageDraw.Draw(alpha).rectangle((20,10,59,89),fill=255)
        protected=Image.new('L',before.size);ImageDraw.Draw(protected).rectangle((20,35,59,65),fill=255)
        field=harmonization.guide_field(before,guide,alpha,protected,.5)
        self.assertTrue(np.isfinite(field).all())
        self.assertLessEqual(float(field.max()),1.15)
        self.assertGreaterEqual(float(field.min()),.85)
        # The only modified guide pixels are protected lettering; ignore them.
        self.assertTrue(np.allclose(field,1,atol=.015))

    def test_invalid_strength_and_guide_geometry_rejected(self):
        before=Image.new('RGB',(20,30));mask=Image.new('L',before.size,255)
        for strength in (float('nan'),-1,2):
            with self.assertRaises(ValueError):harmonization.guide_field(before,before,mask,Image.new('L',before.size),strength)
        with self.assertRaises(ValueError):harmonization.guide_field(before,Image.new('RGB',(21,30)),mask,mask,.5)

    def test_zero_strength_is_identity_field(self):
        before=Image.new('RGB',(20,30),(80,90,100));mask=Image.new('L',before.size,255)
        field=harmonization.guide_field(before,Image.new('RGB',before.size,'white'),mask,mask,0)
        self.assertTrue(np.array_equal(field,np.ones((30,20))))

    def test_contact_core_follows_two_supports_without_filling_raised_gap(self):
        product=Image.new('RGBA',(80,100));draw=ImageDraw.Draw(product)
        draw.rectangle((2,40,25,99),fill=(30,40,50,255))
        draw.rectangle((55,40,77,99),fill=(30,40,50,255))
        draw.rectangle((25,40,55,75),fill=(30,40,50,255))
        mask=harmonization.contour_shadow(product,(100,120),10,10,.5)
        self.assertGreater(mask.getpixel((20,110)),0)
        self.assertGreater(mask.getpixel((70,110)),0)
        self.assertEqual(mask.getpixel((50,110)),0)
        self.assertEqual(mask.getpixel((50,85)),0)

    def test_review_cannot_promote_score_pass_with_unresolved_problem(self):
        import optimize_2d
        versions=[{'id':id,'scores':{'product_fidelity':97,'edge_quality':92,'lighting_coherence':92,'grounding':92},
            'problems':[],'integration_acceptable':True} for id in ['baseline','A','B','C']]
        versions[2]['problems']=[{'problem':'thin contact core'}]
        result=optimize_2d.select_review({'versions':versions,'preferred':'B'})
        self.assertEqual(result['status'],'NEEDS_REVIEW')
        self.assertFalse(result['commercial_release_allowed'])

    def test_manual_spill_cleanup_keeps_alpha_and_red_brand_texture(self):
        product=Image.new('RGBA',(20,30))
        ImageDraw.Draw(product).rectangle((3,2,16,27),fill=(20,30,40,255))
        product.putpixel((3,18),(220,160,30,255))
        product.putpixel((10,18),(230,30,30,255))
        result=harmonization.clean_spill(product,[{'bbox':[0,.4,1,.8],'strength':1}])
        self.assertEqual(result.getchannel('A').tobytes(),product.getchannel('A').tobytes())
        self.assertEqual(result.getpixel((10,18)),product.getpixel((10,18)))
        color=result.getpixel((3,18))[:3]
        self.assertLess(max(color)-min(color),5)

    def test_optional_alpha_repair_never_expands_or_changes_interior_label_rgb(self):
        product=Image.new('RGBA',(20,30));ImageDraw.Draw(product).rectangle((3,2,16,27),fill=(230,30,40,255))
        source=np.asarray(product);result=np.asarray(harmonization.refine_edge_alpha(product))
        self.assertTrue(np.array_equal(source[:,:,:3],result[:,:,:3]))
        self.assertTrue((result[:,:,3]<=source[:,:,3]).all())
        self.assertEqual(result[15,10,3],255)
        self.assertGreater(int((source[:,:,3]!=result[:,:,3]).sum()),0)

    def test_wrap_changes_only_reviewed_edge_and_preserves_alpha(self):
        product=Image.new('RGBA',(20,30));ImageDraw.Draw(product).rectangle((3,2,16,27),fill=(230,230,230,255))
        result=harmonization.ambient_wrap(product,Image.new('RGB',(40,50),(100,100,100)),10,10,[{'bbox':[0,0,1,.3],'strength':.25}])
        self.assertEqual(product.getchannel('A').tobytes(),result.getchannel('A').tobytes())
        self.assertLess(result.getpixel((3,3))[0],230)
        self.assertEqual(result.getpixel((10,5)),product.getpixel((10,5)))
        self.assertEqual(result.getpixel((3,20)),product.getpixel((3,20)))
        with self.assertRaises(ValueError):harmonization.ambient_wrap(product,Image.new('RGB',(40,50)),10,10,[{'bbox':[0,0,1,1],'strength':1}])

    def test_reflection_guide_cannot_touch_locked_lettering_or_background(self):
        before=Image.new('RGB',(80,100),(20,20,20));guide=Image.new('RGB',before.size,'white')
        alpha=Image.new('L',before.size);ImageDraw.Draw(alpha).rectangle((15,5,65,95),fill=255)
        protected=Image.new('L',before.size);ImageDraw.Draw(protected).rectangle((15,40,65,60),fill=255)
        field=harmonization.reflection_field(before,guide,alpha,protected,.12)
        self.assertEqual(field[50,40],0)
        self.assertEqual(field[10,5],0)
        self.assertGreater(field[25,40],0)
        self.assertLessEqual(float(field.max()),.06)

    def test_comfy_node_emits_actual_images_and_rejects_batch_and_nan(self):
        # Exercise the actual node class without importing unrelated HTTP routes.
        import ast,json
        import torch
        import poster
        tree=ast.parse((poster.ROOT/'comfy_node/__init__.py').read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Product2DHarmonize')
        namespace={'Image':Image,'np':np,'torch':torch,'engine':poster,'json':json}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_comfy_node','exec'),namespace)
        runner=namespace['Product2DHarmonize']()
        spec=poster.read(poster.ROOT/'samples/relighting/beverage-20261003/SourceSpec.json')
        spec['canvas']={'width':512,'height':512};spec['product']={'x':160,'y':256,'width':140,'height':320}
        for name in poster.TEXT_LAYERS:spec[name].update(text='',x=0,y=0,size=12,font='C:/Windows/Fonts/arial.ttf')
        spec['decoration']['enabled']=False
        product=torch.full((1,400,120,3),.3);mask=torch.zeros((1,400,120));background=torch.full((1,512,512,3),.65)
        args=(product,mask,background,json.dumps(spec),'C:/Windows/Fonts/arial.ttf','{"ground_top":0.65}')
        output=runner.execute(*args)
        self.assertEqual(tuple(output[0].shape),(1,512,512,3))
        self.assertTrue(torch.isfinite(output[0]).all().item())
        self.assertEqual(json.loads(output[2])['status'],'UNREVIEWED')
        self.assertFalse(json.loads(output[2])['commercial_release_allowed'])
        with self.assertRaises(ValueError):runner.execute(product.repeat(2,1,1,1),*args[1:])
        invalid=mask.clone();invalid[0,0,0]=float('nan')
        with self.assertRaises(ValueError):runner.execute(product,invalid,*args[2:])
        wrong_guide=torch.ones((1,256,256,3))
        parameters=json.dumps({'ground_top':.65,'identity_zones':[{'name':'label','bbox':[0,.4,1,.6]}]})
        with self.assertRaisesRegex(ValueError,'Guide baseline must match'):
            runner.execute(*args[:5],parameters,guide_before=wrong_guide,guide=wrong_guide)

    def test_incomplete_independent_defect_evidence_cannot_be_approved(self):
        import optimize_2d
        rows=[{'id':id,'product_fidelity':97,'physical_integration':91,'edge_quality':90,
            'blocking_problems':[],'acceptable_integration':True} for id in ['X','Y','Z']]
        review={'candidates':rows,'preferred':'X','reason':'Visible contact and clean label edge'}
        self.assertEqual(optimize_2d.select_independent(review)['status'],'INTEGRATION_ONLY')
        rows[1]['blocking_problems']=[{}]
        with self.assertRaises(ValueError):optimize_2d.select_independent(review)


if __name__=='__main__':unittest.main()
