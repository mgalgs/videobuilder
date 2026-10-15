"""The /capabilities routes: single-project and library, gated and ungated,
with and without a --capabilities-dir, following tests/test_library.py's and
tests/test_editor.py's fixtures."""
import json
import re
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from videobuilder import capabilities

from tests import fixtures


def _embedded_data(page):
    """The page's per-card JSON blob (id, title, ..., available, unmute)."""
    m = re.search(rb'<script id="capabilities-data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1))


def _status(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.read(), e.headers


class SingleProjectRoutes(fixtures.API):
    """No accounts in single-project mode: the page is always reachable."""

    def test_page_lists_every_card_with_a_placeholder_with_no_capabilities_dir(self):
        code, page, _ = _status(self.base, '/capabilities')
        self.assertEqual(code, 200)
        self.assertIn(b'Capabilities', page)
        self.assertIn(b'clip not built', page)
        for e in capabilities.CATALOG:
            self.assertIn(e['id'].encode(), page)

    def test_unknown_and_traversal_shaped_ids_404(self):
        for bad in ('not-a-real-capability', '..', '%2e%2e%2fetc%2fpasswd', 'eased-entrances%2f..%2f..'):
            with self.subTest(bad=bad):
                code, _, _ = _status(self.base, f'/capabilities/{bad}.mp4')
                self.assertEqual(code, 404)
                code, _, _ = _status(self.base, f'/capabilities/{bad}.jpg')
                self.assertEqual(code, 404)

    def test_clip_404_without_capabilities_dir(self):
        code, _, _ = _status(self.base, '/capabilities/eased-entrances.mp4')
        self.assertEqual(code, 404)


class SingleProjectWithClip(fixtures.API):
    """Single-project mode with a --capabilities-dir configured and one built clip."""

    def setUp(self):
        super(fixtures.API, self).setUp()
        self.cap_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.cap_tmp.cleanup)
        Path(self.cap_tmp.name, 'eased-entrances.mp4').write_bytes(b'0123456789')
        Path(self.cap_tmp.name, 'eased-entrances.jpg').write_bytes(b'\xff\xd8\xffposter\xff\xd9')
        self.start(capabilities_dir=self.cap_tmp.name)

    def test_single_project_mode_serves_the_page(self):
        code, page, _ = _status(self.base, '/capabilities')
        self.assertEqual(code, 200)
        self.assertIn(b'/capabilities/eased-entrances.jpg', page)

    def test_poster_served(self):
        code, body, headers = _status(self.base, '/capabilities/eased-entrances.jpg')
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), 'image/jpeg')
        self.assertTrue(body.startswith(b'\xff\xd8\xff'))

    def test_range_request_on_a_clip_gets_206(self):
        code, body, headers = _status(self.base, '/capabilities/eased-entrances.mp4', {'Range': 'bytes=2-5'})
        self.assertEqual((code, body), (206, b'2345'))
        self.assertEqual(headers['Content-Range'], 'bytes 2-5/10')
        code, body, _ = _status(self.base, '/capabilities/eased-entrances.mp4')
        self.assertEqual((code, body), (200, b'0123456789'))

    def test_unknown_id_still_404s_with_a_dir_configured(self):
        code, _, _ = _status(self.base, '/capabilities/not-a-real-capability.mp4')
        self.assertEqual(code, 404)


class AuthCapabilities(fixtures.Auth):
    """Library mode with accounts: the capabilities page follows the same
    sign-in gate as the index, and is reachable by anyone signed in (it isn't
    gated per-project, unlike /v/<name>/)."""

    def library_kwargs(self):
        self.cap_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.cap_tmp.cleanup)
        Path(self.cap_tmp.name, 'eased-entrances.mp4').write_bytes(b'fake-mp4-bytes')
        return {**super().library_kwargs(), 'capabilities_dir': self.cap_tmp.name}

    def test_anonymous_page_gets_the_signin_page_and_clip_is_refused_like_other_gated_assets(self):
        code, page, _ = self.request_full('/capabilities')
        self.assertEqual(code, 200)
        self.assertIn(b'Sign in', page)
        code, body, _ = self.request_full('/capabilities/eased-entrances.mp4')
        self.assertEqual(code, 401)
        self.assertIn('error', body)

    def test_signed_in_user_with_no_shared_projects_sees_the_page(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, page = self.request('/capabilities', headers={'Cookie': dana})
        self.assertEqual(code, 200)
        self.assertIn(b'Capabilities', page)
        self.assertIn(b'/capabilities/eased-entrances.jpg', page)  # the poster, shown directly on the card
        data = {e['id']: e for e in _embedded_data(page)}
        self.assertTrue(data['eased-entrances']['available'])  # the mp4 URL itself is built by JS on open

    def test_unknown_and_traversal_shaped_ids_404_when_signed_in(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        for bad in ('not-a-real-capability', '..%2f..%2fetc%2fpasswd'):
            code, _ = self.request(f'/capabilities/{bad}.mp4', headers={'Cookie': dana})
            self.assertEqual(code, 404, bad)


if __name__ == '__main__':
    unittest.main()
