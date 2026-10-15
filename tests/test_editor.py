"""The editor's HTTP API, on a temp project in a git repo."""
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from videobuilder.editor import Editor
from tests.fixtures import API
from tests.test_project import TempProject


class Command(unittest.TestCase):
    def test_a_missing_project_dir(self):
        from videobuilder.cli import main
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project'])
        self.assertIn('not a directory', str(e.exception))

    def test_account_daily_caps_are_refused_outside_library_mode(self):
        from videobuilder.cli import main
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project', '--account-daily-note-cap', '5'])
        self.assertIn('--account-daily-note-cap', str(e.exception))
        self.assertIn('--library mode', str(e.exception))
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project', '--account-daily-cost-cap-usd', '2.5'])
        self.assertIn('--account-daily-cost-cap-usd', str(e.exception))

    def test_account_daily_caps_must_be_positive(self):
        from videobuilder.cli import main
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-note-cap', '0'])
            self.assertIn('account_daily_note_cap', str(e.exception))
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-cost-cap-usd', '-1'])
            self.assertIn('account_daily_cost_cap_usd', str(e.exception))

    def test_account_daily_cost_cap_rejects_nan_and_infinity(self):
        from videobuilder.cli import main
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-cost-cap-usd', 'nan'])
            self.assertIn('account_daily_cost_cap_usd', str(e.exception))
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-cost-cap-usd', 'inf'])
            self.assertIn('account_daily_cost_cap_usd', str(e.exception))


