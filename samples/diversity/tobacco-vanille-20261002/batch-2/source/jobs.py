"""Run the director outside ComfyUI's prompt worker to avoid self-queue deadlocks."""
import copy
import os
from pathlib import Path
import re
import threading
import uuid


class DirectorJobs:
    def __init__(self, root, engine):
        self.root = Path(root).resolve()
        self.engine = engine
        self.directory = self.root/'runtime/director-jobs'
        self.lock = threading.RLock()
        self.active = None
        for path in self.directory.glob('*/state.json'):
            try:
                state = self.engine.read(path)
            except (ValueError, OSError):
                state = {'id': path.parent.name, 'status': 'ERROR', 'stage': 'FAILED', 'error': 'UnreadableSavedState'}
                self.save_state(path, state)
            if state.get('status') == 'RUNNING':
                state.update(status='ERROR', stage='FAILED', error='ServerRestarted',
                    message='Server restarted; run the workflow again to begin a new job.')
                self.save_state(path, state)

    def save_state(self, path, state):
        temporary = path.with_suffix('.tmp')
        self.engine.write(temporary, state)
        temporary.replace(path)

    def state_path(self, job_id):
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise ValueError('Invalid job ID')
        return self.directory/job_id/'state.json'

    def status(self, job_id):
        with self.lock:
            return self.engine.read(self.state_path(job_id))

    def update(self, job_id, values):
        with self.lock:
            state = self.status(job_id)
            state.update(values)
            self.save_state(self.state_path(job_id), state)

    def start(self, product, brief, comfy_url):
        config = self.engine.read(self.root/'config.local.json')
        if not os.environ.get(config['api_key_env']) or config['vision_model'] == 'YOUR_VISION_MODEL':
            raise ValueError('Configure the vision model and '+config['api_key_env']+' before starting ComfyUI')
        config = copy.deepcopy(config)
        config['comfy_url'] = comfy_url
        if config.get('background_workflow'):
            config['background_workflow'] = str(self.root/config['background_workflow'])
        if product.mode != 'RGBA' or product.getchannel('A').getextrema()[0] == 255:
            raise ValueError('Load a transparent PNG and connect both IMAGE and MASK')
        if not brief.strip():
            raise ValueError('Brief must not be empty')
        with self.lock:
            if self.active:
                raise ValueError('A director loop is still running; wait for its final result')
            job_id = uuid.uuid4().hex
            path = self.state_path(job_id).parent
            path.mkdir(parents=True)
            product.save(path/'product.png')
            self.save_state(path/'state.json', {'id': job_id, 'status': 'RUNNING', 'stage': 'QUEUED',
                'vision_model': config['vision_model'], 'vision_endpoint': config['vision_base_url']})
            self.active = job_id
            try:
                threading.Thread(target=self.work, args=(job_id, config, path/'product.png', brief), daemon=True).start()
            except Exception:
                self.active = None
                self.update(job_id, {'status': 'ERROR', 'error': 'Could not start the background worker'})
                raise
        return job_id

    def work(self, job_id, config, product, brief):
        try:
            run_dir = self.engine.run_four(config, product, brief,
                progress=lambda values: self.update(job_id, values))
            result = self.engine.read(run_dir/'result.json')
            self.update(job_id, {'status': result['status'], 'stage': 'FINISHED',
                'run_dir': str(run_dir), 'directions': result['directions']})
        except Exception as error:
            # Do not expose arbitrary provider messages, request data or credentials.
            self.update(job_id, {'status': 'ERROR', 'stage': 'FAILED', 'error': type(error).__name__,
                'message': 'Loop stopped; inspect the saved run and server log. No PASS was recorded.'})
            print('Perfume Director loop stopped:', type(error).__name__, flush=True)
        finally:
            with self.lock:
                self.active = None

    def preview(self, job_id, direction=None):
        state = self.status(job_id)
        if state.get('directions'):
            candidates = [item for item in state['directions'] if 'selected' in item and (direction is None or item['id']==direction)]
            if not candidates:
                raise FileNotFoundError('No preview for this direction')
            state = candidates[0]
        elif direction is not None:
            raise FileNotFoundError('Unknown direction')
        if state['status'] not in ('PASS', 'NEEDS_REVIEW'):
            raise FileNotFoundError('No final preview yet')
        run = Path(state['run_dir']).resolve()
        path = (run/state['selected']['poster'].replace('\\', '/')).resolve()
        if not run.is_relative_to(self.root/'runs') or not path.is_relative_to(run) or path.suffix != '.png':
            raise ValueError('Preview path outside saved run')
        return path
