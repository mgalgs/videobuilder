import itertools
import json
import os
import tempfile
import textwrap
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from videobuilder.preview import Session, make_handler

FILM = textwrap.dedent('''
    import videobuilder as vb
    from {helper} import COLOUR
    grid = vb.Grid(fps=30, bpm=120)
    tl = vb.Timeline(grid, [vb.Segment('one', 0, 2), vb.Segment('two', 2, 4)], end=4)
    def draw(n, cv):
        cv.rect(0, 0, cv.width / 2, cv.height, COLOUR)
    FILM = vb.Film(draw=draw, timeline=tl, formats=('16x9', '1x1'))
''')

_names = itertools.count()


class PreviewServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.film = os.path.join(d, 'film.py')
        # A fresh helper name per test: sys.modules outlives each test's temp dir.
        name = f'colour_vbpreview_{next(_names)}'
        self.source = FILM.replace('{helper}', name)
        self.helper = os.path.join(d, f'{name}.py')
        self.write(self.helper, "COLOUR = '#ff0000'\n")
        self.write(self.film, self.source)
        self.session = Session(self.film, poll=0)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.session))
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def write(self, path, body):
        # Bump the mtime past the last stat so the change is seen even on coarse clocks.
        with open(path, 'w') as fh:
            fh.write(body)
        t = time.time() + getattr(self, '_bump', 0)
        self._bump = getattr(self, '_bump', 0) + 2
        os.utime(path, (t, t))

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.status, r.headers.get('Content-Type'), r.read()

    def test_page_and_info(self):
        status, ctype, body = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn(b'id="scrub"', body)
        info = json.loads(self.get('/info')[2])
        self.assertIsNone(info['error'])
        self.assertEqual((info['fps'], info['frames']), (30, 60))
        self.assertEqual([f['name'] for f in info['formats']], ['16x9', '1x1'])
        self.assertEqual([s['name'] for s in info['timeline']['segments']], ['one', 'two'])
        self.assertEqual(info['timeline']['beats'], [0, 15, 30, 45, 60])

    def test_frame_png(self):
        status, ctype, body = self.get('/frame?frame=10&format=1x1&scale=0.25&overlay=1')
        self.assertEqual((status, ctype), (200, 'image/png'))
        self.assertEqual(body[:8], b'\x89PNG\r\n\x1a\n')
        w, h = int.from_bytes(body[16:20], 'big'), int.from_bytes(body[20:24], 'big')
        self.assertEqual((w, h), (270, 270))

    def test_hot_reload(self):
        before = self.get('/frame?frame=0&scale=0.1')[2]
        v0 = json.loads(self.get('/info')[2])['version']
        self.write(self.helper, "COLOUR = '#00ff00'\n")  # a neighbour module, not the film itself
        after = self.get('/frame?frame=0&scale=0.1')[2]
        self.assertNotEqual(before, after)
        self.assertEqual(json.loads(self.get('/info')[2])['version'], v0 + 1)

    def test_broken_edit_keeps_last_good_film(self):
        good = self.get('/frame?frame=0&scale=0.1')[2]
        self.write(self.film, self.source + '\ndef broken(:\n')
        info = json.loads(self.get('/info')[2])
        self.assertIn('SyntaxError', info['error'])
        self.assertEqual(self.get('/frame?frame=0&scale=0.1')[2], good)
        self.write(self.film, self.source)
        self.assertIsNone(json.loads(self.get('/info')[2])['error'])

    def test_draw_error_is_a_500_with_traceback(self):
        self.write(self.film, self.source.replace('cv.rect(', 'undefined_name(cv, '))
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/frame?frame=0')
        self.assertEqual(e.exception.code, 500)
        self.assertIn(b'NameError', e.exception.read())


    def test_info_lists_children_groups_overlaps_and_cuts(self):
        self.write(self.film, self.source.replace(
            "[vb.Segment('one', 0, 2), vb.Segment('two', 2, 4)]",
            "[vb.Segment('g', 0, 2, children=vb.timeline.sequence(0, [('one', 1), ('one b', 1)])),"
            " vb.Segment('two', 2, 4, overlap=1)]"))
        info = json.loads(self.get('/info')[2])
        self.assertIsNone(info['error'])
        tl = info['timeline']
        self.assertEqual([(s['name'], s['group'], s['overlap_end']) for s in tl['segments']],
                         [('one', 'g', None), ('one b', 'g', None), ('two', None, 45)])
        self.assertEqual(tl['groups'], [{'name': 'g', 'start': 0, 'end': 30, 'depth': 0}])
        self.assertEqual(tl['cuts'], [0, 15])
        status, ctype, body = self.get('/frame?frame=35&format=1x1&scale=0.25&overlay=1')  # overlay draws them
        self.assertEqual(status, 200)

    def test_info_has_copy_rollable_and_edits(self):
        self.write(self.film, self.source.replace("vb.Segment('one', 0, 2)", "vb.Segment('one', 0, 2, dict(title='Hi', n=3))"))
        info = json.loads(self.get('/info')[2])
        self.assertIsNone(info['edits'])
        self.assertEqual([(s['name'], s['copy'], s['rollable']) for s in info['timeline']['segments']],
                         [('one', {'title': 'Hi'}, True), ('two', {}, False)])
        toml = os.path.join(self.tmp.name, 'edits.toml')
        self.write(toml, '[segments.one]\nuntil = 3\n[segments.one.data]\ntitle = "Hello"\n')
        info = json.loads(self.get('/info')[2])
        self.assertIsNone(info['error'])
        self.assertEqual(info['edits'], {'path': toml, 'segments': {'one': {'until': 3, 'data': {'title': 'Hello'}}}})
        seg = info['timeline']['segments'][0]
        self.assertEqual((seg['end'], seg['until'], seg['copy']), (45, 3, {'title': 'Hello'}))
        self.assertEqual(info['timeline']['cuts'], [0, 45])

    def test_edits_toml_hot_reload(self):
        toml = os.path.join(self.tmp.name, 'edits.toml')
        v0 = json.loads(self.get('/info')[2])['version']
        self.write(toml, '[segments.one]\nuntil = 1\n')
        info = json.loads(self.get('/info')[2])
        self.assertEqual((info['version'], info['timeline']['cuts']), (v0 + 1, [0, 15]))
        self.write(toml, '[segments.one]\nuntil = 1.5\n')  # an edit to it
        self.assertEqual(json.loads(self.get('/info')[2])['timeline']['cuts'], [0, 23])
        self.write(toml, '[segments.one]\nuntil = 9\n')  # a bad edit keeps the last good film
        info = json.loads(self.get('/info')[2])
        self.assertIn('strictly between', info['error'])
        self.assertEqual(info['timeline']['cuts'], [0, 23])
        os.remove(toml)  # and removing it is a change too
        info = json.loads(self.get('/info')[2])
        self.assertEqual((info['error'], info['edits'], info['timeline']['cuts']), (None, None, [0, 30]))


if __name__ == '__main__':
    unittest.main()
