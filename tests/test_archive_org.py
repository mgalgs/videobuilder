"""Unit tests for videobuilder/archive_org.py: host/redirect allowlisting,
search/metadata parsing on synthetic fixtures, derivative picking, and the
capped download path. Every test here mocks videobuilder.archive_org._open --
this sandbox has no network, and CI must not depend on archive.org being
reachable."""
import json
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from videobuilder import archive_org


class _FakeResponse:
    def __init__(self, data, url, content_length=None, headers=None, content_type=None):
        self._data = data
        self._url = url
        self._pos = 0
        self.headers = dict(headers or {})
        if content_length is not None:
            self.headers['Content-Length'] = str(content_length)
        if content_type is not None:
            self.headers['Content-Type'] = content_type

    def read(self, n=-1):
        if n is None or n < 0:
            chunk, self._pos = self._data[self._pos:], len(self._data)
            return chunk
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def geturl(self):
        return self._url

    def close(self):
        pass


SEARCH_FIXTURE = {
    'response': {'docs': [
        {'identifier': 'farm-safety-1955', 'title': 'Farm Safety', 'year': '1955',
         'licenseurl': 'https://creativecommons.org/publicdomain/mark/1.0/', 'runtime': '10:30'},
        {'identifier': 'no-title-item', 'runtime': 62.5},
        {'identifier': 42},  # not a string identifier: dropped
        'not-a-dict',  # dropped
    ]},
}

METADATA_FIXTURE = {
    'metadata': {
        'identifier': 'farm-safety-1955', 'title': 'Farm Safety', 'creator': ['A. Studio', 'B. Co'],
        'year': '1955', 'licenseurl': 'https://creativecommons.org/publicdomain/mark/1.0/',
        'collection': ['prelinger', 'ephemera'], 'mediatype': 'movies',
    },
    'files': [
        {'name': 'farm-safety-1955.mp4', 'format': 'MPEG4', 'size': '5000000'},
        {'name': 'farm-safety-1955_512kb.mp4', 'format': '512Kb MP4', 'size': '1000000'},
        {'name': 'farm-safety-1955.ogv', 'format': 'Ogg Video', 'size': '2000000'},
        {'name': 'bad-size.mp4', 'size': 'not-a-number'},
        'not-a-dict',
    ],
}


class HostAllowlisting(unittest.TestCase):
    def test_archive_org_and_mirrors_allowed(self):
        for host in ('archive.org', 'ia801508.us.archive.org', 'ia601234.archive.org'):
            with self.subTest(host=host):
                self.assertTrue(archive_org._host_ok(host))

    def test_other_hosts_refused(self):
        for host in ('evil.example', 'archive.org.evil.example', None, ''):
            with self.subTest(host=host):
                self.assertFalse(archive_org._host_ok(host))

    @mock.patch('videobuilder.archive_org._open')
    def test_non_archive_host_never_fetched(self, opened):
        with self.assertRaises(archive_org.ArchiveError):
            archive_org._fetch('https://evil.example/x.json', archive_org.SEARCH_MAX_BYTES)
        opened.assert_not_called()

    @mock.patch('videobuilder.archive_org._open')
    def test_plain_http_never_fetched(self, opened):
        with self.assertRaises(archive_org.ArchiveError):
            archive_org._fetch('http://archive.org/x.json', archive_org.SEARCH_MAX_BYTES)
        opened.assert_not_called()


class RedirectSafety(unittest.TestCase):
    def test_redirect_handler_refuses_off_host(self):
        handler = archive_org._AllowlistRedirect()
        req = urllib.request.Request('https://archive.org/orig')
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(req, None, 302, 'Found', {}, 'https://evil.example/x')
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(req, None, 302, 'Found', {}, 'http://archive.org/x')
        result = handler.redirect_request(req, None, 302, 'Found', {}, 'https://ia801508.us.archive.org/x')
        self.assertIsInstance(result, urllib.request.Request)

    @mock.patch('videobuilder.archive_org._open')
    def test_final_url_off_host_is_dropped(self, opened):
        opened.return_value = _FakeResponse(b'{}', 'https://evil.example/final.json')
        with self.assertRaises(archive_org.ArchiveError):
            archive_org._fetch('https://archive.org/metadata/x', archive_org.METADATA_MAX_BYTES)


