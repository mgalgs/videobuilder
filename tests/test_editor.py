"""The editor's HTTP API, on a temp project in a git repo."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

from videobuilder.editor import Editor, Forbidden, make_handler

from tests.test_project import FILM, TempProject, git


class API(TempProject):
    def tearDown(self):
        self.editor.renders.close()
        super().tearDown()

    def start(self, **kw):
        hook = kw.pop('hook', None)
        self.editor = Editor(self.root, poll=0, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)
        handler = make_handler(self.editor, hook) if hook else make_handler(self.editor)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def setUp(self):
        super().setUp()
        self.start()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            body = r.read()
            return json.loads(body) if r.headers.get('Content-Type') == 'application/json' else body

    def post(self, path, body, headers=None):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(), method='POST',
                                     headers=headers or {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_healthz_ignores_host_allowlist(self):
        req = urllib.request.Request(self.base + '/healthz', headers={'Host': 'kubelet.invalid'})
        with urllib.request.urlopen(req) as response:
            from videobuilder import __version__
            self.assertEqual((response.status, response.read()), (200, b'ok ' + __version__.encode()))

    def test_page_and_project(self):
        page = self.get('/')
        self.assertIn(b'videobuilder editor', page)
        self.assertNotIn(b'http://', page.replace(b'http://www.w3.org', b''))  # nothing from a CDN
        p = self.get('/api/project')
        self.assertEqual((p['name'], p['git'], p['backend'], p['error']), ('project', True, 'null', None))
        self.assertEqual(p['videos'], [{'id': 'promo/film', 'path': 'promo/film.py',
                                        'edits': 'promo/film.edits.toml', 'pin': "editor's own",
                                        'env': 'ready', 'error': None, 'upgrade': None}])
        self.assertEqual(p['state_dir'], str(self.root / '.vb-editor'))
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')  # the state dir ignores itself

    def test_info_and_frame(self):
        info = self.get('/api/info?video=promo/film')
        self.assertEqual((info['video'], info['edits_file'], info['git'], info['undo'], info['error']),
                         ('promo/film', 'promo/film.edits.toml', {'repo': True, 'state': 'clean'}, None, None))
        self.assertEqual([(s['name'], s['rollable'], s['copy']) for s in info['timeline']['segments']],
                         [('intro', True, {'title': 'Hello'}), ('body', False, {'line': 'Body copy'}),
                          ('c1', True, {}), ('c2', False, {}), ('close', False, {})])
        self.assertEqual(info['timeline']['groups'][0]['copy'], {'head': 'Cuts'})
        png = self.get('/api/frame?video=promo/film&frame=10&format=1x1&scale=0.25')
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual((int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')), (270, 270))
        for path, code in (('/api/info?video=nope', 404), ('/api/info', 400), ('/api/nothing', 404),
                           ('/api/frame?video=promo/film&format=4x3', 400)):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as e:
                self.get(path)
            e.exception.close()
            self.assertEqual(e.exception.code, code)

    def test_roll_copy_refusal_and_undo(self):
        code, r = self.post('/api/roll', {'video': 'promo/film', 'segment': 'intro', 'until': 6})
        self.assertEqual(code, 200, r)
        self.assertEqual(r['message'], 'edit(promo/film): roll intro to beat 6')
        self.assertEqual(r['commit'], git(self.root, 'rev-parse', 'HEAD').strip())
        info = self.get('/api/info?video=promo/film')
        self.assertEqual(info['timeline']['cuts'][1], 90)  # reloaded at once
        self.assertEqual(info['undo'], {'op': 'roll', 'segment': 'intro', 'value': 4})
        self.assertEqual(info['edits']['segments'], {'intro': {'until': 6}})

        code, r = self.post('/api/roll', {'video': 'promo/film', 'segment': 'intro', 'until': 6.25})
        self.assertEqual((code, r), (400, {'error': 'segment intro: until 6.25 is off the half-beat grid'}))
        code, r = self.post('/api/copy', {'video': 'promo/film', 'segment': 'cuts', 'key': 'head', 'value': 'Quick'})
        self.assertEqual((code, r['message']), (200, 'edit(promo/film): copy cuts.head'))
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['groups'][0]['copy'], {'head': 'Quick'})
        code, r = self.post('/api/undo', {'video': 'promo/film'})
        self.assertEqual((code, r['message'], r['undo']), (200, 'edit(promo/film): copy cuts.head (undo)', None))
        self.assertEqual(self.log(), ['edit(promo/film): copy cuts.head (undo)', 'edit(promo/film): copy cuts.head',
                                      'edit(promo/film): roll intro to beat 6', 'init'])
        self.assertEqual(self.post('/api/undo', {'video': 'promo/film'}), (400, {'error': 'nothing to undo'}))
        for body in ({'video': 'promo/film', 'segment': 'intro'}, {'video': 'promo/film', 'segment': 'intro', 'until': 'x'},
                     {'segment': 'intro', 'until': 5}):
            with self.subTest(body=body):
                self.assertEqual(self.post('/api/roll', body)[0], 400)
        self.assertEqual(self.post('/api/roll', {'video': 'nope', 'segment': 'intro', 'until': 5})[0], 404)

    def test_posts_must_be_json_from_this_origin(self):
        body = {'video': 'promo/film', 'segment': 'intro', 'until': 6}
        self.assertEqual(self.post('/api/roll', body, {'Content-Type': 'text/plain'})[0], 415)
        code, r = self.post('/api/roll', body, {'Content-Type': 'application/json', 'Origin': 'http://elsewhere.example'})
        self.assertEqual((code, r['error']), (403, 'cross-origin request refused'))
        same = self.base.removeprefix('http://')
        self.assertEqual(self.post('/api/roll', body, {'Content-Type': 'application/json',
                                                       'Origin': f'http://{same}'})[0], 200)
        self.assertEqual(self.log(), ['edit(promo/film): roll intro to beat 6', 'init'])

    def test_notes(self):
        code, n = self.post('/api/notes', {'video': 'promo/film', 'format': '1x1', 'frame': 70, 'text': 'Too fast'})
        self.assertEqual(code, 200, n)
        self.assertEqual((n['video'], n['format'], n['frame'], n['segment'], n['text'], n['state'], n['author']),
                         ('promo/film', '1x1', 70, 'body', 'Too fast', 'queued', 'anonymous'))
        png = self.get(f'/api/notes/{n["id"]}.png')
        self.assertEqual((int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')), (540, 540))
        self.assertTrue((self.root / '.vb-editor' / 'notes' / f'{n["id"]}.json').exists())
        self.assertEqual(self.get(f'/api/notes/{n["id"]}'), n)
        self.assertEqual([x['id'] for x in self.get('/api/notes?video=promo/film')['notes']], [n['id']])
        self.assertEqual(self.get('/api/notes?video=other')['notes'], [])
        code, d = self.post('/api/notes', {'video': 'promo/film', 'frame': 9999, 'text': 'the end'})
        self.assertEqual((d['frame'], d['format'], d['segment']), (209, '16x9', 'close'))  # clamped, default format
        self.assertEqual(self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': ''})[0], 400)
        self.assertEqual(self.post(f'/api/notes/{n["id"]}/delete', {}), (200, {'deleted': n['id']}))
        self.assertEqual(self.post(f'/api/notes/{n["id"]}/delete', {})[0], 404)
        self.assertEqual(len(self.get('/api/notes')['notes']), 1)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')  # notes stay out of git

    def test_state_dir_is_configurable(self):
        state = Path(self.tmp.name, 'elsewhere')
        self.start(state_dir=str(state))
        code, n = self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': 'hi'})
        self.assertTrue((state / 'notes' / f'{n["id"]}.png').exists())
        (self.root / 'videobuilder.toml').write_text('[editor]\nstate_dir = "review-state"\n')
        self.assertEqual(Editor(self.root).state_dir, str(self.root / 'review-state'))

    def test_the_request_hook(self):
        def hook(request):
            user = request.headers.get('X-Forwarded-User')
            if not user:
                raise Forbidden('who are you?')
            return user
        self.start(hook=hook)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/api/project')
        with e.exception:
            self.assertEqual((e.exception.code, json.loads(e.exception.read())), (403, {'error': 'who are you?'}))
        code, n = self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': 'hi'},
                            {'Content-Type': 'application/json', 'X-Forwarded-User': 'sam'})
        self.assertEqual((code, n['author']), (200, 'sam'))

    def test_a_broken_film_keeps_its_last_good_load_and_refuses_edits(self):
        self.assertIsNone(self.get('/api/info?video=promo/film')['error'])
        self.film.write_text(FILM + '\ndef broken(:\n')  # it stays listed while it doesn't parse
        info = self.get('/api/info?video=promo/film')
        self.assertIn('SyntaxError', info['error'])
        self.assertEqual(info['frames'], 210)  # the last good film, still on screen
        self.assertEqual(self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': 'hi'})[0], 200)
        code, r = self.post('/api/roll', {'video': 'promo/film', 'segment': 'intro', 'until': 6})
        self.assertEqual(code, 400)
        self.assertIn('SyntaxError', r['error'])
        self.assertEqual(self.log(), ['init'])


    def test_draft_endpoints(self):
        from videobuilder.agents import FakeBackend
        git(self.root, 'branch', '-M', 'main')
        self.editor.notes.backend = FakeBackend(delay=0)
        code, note = self.post('/api/notes', dict(video='promo/film', frame=0, text='Highlight'))
        self.assertEqual(code, 200)
        self.get('/api/notes')
        detail = self.get('/api/draft?video=promo/film')
        self.assertEqual(detail['files'], ['promo/film.py'])
        from unittest.mock import patch
        self.editor.unsandboxed_previews = True
        with patch('videobuilder.drafts.shutil.which', return_value=None):
            self.assertEqual(self.get('/api/draft/info?video=promo/film')['frames'], 210)
            self.assertTrue(self.get('/api/draft/frame?video=promo/film&scale=0.1').startswith(b'\x89PNG'))
        self.assertEqual(self.post('/api/draft/accept', dict(video='promo/film'))[1]['state'], 'accepted')
        self.assertEqual(self.get('/api/notes')["notes"][0]['state'], 'accepted')
        self.post('/api/notes', dict(video='promo/film', frame=0, text='Again'))
        self.get('/api/notes')
        self.assertEqual(self.post('/api/draft/drop', dict(video='promo/film'))[1]['state'], 'dropped')

    def test_host_allowlist_get_and_post(self):
        for method in ('GET', 'POST', 'HEAD', 'OPTIONS'):
            req = urllib.request.Request(self.base + '/api/project', method=method,
                                         headers={'Host': 'rebinding.example', 'Origin': 'http://rebinding.example'})
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req)
            with e.exception:
                self.assertEqual(e.exception.code, 403)
                if method != 'HEAD':
                    self.assertIn('Host is not allowed', e.exception.read().decode())
        self.editor.allowed_hosts.add('review.example')
        req = urllib.request.Request(self.base + '/api/project', headers={'Host': 'review.example:8100'})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)


class Command(unittest.TestCase):
    def test_a_missing_project_dir(self):
        from videobuilder.cli import main
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project'])
        self.assertIn('not a directory', str(e.exception))


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
                    'draft/accept','draft/drop','upgrade','access'}
        # Dynamic attachment and draft actions have their own router patterns.
        self.assertTrue(paths - {'attachments/', 'draft/'} <= expected, paths - expected)
        router = (PKG / 'editor.py').read_text()
        for path in paths - {'attachments/', 'draft/'}:
            self.assertIn("'/api/" + path + "'", router, path)
        self.assertIn("api('attachments/'", js)
        self.assertIn("api('video'", js)

    def test_fine_tuning_edit_endpoints(self):
        self.assertIn(b'id="pane-copy"', self.get('/tuning.html'))
        video = 'promo/film'
        self.assertEqual(self.post('/api/roll', {'video': video, 'segment': 'intro', 'until': 6})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['cuts'][1], 90)
        self.assertEqual(self.post('/api/copy', {'video': video, 'segment': 'intro', 'key': 'title', 'value': 'New'})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['segments'][0]['copy']['title'], 'New')
        self.assertEqual(self.post('/api/undo', {'video': video})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['segments'][0]['copy']['title'], 'Hello')


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
