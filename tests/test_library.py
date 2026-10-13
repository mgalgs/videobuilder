"""Library routing and smart HTTP with a real git client."""
import base64
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


class LibraryFixture:
    def library_kwargs(self):
        return {}

    def hook(self, hook):
        return hook

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
        self.library = Library(self.root / 'library', unsandboxed_previews=True, envs='current',
                               **self.library_kwargs())
        self.git_requests = []
        def hook(request):
            if request.path.startswith('/git/'):
                self.git_requests.append((request.command, request.headers.get('Transfer-Encoding')))
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.library, self.hook(hook)))
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

    def request_full(self, path, body=None, headers=None, method=None):
        req = urllib.request.Request(self.base + path, method=method or ('POST' if body is not None else 'GET'),
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers or ({'Content-Type': 'application/json'} if body is not None else {}))
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = response.read()
                parsed = json.loads(data) if response.headers.get_content_type() == 'application/json' else data
                return response.status, parsed, response.headers
        except urllib.error.HTTPError as e:
            with e:
                data = e.read()
                parsed = json.loads(data) if e.headers.get_content_type() == 'application/json' else data
                return e.code, parsed, e.headers

    def cookie(self, headers):
        raw = headers.get('Set-Cookie', '')
        return raw.split(';', 1)[0]

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


class HostedGit(LibraryFixture, unittest.TestCase):
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