class SizeCaps(unittest.TestCase):
    @mock.patch('videobuilder.archive_org._open')
    def test_content_length_over_cap_refused(self, opened):
        opened.return_value = _FakeResponse(b'x' * 10, 'https://archive.org/x', content_length=10 ** 9)
        with self.assertRaises(archive_org.TooLarge):
            archive_org._fetch('https://archive.org/x', 100)

    @mock.patch('videobuilder.archive_org._open')
    def test_streamed_body_over_cap_aborted(self, opened):
        big = b'x' * 200
        opened.return_value = _FakeResponse(big, 'https://archive.org/x')
        with self.assertRaises(archive_org.TooLarge):
            archive_org._fetch('https://archive.org/x', 100)


class Search(unittest.TestCase):
    @mock.patch('videobuilder.archive_org._open')
    def test_search_parses_and_drops_bad_docs(self, opened):
        opened.return_value = _FakeResponse(json.dumps(SEARCH_FIXTURE).encode(), archive_org.SEARCH_URL)
        results = archive_org.search_films('farm safety', rows=5)
        self.assertEqual(len(results), 2)
        first = results[0]
        self.assertEqual(first['identifier'], 'farm-safety-1955')
        self.assertEqual(first['title'], 'Farm Safety')
        self.assertEqual(first['year'], '1955')
        self.assertEqual(first['duration'], 630.0)
        self.assertEqual(first['license'], 'https://creativecommons.org/publicdomain/mark/1.0/')
        self.assertEqual(first['thumbnail'], 'https://archive.org/services/img/farm-safety-1955')
        self.assertEqual(first['details_url'], 'https://archive.org/details/farm-safety-1955')
        second = results[1]
        self.assertEqual(second['title'], 'no-title-item')  # falls back to the identifier
        self.assertEqual(second['duration'], 62.5)

    @mock.patch('videobuilder.archive_org._open')
    def test_search_results_are_cached(self, opened):
        opened.return_value = _FakeResponse(json.dumps(SEARCH_FIXTURE).encode(), archive_org.SEARCH_URL)
        archive_org._cache._entries.clear()
        archive_org.search_films('cached query', rows=5)
        archive_org.search_films('cached query', rows=5)
        self.assertEqual(opened.call_count, 1)


    @mock.patch('videobuilder.archive_org._open')
    def test_upstream_failure_raises_archive_error(self, opened):
        opened.side_effect = urllib.error.URLError('no route')
        with self.assertRaises(archive_org.ArchiveError):
            archive_org.search_films('anything', rows=5)


class CacheEviction(unittest.TestCase):
    """Unlike MusicLibrary's cache, this one is keyed in part by a creator's
    own search text, so it must not simply grow for as long as the process
    runs (see the _Cache docstring)."""

    def test_expired_entries_are_dropped_on_insert(self):
        cache = archive_org._Cache()
        cache.get_or_fetch('stale', lambda: 'old')
        cache._entries['stale'] = ('old', time.monotonic() - archive_org.CACHE_TTL - 1)
        cache.get_or_fetch('fresh', lambda: 'new')
        self.assertNotIn('stale', cache._entries)
        self.assertIn('fresh', cache._entries)

    def test_entry_count_is_capped_evicting_the_oldest_first(self):
        cache = archive_org._Cache()
        now = time.monotonic()
        for i in range(archive_org.CACHE_MAX_ENTRIES):
            cache._entries[f'k{i}'] = (i, now - (archive_org.CACHE_MAX_ENTRIES - i))
        cache.get_or_fetch('newest', lambda: 'value')
        self.assertLessEqual(len(cache._entries), archive_org.CACHE_MAX_ENTRIES)
        self.assertNotIn('k0', cache._entries)  # the oldest entry is the one evicted
        self.assertIn('newest', cache._entries)


