"""The suggest endpoint (suggest.py, and its routes in video_api.py): id/span
validation, caps, the no-model and too-short-note no-ops, and that usage is
recorded per account -- against a fake OpenAI-compatible endpoint, never the
real network."""
import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

import tests.fixtures as fixtures
from tests.fake_suggest import FakeSuggest
from tests.test_project import TempProject
from videobuilder.editor import Editor, make_handler

VIDEO = 'promo/film'


class Server(TempProject):
    def setUp(self):
        super().setUp()
        self.start()

    def start(self, **kw):
        self.editor = Editor(self.root, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.editor))
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            body = r.read()
            return json.loads(body) if r.headers.get('Content-Type', '').startswith('application/json') else body

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())


class NoModel(Server):
    def test_config_says_false(self):
        self.assertEqual(self.get('/api/suggest/config'), {'model': False})

    def test_ask_404s(self):
        status, _ = self.post('/api/suggest', {'video': VIDEO, 'text': 'make it look like a comic',
                                                'surface': 'editor', 'seq': 1})
        self.assertEqual(status, 404)

    def test_catalog_and_fonts_and_sfx_still_work_with_no_model(self):
        catalog = self.get('/api/suggest/catalog')
        self.assertIn('looks', catalog)
        self.assertEqual(len(catalog['fonts']), 9)
        self.assertTrue(catalog['sfx'])
        self.assertTrue(len(self.get('/api/fonts/inter/file')) > 0)


class Base(Server):
    def setUp(self):
        self.fake = FakeSuggest()
        self.addCleanup(self.fake.close)
        super().setUp()

    def start(self, **kw):
        kw.setdefault('suggest_url', self.fake.base)
        patcher = mock.patch.dict(os.environ, {'VIDEOBUILDER_SUGGEST_KEY': 'test-key'})
        patcher.start()
        self.addCleanup(patcher.stop)
        super().start(**kw)

    def ask(self, text='Make the intro look like a comic, and add a whoosh', surface='editor', seq=1, **extra):
        return self.post('/api/suggest', {'video': VIDEO, 'text': text, 'surface': surface, 'seq': seq, **extra})


class Config(Base):
    def test_config_says_true(self):
        self.assertEqual(self.get('/api/suggest/config'), {'model': True})


