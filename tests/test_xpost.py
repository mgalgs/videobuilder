"""Unit tests for videobuilder/xpost.py: URL validation, the verified token
pair, syndication JSON parsing on synthetic fixtures, and the capped,
allowlisted download path. Every test here mocks videobuilder.xpost._open --
this sandbox has no network, and CI must not depend on X being reachable."""
import json
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from videobuilder import xpost

ACCEPTED_URLS = (
    'https://x.com/a_b/status/123',
    'https://twitter.com/a/status/123',
    'https://mobile.twitter.com/a/status/123',
    'https://www.x.com/a/status/123',
    'https://www.twitter.com/a/status/123',
    'https://X.com/a/status/123?s=20',
    'https://x.com/a/status/123#m',
    'https://x.com/a/status/123/',
)

REFUSED_URLS = (
    'http://x.com/a/status/1',
    'https://x.com.evil.example/a/status/1',
    'https://evilx.com/a/status/1',
    'https://x.com@evil.example/a/status/1',
    'https://x.com:8443/a/status/1',
    'https://x.com/a/status/12ab',
    'https://x.com/a/likes',
    'https://x.com/a/status/1/photo/1',
    'ftp://x.com/a/status/1',
    '',
)


class _FakeResponse:
    def __init__(self, data, url, content_length=None, headers=None):
        self._data = data
        self._url = url
        self._pos = 0
        self.headers = dict(headers or {})
        if content_length is not None:
            self.headers['Content-Length'] = str(content_length)

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


class UrlValidation(unittest.TestCase):
    def test_accepted_urls(self):
        for url in ACCEPTED_URLS:
            with self.subTest(url=url):
                xpost.parse_url(url)  # must not raise

    @mock.patch('videobuilder.xpost._open')
    def test_refused_urls_make_no_network_call(self, opened):
        for url in REFUSED_URLS:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    xpost.parse_url(url)
        opened.assert_not_called()


class Token(unittest.TestCase):
    def test_verified_token_pair(self):
        self.assertEqual(xpost.token('1585341984679469056'), '3uchycv2wqc')
        self.assertEqual(
            xpost.syndication_url('1585341984679469056'),
            'https://cdn.syndication.twimg.com/tweet-result?id=1585341984679469056&token=3uchycv2wqc')


class Parsing(unittest.TestCase):
    def test_parse_photos_text_handle(self):
        data = {
            'text': 'A neat zoom transition on the logo.',
            'user': {'screen_name': 'example_creator'},
            'mediaDetails': [
                {'type': 'photo', 'media_url_https': 'https://pbs.twimg.com/media/fake1.jpg'},
                {'type': 'photo', 'media_url_https': 'https://pbs.twimg.com/media/fake2.png'},
            ],
        }
        parsed = xpost.parse(data)
        self.assertEqual(parsed['text'], data['text'])
        self.assertEqual(parsed['handle'], 'example_creator')
        self.assertEqual(parsed['photos'], ['https://pbs.twimg.com/media/fake1.jpg',
                                            'https://pbs.twimg.com/media/fake2.png'])
        self.assertEqual(parsed['videos'], [])

    def test_best_mp4_variant_skips_hls(self):
        data = {
            'text': None, 'user': None,
            'mediaDetails': [{
                'type': 'video',
                'video_info': {'variants': [
                    {'content_type': 'application/x-mpegURL', 'url': 'https://video.twimg.com/hls/x.m3u8'},
                    {'content_type': 'video/mp4', 'url': 'https://video.twimg.com/vid/320x240/low.mp4',
                     'bitrate': 100},
                    {'content_type': 'video/mp4', 'url': 'https://video.twimg.com/vid/1280x720/high.mp4',
                     'bitrate': 900},
                ]},
            }],
        }
        parsed = xpost.parse(data)
        self.assertEqual(parsed['videos'], ['https://video.twimg.com/vid/1280x720/high.mp4',
                                            'https://video.twimg.com/vid/320x240/low.mp4'])

    def test_top_level_video_variants_used_when_no_media_details(self):
        data = {
            'text': 'clip', 'user': {'screen_name': 'maker_99'},
            'video': {'variants': [
                {'type': 'application/x-mpegURL', 'src': 'https://video.twimg.com/hls/x.m3u8'},
                {'type': 'video/mp4', 'src': 'https://video.twimg.com/vid/640x360/clip.mp4'},
            ]},
        }
        parsed = xpost.parse(data)
        self.assertEqual(parsed['handle'], 'maker_99')
        self.assertEqual(parsed['videos'], ['https://video.twimg.com/vid/640x360/clip.mp4'])


