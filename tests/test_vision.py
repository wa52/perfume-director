import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import poster


class VisionTests(unittest.TestCase):
    def call(self, response, options=None):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory)/'product.png'
            trace = Path(directory)/'call.json'
            Image.new('RGB', (8, 8), 'white').save(image)
            config = {'api_key_env': 'TEST_VISION_KEY', 'vision_model': 'test-vision',
                'vision_base_url': 'https://example.invalid/v4',
                'vision_timeout_seconds': 123, 'vision_options': options or {}}
            with patch.dict(os.environ, {'TEST_VISION_KEY': 'never-log-this-key'}), \
                 patch.object(poster, 'http', return_value=json.dumps(response).encode()) as request:
                try:
                    result = poster.vision(config, 'Inspect this image as JSON.', [image]*5, trace)
                except Exception:
                    self.failed_trace = poster.read(trace) if trace.exists() else None
                    raise
            data = poster.read(trace)
            self.assertNotIn('never-log-this-key', trace.read_text())
            return result, data, request.call_args

    def response(self, content, finish='stop'):
        return {'id': 'actual-response-id', 'model': 'returned-model',
            'usage': {'total_tokens': 123},
            'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(content)}}]}

    def test_multimodal_payload_options_and_audit(self):
        result, trace, call = self.call(self.response({'pass': True}), {'thinking': {'type': 'disabled'}})
        payload = json.loads(call.args[1])
        self.assertEqual(len(payload['messages'][1]['content']), 6)
        self.assertEqual(payload['thinking']['type'], 'disabled')
        self.assertEqual(call.kwargs['timeout'], 123)
        self.assertEqual(trace['image_count'], 5)
        self.assertEqual(trace['response_id'], 'actual-response-id')
        self.assertEqual(trace['returned_model'], 'returned-model')
        self.assertEqual(result, {'pass': True})

    def test_single_answer_envelope_preserves_raw_evidence(self):
        result, trace, _ = self.call(self.response({'answer': {'pass': True}}))
        self.assertEqual(result, {'pass': True})
        self.assertEqual(trace['raw_output'], {'answer': result})
        self.assertEqual(trace['normalization'], 'single_answer_envelope')

    def test_truncated_response_is_rejected_and_recorded(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.call(self.response({'pass': True}, finish='length'))
        self.assertEqual(self.failed_trace['status'], 'ERROR')
        self.assertEqual(self.failed_trace['finish_reason'], 'length')

    def test_options_cannot_override_model_or_messages(self):
        with self.assertRaisesRegex(ValueError, 'cannot be overridden'):
            self.call(self.response({}), {'messages': []})


if __name__ == '__main__':
    unittest.main()