class AccountCapConfigKeys(TempProject):
    def _editor(self, state_dir, **kw):
        editor = Editor(self.root, state_dir=state_dir, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def test_unset_by_default(self):
        editor = self._editor('state-defaults')
        self.assertIsNone(editor.account_daily_note_cap)
        self.assertIsNone(editor.account_daily_cost_cap_usd)

    def test_configured_in_videobuilder_toml(self):
        (self.root / 'videobuilder.toml').write_text(
            '[editor]\n'
            'account_daily_note_cap = 3\n'
            'account_daily_cost_cap_usd = 1.5\n')
        editor = self._editor('state-configured')
        self.assertEqual(editor.account_daily_note_cap, 3)
        self.assertEqual(editor.account_daily_cost_cap_usd, 1.5)

    def test_explicit_kwarg_overrides_the_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\naccount_daily_note_cap = 3\n')
        editor = self._editor('state-override', account_daily_note_cap=9)
        self.assertEqual(editor.account_daily_note_cap, 9)

    def test_rejects_a_non_positive_cap(self):
        with self.assertRaisesRegex(ValueError, 'account_daily_note_cap'):
            self._editor('state-bad-note-cap', account_daily_note_cap=0)
        with self.assertRaisesRegex(ValueError, 'account_daily_cost_cap_usd'):
            self._editor('state-bad-cost-cap', account_daily_cost_cap_usd=-1)


class CompendiumForBuilderConfigKey(TempProject):
    def _editor(self, state_dir, **kw):
        editor = Editor(self.root, state_dir=state_dir, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def test_defaults_to_true(self):
        self.assertIs(self._editor('state-defaults').compendium_for_builder, True)

    def test_configured_in_videobuilder_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\ncompendium_for_builder = false\n')
        self.assertIs(self._editor('state-configured').compendium_for_builder, False)

    def test_explicit_kwarg_overrides_the_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\ncompendium_for_builder = false\n')
        editor = self._editor('state-override', compendium_for_builder=True)
        self.assertIs(editor.compendium_for_builder, True)

    def test_a_non_bool_value_is_a_clear_config_error(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\ncompendium_for_builder = "yes"\n')
        with self.assertRaisesRegex(ValueError, 'compendium_for_builder'):
            self._editor('state-bad')

    def test_votes_for_the_builder_come_from_this_editors_own_store_in_single_project_mode(self):
        editor = self._editor('state-votes')
        editor.compendium_votes.record('owner', 'a', 'up', None)
        editor.compendium_votes.record('owner', 'b', 'down', None)
        editor.compendium_votes.record('owner', 'c', None, None)  # reset: never surfaced
        self.assertEqual(editor._compendium_votes_for_builder(), {'a': 'up', 'b': 'down'})

    def test_votes_for_the_builder_come_from_the_library_store_once_library_hosted(self):
        editor = self._editor('state-votes-library')
        editor.compendium_votes.record('owner', 'a', 'up', None)  # this project's own store: ignored once hosted

        class FakeVotes:
            def current(self):
                return {'z': {'vote': 'down', 'reason': None}}

        class FakeLibrary:
            compendium_votes = FakeVotes()
        editor.library = FakeLibrary()
        self.assertEqual(editor._compendium_votes_for_builder(), {'z': 'down'})

    def test_a_stale_vote_is_left_out_of_the_builders_lists(self):
        """A vote cast against a fingerprint the entry no longer has doesn't
        count: `current()` reports it with `vote: None` (see
        CompendiumVotes._view), which this method's own "up"/"down" filter
        already excludes."""
        editor = self._editor('state-votes-stale')
        with mock.patch('videobuilder.compendium.fingerprint', return_value='oldoldoldold'):
            editor.compendium_votes.record('owner', 'a', 'up', None)
        with mock.patch('videobuilder.compendium.fingerprint', return_value='newnewnewnew'):
            self.assertEqual(editor._compendium_votes_for_builder(), {})

    def test_a_legacy_vote_with_no_fingerprint_still_counts_for_the_builder(self):
        editor = self._editor('state-votes-legacy')
        path = editor.compendium_votes.path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps({'at': '2026-01-01T00:00:00Z', 'by': 'owner', 'id': 'a',
                                 'vote': 'up', 'reason': None, 'version': '0.1.0'}) + '\n')
        self.assertEqual(editor._compendium_votes_for_builder(), {'a': 'up'})


PKG = Path(__file__).resolve().parents[1] / 'videobuilder'


class DirectorPageRoutes(API):
    def test_director_source_line_length(self):
        for name in ('director.js', 'director.css'):
            path = PKG / name
            long_lines = [number for number, line in enumerate(path.read_text().splitlines(), 1)
                          if len(line) > 120]
            self.assertEqual(long_lines, [], f'{path}: lines over 120 characters')

    def test_director_assets_and_api_contract(self):
        import re
        for path, content_type, marker in (
            ('/', 'text/html', b'id="player"'),
            ('/tuning.html', 'text/html', b'id="tl"'),
            ('/director.js', 'text/javascript', b"json('versions'"),
            ('/director.css', 'text/css', b'.panel')):
            with urllib.request.urlopen(self.base + path, timeout=20) as response:
                self.assertEqual(response.headers.get_content_type(), content_type)
                self.assertIn(marker, response.read())
        js = (PKG / 'director.js').read_text()
        tuning = (PKG / 'tuning.html').read_text()
        paths = set(re.findall(r"(?:api|json|postJSON|getJSON)\('([a-z][a-z/-]*)'", js+tuning))
        expected = {'project','name','info','frame','video','notes','versions','versions/restore',
                    'attachments','video/retry','roll','copy','undo','draft','draft/info','draft/frame',
                    'draft/accept','draft/drop','upgrade','access','music/sources','music/tracks','music/attach',
                    'videos/first-note'}
        # Dynamic attachment and draft actions have their own router patterns.
        self.assertTrue(paths - {'attachments/', 'draft/'} <= expected, paths - expected)
        # The route literals live wherever make_handler's pieces do now, not all in editor.py.
        router = ''.join((PKG / name).read_text() for name in
                         ('editor.py', 'handler_library.py', 'video_api.py'))
        for path in paths - {'attachments/', 'draft/'}:
            self.assertIn("'/api/" + path + "'", router, path)
        self.assertIn("api('attachments/'", js)
        self.assertIn("api('video'", js)

    def test_signed_out_handling_pins_resume_probe_banner_and_draft_order(self):
        # A session can expire while the director tab sits open: the 401 handler
        # must show the banner, stop polling, keep whatever was typed, and the
        # resume check (on regaining focus) must hit a route that actually
        # exists under /v/<name>/api/ -- 'project', not the top-level-only 'name'.
        import re
        js = (PKG / 'director.js').read_text()
        resume = re.search(r'async function resumeFromSignedOut\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertIn("json('project')", resume)
        self.assertNotIn("json('name')", resume)
        self.assertIn("$('signed-out-banner').hidden=false", js)
        self.assertIn("$('signed-out-banner').hidden=true", js)
        for guard in ("state.video&&!state.signedOut", "document.hidden||state.signedOut",
                      "document.hidden||!state.project||state.signedOut"):
            self.assertIn(guard, js)
        send_pending = re.search(r'async function sendPending\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertLess(send_pending.index("await json('notes'"), send_pending.index('state.pending=[]'),
                         'the pending draft must only be cleared after the send succeeds')
        send_now = re.search(r'async function sendNow\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertLess(send_now.index("await json('notes'"), send_now.index("$('message').value=''"),
                         'the typed note must only be cleared after the send succeeds')

    def test_fine_tuning_edit_endpoints(self):
        self.assertIn(b'id="pane-copy"', self.get('/tuning.html'))
        video = 'promo/film'
        self.assertEqual(self.post('/api/roll', {'video': video, 'segment': 'intro', 'until': 6})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['cuts'][1], 90)
        self.assertEqual(self.post('/api/copy', {'video': video, 'segment': 'intro', 'key': 'title', 'value': 'New'})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['segments'][0]['copy']['title'], 'New')
        self.assertEqual(self.post('/api/undo', {'video': video})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['segments'][0]['copy']['title'], 'Hello')


class ServerErrors(API):
    """An unhandled exception must never put its traceback (or any other internal
    detail) in the response a guest sees; the operator still gets it, in the log."""
    LEAK = '/nonexistent/secret-path/traceback-marker'

    def test_unhandled_exception_on_an_api_route_hides_internals(self):
        with mock.patch.object(self.editor, 'info', side_effect=RuntimeError(self.LEAK)), \
             mock.patch('sys.stderr', new_callable=io.StringIO) as err:
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.get('/api/info?video=promo/film')
            with e.exception:
                self.assertEqual(e.exception.code, 500)
                self.assertEqual(e.exception.headers.get_content_type(), 'application/json')
                body = e.exception.read()
            log = err.getvalue()
        self.assertEqual(json.loads(body), {'error': 'internal error'})
        self.assertNotIn(self.LEAK.encode(), body)
        self.assertNotIn(b'Traceback', body)
        self.assertIn(self.LEAK, log)
        self.assertIn('Traceback', log)

    def test_unhandled_exception_on_a_page_route_is_a_plain_html_error(self):
        with mock.patch('videobuilder.video_api._page', side_effect=RuntimeError(self.LEAK)), \
             mock.patch('sys.stderr', new_callable=io.StringIO) as err:
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(self.base + '/', timeout=20)
            with e.exception:
                self.assertEqual(e.exception.code, 500)
                self.assertEqual(e.exception.headers.get_content_type(), 'text/html')
                body = e.exception.read()
            log = err.getvalue()
        self.assertNotIn(self.LEAK.encode(), body)
        self.assertNotIn(b'Traceback', body)
        self.assertIn(self.LEAK, log)
        self.assertIn('Traceback', log)


class _MusicServer:
    """A local http.server answering fixed GETs by path, so route tests never touch
    the network. `routes` maps a path to (bytes, content_type)."""

    def __init__(self, routes):
        self.routes = routes
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hit = outer.routes.get(self.path)
                if hit is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                data, content_type = hit
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *a):
                pass
        self.httpd = HTTPServer(('127.0.0.1', 0), Handler)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Music(API):
    """GET api/music/sources, api/music/tracks and POST api/music/attach."""

    TRACK_MP3 = b'ID3' + b'\x00' * 7 + b'fake mp3 bytes for the test'

    def _configure(self):
        self.server = _MusicServer({'/track.mp3': (self.TRACK_MP3, 'audio/mpeg')})
        self.addCleanup(self.server.close)
        track = {'id': 'calm-1', 'title': 'Calm Piano', 'audio_url': self.server.base + '/track.mp3',
                'tags': ['calm', 'piano'], 'duration': 61}
        self.server.routes['/tracks.json'] = (json.dumps({'tracks': [track]}).encode(), 'application/json')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, 'music.toml')
        path.write_text(f'''
            [[sources]]
            id = "calm"
            name = "Calm Library"
            license = "CC BY-NC 4.0"
            url = "{self.server.base}/tracks.json"
            [sources.fields]
            tracks = "tracks"
            id = "id"
            title = "title"
            audio_url = "audio_url"
            tags = "tags"
            duration = "duration"
        ''')
        self.start(music_sources=str(path))

    def test_no_sources_configured(self):
        self.assertEqual(self.get('/api/music/sources'), [])
        self.assertEqual(self.post('/api/music/attach', {'video': 'promo/film', 'source': 'x', 'track': 'y'})[0], 404)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/api/music/tracks?source=x')
        e.exception.close()
        self.assertEqual(e.exception.code, 404)
        with urllib.request.urlopen(self.base + '/', timeout=20) as response:
            html = response.read()
        self.assertIn(b'id="music-button"', html)
        self.assertIn(b'hidden', html.split(b'id="music-button"', 1)[1].split(b'>', 1)[0])
        js = (PKG / 'director.js').read_text()
        self.assertIn("$('music-button').hidden=!state.musicSources.length", js)

    def test_sources_and_tracks_listing(self):
        self._configure()
        self.assertEqual(self.get('/api/music/sources'),
                         [{'id': 'calm', 'name': 'Calm Library', 'license': 'CC BY-NC 4.0'}])
        data = self.get('/api/music/tracks?source=calm')
        self.assertEqual(data['source'], {'id': 'calm', 'name': 'Calm Library', 'license': 'CC BY-NC 4.0'})
        self.assertEqual(data['tracks'], [{'id': 'calm-1', 'title': 'Calm Piano', 'tags': ['calm', 'piano'],
                                           'duration': 61.0, 'audio_url': self.server.base + '/track.mp3'}])
        self.assertEqual(self._status('/api/music/tracks?source=nope'), 404)

    def _status(self, path):
        try:
            self.get(path)
            return 200
        except urllib.error.HTTPError as e:
            with e:
                return e.code

    def test_attach_stores_the_right_name_type_and_upload_shaped_record(self):
        self._configure()
        code, record = self.post('/api/music/attach', {'video': 'promo/film', 'source': 'calm', 'track': 'calm-1'})
        self.assertEqual(code, 201, record)
        self.assertEqual((record['name'], record['type']), ('Calm_Piano.mp3', 'audio/mpeg'))
        self.assertEqual(record['size'], len(self.TRACK_MP3))
        self.assertEqual(set(record), {'id', 'name', 'type', 'size'})
        stored = self.get('/api/attachments/' + record['id'])
        self.assertEqual(stored, self.TRACK_MP3)

    def test_attach_unknown_source_or_track_is_404(self):
        self._configure()
        self.assertEqual(self.post('/api/music/attach',
                                   {'video': 'promo/film', 'source': 'nope', 'track': 'calm-1'})[0], 404)
        self.assertEqual(self.post('/api/music/attach',
                                   {'video': 'promo/film', 'source': 'calm', 'track': 'nope'})[0], 404)

    def test_attach_never_fetches_a_url_from_the_request_body(self):
        self._configure()
        # A non-routable test address: if the server fetched this instead of the
        # track's own cached audio_url, the request would hang or fail.
        code, record = self.post('/api/music/attach', {
            'video': 'promo/film', 'source': 'calm', 'track': 'calm-1',
            'url': 'http://192.0.2.1/evil.mp3', 'audio_url': 'http://192.0.2.1/evil.mp3',
        })
        self.assertEqual(code, 201, record)
        self.assertEqual(self.get('/api/attachments/' + record['id']), self.TRACK_MP3)

    def test_attach_over_size_limit_is_refused(self):
        self._configure()
        self.editor.attachments.max_file = len(self.TRACK_MP3) - 1
        code, result = self.post('/api/music/attach', {'video': 'promo/film', 'source': 'calm', 'track': 'calm-1'})
        self.assertEqual(code, 413, result)


if __name__ == '__main__':
    unittest.main()
