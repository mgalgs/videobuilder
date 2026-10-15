"""Shared TestCase base classes reused by more than one test_*.py module.

Not itself named test_*.py, so pytest's test-file discovery never scans it
directly: each class below is collected exactly once, in whichever test_*.py
module binds its name at module level. A module that only needs to subclass
one of these must reference it as `fixtures.API` / `fixtures.Auth` rather
than `from tests.fixtures import API`, or pytest's unittest collector picks
up that second bare name too and reruns every inherited test a second time.
"""
import base64
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from videobuilder.editor import Editor, Forbidden, make_handler
from videobuilder.library import Library

from tests.test_project import FILM, TempProject, git


class API(TempProject):
    def tearDown(self):
        self.editor.renders.close()
        super().tearDown()

    def start(self, **kw):
        hook = kw.pop('hook', None)
        self.editor = Editor(self.root, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)
        handler = make_handler(self.editor, hook) if hook else make_handler(self.editor)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def setUp(self):
        super().setUp()
        self.start()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            body = r.read()
            return json.loads(body) if r.headers.get('Content-Type') == 'application/json' else body

    def post(self, path, body, headers=None):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(), method='POST',
                                     headers=headers or {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_healthz_ignores_host_allowlist(self):
        req = urllib.request.Request(self.base + '/healthz', headers={'Host': 'kubelet.invalid'})
        with urllib.request.urlopen(req) as response:
            from videobuilder import __version__
            self.assertEqual((response.status, response.read()), (200, b'ok ' + __version__.encode()))

    def test_page_and_project(self):
        page = self.get('/')
        self.assertIn(b'videobuilder editor', page)
        self.assertNotIn(b'http://', page.replace(b'http://www.w3.org', b''))  # nothing from a CDN
        p = self.get('/api/project')
        self.assertEqual((p['name'], p['git'], p['backend'], p['error']), ('project', True, 'null', None))
        self.assertEqual(p['videos'], [{'id': 'promo/film', 'path': 'promo/film.py',
                                        'edits': 'promo/film.edits.toml', 'pin': "editor's own",
                                        'env': 'ready', 'error': None, 'upgrade': None}])
        self.assertEqual(p['state_dir'], str(self.root / '.vb-editor'))
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')  # the state dir ignores itself

    def test_info_and_frame(self):
        info = self.get('/api/info?video=promo/film')
        self.assertEqual((info['video'], info['edits_file'], info['git'], info['undo'], info['error']),
                         ('promo/film', 'promo/film.edits.toml', {'repo': True, 'state': 'clean'}, None, None))
        self.assertEqual([(s['name'], s['rollable'], s['copy']) for s in info['timeline']['segments']],
                         [('intro', True, {'title': 'Hello'}), ('body', False, {'line': 'Body copy'}),
                          ('c1', True, {}), ('c2', False, {}), ('close', False, {})])
        self.assertEqual(info['timeline']['groups'][0]['copy'], {'head': 'Cuts'})
        png = self.get('/api/frame?video=promo/film&frame=10&format=1x1&scale=0.25')
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual((int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')), (270, 270))
        for path, code in (('/api/info?video=nope', 404), ('/api/info', 400), ('/api/nothing', 404),
                           ('/api/frame?video=promo/film&format=4x3', 400)):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as e:
                self.get(path)
            e.exception.close()
            self.assertEqual(e.exception.code, code)

    def test_roll_copy_refusal_and_undo(self):
        code, r = self.post('/api/roll', {'video': 'promo/film', 'segment': 'intro', 'until': 6})
        self.assertEqual(code, 200, r)
        self.assertEqual(r['message'], 'edit(promo/film): roll intro to beat 6')
        self.assertEqual(r['commit'], git(self.root, 'rev-parse', 'HEAD').strip())
        info = self.get('/api/info?video=promo/film')
        self.assertEqual(info['timeline']['cuts'][1], 90)  # reloaded at once
        self.assertEqual(info['undo'], {'op': 'roll', 'segment': 'intro', 'value': 4})
        self.assertEqual(info['edits']['segments'], {'intro': {'until': 6}})

        code, r = self.post('/api/roll', {'video': 'promo/film', 'segment': 'intro', 'until': 6.25})
        self.assertEqual((code, r), (400, {'error': 'segment intro: until 6.25 is off the half-beat grid'}))
        code, r = self.post('/api/copy', {'video': 'promo/film', 'segment': 'cuts', 'key': 'head', 'value': 'Quick'})
        self.assertEqual((code, r['message']), (200, 'edit(promo/film): copy cuts.head'))
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['groups'][0]['copy'], {'head': 'Quick'})
        code, r = self.post('/api/undo', {'video': 'promo/film'})
        self.assertEqual((code, r['message'], r['undo']), (200, 'edit(promo/film): copy cuts.head (undo)', None))
        self.assertEqual(self.log(), ['edit(promo/film): copy cuts.head (undo)', 'edit(promo/film): copy cuts.head',
                                      'edit(promo/film): roll intro to beat 6', 'init'])
        self.assertEqual(self.post('/api/undo', {'video': 'promo/film'}), (400, {'error': 'nothing to undo'}))
        for body in ({'video': 'promo/film', 'segment': 'intro'}, {'video': 'promo/film', 'segment': 'intro', 'until': 'x'},
                     {'segment': 'intro', 'until': 5}):
            with self.subTest(body=body):
                self.assertEqual(self.post('/api/roll', body)[0], 400)
        self.assertEqual(self.post('/api/roll', {'video': 'nope', 'segment': 'intro', 'until': 5})[0], 404)

    def test_posts_must_be_json_from_this_origin(self):
        body = {'video': 'promo/film', 'segment': 'intro', 'until': 6}
        self.assertEqual(self.post('/api/roll', body, {'Content-Type': 'text/plain'})[0], 415)
        code, r = self.post('/api/roll', body, {'Content-Type': 'application/json', 'Origin': 'http://elsewhere.example'})
        self.assertEqual((code, r['error']), (403, 'cross-origin request refused'))
        same = self.base.removeprefix('http://')
        self.assertEqual(self.post('/api/roll', body, {'Content-Type': 'application/json',
                                                       'Origin': f'http://{same}'})[0], 200)
        self.assertEqual(self.log(), ['edit(promo/film): roll intro to beat 6', 'init'])

    def test_body_limits_and_malformed_json(self):
        from videobuilder.editor import MAX_BODY

        def status(data):
            req = urllib.request.Request(self.base + '/api/roll', data=data, method='POST',
                                         headers={'Content-Type': 'application/json'})
            try:
                urllib.request.urlopen(req, timeout=20)
            except urllib.error.HTTPError as e:
                with e:
                    return e.code
        self.assertEqual(status(b'{not json'), 400)
        self.assertEqual(status(b'[1, 2, 3]'), 400)
        self.assertEqual(status(b'"a string"'), 400)

        # 413 is decided from Content-Length alone, before the body is read: claim one
        # over the limit without actually sending it (over a real socket, the server
        # would otherwise answer before the client finishes writing a 1MiB+ body).
        import http.client
        host, _, port = self.base.removeprefix('http://').partition(':')
        conn = http.client.HTTPConnection(host, int(port), timeout=20)
        self.addCleanup(conn.close)
        conn.putrequest('POST', '/api/roll')
        conn.putheader('Content-Type', 'application/json')
        conn.putheader('Content-Length', str(MAX_BODY + 1))
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        response.read()

    def test_note_id_path_traversal_refused_through_the_http_route(self):
        for bad in ('..', '..%2fescape', '%2e%2e%2fescape'):
            with self.subTest(bad=bad), self.assertRaises(urllib.error.HTTPError) as e:
                self.get(f'/api/notes/{bad}')
            with e.exception:
                self.assertEqual(e.exception.code, 404)

    def test_notes(self):
        code, n = self.post('/api/notes', {'video': 'promo/film', 'format': '1x1', 'frame': 70, 'text': 'Too fast'})
        self.assertEqual(code, 200, n)
        self.assertEqual((n['video'], n['format'], n['frame'], n['segment'], n['text'], n['state'], n['author']),
                         ('promo/film', '1x1', 70, 'body', 'Too fast', 'queued', 'anonymous'))
        png = self.get(f'/api/notes/{n["id"]}.png')
        self.assertEqual((int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')), (540, 540))
        self.assertTrue((self.root / '.vb-editor' / 'notes' / f'{n["id"]}.json').exists())
        self.assertEqual(self.get(f'/api/notes/{n["id"]}'), n)
        self.assertEqual([x['id'] for x in self.get('/api/notes?video=promo/film')['notes']], [n['id']])
        self.assertEqual(self.get('/api/notes?video=other')['notes'], [])
        code, d = self.post('/api/notes', {'video': 'promo/film', 'frame': 9999, 'text': 'the end'})
        self.assertEqual((d['frame'], d['format'], d['segment']), (209, '16x9', 'close'))  # clamped, default format
        self.assertEqual(self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': ''})[0], 400)
        self.assertEqual(self.post(f'/api/notes/{n["id"]}/delete', {}), (200, {'deleted': n['id']}))
        self.assertEqual(self.post(f'/api/notes/{n["id"]}/delete', {})[0], 404)
        self.assertEqual(len(self.get('/api/notes')['notes']), 1)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')  # notes stay out of git

    def test_questions_state_and_answer_route(self):
        from videobuilder.agents import FakeBackend
        git(self.root, 'branch', '-M', 'main')
        self.editor.notes.backend = FakeBackend(delay=0, questions=[
            {'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
            {'text': 'Any specific tagline?'}])
        code, note = self.post('/api/notes', dict(video='promo/film', frame=0, text='Make the logo pop'))
        self.assertEqual(code, 200, note)
        self.get('/api/notes')
        stored = self.get(f'/api/notes/{note["id"]}')
        self.assertEqual(stored['state'], 'questions')
        self.assertEqual(stored['questions'], [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
                                               {'text': 'Any specific tagline?', 'choices': []}])
        self.assertNotIn('```questions', stored['reply'] or '')
        self.assertNotIn('version', stored)

        code, followup = self.post(f'/api/notes/{note["id"]}/answer',
                                   {'answers': ['Dark', 'Keep it short']})
        self.assertEqual(code, 200, followup)
        self.assertIn('Light or dark logo?', followup['text'])
        self.assertIn('Dark', followup['text'])
        self.assertIn('Keep it short', followup['text'])
        self.assertTrue(followup['no_questions'])
        original = self.get(f'/api/notes/{note["id"]}')
        self.assertEqual(original['answered'], followup['id'])
        self.assertEqual(original['answered_answers'], ['Dark', 'Keep it short'])
        self.assertFalse(original['answered_build'])

        code, err = self.post(f'/api/notes/{note["id"]}/answer', {'answers': ['Dark', 'x']})
        self.assertEqual(code, 409, err)

        code, err = self.post('/api/notes/does-not-exist/answer', {'build': True})
        self.assertEqual(code, 404, err)

        code, note2 = self.post('/api/notes', dict(video='promo/film', frame=0, text='Not waiting'))
        self.editor.notes.get(note2['id'])  # still queued behind the backend's single-flight slot
        code, err = self.post(f'/api/notes/{note2["id"]}/answer', {'build': True})
        self.assertEqual(code, 409, err)

    def test_answer_just_build_it(self):
        from videobuilder.agents import FakeBackend
        git(self.root, 'branch', '-M', 'main')
        self.editor.notes.backend = FakeBackend(delay=0, questions=[{'text': 'Light or dark logo?',
                                                                      'choices': ['Light', 'Dark']}])
        note = self.post('/api/notes', dict(video='promo/film', frame=0, text='Make the logo pop'))[1]
        self.get('/api/notes')
        code, followup = self.post(f'/api/notes/{note["id"]}/answer', {'build': True})
        self.assertEqual(code, 200, followup)
        self.assertIn('Build it with your best judgement; do not ask questions.', followup['text'])
        self.assertTrue(followup['no_questions'])
        self.assertTrue(self.get(f'/api/notes/{note["id"]}')['answered_build'])

    def test_state_dir_is_configurable(self):
        state = Path(self.tmp.name, 'elsewhere')
        self.start(state_dir=str(state))
        code, n = self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': 'hi'})
        self.assertTrue((state / 'notes' / f'{n["id"]}.png').exists())
        (self.root / 'videobuilder.toml').write_text('[editor]\nstate_dir = "review-state"\n')
        self.assertEqual(Editor(self.root).state_dir, str(self.root / 'review-state'))

    def test_the_request_hook(self):
        def hook(request):
            user = request.headers.get('X-Forwarded-User')
            if not user:
                raise Forbidden('who are you?')
            return user
        self.start(hook=hook)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/api/project')
        with e.exception:
            self.assertEqual((e.exception.code, json.loads(e.exception.read())), (403, {'error': 'who are you?'}))
        code, n = self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': 'hi'},
                            {'Content-Type': 'application/json', 'X-Forwarded-User': 'sam'})
        self.assertEqual((code, n['author']), (200, 'sam'))

    def test_a_broken_film_keeps_its_last_good_load_and_refuses_edits(self):
        self.assertIsNone(self.get('/api/info?video=promo/film')['error'])
        self.film.write_text(FILM + '\ndef broken(:\n')  # it stays listed while it doesn't parse
        info = self.get('/api/info?video=promo/film')
        self.assertIn('SyntaxError', info['error'])
        self.assertEqual(info['frames'], 210)  # the last good film, still on screen
        self.assertEqual(self.post('/api/notes', {'video': 'promo/film', 'frame': 0, 'text': 'hi'})[0], 200)
        code, r = self.post('/api/roll', {'video': 'promo/film', 'segment': 'intro', 'until': 6})
        self.assertEqual(code, 400)
        self.assertIn('SyntaxError', r['error'])
        self.assertEqual(self.log(), ['init'])


    def test_draft_endpoints(self):
        from videobuilder.agents import FakeBackend
        git(self.root, 'branch', '-M', 'main')
        self.editor.notes.backend = FakeBackend(delay=0)
        code, note = self.post('/api/notes', dict(video='promo/film', frame=0, text='Highlight'))
        self.assertEqual(code, 200)
        self.get('/api/notes')
        detail = self.get('/api/draft?video=promo/film')
        self.assertEqual(detail['files'], ['promo/film.py'])
        from unittest.mock import patch
        self.editor.unsandboxed_previews = True
        with patch('videobuilder.drafts.shutil.which', return_value=None):
            self.assertEqual(self.get('/api/draft/info?video=promo/film')['frames'], 210)
            self.assertTrue(self.get('/api/draft/frame?video=promo/film&scale=0.1').startswith(b'\x89PNG'))
        self.assertEqual(self.post('/api/draft/accept', dict(video='promo/film'))[1]['state'], 'accepted')
        self.assertEqual(self.get('/api/notes')["notes"][0]['state'], 'accepted')
        self.post('/api/notes', dict(video='promo/film', frame=0, text='Again'))
        self.get('/api/notes')
        self.assertEqual(self.post('/api/draft/drop', dict(video='promo/film'))[1]['state'], 'dropped')

    def test_host_allowlist_get_and_post(self):
        for method in ('GET', 'POST', 'HEAD', 'OPTIONS'):
            req = urllib.request.Request(self.base + '/api/project', method=method,
                                         headers={'Host': 'rebinding.example', 'Origin': 'http://rebinding.example'})
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req)
            with e.exception:
                self.assertEqual(e.exception.code, 403)
                if method != 'HEAD':
                    self.assertIn('Host is not allowed', e.exception.read().decode())
        self.editor.allowed_hosts.add('review.example')
        req = urllib.request.Request(self.base + '/api/project', headers={'Host': 'review.example:8100'})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)


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

    def _expire(self, cookie):
        """Makes a session cookie from login()/signup() look like it expired
        while the director tab sat open, rather than one that was never set."""
        import hashlib
        token = cookie.split('=', 1)[1]
        key = hashlib.sha256(token.encode()).hexdigest()
        self.library.accounts._data['sessions'][key]['expires'] = time.time() - 1
        self.library.accounts._save()

    def test_expired_session_on_video_api_route_is_401_json_not_signin_page(self):
        self.seed('acme/launch', film=True)
        cookie = self.admin_login()
        self._expire(cookie)
        code, body, headers = self.request_full('/v/acme/launch/api/project', headers={'Cookie': cookie})
        self.assertEqual(code, 401)
        self.assertEqual(headers.get_content_type(), 'application/json')
        self.assertEqual(body, {'error': 'sign in required'})

    def test_expired_session_on_a_page_route_still_shows_signin(self):
        cookie = self.admin_login()
        self._expire(cookie)
        code, page, headers = self.request_full('/', headers={'Cookie': cookie})
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), 'text/html')
        self.assertIn(b'Sign in', page)

    def test_a_401_mid_send_loses_nothing_and_a_resend_does_not_duplicate(self):
        # Models what the director does on a 401: the failed send must not have
        # queued a half-done note, and the same text, resent after signing back
        # in, must land as exactly one note -- never zero, never two.
        self.seed('acme/launch', film=True)
        cookie = self.admin_login()
        self._expire(cookie)
        note_body = {'video': 'promo/film', 'text': 'Make the logo pop'}
        code, body = self.request('/v/acme/launch/api/notes', note_body, headers={
            'Content-Type': 'application/json', 'Cookie': cookie})
        self.assertEqual(code, 401, body)
        fresh = self.admin_login()
        code, note = self.request('/v/acme/launch/api/notes', note_body, headers={
            'Content-Type': 'application/json', 'Cookie': fresh})
        self.assertEqual(code, 200, note)
        code, listing = self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': fresh})
        self.assertEqual(code, 200)
        self.assertEqual(len(listing['notes']), 1)

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
                     '/v/acme/launch/api/music/sources',
                     '/v/acme/launch/api/frame?video=promo/film&frame=0',
                     '/v/acme/launch/api/video?video=promo/film'):
            self.assertEqual(self.request(path, headers={'Cookie': outsider})[0], 404, path)
        code, _, headers = self.request_full('/git/acme/launch.git/info/refs?service=git-receive-pack',
                                              headers={'Authorization': 'Basic ' + base64.b64encode(
                                                  b'outsider:longenoughpassword').decode()})
        self.assertEqual(code, 404)
        self.assertNotIn(b'acme/launch', self.request('/', headers={'Cookie': outsider})[1])

    def test_attachment_route_is_gated_by_project_access_not_just_a_valid_id(self):
        # The attachment id itself carries no access check (see Attachments.get called with
        # video=None from _get_attachment); what actually protects it is the same `/v/<name>`
        # project-access gate every other project route goes through, checked before the
        # per-project Editor (and so its own attachments store) is even reached.
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        req = urllib.request.Request(
            self.base + '/v/acme/launch/api/attachments?video=promo/film&name=shot.png',
            data=b'\x89PNG\r\n\x1a\n' + b'0123456789', method='POST',
            headers={'Content-Type': 'image/png', 'Cookie': admin})
        with urllib.request.urlopen(req, timeout=20) as r:
            uploaded = json.loads(r.read())
        code, body, headers = self.request_full('/v/acme/launch/api/attachments/' + uploaded['id'],
                                                 headers={'Cookie': admin})
        self.assertEqual(code, 200)
        _, _, outsider = self.signup('outsider', 'longenoughpassword')
        code, body, headers = self.request_full('/v/acme/launch/api/attachments/' + uploaded['id'],
                                                 headers={'Cookie': outsider})
        self.assertEqual(code, 404)

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

    def test_access_remove_by_a_non_owner_is_403(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, collaborator = self.signup('collaborator', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'collaborator'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        # A second collaborator has access to the project but, like any non-owner,
        # cannot remove the first one: sharing is owner-or-admin only.
        _, _, other = self.signup('other', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'other'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        code, err = self.request('/v/acme/launch/api/access', {'action': 'remove', 'username': 'collaborator'},
                                 headers={'Content-Type': 'application/json', 'Cookie': other})
        self.assertEqual(code, 403)
        code, access = self.request('/v/acme/launch/api/access', headers={'Cookie': admin})
        self.assertEqual((code, sorted(access['collaborators'])), (200, ['collaborator', 'other']))

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

    def test_notes_and_usage_hide_cost_from_a_non_admin(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0, cost_usd=1.23, tokens={'input': 10})
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, note)
        self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': admin})  # force poll
        code, as_admin = self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': admin})
        self.assertEqual((code, as_admin['notes'][0]['cost_usd']), (200, 1.23))
        code, as_bob = self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': bob})
        self.assertEqual(code, 200)
        self.assertNotIn('cost_usd', as_bob['notes'][0])
        self.assertNotIn('tokens', as_bob['notes'][0])
        code, single = self.request(f'/v/acme/launch/api/notes/{note["id"]}', headers={'Cookie': bob})
        self.assertEqual(code, 200)
        self.assertNotIn('cost_usd', single)
        code, usage = self.request('/v/acme/launch/api/usage', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertEqual(usage['accounts']['mgalgs']['last_24h']['cost_usd'], 1.23)
        self.assertEqual(usage['accounts']['mgalgs']['last_24h']['notes'], 1)
        code, _ = self.request('/v/acme/launch/api/usage', headers={'Cookie': bob})
        self.assertEqual(code, 403)

    def test_daily_note_cap_refuses_the_third_note_but_never_an_admin(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 2
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        for _ in range(2):
            code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                      headers=bob_headers)
            self.assertEqual(code, 200, note)
        code, data, _ = self.request_full('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        for _ in range(3):
            code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                      headers=admin_headers)
            self.assertEqual(code, 200, note)

    def test_daily_cost_cap_refuses_once_recorded_cost_reaches_it(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0, cost_usd=3)
        editor.account_daily_cost_cap_usd = 5
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        for _ in range(2):
            code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                      headers=bob_headers)
            self.assertEqual(code, 200, note)
            self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': bob})  # force poll
        code, data, _ = self.request_full('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_daily_note_cap_refuses_an_answer_follow_up(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0, questions=[{'text': 'Light or dark logo?',
                                                                 'choices': ['Light', 'Dark']}])
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Make it pop'},
                                  headers=bob_headers)
        self.assertEqual(code, 200, note)
        self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': bob})  # force poll
        self.assertEqual(editor.notes.get(note['id'])['state'], 'questions')
        editor.account_daily_note_cap = 1  # the original note already fills the cap
        code, data, _ = self.request_full(f'/v/acme/launch/api/notes/{note["id"]}/answer', {'answers': ['Dark']},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_daily_note_cap_counts_every_project_in_the_library(self):
        # A cap on one project must bind the account everywhere, not just there --
        # otherwise "New video" is a free reset for anyone who hits it.
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        launch = self.library.editor('acme/launch')
        launch.notes.backend = FakeBackend(delay=0)
        launch.account_daily_note_cap = 2
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        for _ in range(2):
            code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                      headers=bob_headers)
            self.assertEqual(code, 200, note)
        code, created = self.request('/api/videos/new', {'name': 'bob/second', 'start': 'blank'},
                                     headers=bob_headers)
        self.assertEqual(code, 201, created)
        second = self.library.editor('bob/second')
        second.notes.backend = FakeBackend(delay=0)
        second.account_daily_note_cap = 2
        code, data, _ = self.request_full('/v/bob/second/api/videos/first-note', {'description': 'Hi'},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])
        # An admin stays exempt in a brand-new project too.
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        code, created = self.request('/api/videos/new', {'name': 'admin/second', 'start': 'blank'},
                                     headers=admin_headers)
        self.assertEqual(code, 201, created)
        third = self.library.editor('admin/second')
        third.notes.backend = FakeBackend(delay=0)
        third.account_daily_note_cap = 2
        code, note, _ = self.request_full('/v/admin/second/api/videos/first-note', {'description': 'Hi'},
                                          headers=admin_headers)
        self.assertEqual(code, 200, note)

    def test_daily_note_cap_counts_a_keys_notes_toward_its_account(self):
        # A key is attributed as "bob (ci)", a different string from the cookie
        # session "bob" -- the cap must still treat them as the same account.
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 2
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        for _ in range(2):
            code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                      headers=bob_headers)
            self.assertEqual(code, 200, note)
        code, key = self.request('/api/account/keys', {'label': 'ci', 'mode': 'write'},
                                 headers={'Content-Type': 'application/json', 'Cookie': bob})
        self.assertEqual(code, 201, key)
        key_headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key['secret']}
        code, data, _ = self.request_full('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                          headers=key_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_note_retry_is_capped_too(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers=bob_headers)
        self.assertEqual(code, 200, note)
        editor.notes.update(editor.notes.get(note['id']), state='failed')
        editor.account_daily_note_cap = 1  # the failed note already fills the cap
        code, data, _ = self.request_full(f'/v/acme/launch/api/notes/{note["id"]}/retry', {},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_post_note_responses_hide_cost_from_a_non_admin(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0, cost_usd=1.23)
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', 'Cookie': bob})
        self.assertEqual(code, 200, note)
        self.assertNotIn('cost_usd', note)
        self.assertNotIn('tokens', note)
        code, admin_note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                        headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, admin_note)
        self.assertIn('cost_usd', admin_note)

    def test_usage_route_is_shared_across_the_library(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        launch = self.library.editor('acme/launch')
        launch.notes.backend = FakeBackend(delay=0, cost_usd=2.5)
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers=admin_headers)
        self.assertEqual(code, 200, note)
        self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': admin})  # force poll
        code, created = self.request('/api/videos/new', {'name': 'acme/second', 'start': 'blank'},
                                     headers=admin_headers)
        self.assertEqual(code, 201, created)
        second = self.library.editor('acme/second')
        second.notes.backend = FakeBackend(delay=0, cost_usd=1.5)
        code, note2 = self.request('/v/acme/second/api/videos/first-note', {'description': 'Hi'},
                                   headers=admin_headers)
        self.assertEqual(code, 200, note2)
        self.request('/v/acme/second/api/notes?video=film', headers={'Cookie': admin})  # force poll
        # The bare route, shared across the library like /api/name -- not /v/<name>/api/usage.
        code, usage = self.request('/api/usage', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertAlmostEqual(usage['accounts']['mgalgs']['last_24h']['cost_usd'], 4.0)
        self.assertEqual(usage['accounts']['mgalgs']['last_24h']['notes'], 2)
        code, _ = self.request('/api/usage', headers={'Cookie': bob})
        self.assertEqual(code, 403)

    def test_daily_note_cap_message_is_in_local_time_not_utc(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 1
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers=bob_headers)
        self.assertEqual(code, 200, note)
        code, data, _ = self.request_full('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertNotIn('UTC', data['error'])
        self.assertRegex(data['error'], r'after \d{1,2}:\d{2} (AM|PM) (today|tomorrow)')

    def test_custom_account_limit_is_tighter_than_the_library_default(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 5  # the library-wide default: generous
        self.library.accounts.set_limit('bob', 'custom', 1, None)  # bob's own override: tighter
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers=bob_headers)
        self.assertEqual(code, 200, note)
        code, data, _ = self.request_full('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_unlimited_account_is_never_capped(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 1
        self.library.accounts.set_limit('bob', 'unlimited')
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        for _ in range(3):
            code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                      headers=bob_headers)
            self.assertEqual(code, 200, note)

    def test_switching_an_account_back_to_default_restores_the_library_cap(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 1
        self.library.accounts.set_limit('bob', 'unlimited')
        bob_headers = {'Content-Type': 'application/json', 'Cookie': bob}
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers=bob_headers)
        self.assertEqual(code, 200, note)
        self.library.accounts.set_limit('bob', 'default')
        code, data, _ = self.request_full('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                          headers=bob_headers)
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_limit_override_persists_across_an_accounts_reload(self):
        # Models a restart: the operator stops the editor and starts it again, which
        # re-reads accounts.json from scratch rather than keeping the in-memory store.
        from videobuilder.accounts import Accounts
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.library.accounts.set_limit('bob', 'custom', 7, 2.5)
        reloaded = Accounts(str(self.library.state_dir), [('mgalgs', str(self.root / 'admin-pass'))])
        self.assertEqual(reloaded.get_limit('bob'), {'kind': 'custom', 'notes': 7, 'cost_usd': 2.5})

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