class Metadata(unittest.TestCase):
    def setUp(self):
        archive_org._cache._entries.clear()

    @mock.patch('videobuilder.archive_org._open')
    def test_metadata_parses_creator_list_and_files(self, opened):
        opened.return_value = _FakeResponse(json.dumps(METADATA_FIXTURE).encode(), archive_org.SEARCH_URL)
        item = archive_org.get_metadata('farm-safety-1955')
        self.assertEqual(item['title'], 'Farm Safety')
        self.assertEqual(item['creator'], 'A. Studio, B. Co')
        self.assertEqual(item['year'], '1955')
        self.assertEqual(item['license'], 'https://creativecommons.org/publicdomain/mark/1.0/')
        self.assertEqual(item['details_url'], 'https://archive.org/details/farm-safety-1955')
        self.assertEqual(item['collection'], ['prelinger', 'ephemera'])
        self.assertEqual(item['mediatype'], 'movies')
        self.assertEqual(len(item['files']), 4)  # the bare string entry is dropped

    @mock.patch('videobuilder.archive_org._open')
    def test_single_string_collection_is_a_one_item_list(self, opened):
        fixture = json.loads(json.dumps(METADATA_FIXTURE))
        fixture['metadata']['collection'] = 'prelinger'
        opened.return_value = _FakeResponse(json.dumps(fixture).encode(), archive_org.SEARCH_URL)
        item = archive_org.get_metadata('farm-safety-1955')
        self.assertEqual(item['collection'], ['prelinger'])

    @mock.patch('videobuilder.archive_org._open')
    def test_missing_collection_is_an_empty_list(self, opened):
        fixture = json.loads(json.dumps(METADATA_FIXTURE))
        del fixture['metadata']['collection']
        opened.return_value = _FakeResponse(json.dumps(fixture).encode(), archive_org.SEARCH_URL)
        item = archive_org.get_metadata('farm-safety-1955')
        self.assertEqual(item['collection'], [])

    @mock.patch('videobuilder.archive_org._open')
    def test_unknown_identifier_is_not_found(self, opened):
        opened.return_value = _FakeResponse(json.dumps({'metadata': {}}).encode(), archive_org.SEARCH_URL)
        with self.assertRaises(archive_org.NotFound):
            archive_org.get_metadata('no-such-item')

    def test_bad_identifier_never_fetched(self):
        with mock.patch('videobuilder.archive_org._open') as opened:
            with self.assertRaises(archive_org.NotFound):
                archive_org.get_metadata('../etc/passwd')
            opened.assert_not_called()


class DerivativePicking(unittest.TestCase):
    def test_picks_the_largest_mp4_under_the_cap(self):
        name = archive_org.pick_derivative(METADATA_FIXTURE['files'], max_bytes=4_000_000)
        self.assertEqual(name, 'farm-safety-1955_512kb.mp4')

    def test_picks_the_largest_when_everything_fits(self):
        name = archive_org.pick_derivative(METADATA_FIXTURE['files'], max_bytes=10_000_000)
        self.assertEqual(name, 'farm-safety-1955.mp4')

    def test_none_when_nothing_fits(self):
        name = archive_org.pick_derivative(METADATA_FIXTURE['files'], max_bytes=10)
        self.assertIsNone(name)

    def test_ignores_non_mp4_and_bad_sizes(self):
        files = [{'name': 'x.ogv', 'size': '1'}, {'name': 'y.mp4', 'size': 'nope'}]
        self.assertIsNone(archive_org.pick_derivative(files, max_bytes=10_000_000))


class Download(unittest.TestCase):
    @mock.patch('videobuilder.archive_org._open')
    def test_open_download_returns_length_and_type(self, opened):
        opened.return_value = _FakeResponse(b'movie bytes', 'https://archive.org/download/x/x.mp4',
                                            content_length=11, content_type='video/mp4')
        response, length, ctype = archive_org.open_download('farm-safety-1955', 'farm-safety-1955.mp4')
        self.assertEqual(length, 11)
        self.assertEqual(ctype, 'video/mp4')
        self.assertEqual(response.read(), b'movie bytes')

    @mock.patch('videobuilder.archive_org._open')
    def test_no_content_length_is_an_error(self, opened):
        opened.return_value = _FakeResponse(b'x', 'https://archive.org/download/x/x.mp4')
        with self.assertRaises(archive_org.ArchiveError):
            archive_org.open_download('farm-safety-1955', 'farm-safety-1955.mp4')

    def test_bad_filename_never_fetched(self):
        with mock.patch('videobuilder.archive_org._open') as opened:
            with self.assertRaises(archive_org.ArchiveError):
                archive_org.open_download('farm-safety-1955', '../../etc/passwd')
            opened.assert_not_called()

    @mock.patch('videobuilder.archive_org._open')
    def test_redirected_off_host_is_refused(self, opened):
        opened.return_value = _FakeResponse(b'x', 'https://evil.example/final.mp4', content_length=1)
        with self.assertRaises(archive_org.ArchiveError):
            archive_org.open_download('farm-safety-1955', 'farm-safety-1955.mp4')


