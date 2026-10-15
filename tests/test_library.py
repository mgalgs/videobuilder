"""Library routing and smart HTTP with a real git client."""
import base64
import http.client
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
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
        work = self.root / 'author' / name.replace('/', '--')
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

    def test_pushed_config_cannot_configure_the_editor(self):
        work = self.root / 'author'
        self.git('init', '-b', 'main', str(work))
        (work / 'videobuilder.toml').write_text(
            '[editor]\nunsandboxed_previews = true\nallowed_hosts = ["evil.example"]\n'
            'auto_land = false\nrender_jobs = 64\n'
            '[editor.agent]\nbackend = "command"\nsubmit_command = ["sh", "-c", "touch pwned"]\n'
            'poll_command = ["true"]\nexecutable = "/bin/sh"\nsubmit_args = ["-c", "touch pwned"]\n')
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'first', cwd=work)
        self.git('remote', 'add', 'origin', self.url('acme/launch'), cwd=work)
        self.git('push', '-u', 'origin', 'main', cwd=work)
        library = Library(self.root / 'library2', envs='current')
        self.addCleanup(library.close)
        # Seed the second library from the first one's bare repo.
        library.path('acme/launch').parent.mkdir(parents=True)
        self.git('clone', '--bare', str(self.library.path('acme/launch')), str(library.path('acme/launch')))
        editor = library.editor('acme/launch')
        self.assertFalse(editor.unsandboxed_previews)
        self.assertNotIn('evil.example', editor.allowed_hosts)
        self.assertEqual(type(editor.notes.backend).__name__, 'NullBackend')
        self.assertFalse(editor.auto_land)
        # As deployed: the operator picks the backend, and the repo must not fill in the rest.
        library3 = Library(self.root / 'library3', envs='current', agent={'backend': 'fork-sandbox'})
        self.addCleanup(library3.close)
        library3.path('acme/launch').parent.mkdir(parents=True)
        self.git('clone', '--bare', str(self.library.path('acme/launch')), str(library3.path('acme/launch')))
        backend = library3.editor('acme/launch').notes.backend
        self.assertEqual((backend.executable, backend.submit_args), ('fork-sandbox', ['run']))

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

    def test_library_page_shows_a_new_video_button_and_card_per_video(self):
        self.seed('acme/launch')
        page = self.request('/')[1]
        self.assertIn(b'New video', page)
        self.assertIn(b'href="/new"', page)
        self.assertIn(b'lib-card', page)
        self.assertIn(b'acme/launch', page)

    def test_new_video_page_is_reachable_without_accounts(self):
        code, page = self.request('/new')
        self.assertEqual(code, 200)
        self.assertIn(b'id="new-video"', page)
        self.assertIn(b'name="start"', page)
        self.assertIn(b'name="description"', page)
        self.assertIn(b'name="links"', page)

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

    def test_blank_start_has_one_commit_pinned_to_the_editors_version(self):
        from videobuilder import __version__
        code, result = self.request('/api/videos/new', {'name': 'acme/blank', 'start': 'blank'})
        self.assertEqual((code, result['video']), (201, 'film'))
        clone = self.root / 'blank-clone'
        self.git('clone', self.url('acme/blank'), str(clone))
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')
        self.assertEqual((clone / 'requirements.txt').read_text(), f'videobuilder=={__version__}\n')
        self.assertTrue((clone / 'film.py').is_file())
        # The new video is actually buildable: Project discovers it as a real video.
        code, info = self.request('/v/acme/blank/api/project')
        self.assertEqual((code, [v['id'] for v in info['videos']]), (200, ['film']))

    def test_blank_start_refuses_an_existing_name(self):
        self.request('/api/videos/new', {'name': 'acme/dup', 'start': 'blank'})
        code, err = self.request('/api/videos/new', {'name': 'acme/dup', 'start': 'blank'})
        self.assertEqual(code, 400)

    def test_copy_start_still_works_through_the_new_route(self):
        self.seed('acme/launch', film=True)
        code, result = self.request('/api/videos/new', {'name': 'acme/copy', 'start': 'copy', 'from': 'acme/launch'})
        self.assertEqual((code, result['video']), (201, None))
        clone = self.root / 'copy-clone'
        self.git('clone', self.url('acme/copy'), str(clone))
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')

    def test_first_note_carries_description_attachments_and_a_gathering_failure_line(self):
        from videobuilder.agents import FakeBackend
        self.request('/api/videos/new', {'name': 'acme/scratch', 'start': 'blank'})
        self.library.editor('acme/scratch').notes.backend = FakeBackend(delay=0)
        import urllib.request
        req = urllib.request.Request(self.base + '/v/acme/scratch/api/attachments?video=film&name=brief.txt',
                                     data=b'notes for the builder', method='POST',
                                     headers={'Content-Type': 'text/plain'})
        with urllib.request.urlopen(req, timeout=20) as r:
            attach = json.loads(r.read())
        code, note = self.request('/v/acme/scratch/api/videos/first-note', {
            'description': 'A marketing video for the launch.',
            'attachments': [attach['id']],
            'links': ['http://127.0.0.1:1/unreachable'],
        })
        # The note is created right away, before the (possibly slow) crawl runs, so the
        # call returns the placeholder: 'gathering', with the brief already on it.
        self.assertEqual(code, 200, note)
        self.assertEqual(note['state'], 'gathering')
        self.assertEqual(note['text'], 'A marketing video for the launch.')
        note = self.wait_for_note(note['id'], lambda n: n['state'] != 'gathering')
        self.assertIn('A marketing video for the launch.', note['text'])
        self.assertIn('Some pages were not gathered', note['text'])
        names = {a['name'] for a in note['attachments']}
        self.assertIn('brief.txt', names)
        self.assertIn('gathered-pages.md', names)
        # Left 'gathering' for the normal dispatch states; a FakeBackend with no
        # delay can race straight through 'queued'/'working' to a final state.
        self.assertNotEqual(note['state'], 'gathering')

    def wait_for_note(self, nid, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        note = None
        while time.monotonic() < deadline:
            _, notes = self.request('/v/acme/scratch/api/notes?video=film')
            note = next((n for n in notes['notes'] if n['id'] == nid), None)
            if note is not None and predicate(note):
                return note
            time.sleep(0.05)
        self.fail(f'note {nid} did not reach the expected state in time: {note}')

    def test_first_note_without_links_queues_immediately(self):
        from videobuilder.agents import FakeBackend
        self.request('/api/videos/new', {'name': 'acme/no-links', 'start': 'blank'})
        self.library.editor('acme/no-links').notes.backend = FakeBackend(delay=0)
        code, note = self.request('/v/acme/no-links/api/videos/first-note', {'description': 'Simple brief.'})
        self.assertEqual(code, 200, note)
        self.assertIn('Simple brief.', note['text'])
        self.assertEqual(note['attachments'], [])

    def test_first_note_refuses_malformed_links(self):
        self.request('/api/videos/new', {'name': 'acme/bad-links', 'start': 'blank'})
        # A non-string element must be refused with 400, not crash with a 500 when
        # the route tries to .strip() it.
        code, err = self.request('/v/acme/bad-links/api/videos/first-note', {'links': [1]})
        self.assertEqual(code, 400, err)
        # A bare string must be refused, not silently iterated into one-character "links".
        code, err = self.request('/v/acme/bad-links/api/videos/first-note', {'links': 'https://a.example'})
        self.assertEqual(code, 400, err)


class AccountMixin:
    """Shared accounts/session setup for Auth, Keys and AccountPage: not itself a TestCase."""
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


class Auth(AccountMixin, LibraryFixture, unittest.TestCase):
    """Accounts, sessions and per-project access on a library with --admin."""

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
                     '/v/acme/launch/director.js', '/v/acme/launch/tuning.html',
                     '/v/acme/launch/api/music/sources'):
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

    def test_any_signed_in_user_starts_a_video_and_owns_it(self):
        # Unlike /api/library/new (admin-only, above), /api/videos/new -- the New Video
        # page's own route -- is open to any signed-in user, who becomes its owner.
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, result = self.request('/api/videos/new', {'name': 'acme/dana-video', 'start': 'blank'},
                                    headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 201, result)
        code, access = self.request('/v/acme/dana-video/api/access', headers={'Cookie': dana})
        self.assertEqual((code, access['owner']), (200, 'dana'))

    def test_copy_start_refuses_a_source_the_user_cannot_access(self):
        # Unlike /api/library/new (admin-only, so admins always have access to
        # the source), start:"copy" on /api/videos/new is open to any signed-in
        # user and must not let them copy a private project they have no access to.
        self.seed('secret/private', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'secret/private', 'secret/private')
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.request('/v/secret/private/api/project', headers={'Cookie': dana})[0], 404)
        code, result = self.request('/api/videos/new', {'name': 'dana/stolen', 'start': 'copy',
                                                         'from': 'secret/private'},
                                    headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 404, result)
        self.assertFalse(self.library.path('dana/stolen').exists())

    def test_anonymous_cannot_start_a_video(self):
        code, _ = self.request('/api/videos/new', {'name': 'acme/anon-video', 'start': 'blank'})
        self.assertEqual(code, 401)
        self.assertFalse(self.library.path('acme/anon-video').exists())

    def test_new_video_page_requires_sign_in_with_accounts_on(self):
        code, page, _ = self.request_full('/new')
        self.assertEqual(code, 200)
        self.assertIn(b'Sign in', page)
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, page = self.request('/new', headers={'Cookie': dana})
        self.assertEqual(code, 200)
        self.assertIn(b'id="new-video"', page)

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

    def test_log_route_refuses_a_non_collaborator(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, note)
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, _ = self.request(f'/v/acme/launch/api/notes/{note["id"]}/log', headers={'Cookie': dana})
        self.assertEqual(code, 404)

    def test_answer_route_refuses_a_non_collaborator(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0, questions=[{'text': 'Light or dark logo?',
                                                                 'choices': ['Light', 'Dark']}])
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Make it pop'},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, note)
        self.request(f'/v/acme/launch/api/notes', headers={'Cookie': admin})
        self.assertEqual(editor.notes.get(note['id'])['state'], 'questions')
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, _ = self.request(f'/v/acme/launch/api/notes/{note["id"]}/answer', {'answers': ['Dark']},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 404)

    def test_log_route_hides_cost_from_a_non_admin_collaborator(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, note)
        editor = self.library.editor('acme/launch')
        stored = editor.notes.get(note['id'])
        handle_dir = editor.notes.session_dir('promo/film') / 'run'
        handle_dir.mkdir()
        (handle_dir / 'events.jsonl').write_text(json.dumps(
            {'type': 'result', 'num_turns': 2, 'duration_ms': 1000, 'total_cost_usd': 4.5}) + '\n')
        stored['handle'] = str(handle_dir)
        editor.notes._save(stored)
        code, as_bob = self.request(f'/v/acme/launch/api/notes/{note["id"]}/log', headers={'Cookie': bob})
        self.assertEqual(code, 200)
        code, as_admin = self.request(f'/v/acme/launch/api/notes/{note["id"]}/log', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        bob_result = next(e for e in as_bob['entries'] if e['kind'] == 'result')
        admin_result = next(e for e in as_admin['entries'] if e['kind'] == 'result')
        self.assertEqual(bob_result['text'], '2 turns · 1s')
        self.assertEqual(admin_result['text'], '2 turns · 1s · $4.50')

    def test_api_name_reflects_login(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.assertEqual(self.request('/api/name', headers={'Cookie': dana})[1], {'name': 'dana'})
        code, err = self.request('/api/name', {'name': 'Someone'},
                                 headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 409)


class KeyMixin:
    """Shared key-request helpers for Keys and AccountPage: not itself a TestCase."""

    def bearer(self, secret):
        return {'Authorization': 'Bearer ' + secret}

    def git_key_url(self, name, secret):
        return self.base.replace('http://', f'http://x:{secret}@') + '/git/' + name + '.git'


class Keys(AccountMixin, KeyMixin, LibraryFixture, unittest.TestCase):
    """Per-account API keys: git over HTTP, the video API, scope, mode and attribution."""

    def test_git_clone_fetch_with_read_key_works_and_push_is_refused(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'reader', None, 'read')
        clone = self.root / 'read-clone'
        self.git('clone', self.git_key_url('acme/launch', secret), str(clone))
        self.assertEqual((clone / 'README.md').read_text(), 'first\n')
        (clone / 'extra').write_text('extra')
        self.git('add', '.', cwd=clone)
        self.git('commit', '-m', 'extra', cwd=clone)
        result = self.git('push', cwd=clone, ok=False)
        self.assertNotEqual(result.returncode, 0)

    def test_git_push_with_write_key_works_and_stays_fast_forward_only(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        clone = self.root / 'write-clone'
        self.git('clone', self.git_key_url('acme/launch', secret), str(clone))
        stale = self.root / 'stale-clone'
        self.git('clone', self.git_key_url('acme/launch', secret), str(stale))
        (clone / 'extra').write_text('extra')
        self.git('add', '.', cwd=clone)
        self.git('commit', '-m', 'extra', cwd=clone)
        self.git('push', cwd=clone)
        (stale / 'stale').write_text('stale')
        self.git('add', '.', cwd=stale)
        self.git('commit', '-m', 'stale', cwd=stale)
        self.assertNotEqual(self.git('push', cwd=stale, ok=False).returncode, 0)

    def test_bearer_get_and_post_work_for_write_post_refused_for_read(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, write_secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        _, read_secret = self.library.accounts.create_key('mgalgs', 'reader', None, 'read')
        self.assertEqual(self.request('/v/acme/launch/api/project', headers=self.bearer(read_secret))[0], 200)
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', **self.bearer(write_secret)})
        self.assertEqual(code, 200, note)
        code, err = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                 headers={'Content-Type': 'application/json', **self.bearer(read_secret)})
        self.assertEqual(code, 403)

    def test_scope_refuses_another_namespace(self):
        self.seed('acme/launch', film=True)
        self.seed('gardening/promo', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.new_project(admin, 'gardening/promo', 'gardening/promo')
        _, secret = self.library.accounts.create_key('mgalgs', 'scoped', 'gardening', 'write')
        self.assertEqual(self.request('/v/gardening/promo/api/project', headers=self.bearer(secret))[0], 200)
        self.assertEqual(self.request('/v/acme/launch/api/project', headers=self.bearer(secret))[0], 404)
        code, _, headers = self.request_full(
            '/git/acme/launch.git/info/refs?service=git-receive-pack', headers=self.bearer(secret))
        # Git never accepts a bearer header; this key must act only through Basic auth there.
        self.assertIn(code, (401, 404))

    def test_scope_refuses_a_top_level_project_named_like_the_scope(self):
        # 'gardening' is a valid single-part project name in its own right, distinct from the
        # 'gardening/...' namespace: a key scoped to 'gardening' must not reach it.
        self.seed('gardening', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'gardening', 'gardening')
        _, secret = self.library.accounts.create_key('mgalgs', 'scoped', 'gardening', 'write')
        self.assertEqual(self.request('/v/gardening/api/project', headers=self.bearer(secret))[0], 404)
        basic = {'Authorization': 'Basic ' + base64.b64encode(f'x:{secret}'.encode()).decode()}
        code, _, _ = self.request_full('/git/gardening.git/info/refs?service=git-receive-pack', headers=basic)
        self.assertEqual(code, 404)

    def test_key_refused_on_api_library_new(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        self.assertNotEqual(self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/copy'},
                                         headers={'Content-Type': 'application/json', **self.bearer(secret)})[0], 201)

    def test_scope_excludes_access_management_even_though_it_is_under_api(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        self.assertEqual(self.request('/v/acme/launch/api/access', headers=self.bearer(secret))[0], 401)

    def test_password_not_prefixed_vbk_still_checks_password_and_locks_out(self):
        self.seed('acme/launch')
        from videobuilder.accounts import LOGIN_LIMIT
        import base64
        def basic(password):
            return {'Authorization': 'Basic ' + base64.b64encode(f'mgalgs:{password}'.encode()).decode()}
        for _ in range(LOGIN_LIMIT):
            code, _, _ = self.request_full('/git/acme/launch.git/info/refs?service=git-receive-pack',
                                           headers=basic('wrong'))
            self.assertEqual(code, 401)
        with self.assertRaises(ValueError) as caught:
            self.library.accounts.verify('mgalgs', self.ADMIN_PASSWORD)
        self.assertIn('too many attempts', str(caught.exception))

    def test_session_cookie_plus_bad_bearer_key_is_refused(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        code, _ = self.request('/v/acme/launch/api/project',
                               headers={'Cookie': admin, 'Authorization': 'Bearer vbk_notarealkey'})
        self.assertEqual(code, 401)

    def test_note_author_and_directed_by_trailer_show_key_attribution(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.library.editor('acme/launch').notes.backend = FakeBackend(delay=0)
        _, secret = self.library.accounts.create_key('mgalgs', 'claude explainer-videos', None, 'write')
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual((code, note['author']), (200, 'mgalgs (claude explainer-videos)'))
        self.request('/v/acme/launch/api/notes', headers=self.bearer(secret))
        log = self.git('show', '-s', '--format=%B', 'HEAD', cwd=self.library.checkouts / 'acme--launch').stdout
        self.assertIn('Directed-by: mgalgs (claude explainer-videos)', log)


if __name__ == '__main__':
    unittest.main()
