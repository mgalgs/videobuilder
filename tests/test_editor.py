"""The editor's HTTP API, on a temp project in a git repo."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from tests.fixtures import API


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
