"""The suggest model client (suggest_client.py), against a fake OpenAI-compatible
endpoint on a local port: request shape, timeout, cancellation, and that the
key never appears in an error."""
import json
import threading
import time
import unittest

from tests.fake_suggest import FakeSuggest
from videobuilder.suggest_client import (DEFAULT_MODEL, SuggestCancelled, SuggestClient, SuggestError,
                                         check_suggest_url)


class CheckUrl(unittest.TestCase):
    def test_plain_http_and_https_ok(self):
        self.assertEqual(check_suggest_url('http://example.com:8000/'), 'http://example.com:8000')
        self.assertEqual(check_suggest_url('https://openrouter.ai/api/v1'), 'https://openrouter.ai/api/v1')

    def test_rejects_credentials_query_fragment_and_non_http(self):
        for bad in ('ftp://example.com', 'https://user:pass@example.com', 'https://example.com/?x=1',
                    'https://example.com/#frag', 'not a url', 42):
            with self.assertRaises(ValueError):
                check_suggest_url(bad)


class Client(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSuggest(answer={'items': [{'id': 'look-pop-art', 'family': 'looks'}]})
        self.addCleanup(self.fake.close)
        self.client = SuggestClient(self.fake.base, model='a-model', key='top-secret-key')

    def test_request_shape(self):
        answer, usage = self.client.complete('static block', 'video block', 'make it pop art')
        self.assertEqual(answer, {'items': [{'id': 'look-pop-art', 'family': 'looks'}]})
        self.assertEqual(usage['total_tokens'], 120)
        [req] = self.fake.requests
        self.assertEqual(req['path'], '/v1/chat/completions')
        self.assertEqual(req['headers']['Authorization'], 'Bearer top-secret-key')
        body = req['body']
        self.assertEqual(body['model'], 'a-model')
        self.assertEqual(body['temperature'], 0)
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        roles = [m['role'] for m in body['messages']]
        self.assertEqual(roles, ['system', 'system', 'user'])
        self.assertEqual(body['messages'][0]['content'][0]['text'], 'static block')
        self.assertEqual(body['messages'][0]['content'][0]['cache_control'], {'type': 'ephemeral'})
        self.assertEqual(body['messages'][1]['content'], 'video block')
        self.assertEqual(body['messages'][2]['content'], 'make it pop art')

    def test_default_model(self):
        client = SuggestClient(self.fake.base, key='k')
        self.assertEqual(client.model, DEFAULT_MODEL)
        client.complete('s', 'v', 'u')
        self.assertEqual(self.fake.requests[0]['body']['model'], DEFAULT_MODEL)

    def test_no_key_means_no_authorization_header(self):
        SuggestClient(self.fake.base).complete('s', 'v', 'u')
        self.assertNotIn('Authorization', self.fake.requests[0]['headers'])

    def test_http_error_status(self):
        self.fake.status = 500
        with self.assertRaises(SuggestError):
            self.client.complete('s', 'v', 'u')

    def test_http_error_carries_the_endpoint_reason(self):
        self.fake.status = 400
        self.fake.raw_body = b'{"error":{"message":"bad model id"}}'
        with self.assertRaisesRegex(SuggestError, 'HTTP 400.*bad model id'):
            self.client.complete('s', 'v', 'u')

    def test_answer_in_a_code_fence(self):
        content = '```json\n{"items": [{"id": "x"}]}\n```'
        self.fake.raw_body = json.dumps({'choices': [{'message': {'content': content}}]}).encode()
        answer, _ = self.client.complete('s', 'v', 'u')
        self.assertEqual(answer, {'items': [{'id': 'x'}]})

    def test_unusable_answer(self):
        self.fake.raw_body = b'not json at all'
        with self.assertRaises(SuggestError):
            self.client.complete('s', 'v', 'u')

    def test_timeout_gives_up(self):
        self.fake.stall = 10
        client = SuggestClient(self.fake.base, key='k', timeout=0.3)
        start = time.monotonic()
        with self.assertRaises(SuggestError):
            client.complete('s', 'v', 'u')
        self.assertLess(time.monotonic() - start, 5)

    def test_key_never_in_error_message(self):
        self.fake.status = 500
        client = SuggestClient(self.fake.base, key='super-secret-123')
        try:
            client.complete('s', 'v', 'u')
            self.fail('expected SuggestError')
        except SuggestError as exc:
            self.assertNotIn('super-secret-123', str(exc))

    def test_cancel_event_stops_the_call_quickly(self):
        self.fake.stall = 30
        client = SuggestClient(self.fake.base, key='k', timeout=20)
        cancel = threading.Event()
        result = {}

        def run():
            try:
                client.complete('s', 'v', 'u', cancel_event=cancel)
            except SuggestCancelled:
                result['cancelled'] = True
            except SuggestError as exc:
                result['error'] = exc

        t = threading.Thread(target=run)
        start = time.monotonic()
        t.start()
        time.sleep(0.2)
        cancel.set()
        t.join(timeout=5)
        self.assertFalse(t.is_alive())
        self.assertLess(time.monotonic() - start, 5)
        self.assertTrue(result.get('cancelled') or result.get('error'), result)


if __name__ == '__main__':
    unittest.main()
