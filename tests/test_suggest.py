"""The suggest endpoint (suggest.py, and its routes in video_api.py): id/span
validation, caps, the no-model and too-short-note no-ops, and that usage is
recorded per account -- against a fake OpenAI-compatible endpoint, never the
real network."""
import http.client
import json
import os
import socket
import tempfile
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
from videobuilder.handler_base import watch_disconnect
from videobuilder.suggest import CATALOG_TTL, Suggest
from videobuilder.suggest_index import BM25

VIDEO = 'promo/film'


class WatchDisconnect(unittest.TestCase):
    """watch_disconnect (handler_base.py) is the piece _post_suggest and the
    library's /api/suggest route use to notice the browser's own connection
    closing while they block on the model call -- tested here against a
    plain socket pair, without any HTTP or model endpoint involved."""

    def test_sets_the_event_when_the_peer_closes(self):
        server_sock, client_sock = socket.socketpair()
        self.addCleanup(server_sock.close)
        cancel_event = threading.Event()
        stop = watch_disconnect(server_sock, cancel_event, interval=0.05)
        try:
            self.assertFalse(cancel_event.wait(timeout=0.3))
            client_sock.close()
            self.assertTrue(cancel_event.wait(timeout=2))
        finally:
            stop()

    def test_stop_function_ends_the_watcher_without_setting_the_event(self):
        server_sock, client_sock = socket.socketpair()
        self.addCleanup(server_sock.close)
        self.addCleanup(client_sock.close)
        cancel_event = threading.Event()
        stop = watch_disconnect(server_sock, cancel_event, interval=0.05)
        stop()
        time.sleep(0.3)
        self.assertFalse(cancel_event.is_set())


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

    def test_catalog_merges_registry_entries_into_capabilities(self):
        catalog = self.get('/api/suggest/catalog')
        by_id = {c['id']: c for c in catalog['capabilities']}
        self.assertIn('ease-out-back', by_id)  # a videobuilder.techniques id
        entry = by_id['ease-out-back']
        self.assertEqual(entry['poster'], '/capabilities/techniques/ease-out-back.jpg')
        self.assertEqual(entry['clip'], '/capabilities/techniques/ease-out-back.mp4')
        self.assertEqual(entry['category'], 'Animation principles')
        self.assertEqual(entry['group'], 'Easing')
        self.assertIn('back out', entry['aliases'])
        self.assertIn('arrives with a small overshoot', entry['phrasings'])
        for leaked in ('api', 'related', 'family'):
            self.assertNotIn(leaked, entry)
        curated = by_id['seamless-loops']  # a hand-written entry: no group/aliases/phrasings
        self.assertNotIn('group', curated)
        self.assertNotIn('aliases', curated)

    def test_no_capability_group_says_technique_a_director_never_sees_that_word(self):
        catalog = self.get('/api/suggest/catalog')
        groups = {c['group'] for c in catalog['capabilities'] if c.get('group')}
        self.assertTrue(groups)
        self.assertFalse([g for g in groups if 'technique' in g.lower()])
        self.assertIn('delay', [c['id'] for c in catalog['capabilities'] if c.get('group') == 'Principle details'])


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

    def test_usage_shows_up_in_the_admin_usage_endpoint(self):
        # GET /api/usage is where an admin already looks for usage (notes' cost_usd);
        # suggest's own totals must land there too, not just in a log nothing reads.
        self.ask()
        usage = self.get('/api/usage')
        self.assertIn('anonymous', usage['suggest'])
        self.assertEqual(usage['suggest']['anonymous']['calls'], 1)
        self.assertEqual(usage['suggest']['anonymous']['total_tokens'], 120)

    def test_key_not_in_response_or_usage_log(self):
        _, data = self.ask()
        self.assertNotIn('test-key', json.dumps(data))
        self.assertNotIn('test-key', self.editor.suggest.usage_path.read_text())

    def test_client_disconnect_cancels_the_upstream_call(self):
        # The fake endpoint's stall (1.5s) is comfortably under SuggestClient's own
        # timeout (8s default): without the server itself watching the browser's
        # connection, nothing would cancel this call before it completes normally
        # and records usage -- which is exactly what the assertion below would see.
        self.fake.stall = 1.5
        body = json.dumps({'video': VIDEO, 'text': 'Make the intro look like a comic, and add a whoosh',
                           'surface': 'editor', 'seq': 1}).encode()
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1], timeout=20)
        conn.request('POST', '/api/suggest', body=body, headers={'Content-Type': 'application/json'})
        time.sleep(0.2)  # give the server time to dispatch and start the stalled upstream call
        conn.close()
        time.sleep(self.fake.stall + 1)  # past the stall: a completed call would have recorded usage by now
        self.assertEqual(self.editor.suggest.usage_totals(), {})


class CatalogCaching(unittest.TestCase):
    """The static block and the per-note retrieval indices are built
    together and share one cache, rebuilt on CATALOG_TTL's own schedule --
    against mocks, so this never pays the real catalog's build cost."""

    def test_rebuilt_once_within_ttl_then_again_once_stale(self):
        empty = BM25([])
        with tempfile.TemporaryDirectory() as d, \
             mock.patch('videobuilder.suggest._build_static_block', return_value='TEXT') as build_text, \
             mock.patch('videobuilder.suggest._build_indices',
                        return_value=(empty, empty, empty, {})) as build_indices:
            s = Suggest(d, mock.Mock())
            s._static_block()
            s._static_block()
            self.assertEqual((build_text.call_count, build_indices.call_count), (1, 1))
            # force staleness without waiting CATALOG_TTL seconds for real
            s._catalog = s._catalog[:-1] + (s._catalog[-1] - CATALOG_TTL - 1,)
            s._static_block()
            self.assertEqual((build_text.call_count, build_indices.call_count), (2, 2))


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
        _, usage = self.request('/api/usage')
        self.assertEqual(usage['suggest']['anonymous']['calls'], 2)

    def test_two_projects_with_the_same_video_name_do_not_share_an_answer(self):
        # Every project's Editor shares this one Suggest (and its answer cache), and
        # `video` in the cache key is just the bare in-project name -- so two projects
        # with the same video name and the same note must not collide and serve one
        # project's (bible-derived) answer to the other.
        self.seed('acme/one', film=True)
        self.seed('acme/two', film=True)
        text = 'a 30-second launch video, playful and upbeat'
        status1, _ = self.request('/v/acme/one/api/suggest', {'video': 'promo/film', 'surface': 'editor',
                                                               'seq': 1, 'text': text})
        status2, _ = self.request('/v/acme/two/api/suggest', {'video': 'promo/film', 'surface': 'editor',
                                                               'seq': 1, 'text': text})
        self.assertEqual((status1, status2), (200, 200))
        self.assertEqual(len(self.fake.requests), 2)


if __name__ == '__main__':
    unittest.main()