class Rpm78EntryPoint(unittest.TestCase):
    def setUp(self):
        archive_org._cache._entries.clear()

    @mock.patch('videobuilder.archive_org._open')
    def test_lists_tracks_with_disputed_flag_and_credit(self, opened):
        search_body = {'response': {'docs': [{'identifier': 'disc-1'}]}}
        meta_body = {
            'metadata': {'identifier': 'disc-1', 'title': 'Some Tune', 'creator': 'Some Band', 'year': '1931'},
            'files': [{'name': 'disc-1.mp3', 'size': '1000'}],
        }
        opened.side_effect = [
            _FakeResponse(json.dumps(search_body).encode(), archive_org.SEARCH_URL),
            _FakeResponse(json.dumps(meta_body).encode(), archive_org.SEARCH_URL),
        ]
        tracks = archive_org.list_78rpm_tracks({'id': 'rpm78', 'rows': 5})
        self.assertEqual(len(tracks), 1)
        track = tracks[0]
        self.assertEqual(track['id'], 'disc-1')
        self.assertEqual(track['title'], 'Some Tune')
        self.assertEqual(track['creator'], 'Some Band')
        self.assertEqual(track['year'], '1931')
        self.assertTrue(track['disputed'])
        self.assertEqual(track['audio_url'], 'https://archive.org/download/disc-1/disc-1.mp3')
        self.assertIn('rights disputed', track['license'])

    @mock.patch('videobuilder.archive_org._open')
    def test_item_with_no_mp3_is_skipped(self, opened):
        search_body = {'response': {'docs': [{'identifier': 'disc-2'}]}}
        meta_body = {'metadata': {'identifier': 'disc-2', 'title': 'No Audio'}, 'files': [{'name': 'disc-2.flac'}]}
        opened.side_effect = [
            _FakeResponse(json.dumps(search_body).encode(), archive_org.SEARCH_URL),
            _FakeResponse(json.dumps(meta_body).encode(), archive_org.SEARCH_URL),
        ]
        self.assertEqual(archive_org.list_78rpm_tracks({}), [])


class RuntimeParsing(unittest.TestCase):
    def test_parses_seconds_and_clock_formats(self):
        self.assertEqual(archive_org._parse_runtime(90), 90.0)
        self.assertEqual(archive_org._parse_runtime('90.5'), 90.5)
        self.assertEqual(archive_org._parse_runtime('1:02:03'), 3723.0)
        self.assertEqual(archive_org._parse_runtime('02:03'), 123.0)
        self.assertIsNone(archive_org._parse_runtime('not a duration'))
        self.assertIsNone(archive_org._parse_runtime(None))


class IPGuard(unittest.TestCase):
    def test_open_refuses_a_rebound_address(self):
        request = urllib.request.Request('https://archive.org/x')
        with mock.patch('videobuilder.guard.resolve_and_check', side_effect=guard_refused()):
            with self.assertRaises(archive_org.ArchiveError):
                archive_org._open(request, 5)

    def test_rebound_address_refused_at_the_real_connect_not_just_the_first_check(self):
        """A DNS answer that is safe for _open's own fail-fast check but
        turns unsafe by the time the real connection is made (the classic
        rebinding attack) must still be refused: the actual connect goes
        through the same guard (via the guard proxy), not a second,
        independently-resolved address for the same host."""
        from videobuilder import guard
        self.addCleanup(self._reset_guard_proxy)
        request = urllib.request.Request('https://archive.org/x')
        answers = iter([(0, ('203.0.113.5', 443)), guard.Refused('rebound to a private address')])

        def fake_resolve(host, port, allow_loopback=False):
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer

        with mock.patch('videobuilder.guard.resolve_and_check', side_effect=fake_resolve):
            with self.assertRaises(urllib.error.URLError):
                archive_org._open(request, 5)

    def _reset_guard_proxy(self):
        if archive_org._guard_proxy is not None:
            archive_org._guard_proxy.close()
            archive_org._guard_proxy = None


def guard_refused():
    from videobuilder import guard

    def raiser(*args, **kwargs):
        raise guard.Refused('blocked')
    return raiser


if __name__ == '__main__':
    unittest.main()
