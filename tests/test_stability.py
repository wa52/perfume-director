import copy
import http.client
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import poster

SAMPLE = poster.ROOT/'samples/automatic-four/jadore-20261001'

class StabilityTests(unittest.TestCase):
    def test_actual_contradictory_pass_is_downgraded_not_crashed(self):
        raw = poster.read(SAMPLE/'black-gold/v1/Critic-call.json')['output']
        result = poster.validate_critique(copy.deepcopy(raw), strict=True)
        self.assertFalse(result['pass'])
        self.assertTrue(result['changes'])
        self.assertTrue(result['validation_notes'])

    def test_transient_disconnect_retries_and_records_attempts(self):
        response = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]}
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory)/'image.png';Image.new('RGB',(8,8),'white').save(image)
            trace = Path(directory)/'trace.json'
            config = {'api_key_env':'TEST_VISION_KEY','vision_model':'test','vision_base_url':'https://example.invalid', 'vision_retry_delay':0}
            with patch.dict(os.environ, {'TEST_VISION_KEY':'never-log'}), patch.object(poster,'http',side_effect=[http.client.RemoteDisconnected(),json.dumps(response).encode()]) as request:
                self.assertEqual(poster.vision(config,'test',[image],trace), {'ok':True})
            self.assertEqual(request.call_count,2)
            self.assertEqual(len(poster.read(trace)['attempts']),2)
            self.assertNotIn('never-log',trace.read_text())

    def test_actual_bad_cream_patch_is_blocked_by_safe_layout(self):
        spec = poster.read(SAMPLE/'cream-minimal/v1/PosterSpec.json')
        changes = poster.read(SAMPLE/'cream-minimal/v1/Critic.json')['changes']
        with self.assertRaises(ValueError):
            poster.apply_safe_changes(spec, changes, SAMPLE/'product.png', 'C:/Windows/Fonts/msyh.ttc')

    def test_preflight_restores_safe_layout_without_changing_copy(self):
        spec = poster.read(SAMPLE/'cream-minimal/v2/PosterSpec.json')
        original = copy.deepcopy(spec)
        prepared, issues = poster.prepare_layout({'font':'C:/Windows/Fonts/msyh.ttc','direction_id':'cream-minimal'},spec,SAMPLE/'product.png')
        self.assertTrue(issues)
        self.assertFalse(poster.layout_issues(prepared,SAMPLE/'product.png','C:/Windows/Fonts/msyh.ttc'))
        self.assertEqual(spec,original)
        for name in poster.TEXT_LAYERS:
            self.assertEqual(prepared[name]['text'],spec[name]['text'])

    def test_directions_use_relevant_diverse_references(self):
        store = poster.reference_store_module()
        dark = store.select(poster.ROOT,3,direction='black-gold')
        cream = store.select(poster.ROOT,3,direction='cream-minimal')
        green = store.select(poster.ROOT,3,direction='botanical')
        self.assertNotEqual([r['id'] for r in dark],[r['id'] for r in cream])
        self.assertEqual(len({r['brand'] for r in cream}),3)
        self.assertTrue(any('green' in r['analysis']['color'] or 'mint_green' in r['analysis']['color'] for r in green))

    def test_actual_editorial_white_frame_is_detected(self):
        issues = poster.background_issues(SAMPLE/'burgundy-editorial/v1/background.png', 'burgundy-editorial')
        self.assertIn('unexpected_white_frame', issues)

    def test_narrow_frame_is_detected(self):
        from PIL import ImageDraw
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'narrow.png'
            image = Image.new('RGB',(1080,1440),'white')
            ImageDraw.Draw(image).rectangle((37,37,1042,1402),fill='#121416')
            image.save(path)
            self.assertIn('unexpected_white_frame',poster.background_issues(path,'black-gold'))

    def test_review_failure_preserves_image_without_invented_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = poster.read(poster.ROOT/'examples/PosterSpec.json')
            poster.write(root/'examples/PosterSpec.json', spec)
            poster.write(root/'kb/luxury.json', [{'image':'reference.png','analysis':{'perfume_suitability':80}}]*3)
            product = root/'product.png'; Image.new('RGBA',(20,40),(255,255,255,128)).save(product)
            def render(config, spec, product, destination, background):
                Image.new('RGB',(20,40),'black').save(destination)
            with patch.object(poster,'ROOT',root), patch.object(poster,'vision',return_value=spec), patch.object(poster,'comfy_render',side_effect=render), patch.object(poster,'review_validated',side_effect=http.client.RemoteDisconnected()):
                run = poster.run({'font':'C:/Windows/Fonts/msyh.ttc'},product,'test')
            result = poster.read(run/'result.json')
            self.assertEqual(result['status'],'NEEDS_REVIEW')
            self.assertIsNone(result['selected']['score'])
            self.assertTrue((run/result['selected']['poster']).exists())
            self.assertEqual(result['review_failures'],[1])

    def test_legibility_guard_preserves_copy_and_geometry(self):
        spec = poster.read(poster.ROOT/'examples/PosterSpec.json')
        for name in poster.TEXT_LAYERS: spec[name]['color'] = '#FFFFFF'
        original = copy.deepcopy(spec)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'background.png'
            Image.new('RGB',(1080,1440),'white').save(path)
            changes = poster.quality_module().contrast_adjustments(spec,{'text_bbox':{'title':[50,50,300,100]}},path)
        self.assertEqual(changes[0]['path'],'title.color')
        self.assertEqual(changes[0]['value'],'#261E16')
        self.assertEqual(spec,original)

    def test_background_retries_before_composite(self):
        from PIL import ImageDraw
        spec = poster.direction_template(poster.read(poster.ROOT/'examples/PosterSpec.json'),'burgundy-editorial')
        config = poster.read(poster.ROOT/'config.zhipu.example.json')
        config['direction_id'] = 'burgundy-editorial'
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)/'poster.png'
            def execute(config, workflow, node, path):
                image = Image.new('RGB',(1080,1440),'white')
                if Path(path).name == 'background-attempt-1.png':
                    ImageDraw.Draw(image).rectangle((40,40,1040,1400),fill='#58192C')
                else:
                    image.paste('#58192C',(0,0,1080,1440))
                    ImageDraw.Draw(image).rectangle((600,0,1080,1440),fill='#6C2035')
                image.save(path);return Path(path)
            with patch.object(poster,'execute',side_effect=execute) as renderer, patch.object(poster,'upload',return_value='input.png'), patch.object(poster,'rendered_geometry',return_value={'text_bbox':{}}):
                poster.comfy_render(config,spec,'product.png',destination,None)
            audit = poster.read(destination.with_name('Background-audit.json'))
            self.assertEqual(renderer.call_count,3)
            self.assertEqual(audit['source'],'comfyui_generated')
            self.assertIn('unexpected_white_frame',audit['attempts'][0]['issues'])
            self.assertFalse(audit['attempts'][1]['issues'])

    def test_auth_failure_does_not_retry(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory)/'image.png';Image.new('RGB',(8,8),'white').save(image)
            config = {'api_key_env':'TEST_VISION_KEY','vision_model':'test','vision_base_url':'https://example.invalid'}
            with patch.dict(os.environ,{'TEST_VISION_KEY':'never-log'}), patch.object(poster,'http',side_effect=urllib.error.HTTPError('url',401,'Unauthorized',{},None)) as request:
                with self.assertRaises(ValueError): poster.vision(config,'test',[image])
            self.assertEqual(request.call_count,1)

    def test_contact_shadow_is_darkest_at_actual_product_base(self):
        spec = poster.read(poster.ROOT/'examples/PosterSpec.json')
        spec['canvas'] = {'width':512,'height':512}
        spec['product'] = {'x':256,'y':256,'width':100,'height':200}
        spec['shadow'].update(kind='contact',offset_x=0,offset_y=0,opacity=.35,blur=10)
        spec['decoration']['enabled'] = False
        for name in poster.TEXT_LAYERS:spec[name].update(text='',x=0,y=0)
        rendered = poster.render(spec,Image.new('RGBA',(100,200),(255,0,0,255)),'C:/Windows/Fonts/msyh.ttc',Image.new('RGB',(512,512),'white'))
        self.assertLess(rendered.getpixel((256,357))[0],rendered.getpixel((256,380))[0])
        self.assertEqual(rendered.getpixel((256,355)),(255,0,0))

if __name__ == '__main__': unittest.main()
