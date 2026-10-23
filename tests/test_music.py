"""The music module: config loading, field mapping, entry points, fetching."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from videobuilder import music
from videobuilder.music import MusicLibrary


def _entry_point_tracks(config):
    """A fake entry-point source, used by test_entry_point_source below."""
    assert config['id'] == 'catalog'
    return [
        {'id': '1', 'title': 'Catalog One', 'audio_url': 'http://example.com/1.mp3', 'tags': ['calm'], 'duration': 12},
        {'id': 'skip-me', 'title': 'No url'},  # missing audio_url: skipped
        {'id': '2', 'title': 'Catalog Two', 'audio_url': 'ftp://example.com/2.mp3'},  # not http(s): skipped
    ]


_flaky_calls = []


def _flaky_entry_point_tracks(config):
    """A generator entry-point that succeeds once and raises on a later call, used by
    test_stale_cache_served_when_a_generator_entry_point_raises below. Its body only runs
    once iterated, so the raise happens inside the caller's `for` loop, not the call."""
    _flaky_calls.append(None)
    if len(_flaky_calls) > 1:
        raise RuntimeError('upstream down')
    yield {'id': '1', 'title': 'Flaky One', 'audio_url': 'http://example.com/1.mp3'}


class _JSONServer:
    """A local http.server serving one fixed JSON body, so tests never touch the network."""

    def __init__(self, body, content_type='application/json'):
        self.body = body
        self.failing = False
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if outer.failing:
                    self.send_response(500)
                    self.end_headers()
                    return
                data = outer.body if isinstance(outer.body, bytes) else json.dumps(outer.body).encode()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *a):
                pass
        self.httpd = HTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_address[1]}/tracks.json'
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Config(unittest.TestCase):
    """Startup validation of a --music-sources TOML file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name, 'music.toml')

    def write(self, text):
        self.path.write_text(text)
        return self.path

    def test_both_url_and_entry_point_is_an_error(self):
        self.write('''
            [[sources]]
            id = "dual"
            name = "Dual"
            license = "CC0"
            url = "https://music.example.com/tracks.json"
            entry_point = "tests.test_music:_entry_point_tracks"
            [sources.fields]
            id = "id"
            title = "title"
            audio_url = "audio_url"
        ''')
        with self.assertRaises(ValueError) as e:
            MusicLibrary.from_file(self.path)
        self.assertIn('not both', str(e.exception))

    def test_neither_url_nor_entry_point_is_an_error(self):
        self.write('''
            [[sources]]
            id = "neither"
            name = "Neither"
            license = "CC0"
        ''')
        with self.assertRaises(ValueError):
            MusicLibrary.from_file(self.path)

    def test_missing_license_is_an_error(self):
        self.write('''
            [[sources]]
            id = "nolicense"
            name = "No License"
            entry_point = "tests.test_music:_entry_point_tracks"
        ''')
        with self.assertRaises(ValueError) as e:
            MusicLibrary.from_file(self.path)
        self.assertIn('license', str(e.exception))

    def test_bad_toml_names_the_problem(self):
        self.write('not valid toml [[[')
        with self.assertRaises(ValueError) as e:
            MusicLibrary.from_file(self.path)
        self.assertIn(str(self.path), str(e.exception))

    def test_duplicate_id_is_an_error(self):
        self.write('''
            [[sources]]
            id = "dup"
            name = "A"
            license = "CC0"
            entry_point = "tests.test_music:_entry_point_tracks"
            [[sources]]
            id = "dup"
            name = "B"
            license = "CC0"
            entry_point = "tests.test_music:_entry_point_tracks"
        ''')
        with self.assertRaises(ValueError) as e:
            MusicLibrary.from_file(self.path)
        self.assertIn('duplicate', str(e.exception))

    def test_bad_entry_point_is_an_error(self):
        self.write('''
            [[sources]]
            id = "bad"
            name = "Bad"
            license = "CC0"
            entry_point = "tests.test_music:nonexistent_function"
        ''')
        with self.assertRaises(ValueError):
            MusicLibrary.from_file(self.path)


class MappingSource(unittest.TestCase):
    """Fetching and normalising a JSON mapping source, over a local http.server."""

    def _library(self, body, fields, url=None):
        self.server = _JSONServer(body)
        self.addCleanup(self.server.close)
        return MusicLibrary.from_file(self._write(url or self.server.url, fields))

    def _write(self, url, fields):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, 'music.toml')
        field_lines = '\n'.join(f'{k} = {json.dumps(v)}' for k, v in fields.items())
        path.write_text(f'''
            [[sources]]
            id = "lib"
            name = "Library"
            license = "CC BY-NC 4.0"
            url = "{url}"
            [sources.fields]
            {field_lines}
        ''')
        return path

    def test_nested_paths_and_duration_ms(self):
        body = {'data': {'tracks': [
            {'meta': {'id': 't1'}, 'title': 'One', 'tags': ['calm', 'piano'], 'length_ms': 90500,
             'files': {'mp3': 'http://example.com/one.mp3'}},
        ]}}
        lib = self._library(body, {'tracks': 'data.tracks', 'id': 'meta.id', 'title': 'title',
                                   'audio_url': 'files.mp3', 'tags': 'tags', 'duration': 'length_ms',
                                   'duration_unit': 'ms'})
        source, tracks = lib.list_tracks('lib')
        self.assertEqual(source.license, 'CC BY-NC 4.0')
        self.assertEqual(tracks, [{'id': 't1', 'title': 'One', 'tags': ['calm', 'piano'], 'duration': 90.5,
                                   'audio_url': 'http://example.com/one.mp3'}])

    def test_duration_unit_seconds_is_the_default(self):
        body = {'tracks': [{'id': 't1', 'title': 'One', 'audio_url': 'http://example.com/one.mp3', 'duration': 12.5}]}
        lib = self._library(body, {'tracks': 'tracks', 'id': 'id', 'title': 'title', 'audio_url': 'audio_url',
                                   'duration': 'duration'})
        _, tracks = lib.list_tracks('lib')
        self.assertEqual(tracks[0]['duration'], 12.5)

    def test_top_level_list(self):
        body = [{'id': 't1', 'title': 'One', 'audio_url': 'http://example.com/one.mp3'}]
        lib = self._library(body, {'tracks': '', 'id': 'id', 'title': 'title', 'audio_url': 'audio_url'})
        _, tracks = lib.list_tracks('lib')
        self.assertEqual([t['id'] for t in tracks], ['t1'])

    def test_skips_incomplete_tracks_and_non_http_urls(self):
        body = {'tracks': [
            {'id': 't1', 'title': 'One', 'audio_url': 'http://example.com/one.mp3'},
            {'id': 't2', 'audio_url': 'http://example.com/two.mp3'},  # no title
            {'title': 'No id', 'audio_url': 'http://example.com/three.mp3'},  # no id
            {'id': 't4', 'title': 'No url'},  # no audio_url
            {'id': 't5', 'title': 'Not http', 'audio_url': 'file:///etc/passwd'},
        ]}
        lib = self._library(body, {'tracks': 'tracks', 'id': 'id', 'title': 'title', 'audio_url': 'audio_url'})
        _, tracks = lib.list_tracks('lib')
        self.assertEqual([t['id'] for t in tracks], ['t1'])

    def test_cache_and_stale_on_failure(self):
        body = {'tracks': [{'id': 't1', 'title': 'One', 'audio_url': 'http://example.com/one.mp3'}]}
        lib = self._library(body, {'tracks': 'tracks', 'id': 'id', 'title': 'title', 'audio_url': 'audio_url'})
        _, first = lib.list_tracks('lib')
        self.server.failing = True
        _, second = lib.list_tracks('lib')  # still fresh: no refetch at all
        self.assertEqual(first, second)
        lib._cache['lib']['at'] -= music.CACHE_TTL + 1  # force a refetch
        _, stale = lib.list_tracks('lib')  # the refetch fails; the old list is served
        self.assertEqual(stale, first)

    def test_fetch_failure_with_no_cache_raises(self):
        self.server = _JSONServer({'tracks': []})
        self.addCleanup(self.server.close)
        self.server.failing = True
        lib = MusicLibrary.from_file(self._write(self.server.url, {'tracks': 'tracks', 'id': 'id', 'title': 'title',
                                                                    'audio_url': 'audio_url'}))
        with self.assertRaises(music.FetchError):
            lib.list_tracks('lib')

    def test_unknown_source_is_a_key_error(self):
        self.server = _JSONServer({'tracks': []})
        self.addCleanup(self.server.close)
        lib = MusicLibrary.from_file(self._write(self.server.url, {'tracks': 'tracks', 'id': 'id', 'title': 'title',
                                                                    'audio_url': 'audio_url'}))
        with self.assertRaises(KeyError):
            lib.list_tracks('nope')


class EntryPointSource(unittest.TestCase):
    def test_entry_point_source(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, 'music.toml')
        path.write_text('''
            [[sources]]
            id = "catalog"
            name = "Catalog"
            license = "Public domain"
            entry_point = "tests.test_music:_entry_point_tracks"
        ''')
        lib = MusicLibrary.from_file(path)
        self.assertEqual(lib.list_sources(), [{'id': 'catalog', 'name': 'Catalog', 'license': 'Public domain'}])
        source, tracks = lib.list_tracks('catalog')
        self.assertEqual(source.name, 'Catalog')
        self.assertEqual([t['id'] for t in tracks], ['1'])
        self.assertEqual(tracks[0]['duration'], 12.0)

    def test_stale_cache_served_when_a_generator_entry_point_raises(self):
        _flaky_calls.clear()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, 'music.toml')
        path.write_text('''
            [[sources]]
            id = "catalog"
            name = "Catalog"
            license = "Public domain"
            entry_point = "tests.test_music:_flaky_entry_point_tracks"
        ''')
        lib = MusicLibrary.from_file(path)
        _, first = lib.list_tracks('catalog')
        self.assertEqual([t['id'] for t in first], ['1'])
        lib._cache['catalog']['at'] -= music.CACHE_TTL + 1  # force a refetch
        _, second = lib.list_tracks('catalog')  # the generator raises; the stale list is served
        self.assertEqual(second, first)


class OptionalCreditFields(unittest.TestCase):
    """finalize_track's optional license/creator/year/item_url/disputed --
    present only when a source actually supplies them (archive_org's 78rpm
    entry point does; an ordinary source doesn't)."""

    def test_absent_by_default(self):
        track = music.finalize_track({'id': '1', 'title': 'One', 'audio_url': 'http://example.com/1.mp3'})
        self.assertEqual(set(track), {'id', 'title', 'tags', 'duration', 'audio_url'})

    def test_present_when_supplied(self):
        track = music.finalize_track({
            'id': '1', 'title': 'One', 'audio_url': 'http://example.com/1.mp3',
            'license': 'rights disputed', 'creator': 'Some Band', 'year': '1931',
            'item_url': 'https://archive.org/details/disc-1', 'disputed': True,
        })
        self.assertEqual(track['license'], 'rights disputed')
        self.assertEqual(track['creator'], 'Some Band')
        self.assertEqual(track['year'], '1931')
        self.assertEqual(track['item_url'], 'https://archive.org/details/disc-1')
        self.assertTrue(track['disputed'])

    def test_non_http_item_url_is_dropped(self):
        track = music.finalize_track({'id': '1', 'title': 'One', 'audio_url': 'http://example.com/1.mp3',
                                      'item_url': 'not-a-url'})
        self.assertNotIn('item_url', track)

    def test_falsy_disputed_is_omitted(self):
        track = music.finalize_track({'id': '1', 'title': 'One', 'audio_url': 'http://example.com/1.mp3',
                                      'disputed': False})
        self.assertNotIn('disputed', track)


class Archive78RpmEntryPoint(unittest.TestCase):
    """The built-in archive_org.list_78rpm_tracks wired up as a real
    --music-sources entry-point source, the way a self-hoster who opts into
    the 78rpm collection would configure it."""

    def test_wired_up_through_a_toml_source(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, 'music.toml')
        path.write_text('''
            [[sources]]
            id = "rpm78"
            name = "78rpm (archive.org)"
            license = "Rights disputed -- see each item"
            entry_point = "videobuilder.archive_org:list_78rpm_tracks"
            rows = 5
        ''')
        fake_track = {'id': 'disc-1', 'title': 'Some Tune', 'audio_url': 'https://archive.org/download/disc-1/x.mp3',
                     'creator': 'Some Band', 'year': '1931', 'license': 'rights disputed (see item page)',
                     'item_url': 'https://archive.org/details/disc-1', 'disputed': True}
        # Patched before from_file: _build_source resolves and binds the entry-point
        # function right away, so the mock must already be in place for that lookup.
        with mock.patch('videobuilder.archive_org.list_78rpm_tracks', return_value=[fake_track]) as listed:
            lib = MusicLibrary.from_file(path)
            source, tracks = lib.list_tracks('rpm78')
        listed.assert_called_once()
        self.assertEqual(source.license, 'Rights disputed -- see each item')
        self.assertEqual(len(tracks), 1)
        track = tracks[0]
        self.assertEqual(track['id'], 'disc-1')
        self.assertTrue(track['disputed'])
        self.assertEqual(track['creator'], 'Some Band')
        self.assertEqual(track['item_url'], 'https://archive.org/details/disc-1')


if __name__ == '__main__':
    unittest.main()
