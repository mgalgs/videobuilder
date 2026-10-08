"""Library routing and smart HTTP with a real git client."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from videobuilder.editor import make_handler
from videobuilder.library import Library, valid_name
from tests.test_project import FILM


class HostedGit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.com',
                    'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.com'}
        self.library = Library(self.root / 'library', unsandboxed_previews=True, envs='current')
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.library))
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.start()
        self.addCleanup(self.library.close)
        self.addCleanup(self.thread.join)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def git(self, *args, cwd=None, ok=True):
        result = subprocess.run(['git', *args], cwd=cwd or self.root, env=self.env,
                                capture_output=True, text=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def url(self, name):
        return self.base + '/git/' + name + '.git'

    def request(self, path, body=None, headers=None):
        req = urllib.request.Request(self.base + path, method='POST' if body is not None else 'GET',
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers or ({'Content-Type': 'application/json'} if body is not None else {}))
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = response.read()
                return response.status, json.loads(data) if response.headers.get_content_type() == 'application/json' else data
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def seed(self, name='acme/launch', film=False):
        work = self.root / 'author'
        self.git('init', '-b', 'main', str(work))
        (work / 'README.md').write_text('first\n')
        if film:
            (work / 'promo').mkdir()
            (work / 'promo' / 'film.py').write_text(FILM)
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'first', cwd=work)
        self.git('remote', 'add', 'origin', self.url(name), cwd=work)
        self.git('push', '-u', 'origin', 'main', cwd=work)
        return work

    def test_git_roundtrip_and_routes(self):
        self.assertEqual(self.request('/git/acme/launch.git/info/refs?service=git-upload-pack')[0], 404)
        work = self.seed()
        self.assertTrue(self.library.has_main('acme/launch'))
        self.assertIn(b'acme/launch', self.request('/')[1])
        self.assertIn(self.url('acme/launch').encode(), self.request('/')[1])
        self.assertEqual(self.request('/v/acme/launch/api/project')[0], 200)
        self.assertIn(b'videobuilder editor', self.request('/v/acme/launch/')[1])
        clone = self.root / 'clone'
        self.git('clone', self.url('acme/launch'), str(clone))
        self.assertEqual((clone / 'README.md').read_text(), 'first\n')
        (work / 'big.bin').write_bytes(os.urandom(100_000))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'large', cwd=work)
        self.git('-c', 'http.postBuffer=1024', 'push', cwd=work)
        self.git('fetch', 'origin', cwd=clone)
        self.git('merge', '--ff-only', 'origin/main', cwd=clone)
        self.assertEqual((clone / 'big.bin').read_bytes(), (work / 'big.bin').read_bytes())
        self.assertTrue((self.library.checkouts / 'acme--launch' / 'big.bin').exists())
        (clone / 'other').write_text('other')
        self.git('add', '.', cwd=clone)
        self.git('commit', '-m', 'other', cwd=clone)
        self.git('push', cwd=clone)
        (work / 'stale').write_text('stale')
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'stale', cwd=work)
        self.assertNotEqual(self.git('push', cwd=work, ok=False).returncode, 0)
        self.assertNotEqual(self.git('push', 'origin', ':main', cwd=work, ok=False).returncode, 0)

    def test_copy_and_validation(self):
        self.seed()
        code, result = self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/promo'})
        self.assertEqual(code, 201, result)
        self.assertNotEqual(result['commit'], result['source_commit'])
        clone = self.root / 'copy'
        self.git('clone', self.url('acme/promo'), str(clone))
        self.assertEqual((clone / 'README.md').read_text(), 'first\n')
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')
        self.assertIn('acme/launch', self.git('log', '-1', '--format=%s', cwd=clone).stdout)
        for name in ('../bad', 'acme/x.git', 'acme/../bad', 'a//b', 'UPPER', 'a/b/c'):
            self.assertFalse(valid_name(name))
            self.assertEqual(self.request('/api/library/new', {'from': 'acme/launch', 'name': name})[0], 400)
            self.assertEqual(self.request('/git/' + name + '.git/info/refs?service=git-receive-pack')[0], 404)
        self.assertEqual(self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/promo'})[0], 400)

    def test_ui_edit_is_in_fresh_clone(self):
        self.seed(film=True)
        code, result = self.request('/v/acme/launch/api/copy',
                                    {'video': 'promo/film', 'segment': 'intro', 'key': 'title', 'value': 'Updated'})
        self.assertEqual(code, 200, result)
        self.assertTrue(result['commit'])
        clone = self.root / 'edited'
        self.git('clone', self.url('acme/launch'), str(clone))
        self.assertIn('Updated', (clone / 'promo' / 'film.edits.toml').read_text())

    def test_host_rule_on_git(self):
        code, _ = self.request('/git/acme/launch.git/info/refs?service=git-receive-pack',
                               headers={'Host': 'other.example'})
        self.assertEqual(code, 403)
        self.assertFalse(self.library.path('acme/launch').exists())


if __name__ == '__main__':
    unittest.main()