class Auth(LibraryFixture, unittest.TestCase):
    """Accounts, sessions and per-project access on a library with --admin."""
    ADMIN_PASSWORD = 'adminsecretpw1'

    def library_kwargs(self):
        path = self.root / 'admin-pass'
        path.write_text(self.ADMIN_PASSWORD + '\n')
        return {'admins': [('mgalgs', str(path))]}

    def url(self, name):
        # seed() pushes as a plain git client: give it the admin's Basic credentials.
        return self.base.replace('http://', f'http://mgalgs:{self.ADMIN_PASSWORD}@') + '/git/' + name + '.git'

    def hook(self, hook):
        # A header-based identity (the old proxy_identity pattern): must be ignored
        # once accounts are configured.
        def combined(request):
            hook(request)
            for header in ('X-SV-User', 'X-Forwarded-User', 'Remote-User'):
                if request.headers.get(header):
                    return request.headers[header]
            return None
        return combined

    def login(self, username, password):
        code, data, headers = self.request_full('/api/login', {'username': username, 'password': password})
        return code, data, self.cookie(headers) if code == 200 else None

    def signup(self, username, password, confirm=None):
        body = {'username': username, 'password': password, 'confirm': password if confirm is None else confirm}
        code, data, headers = self.request_full('/api/signup', body)
        return code, data, self.cookie(headers) if code == 200 else None

    def admin_login(self):
        return self.login('mgalgs', self.ADMIN_PASSWORD)[2]

    def new_project(self, cookie, name='acme/launch', source='acme/launch'):
        return self.request(f'/api/library/new', {'from': source, 'name': name}, headers={
            'Content-Type': 'application/json', 'Cookie': cookie})

    def test_unauthenticated_html_get_is_the_signin_page(self):
        code, page, _ = self.request_full('/')
        self.assertEqual(code, 200)
        self.assertIn(b'Sign in', page)
        self.assertIn(b'Sign up', self.request('/signup')[1])

    def test_unauthenticated_api_call_is_401(self):
        self.seed('acme/launch', film=True)
        self.assertEqual(self.request('/v/acme/launch/api/project')[0], 401)

    def test_unauthenticated_git_is_401_with_basic_challenge(self):
        self.seed('acme/launch')
        code, _, headers = self.request_full('/git/acme/launch.git/info/refs?service=git-receive-pack')
        self.assertEqual(code, 401)
        self.assertEqual(headers['WWW-Authenticate'], 'Basic realm="videobuilder"')

    def test_header_identity_is_ignored_without_a_session(self):
        self.seed('acme/launch', film=True)
        code, body = self.request('/v/acme/launch/api/project', headers={'X-Forwarded-User': 'sam'})
        self.assertEqual(code, 401)

    def test_signup_creates_a_working_session(self):
        code, data, cookie = self.signup('dana', 'longenoughpassword')
        self.assertEqual((code, data['name']), (200, 'dana'))
        code, body = self.request('/api/project', headers={'Cookie': cookie})
        # No project context at the library root: a 404 (not the sign-in page) proves the session worked.
        self.assertNotEqual(code, 401)

    def test_signup_refuses_duplicate_admin_and_bad_input(self):
        self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.signup('Dana', 'anotherlongpassword')[0], 400)
        self.assertEqual(self.signup('mgalgs', 'anotherlongpassword')[0], 400)
        self.assertEqual(self.signup('dana2', 'short')[0], 400)
        self.assertEqual(self.signup('d', 'longenoughpassword')[0], 400)

    def test_signup_throttle(self):
        from videobuilder.accounts import SIGNUP_LIMIT
        for i in range(SIGNUP_LIMIT):
            self.assertEqual(self.signup(f'user{i}', 'longenoughpassword')[0], 200)
        self.assertEqual(self.signup('oneover', 'longenoughpassword')[0], 400)

    def test_admin_bootstrap_login_works(self):
        code, data, cookie = self.login('mgalgs', self.ADMIN_PASSWORD)
        self.assertEqual((code, data['name']), (200, 'mgalgs'))
        self.assertIsNotNone(cookie)

    def test_login_bad_password_and_lockout(self):
        self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.login('dana', 'wrong')[0], 401)
        from videobuilder.accounts import LOGIN_LIMIT
        for _ in range(LOGIN_LIMIT - 1):
            self.login('dana', 'wrong')
        code, data, _ = self.login('dana', 'longenoughpassword')
        self.assertEqual(code, 401)
        self.assertIn('too many', data['error'])

    def test_logout_ends_the_session(self):
        _, _, cookie = self.signup('dana', 'longenoughpassword')
        self.request('/api/logout', {}, headers={'Content-Type': 'application/json', 'Cookie': cookie})
        code, _ = self.request('/api/project', headers={'Cookie': cookie})
        self.assertEqual(code, 401)

    def test_noncollaborator_gets_404_everywhere_and_off_the_index(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, outsider = self.signup('outsider', 'longenoughpassword')
        for path in ('/v/acme/launch/', '/v/acme/launch/api/project',
                     '/v/acme/launch/director.js', '/v/acme/launch/tuning.html'):
            self.assertEqual(self.request(path, headers={'Cookie': outsider})[0], 404, path)
        code, _, headers = self.request_full('/git/acme/launch.git/info/refs?service=git-receive-pack',
                                              headers={'Authorization': 'Basic ' + base64.b64encode(
                                                  b'outsider:longenoughpassword').decode()})
        self.assertEqual(code, 404)
        self.assertNotIn(b'acme/launch', self.request('/', headers={'Cookie': outsider})[1])

    def test_invite_grants_and_remove_revokes_next_request(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, collaborator = self.signup('collaborator', 'longenoughpassword')
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': collaborator})[0], 404)
        code, access = self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'collaborator'},
                                    headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual((code, access['collaborators']), (200, ['collaborator']))
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': collaborator})[0], 200)
        code, access = self.request('/v/acme/launch/api/access', {'action': 'remove', 'username': 'collaborator'},
                                    headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual((code, access['collaborators']), (200, []))
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': collaborator})[0], 404)

    def test_invite_unknown_user_404_and_collaborator_cannot_share(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'nosuchuser'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        code, err = self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'nosuchuser'},
                                 headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 404)
        _, _, collaborator = self.signup('collaborator', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'collaborator'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        code, err = self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'someone'},
                                 headers={'Content-Type': 'application/json', 'Cookie': collaborator})
        self.assertEqual(code, 403)

    def test_only_admin_creates_project_and_owns_it(self):
        self.seed('acme/launch')
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.new_project(dana, 'acme/copy1', 'acme/launch')[0], 403)
        admin = self.admin_login()
        code, result = self.new_project(admin, 'acme/copy2', 'acme/launch')
        self.assertEqual(code, 201)
        code, access = self.request('/v/acme/copy2/api/access', headers={'Cookie': admin})
        self.assertEqual((code, access['owner']), (200, 'mgalgs'))

    def test_deleting_a_user_invalidates_their_outstanding_session(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.request('/api/project', headers={'Cookie': dana})[0], 404)
        # The operator deletes the account by hand (with the editor stopped) and restarts;
        # simulate that here by dropping the record from the in-memory store a restart
        # would have reloaded without it. The old cookie must stop working.
        del self.library.accounts._data['users']['dana']
        self.library.accounts._save()
        code, _ = self.request('/api/project', headers={'Cookie': dana})
        self.assertEqual(code, 401)

    def test_deleted_users_access_does_not_transfer_to_a_reused_name(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': bob})[0], 200)
        # The operator deletes bob's account (with the editor stopped) and restarts;
        # simulate that, then let an unrelated person sign up under the freed name.
        del self.library.accounts._data['users']['bob']
        self.library.accounts._save()
        _, _, impostor = self.signup('bob', 'anotherlongpassword')
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': impostor})[0], 404)
        code, access = self.request('/v/acme/launch/api/access', headers={'Cookie': admin})
        self.assertEqual((code, access['collaborators']), (200, []))
        # The impostor's account still exists under the freed name: re-inviting it
        # must grant the new account, not silently no-op against the stale entry.
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': impostor})[0], 200)
        code, access = self.request('/v/acme/launch/api/access', headers={'Cookie': admin})
        self.assertEqual((code, access['collaborators']), (200, ['bob']))

    def test_note_author_and_directed_by_are_the_username(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.library.editor('acme/launch').notes.backend = FakeBackend(delay=0)
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual((code, note['author']), (200, 'mgalgs'))
        self.request('/v/acme/launch/api/notes', headers={'Cookie': admin})
        log = self.git('show', '-s', '--format=%B', 'HEAD', cwd=self.library.checkouts / 'acme--launch').stdout
        self.assertIn('Directed-by: mgalgs', log)

    def test_api_name_reflects_login(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.request('/api/name', headers={'Cookie': dana})[1], {'name': 'dana'})
        code, err = self.request('/api/name', {'name': 'Someone'},
                                 headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 409)


if __name__ == '__main__':
    unittest.main()