class OffHostMedia(unittest.TestCase):
    @mock.patch('videobuilder.xpost._open')
    def test_off_host_media_urls_never_fetched(self, opened):
        deadline = time.monotonic() + 60
        with self.assertRaises(ValueError):
            xpost._fetch('https://evil.example/x.jpg', xpost.MEDIA_HOSTS, xpost.PHOTO_MAX_BYTES, deadline)
        opened.assert_not_called()


class RedirectSafety(unittest.TestCase):
    def test_redirect_handler_refuses_off_host(self):
        handler = xpost._AllowlistRedirect(xpost.MEDIA_HOSTS)
        req = urllib.request.Request('https://video.twimg.com/orig')
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(req, None, 302, 'Found', {}, 'https://evil.example/x')
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(req, None, 302, 'Found', {}, 'http://video.twimg.com/x')
        result = handler.redirect_request(req, None, 302, 'Found', {}, 'https://video.twimg.com/x')
        self.assertIsInstance(result, urllib.request.Request)

    @mock.patch('videobuilder.xpost._open')
    def test_final_url_off_host_is_dropped(self, opened):
        opened.return_value = _FakeResponse(b'data', 'https://evil.example/final.jpg')
        deadline = time.monotonic() + 60
        with self.assertRaises(ValueError):
            xpost._fetch('https://pbs.twimg.com/media/fake.jpg', xpost.MEDIA_HOSTS, xpost.PHOTO_MAX_BYTES, deadline)


class SizeCaps(unittest.TestCase):
    @mock.patch('videobuilder.xpost._open')
    def test_content_length_over_cap_refused(self, opened):
        opened.return_value = _FakeResponse(b'x' * 10, 'https://pbs.twimg.com/media/fake.jpg',
                                            content_length=10 ** 9)
        deadline = time.monotonic() + 60
        with self.assertRaises(ValueError):
            xpost._fetch('https://pbs.twimg.com/media/fake.jpg', xpost.MEDIA_HOSTS, xpost.PHOTO_MAX_BYTES, deadline)

    @mock.patch('videobuilder.xpost._open')
    def test_streamed_body_over_cap_aborted(self, opened):
        big = b'x' * (xpost.PHOTO_MAX_BYTES + 1)
        opened.return_value = _FakeResponse(big, 'https://pbs.twimg.com/media/fake.jpg')
        deadline = time.monotonic() + 60
        with self.assertRaises(ValueError):
            xpost._fetch('https://pbs.twimg.com/media/fake.jpg', xpost.MEDIA_HOSTS, xpost.PHOTO_MAX_BYTES, deadline)

    @mock.patch('videobuilder.xpost._open')
    def test_oversize_video_falls_back_to_next_variant(self, opened):
        too_big = b'x' * (xpost.VIDEO_MAX_BYTES + 1)
        payload = json.dumps({
            'text': 'clip', 'user': None,
            'video': {'variants': [
                {'type': 'video/mp4', 'src': 'https://video.twimg.com/vid/1280x720/big.mp4'},
                {'type': 'video/mp4', 'src': 'https://video.twimg.com/vid/320x240/small.mp4'},
            ]},
        }).encode()
        opened.side_effect = [
            _FakeResponse(payload, xpost.syndication_url('123')),
            _FakeResponse(too_big, 'https://video.twimg.com/vid/1280x720/big.mp4', content_length=len(too_big)),
            _FakeResponse(b'ok', 'https://video.twimg.com/vid/320x240/small.mp4'),
        ]
        post = xpost.read_post('https://x.com/a/status/123')
        self.assertTrue(post.ok)
        self.assertEqual(post.media, [('x-clip.mp4', 'video/mp4', b'ok')])


class TimeBudget(unittest.TestCase):
    @mock.patch('videobuilder.xpost._open')
    def test_time_budget_stops_the_read(self, opened):
        def already_expired():
            return time.monotonic() - 1000  # the budget is already spent when the read starts
        post = xpost.read_post('https://x.com/a/status/123', now=already_expired)
        self.assertFalse(post.ok)
        opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
