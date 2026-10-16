"""HTTP-level tests for the community-capabilities feature: the reserved
namespace end to end (commit 2), then submission, drafts/publish and the
builder context in later commits. Every test that sends an X post URL mocks
videobuilder.xpost._open -- no test here touches the network."""
import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from videobuilder import community, xpost
from videobuilder.library import Library
from tests import fixtures
from tests.test_xpost import _FakeResponse

SYNTHETIC_POST = {
    'text': 'A neat zoom transition on the logo, worth stealing.',
    'user': {'screen_name': 'example_creator'},
    'mediaDetails': [{'type': 'photo', 'media_url_https': 'https://pbs.twimg.com/media/fake1.jpg'}],
    'video': {'variants': [{'type': 'video/mp4', 'src': 'https://video.twimg.com/vid/640x360/clip.mp4'}]},
}
_JPEG = b'\xff\xd8\xff' + b'0' * 20
_MP4 = b'\x00\x00\x00\x20ftypisom' + b'0' * 20


def _successful_read_responses(id):
    return [
        _FakeResponse(json.dumps(SYNTHETIC_POST).encode(), xpost.syndication_url(id)),
        _FakeResponse(_JPEG, 'https://pbs.twimg.com/media/fake1.jpg'),
        _FakeResponse(_MP4, 'https://video.twimg.com/vid/640x360/clip.mp4'),
    ]


class Reserved(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_videos_new_refuses_reserved_names(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        headers = {'Content-Type': 'application/json', 'Cookie': admin}
        for name, start in (('capabilities', 'blank'), ('capabilities/x', 'blank'),
                            ('capabilities', 'copy'), ('capabilities/x', 'copy')):
            with self.subTest(name=name, start=start):
                body = {'name': name, 'start': start}
                if start == 'copy':
                    body['from'] = 'acme/launch'
                code, data, _ = self.request_full('/api/videos/new', body, headers=headers)
                self.assertEqual(code, 400, data)
                self.assertIn('reserved', data['error'])
                self.assertFalse(self.library.path(name).exists())

    def test_library_new_refuses_reserved_target(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        code, data, _ = self.request_full('/api/library/new', {'from': 'acme/launch', 'name': 'capabilities/copy1'},
                                          headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 400, data)
        self.assertIn('reserved', data['error'])
        self.assertFalse(self.library.path('capabilities/copy1').exists())

    def test_git_push_create_refused_in_reserved_namespace(self):
        work = self.root / 'push-source'
        self.git('init', '-b', 'main', str(work))
        (work / 'README.md').write_text('hi\n')
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'first', cwd=work)
        self.git('remote', 'add', 'origin', self.url('capabilities/pushed'), cwd=work)
        result = self.git('push', '-u', 'origin', 'main', cwd=work, ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.library.path('capabilities/pushed').exists())

    def test_signup_refuses_capabilities_username(self):
        for name in ('capabilities', 'Capabilities'):
            with self.subTest(name=name):
                code, data, cookie = self.signup(name, 'longenoughpassword')
                self.assertEqual(code, 400, data)
                self.assertIn('reserved', data['error'])


class Submission(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def _upload(self, name, video, filename, data, ctype, cookie):
        req = urllib.request.Request(
            self.base + f'/v/{name}/api/attachments?video={video}&name={filename}',
            data=data, method='POST', headers={'Content-Type': ctype, 'Cookie': cookie})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())

    def test_new_creates_draft_project_owned_by_submitter(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        code, created = self.request('/api/capabilities/new', {'files': 1, 'capture': 'the thing'},
                                     headers=headers)
        self.assertEqual(code, 201, created)
        self.assertEqual(created['name'], f'capabilities/{created["slug"]}')
        self.assertEqual(created['attachments'], [])
        self.assertIsNone(created['read'])
        self.assertTrue(self.library.path(created['name']).exists())
        code, access = self.request(f'/v/{created["name"]}/api/access', headers={'Cookie': dana})
        self.assertEqual((code, access['owner']), (200, 'dana'))
        record = self.library.community.get(created['slug'])
        self.assertEqual((record['status'], record['submitter'], record['note']), ('draft', 'dana', None))

    def test_new_needs_a_url_or_files(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, data, _ = self.request_full('/api/capabilities/new', {'files': 0},
                                          headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 400, data)
        self.assertEqual(self.library.names(), [])

    def test_send_creates_first_note_once(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1, 'capture': 'zoom transitions'},
                               headers=headers)[1]
        uploaded = self._upload(created['name'], created['video'], 'ref.png',
                                b'\x89PNG\r\n\x1a\n' + b'0' * 20, 'image/png', dana)
        code, note = self.request(f'/api/capabilities/{created["slug"]}/send', {'attachments': [uploaded['id']]},
                                  headers=headers)
        self.assertEqual(code, 200, note)
        self.assertEqual(note['author'], 'dana')
        for needle in ('film.py', 'capability.toml', 'capability.md', 'ORIGINAL', 'untrusted', 'zoom transitions'):
            self.assertIn(needle, note['text'])
        self.assertEqual([a['id'] for a in note['attachments']], [uploaded['id']])
        record = self.library.community.get(created['slug'])
        self.assertEqual(record['note'], note['id'])
        code, err = self.request_full(f'/api/capabilities/{created["slug"]}/send', {'attachments': []},
                                      headers=headers)[:2]
        self.assertEqual(code, 409, err)

    def test_send_by_non_owner_is_404(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=headers)[1]
        other_headers = {'Content-Type': 'application/json', 'Cookie': other}
        code, data, _ = self.request_full(f'/api/capabilities/{created["slug"]}/send', {'attachments': []},
                                          headers=other_headers)
        self.assertEqual(code, 404, data)
        self.assertIsNone(self.library.community.get(created['slug'])['note'])

    def test_new_respects_daily_cap(self):
        self.library.account_daily_note_cap = 1
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.library.editor('acme/launch').notes.backend = FakeBackend(delay=0)
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'dana'},
                    headers={'Content-Type': 'application/json', 'Cookie': admin})
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers=headers)
        self.assertEqual(code, 200, note)
        code, data, _ = self.request_full('/api/capabilities/new', {'files': 1}, headers=headers)
        self.assertEqual(code, 429, data)
        self.assertEqual(self.library.names(), ['acme/launch'])

    def test_failed_send_can_be_retried(self):
        # Library.account_daily_note_cap is only a constructor-time default for each
        # project's own Editor (see Editor.__init__): mutate the capability project's
        # own Editor, exactly as the existing per-project cap tests do for an ordinary
        # one, to simulate the cap being reached between /new and /send.
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=headers)[1]
        uploaded = self._upload(created['name'], created['video'], 'ref.png',
                                b'\x89PNG\r\n\x1a\n' + b'0' * 20, 'image/png', dana)
        self.library.editor(created['name']).account_daily_note_cap = 1
        # Fill the cap with an unrelated note from the same account, between /new and /send.
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.library.editor('acme/launch').notes.backend = FakeBackend(delay=0)
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'dana'},
                    headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'}, headers=headers)
        code, data, _ = self.request_full(f'/api/capabilities/{created["slug"]}/send',
                                          {'attachments': [uploaded['id']]}, headers=headers)
        self.assertEqual(code, 429, data)
        self.assertIsNone(self.library.community.get(created['slug'])['note'])
        self.library.editor(created['name']).account_daily_note_cap = 5
        code, note = self.request(f'/api/capabilities/{created["slug"]}/send', {'attachments': [uploaded['id']]},
                                  headers=headers)
        self.assertEqual(code, 200, note)
        self.assertEqual(self.library.community.get(created['slug'])['note'], note['id'])


