"""Library routing and smart HTTP with a real git client."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
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
        # The editor runs git in-process: give it this env, not the host's git config.
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.library =Library(self.root / 'library', unsandboxed_previews=True, envs='current')
        self.git_requests = []
        def hook(request):
            if request.path.startswith('/git/'):
                self.git_requests.append((request.command, request.headers.get('Transfer-Encoding')))
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.library, hook))
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
        self.assertIn(('POST', 'chunked'), self.git_requests)
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
        self.assertNotEqual(self.git('push', '--force', cwd=work, ok=False).returncode, 0)
        self.assertNotEqual(self.git('push', 'origin', ':main', cwd=work, ok=False).returncode, 0)

    def test_director_assets_under_video_path(self):
        self.seed(film=True)
        for path, marker in (('', b'id="player"'), ('tuning.html', b'id="tl"'),
                             ('director.js', b'loadVersions'), ('director.css', b'.panel')):
            code, body = self.request('/v/acme/launch/' + path)
            self.assertEqual(code, 200, path)
            self.assertIn(marker, body)

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

    def test_tick_reopens_only_repos_with_pending_notes(self):
        from videobuilder.agents import FakeBackend
        self.library.options['backend'] = FakeBackend(delay=0)
        self.seed(film=True)
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Highlight'})
        self.assertEqual(code, 200, note)

        def forget():
            editor = self.library.editors.pop('acme/launch')
            editor.renders.close()
            editor.pool.close()
        forget()
        self.library.tick()
        self.assertEqual(self.library.editors['acme/launch'].notes.get(note['id'])['state'], 'landed')
        forget()
        self.library.tick()
        self.assertNotIn('acme/launch', self.library.editors)

    def test_host_rule_on_git(self):
        code, _ = self.request('/git/acme/launch.git/info/refs?service=git-receive-pack',
                               headers={'Host': 'other.example'})
        self.assertEqual(code, 403)
        self.assertFalse(self.library.path('acme/launch').exists())

    def test_only_a_git_client_creates_a_repo(self):
        self.assertEqual(self.request('/git/acme/drive-by.git/info/refs?service=git-receive-pack',
                                      headers={'User-Agent': 'Mozilla/5.0'})[0], 404)
        self.assertFalse(self.library.path('acme/drive-by').exists())

    def test_trailing_slash_redirect_and_https_clone_url(self):
        self.seed()
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1], timeout=20)
        self.addCleanup(conn.close)
        conn.request('GET', '/v/acme/launch')
        response = conn.getresponse()
        response.read()
        self.assertEqual((response.status, response.headers['Location']), (301, '/v/acme/launch/'))
        page = self.request('/', headers={'X-Forwarded-Proto': 'https'})[1]
        self.assertIn(b'https://127.0.0.1:', page)

    def test_repos_share_one_env_cache(self):
        self.seed('acme/launch')
        self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/promo'})
        self.assertIs(self.library.editor('acme/launch').envs, self.library.editor('acme/promo').envs)

    def test_empty_repo_is_listed_but_cannot_open_or_copy(self):
        self.assertEqual(self.request('/git/acme/empty.git/info/refs?service=git-receive-pack',
                                      headers={'User-Agent': 'git/2.50.0'})[0], 200)
        self.assertIn(b'Empty', self.request('/')[1])
        self.assertEqual(self.request('/v/acme/empty/')[0], 404)
        self.assertEqual(self.request('/api/library/new', {'from': 'acme/empty', 'name': 'another'})[0], 400)


if __name__ == '__main__':
    unittest.main()