class Ask(Base):
    def test_valid_items_pass_through(self):
        self.fake.answer = {'items': [
            {'id': 'look-pop-art', 'family': 'looks', 'strength': 'strong', 'why': 'a comic look',
             'replace': {'span': 'look like a comic', 'text': 'look like a comic, in the Pop-art halftone look'}},
        ]}
        status, data = self.ask()
        self.assertEqual(status, 200)
        self.assertEqual(data['seq'], 1)
        [item] = data['items']
        self.assertEqual(item['id'], 'look-pop-art')
        self.assertEqual(item['strength'], 'strong')
        self.assertEqual(item['replace']['text'], 'look like a comic, in the Pop-art halftone look')

    def test_unknown_id_dropped(self):
        self.fake.answer = {'items': [{'id': 'not-a-real-capability', 'family': 'looks', 'strength': 'strong',
                                       'why': 'x', 'replace': None}]}
        _, data = self.ask()
        self.assertEqual(data['items'], [])

    def test_unknown_family_dropped(self):
        self.fake.answer = {'items': [{'id': 'look-pop-art', 'family': 'not-a-family', 'strength': 'strong',
                                       'why': 'x', 'replace': None}]}
        _, data = self.ask()
        self.assertEqual(data['items'], [])

    def test_span_not_in_text_is_dropped(self):
        self.fake.answer = {'items': [{'id': 'look-pop-art', 'family': 'looks', 'strength': 'strong', 'why': 'x',
                                       'replace': {'span': 'not in the note', 'text': 'rewritten'}}]}
        _, data = self.ask()
        self.assertIsNone(data['items'][0]['replace'])

    def test_fonts_sfx_and_capabilities_validate_against_real_lists(self):
        self.fake.answer = {'items': [
            {'id': 'cantarell', 'family': 'fonts', 'strength': 'related', 'why': 'friendlier', 'replace': None},
            {'id': 'whoosh_fast/tight', 'family': 'sfx', 'strength': 'related', 'why': 'a whoosh', 'replace': None},
            {'id': 'not-a-font', 'family': 'fonts', 'strength': 'related', 'why': 'x', 'replace': None},
            {'id': 'not-a-sound', 'family': 'sfx', 'strength': 'related', 'why': 'x', 'replace': None},
        ]}
        _, data = self.ask()
        ids = {i['id'] for i in data['items']}
        self.assertEqual(ids, {'cantarell', 'whoosh_fast/tight'})

    def test_caps_strong_and_related(self):
        items = [{'id': f'look-{name}', 'family': 'looks', 'strength': 'strong', 'why': 'x', 'replace': None}
                 for name in ('pop-art', 'pixel', 'bauhaus', 'melt', 'swirl', 'woodblock', 'blueprint')]
        items += [{'id': f'look-filter-{name}', 'family': 'looks', 'strength': 'related', 'why': 'x',
                  'replace': None} for name in ('pop-art', 'pixel', 'woodblock', 'blueprint', 'pointillism')]
        items.append({'id': 'look-pointillism', 'family': 'looks', 'strength': 'related', 'why': 'x',
                     'replace': None})
        self.fake.answer = {'items': items}
        _, data = self.ask()
        strong = [i for i in data['items'] if i['strength'] == 'strong']
        related = [i for i in data['items'] if i['strength'] == 'related']
        self.assertEqual(len(strong), 5)
        self.assertEqual(len(related), 6)

    def test_too_short_note_skips_the_model_entirely(self):
        _, data = self.ask(text='fix typo')
        self.assertEqual(data['items'], [])
        self.assertEqual(self.fake.requests, [])

    def test_bad_surface_400s(self):
        status, _ = self.ask(surface='nope')
        self.assertEqual(status, 400)

    def test_repeat_ask_is_cached_not_re_requested(self):
        self.fake.answer = {'items': []}
        self.ask(seq=1)
        self.ask(seq=2)
        self.assertEqual(len(self.fake.requests), 1)

    def test_a_failing_endpoint_answers_no_items_not_an_error(self):
        self.fake.status = 500
        status, data = self.ask()
        self.assertEqual(status, 200)
        self.assertEqual(data['items'], [])

    def test_usage_recorded_per_account(self):
        self.ask()
        totals = self.editor.suggest.usage_totals()
        self.assertIn('anonymous', totals)
        self.assertEqual(totals['anonymous']['calls'], 1)
        self.assertEqual(totals['anonymous']['total_tokens'], 120)

    def test_key_not_in_response_or_usage_log(self):
        _, data = self.ask()
        self.assertNotIn('test-key', json.dumps(data))
        self.assertNotIn('test-key', self.editor.suggest.usage_path.read_text())


class LibraryWiring(fixtures.LibraryFixture, unittest.TestCase):
    """New video's "In a few words" has no project yet to scope a suggest
    call to (suggest.py's `video=None` path), and shares the one Suggest
    feature every project's Editor also uses (unlike Pictures/Artbox)."""

    def setUp(self):
        self.fake = FakeSuggest(answer={'items': []})
        self.addCleanup(self.fake.close)
        patcher = mock.patch.dict(os.environ, {'VIDEOBUILDER_SUGGEST_KEY': 'test-key'})
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def library_kwargs(self):
        return {'suggest_url': self.fake.base}

    def test_config_true_before_any_project_exists(self):
        status, data = self.request('/api/suggest/config')
        self.assertEqual((status, data), (200, {'model': True}))

    def test_new_video_ask_has_no_video_field(self):
        status, data = self.request('/api/suggest', {'text': 'a 30-second launch video, playful and upbeat',
                                                      'surface': 'new', 'seq': 7})
        self.assertEqual(status, 200)
        self.assertEqual(data, {'seq': 7, 'items': []})

    def test_usage_shared_between_new_video_and_a_project(self):
        self.seed('acme/launch', film=True)
        self.request('/api/suggest', {'text': 'a 30-second launch video, playful and upbeat',
                                      'surface': 'new', 'seq': 1})
        self.request('/v/acme/launch/api/suggest', {'video': 'promo/film', 'surface': 'editor', 'seq': 1,
                                                     'text': 'a 30-second launch video, playful and upbeat'})
        totals = self.library.suggest.usage_totals()
        self.assertEqual(totals['anonymous']['calls'], 2)


if __name__ == '__main__':
    unittest.main()
