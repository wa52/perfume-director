import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image
import poster

module_spec = importlib.util.spec_from_file_location('director_jobs_under_test', poster.ROOT/'comfy_node/jobs.py')
jobs_module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(jobs_module)


class FakeEngine:
    read = staticmethod(poster.read)
    write = staticmethod(poster.write)

    def __init__(self, root):
        self.root = root
        self.gate = threading.Event()
        self.entered = threading.Event()
        self.fail = False

    def run_four(self, config, product, brief, progress):
        folder = self.run(config, product, brief, progress)
        result = self.read(folder/'result.json')
        self.write(folder/'result.json', {'status': 'COMPLETED', 'directions': [
            {'id': 'test', 'name': 'test', 'status': 'PASS', 'run_dir': str(folder), 'selected': result['selected'], 'versions': []}]})
        return folder

    def run(self, config, product, brief, progress):
        self.config = config
        progress({'stage': 'RENDER', 'version': 1})
        self.entered.set()
        self.gate.wait(3)
        if self.fail:
            raise ValueError('private-provider-message')
        folder = self.root/'runs/live/test'
        folder.mkdir(parents=True)
        Image.new('RGB', (4, 4)).save(folder/'poster.png')
        self.write(folder/'result.json', {'status': 'PASS', 'selected': {'poster': 'poster.png', 'version': 1, 'score': 85}, 'versions': []})
        return folder


class ComfyJobsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = FakeEngine(self.root)
        self.engine.write(self.root/'config.local.json', {'api_key_env': 'TEST_LOOP_KEY', 'vision_model': 'test',
            'vision_base_url': 'https://example.invalid', 'background_workflow': 'workflows/background.json'})
        self.manager = jobs_module.DirectorJobs(self.root, self.engine)
        self.environment = patch.dict(os.environ, {'TEST_LOOP_KEY': 'private-key'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.product = Image.new('RGBA', (8, 8), (255, 255, 255, 128))

    def finished(self, job):
        for _ in range(100):
            state = self.manager.status(job)
            if state['status'] != 'RUNNING' and self.manager.active is None:
                return state
            time.sleep(.01)
        self.fail('Worker did not finish')

    def test_submission_does_not_block_comfy_queue_and_prevents_overlap(self):
        job = self.manager.start(self.product, 'brief', 'http://127.0.0.1:8190')
        self.assertTrue(self.engine.entered.wait(1))
        self.assertFalse(self.engine.gate.is_set())
        self.assertEqual(self.manager.status(job)['stage'], 'RENDER')
        with self.assertRaisesRegex(ValueError, 'still running'):
            self.manager.start(self.product, 'again', 'http://127.0.0.1:8190')
        self.engine.gate.set()
        self.assertEqual(self.finished(job)['status'], 'COMPLETED')
        self.assertTrue(self.manager.preview(job).is_file())
        self.assertTrue(self.manager.preview(job,'test').is_file())
        with self.assertRaises(FileNotFoundError):
            self.manager.preview(job,'unknown')
        self.assertEqual(self.engine.config['comfy_url'], 'http://127.0.0.1:8190')
        self.assertEqual(self.engine.config['background_workflow'], str(self.root/'workflows/background.json'))

    def test_independent_recovery_blocks_duplicate_submission(self):
        saved=self.manager.state_path('b'*32)
        self.engine.write(saved,{'id':'b'*32,'status':'RUNNING','stage':'CRITIC'})
        self.assertIsNone(self.manager.active)
        with self.assertRaisesRegex(ValueError,'recovery is still running'):
            self.manager.start(self.product,'again','http://127.0.0.1:8191')

    def test_clothing_subtype_and_source_mode_reach_worker_and_state(self):
        self.engine.gate.set()
        job=self.manager.start(self.product,'brief','http://127.0.0.1:8191',category='womenswear',garment_type='dress',display_mode='hanging')
        state=self.finished(job)
        for key,value in {'product_category':'womenswear','garment_type':'dress','display_mode':'hanging'}.items():
            self.assertEqual(self.engine.config[key],value)
            self.assertEqual(state[key],value)

    def test_error_does_not_publish_pass_or_provider_message(self):
        self.engine.fail = True
        self.engine.gate.set()
        job = self.manager.start(self.product, 'brief', 'http://127.0.0.1:8190')
        state = self.finished(job)
        self.assertEqual(state['status'], 'ERROR')
        self.assertNotIn('private-provider-message', str(state))
        with self.assertRaises(FileNotFoundError):
            self.manager.preview(job)

    def test_rejects_nontransparent_products_and_path_escape(self):
        with self.assertRaises(ValueError):
            self.manager.start(Image.new('RGBA', (8, 8), 'white'), 'brief', 'http://localhost:8190')
        with self.assertRaises(ValueError):
            self.manager.status('../../secret')
        job = 'a'*32
        self.engine.write(self.manager.state_path(job), {'status': 'PASS', 'run_dir': str(self.root/'runs/live/x'),
            'selected': {'poster': '../../../private.png'}})
        with self.assertRaises(ValueError):
            self.manager.preview(job)

    def test_restart_marks_orphans_and_recovers_corrupt_state(self):
        path = self.manager.state_path('b'*32)
        self.engine.write(path, {'id': 'b'*32, 'status': 'RUNNING'})
        corrupt = self.manager.state_path('c'*32)
        corrupt.parent.mkdir(parents=True)
        corrupt.write_text('{partial')
        restarted = jobs_module.DirectorJobs(self.root, self.engine)
        self.assertEqual(restarted.status('b'*32)['error'], 'ServerRestarted')
        self.assertEqual(restarted.status('c'*32)['error'], 'UnreadableSavedState')
        self.assertIsNone(restarted.active)

    def test_running_critic_exposes_draft_without_claiming_a_final_selection(self):
        job='d'*32;run=self.root/'runs/live/draft'
        (run/'v1').mkdir(parents=True)
        Image.new('RGB',(4,4),'white').save(run/'v1/poster.png')
        self.engine.write(self.manager.state_path(job),{'status':'RUNNING','stage':'CRITIC','run_dir':str(run),'version':1})
        state=self.manager.status(job)
        self.assertEqual(state['draft']['version'],1)
        self.assertNotIn('selected',state)
        self.assertEqual(self.manager.preview(job,draft=True),run/'v1/poster.png')
        with self.assertRaises(FileNotFoundError):self.manager.preview(job)
        self.manager.update(job,{'stage':'RENDER','version':2})
        (run/'v2').mkdir();(run/'v2/poster.png').write_bytes(b'incomplete')
        self.assertEqual(self.manager.preview(job,draft=True),run/'v1/poster.png')

    def test_planning_has_clear_repair_state_and_no_fabricated_preview(self):
        job='e'*32;batch=self.root/'runs/batches/plan';batch.mkdir(parents=True)
        self.engine.write(self.manager.state_path(job),{'status':'RUNNING','stage':'CONCEPTS','run_dir':str(batch)})
        self.assertEqual(self.manager.status(job)['planning_phase'],'initial')
        self.engine.write(batch/'Concepts-call.json',{'status':'OK'})
        self.assertEqual(self.manager.status(job)['planning_phase'],'repair')
        self.assertNotIn('draft',self.manager.status(job))
        with self.assertRaises(FileNotFoundError):self.manager.preview(job,draft=True)

    def test_draft_preview_rejects_run_outside_project(self):
        job='f'*32
        self.engine.write(self.manager.state_path(job),{'status':'RUNNING','stage':'CRITIC','version':1,'run_dir':str(self.root.parent)})
        with self.assertRaises(ValueError):self.manager.preview(job,draft=True)


if __name__ == '__main__':
    unittest.main()