class KeysAndOrigin(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_api_keys_cannot_submit_publish_or_reject(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, secret = self.library.accounts.create_key('dana', 'ci', None, 'write')
        bearer = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + secret}
        for path, body in (('/api/capabilities/new', {'files': 1}),
                           ('/api/capabilities/fake-slug/send', {'attachments': []})):
            with self.subTest(path=path):
                self.assertEqual(self.request(path, body, headers=bearer)[0], 401)

    def test_cross_origin_posts_refused(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        for path, body in (('/api/capabilities/new', {'files': 1}),
                           ('/api/capabilities/fake-slug/send', {'attachments': []})):
            with self.subTest(path=path):
                code = self.request(path, body, headers={'Content-Type': 'application/json', 'Cookie': dana,
                                                          'Origin': 'http://elsewhere.example'})[0]
                self.assertEqual(code, 403)


class NoAccountsNoFeature(fixtures.LibraryFixture, unittest.TestCase):
    def test_no_accounts_no_feature(self):
        self.assertEqual(self.request('/api/capabilities/new', {'files': 1})[0], 404)
        page = self.request('/capabilities')[1]
        self.assertNotIn(b'Add capability', page)


class DialogMarkup(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_signed_in_page_has_add_capability_dialog(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        for needle in (b'id="add-capability"', b'id="add-capability-dialog"', b'name="url"',
                      b'id="files-field"', b'name="capture"'):
            self.assertIn(needle, page)


class XPostRead(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    POST_URL = 'https://x.com/example_creator/status/1585341984679469056'
    POST_ID = '1585341984679469056'

    @mock.patch('videobuilder.xpost._open')
    def test_failed_read_without_files_creates_nothing(self, opened):
        opened.side_effect = OSError('no network')
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, data, _ = self.request_full('/api/capabilities/new', {'url': self.POST_URL, 'files': 0},
                                          headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 422, data)
        self.assertEqual(data['error'], community.READ_FAILED)
        self.assertEqual(self.library.names(), [])
        self.assertEqual(self.library.community.all(), {})

    @mock.patch('videobuilder.xpost._open')
    def test_failed_read_with_files_still_submits(self, opened):
        opened.side_effect = OSError('no network')
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, created = self.request('/api/capabilities/new', {'url': self.POST_URL, 'files': 1},
                                     headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 201, created)
        self.assertEqual(created['read']['error'], community.READ_FAILED)
        self.assertTrue(self.library.path(created['name']).exists())

    @mock.patch('videobuilder.xpost._open')
    def test_successful_read_attaches_media_and_quotes_post(self, opened):
        opened.side_effect = _successful_read_responses(self.POST_ID)
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        code, created = self.request('/api/capabilities/new', {'url': self.POST_URL, 'files': 0}, headers=headers)
        self.assertEqual(code, 201, created)
        self.assertIsNone(created['read']['error'])
        self.assertEqual(len(created['attachments']), 2)
        code, note = self.request(f'/api/capabilities/{created["slug"]}/send', {'attachments': []}, headers=headers)
        self.assertEqual(code, 200, note)
        self.assertIn('@example_creator', note['text'])
        self.assertIn('A neat zoom transition on the logo, worth stealing.', note['text'])
        self.assertIn('untrusted', note['text'])

    @mock.patch('videobuilder.xpost._open')
    def test_endpoint_refuses_bad_url_before_network(self, opened):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, data, _ = self.request_full('/api/capabilities/new', {'url': 'not-a-url', 'files': 0},
                                          headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 400, data)
        opened.assert_not_called()


class NoFetch(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def library_kwargs(self):
        return {**super().library_kwargs(), 'capability_fetch': False}

    @mock.patch('videobuilder.xpost._open')
    def test_no_fetch_flag_never_fetches_and_hides_url_field(self, opened):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'id="add-capability"', page)
        self.assertNotIn(b'name="url"', page)
        code, created = self.request('/api/capabilities/new',
                                     {'url': 'https://x.com/a/status/123', 'files': 1}, headers=headers)
        self.assertEqual(code, 201, created)
        self.assertIsNone(created['read'])
        opened.assert_not_called()


class BackendArgs(unittest.TestCase):
    def test_capability_project_backend_gets_heavy_args(self):
        for capability_args in (None, ['--x', '1']):
            with self.subTest(capability_args=capability_args):
                with tempfile.TemporaryDirectory() as tmp:
                    library = Library(Path(tmp) / 'library', envs='current',
                                      agent={'backend': 'fork-sandbox', 'extra_args': ['--model', 'm']},
                                      capability_agent_extra_args=capability_args)
                    self.addCleanup(library.close)
                    library.create_blank('acme/launch')
                    library.create_blank('capabilities/demo', allow_reserved=True)
                    ordinary = library.editor('acme/launch')
                    capability = library.editor('capabilities/demo')
                    self.assertEqual(ordinary.notes.backend.extra_args, ['--model', 'm'])
                    expected = (['--model', 'm', '--x', '1'] if capability_args is not None else
                               ['--model', 'm', '--review-loop', '2', '--maintainer-loop', '1',
                                '--review-model', 'm', '--maintainer-model', 'm'])
                    self.assertEqual(capability.notes.backend.extra_args, expected)

    def test_non_fork_backends_ignore_capability_args(self):
        agents = ({'backend': 'fake'}, {'backend': 'null'},
                 {'backend': 'command', 'submit_command': ['true'], 'poll_command': ['true']})
        for agent in agents:
            with self.subTest(agent=agent['backend']):
                with tempfile.TemporaryDirectory() as tmp:
                    library = Library(Path(tmp) / 'library', envs='current', agent=dict(agent),
                                      capability_agent_extra_args=['--x', '1'])
                    self.addCleanup(library.close)
                    library.create_blank('acme/launch')
                    library.create_blank('capabilities/demo', allow_reserved=True)
                    ordinary = library.editor('acme/launch')
                    capability = library.editor('capabilities/demo')
                    self.assertEqual(type(ordinary.notes.backend), type(capability.notes.backend))
                    self.assertEqual(vars(ordinary.notes.backend), vars(capability.notes.backend))


if __name__ == '__main__':
    unittest.main()
