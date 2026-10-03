import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
import poster
import run_category_matrix


class ComfyTransportTests(unittest.TestCase):
    def test_matrix_status_monitor_uses_bounded_read_recovery(self):
        with patch.object(poster,'http',side_effect=[urllib.error.URLError('temporary disconnect'),b'{"status":"RUNNING"}']) as exchange,patch.object(poster.time,'sleep'):
            result=run_category_matrix.request('http://localhost:8191','/perfume-director/jobs/one')
        self.assertEqual(result,{'status':'RUNNING'})
        self.assertEqual(exchange.call_count,2)

    def test_history_disconnect_retries_same_prompt_without_resubmitting(self):
        calls=[];failures=[True]
        def exchange(url,data=None,headers=None,timeout=60):
            calls.append((url,data))
            if url.endswith('/prompt'):return b'{"prompt_id":"owned-prompt"}'
            if '/history/' in url:
                if failures:
                    failures.pop();raise urllib.error.URLError('temporary local disconnect')
                return json.dumps({'owned-prompt':{'outputs':{'4':{'images':[{'filename':'poster.png','subfolder':'','type':'output'}]}}}}).encode()
            return b'completed image bytes'
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'http',side_effect=exchange),patch.object(poster.time,'sleep'):
            target=Path(folder)/'poster.png'
            poster.execute({'comfy_url':'http://localhost:8191','render_timeout_seconds':60},{},'4',target)
            self.assertEqual(target.read_bytes(),b'completed image bytes')
        self.assertEqual(sum(url.endswith('/prompt') for url,_ in calls),1)
        self.assertEqual([url for url,_ in calls if '/history/' in url],['http://localhost:8191/history/owned-prompt']*2)

    def test_ambiguous_prompt_post_is_never_retried(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(poster,'http',side_effect=urllib.error.URLError('response lost')) as exchange:
            with self.assertRaises(urllib.error.URLError):
                poster.execute({'comfy_url':'http://localhost:8191','render_timeout_seconds':60},{},'4',Path(folder)/'poster.png')
        self.assertEqual(exchange.call_count,1)

    def test_read_retries_are_bounded_and_nonretryable_errors_fail_immediately(self):
        for code,expected in ((503,3),(429,3),(403,1),(404,1)):
            with self.subTest(code=code),patch.object(poster,'http',side_effect=urllib.error.HTTPError('http://localhost',code,'error',{},None)) as exchange,patch.object(poster.time,'sleep'):
                with self.assertRaises(urllib.error.HTTPError):poster.comfy_get('http://localhost/history/one',poster.time.monotonic()+60)
                self.assertEqual(exchange.call_count,expected)

    def test_expired_budget_never_starts_a_new_network_read(self):
        with patch.object(poster,'http') as exchange:
            with self.assertRaises(TimeoutError):poster.comfy_get('http://localhost/history/one',poster.time.monotonic()-1)
        exchange.assert_not_called()


if __name__=='__main__':unittest.main()
