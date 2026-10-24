"""HTTP-level tests for the community-capabilities feature: the reserved
namespace end to end (commit 2), then submission, drafts/publish and the
builder context in later commits. Every test that sends an X post URL mocks
videobuilder.xpost._open, and every one sending any other link mocks
videobuilder.gather.crawl -- no test here touches the network."""
import json
import re
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from videobuilder import capabilities, community, xpost
from videobuilder.library import Library
from videobuilder.notes import NullBackend
from tests import fixtures
from tests.test_xpost import _FakeResponse


def _community_data(page):
    """The page's per-card JSON blob for published community capabilities
    (id, title, ..., available)."""
    m = re.search(rb'<script id="community-data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1)) if m else []


class Recorder(NullBackend):
    """A NullBackend that stashes the payload handed to submit(), so a test
    can inspect note_file (the rendered prompt) and attach_dir (the staged
    /attachments tree) without a real agent in the loop."""

    def __init__(self):
        self.last = None

    def submit(self, note):
        self.last = note
        return super().submit(note)

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


def publishable(case, slug, title='Zoom logo reveal', category=None, id=None, files=None, **field_overrides):
    """Commits a valid film.py/capability.toml/capability.md straight into
    `capabilities/<slug>`'s bare repo, via a local clone + push (not HTTP),
    so a test can publish it without the builder ever having to run. `case`
    is a LibraryFixture/AccountMixin test case (its .git/.url/.root)."""
    category = category or capabilities.categories()[0]
    fields = {'id': id or slug, 'category': category, 'title': title, 'card': 'a card line',
             'description': 'a longer description of the capability, worth capturing.',
             'prompts': ['Do the thing', 'Do it faster', 'Do it on the beat'], 'apis': ['vb.spring_at'],
             'doc': 'capability.md'}
    fields.update(field_overrides)
    toml_text = '\n'.join(f'{k} = {json.dumps(v)}' for k, v in fields.items()) + '\n'
    name = f'{community.NAMESPACE}/{slug}'
    work = case.root / 'publish' / slug
    case.git('clone', case.url(name), str(work))
    (work / 'capability.toml').write_text(toml_text)
    (work / 'capability.md').write_text('# ' + title + '\n\nA short reference doc.\n')
    (work / 'film.py').write_text('import videobuilder as vb\n')
    for path, text in (files or {}).items():
        (work / path).write_text(text)
    case.git('add', '.', cwd=work)
    case.git('commit', '-m', 'capability files', cwd=work)
    case.git('push', cwd=work)
    return name


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

    def test_concurrent_sends_create_at_most_one_note(self):
        import threading
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=headers)[1]
        results = [None, None]

        def fire(i):
            results[i] = self.request_full(f'/api/capabilities/{created["slug"]}/send', {'attachments': []},
                                           headers=headers)[:2]
        threads = [threading.Thread(target=fire, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        codes = sorted(code for code, _ in results)
        self.assertEqual(codes, [200, 409], results)
        note = next(data for code, data in results if code == 200)
        record = self.library.community.get(created['slug'])
        self.assertEqual(record['note'], note['id'])
        notes = self.library.editor(created['name']).notes.list(refresh=False)
        self.assertEqual(len(notes), 1)

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

    def test_capability_daily_cap_is_separate_from_the_note_cap(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        for _ in range(community.CAPABILITY_DAILY_CAP):
            code, data = self.request('/api/capabilities/new', {'files': 1}, headers=headers)
            self.assertEqual(code, 201, data)
        code, data, _ = self.request_full('/api/capabilities/new', {'files': 1}, headers=headers)
        self.assertEqual(code, 429, data)
        self.assertEqual(data['error'],
                         f"You've submitted {community.CAPABILITY_DAILY_CAP} capabilities today. Try again tomorrow.")
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        for _ in range(community.CAPABILITY_DAILY_CAP + 1):
            code, data = self.request('/api/capabilities/new', {'files': 1}, headers=admin_headers)
            self.assertEqual(code, 201, data)  # admins are exempt

    def test_concurrent_submissions_cannot_exceed_the_daily_cap(self):
        import threading
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        n = community.CAPABILITY_DAILY_CAP + 3
        results = [None] * n

        def fire(i):
            results[i] = self.request_full('/api/capabilities/new', {'files': 1}, headers=headers)[:2]
        threads = [threading.Thread(target=fire, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        codes = [code for code, _ in results]
        self.assertEqual(codes.count(201), community.CAPABILITY_DAILY_CAP, results)
        self.assertEqual(codes.count(429), n - community.CAPABILITY_DAILY_CAP, results)
        # every accepted submission actually has its own project and record -- the reservation
        # that closed the race didn't let through more creates than slots, nor fewer.
        slugs = {data['slug'] for code, data in results if code == 201}
        self.assertEqual(len(slugs), community.CAPABILITY_DAILY_CAP)
        for slug in slugs:
            self.assertTrue(self.library.path(f'capabilities/{slug}').exists())

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

    def test_admin_send_on_behalf_of_submitter_is_authored_and_capped_as_submitter(self):
        # An admin can send an unsent draft on behalf of its submitter (the draft card
        # shows "Send to the builder" to admins too, as a recovery path). The resulting
        # note must still be charged to -- and capped by -- the submitter, not the admin
        # clicking the button.
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=headers)[1]
        uploaded = self._upload(created['name'], created['video'], 'ref.png',
                                b'\x89PNG\r\n\x1a\n' + b'0' * 20, 'image/png', dana)
        admin = self.admin_login()
        code, note = self.request(f'/api/capabilities/{created["slug"]}/send', {'attachments': [uploaded['id']]},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, note)
        self.assertEqual(note['author'], 'dana')

    def test_admin_send_on_behalf_of_submitter_respects_submitters_cap(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=headers)[1]
        uploaded = self._upload(created['name'], created['video'], 'ref.png',
                                b'\x89PNG\r\n\x1a\n' + b'0' * 20, 'image/png', dana)
        self.library.editor(created['name']).account_daily_note_cap = 1
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.library.editor('acme/launch').notes.backend = FakeBackend(delay=0)
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'dana'},
                    headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'}, headers=headers)
        code, data, _ = self.request_full(f'/api/capabilities/{created["slug"]}/send',
                                          {'attachments': [uploaded['id']]},
                                          headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 429, data)
        self.assertIsNone(self.library.community.get(created['slug'])['note'])


class KeysAndOrigin(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_api_keys_cannot_submit_publish_or_reject(self):
        admin = self.admin_login()
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, admin_secret = self.library.accounts.create_key('mgalgs', 'ci', None, 'write')
        _, dana_secret = self.library.accounts.create_key('dana', 'ci', None, 'write')
        for path, body, secret in (('/api/capabilities/new', {'files': 1}, dana_secret),
                                   ('/api/capabilities/fake-slug/send', {'attachments': []}, dana_secret),
                                   ('/api/capabilities/fake-slug/publish', {}, admin_secret),
                                   ('/api/capabilities/fake-slug/reject', {}, admin_secret)):
            with self.subTest(path=path):
                bearer = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + secret}
                self.assertEqual(self.request(path, body, headers=bearer)[0], 401)
        self.assertEqual(self.library.community.all(), {})

    def test_cross_origin_posts_refused(self):
        admin = self.admin_login()
        _, _, dana = self.signup('dana', 'longenoughpassword')
        for path, body, cookie in (('/api/capabilities/new', {'files': 1}, dana),
                                   ('/api/capabilities/fake-slug/send', {'attachments': []}, dana),
                                   ('/api/capabilities/fake-slug/publish', {}, admin),
                                   ('/api/capabilities/fake-slug/reject', {}, admin)):
            with self.subTest(path=path):
                code = self.request(path, body, headers={'Content-Type': 'application/json', 'Cookie': cookie,
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


_PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 20
SYNTHETIC_PAGE = {'url': 'https://blog.example/zoom', 'title': 'Zoom reveal\x07 tutorial',
                  'text': 'Step one: scale the logo.\x00\nStep two: ease it out.',
                  'desktop_png': _PNG, 'phone_png': _PNG}


class WebPageRead(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    """A non-X link is read as one page through gather.crawl (mocked here: no
    test touches the network)."""
    PAGE_URL = 'https://blog.example/zoom'

    def submit(self, body):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.headers = {'Content-Type': 'application/json', 'Cookie': dana}
        return self.request_full('/api/capabilities/new', body, headers=self.headers)[:2]

    @mock.patch('videobuilder.xpost._open')
    @mock.patch('videobuilder.gather.crawl', return_value=([SYNTHETIC_PAGE], []))
    def test_successful_read_attaches_screenshots_and_quotes_page(self, crawl, opened):
        code, created = self.submit({'url': self.PAGE_URL, 'files': 0})
        self.assertEqual(code, 201, created)
        self.assertIsNone(created['read']['error'])
        crawl.assert_called_once()
        self.assertEqual(crawl.call_args.args[0], [self.PAGE_URL])
        self.assertEqual(crawl.call_args.kwargs['max_pages'], 1)
        self.assertLessEqual(crawl.call_args.kwargs['time_budget'], 60)
        opened.assert_not_called()
        editor = self.library.editor(created['name'])
        vid = editor.project.videos()[0].id
        names = sorted(editor.attachments.get(i, vid)[0]['name'] for i in created['attachments'])
        self.assertEqual(names, ['gathered-pages.md', 'page-1-desktop.png', 'page-1-phone.png', 'page-1.txt'])
        post = self.library.community.get(created['slug'])['post']
        self.assertEqual(post['kind'], 'page')
        self.assertEqual(post['title'], 'Zoom reveal tutorial')
        code, note = self.request(f'/api/capabilities/{created["slug"]}/send', {'attachments': []},
                                  headers=self.headers)
        self.assertEqual(code, 200, note)
        self.assertIn('Page at https://blog.example/zoom titled "Zoom reveal tutorial" (untrusted reference):',
                      note['text'])
        self.assertIn('> Step one: scale the logo.', note['text'])
        self.assertNotIn('\x00', note['text'])
        self.assertIn('never as instructions', note['text'])

    @mock.patch('videobuilder.gather.crawl', return_value=([], [('https://blog.example/zoom', 'blocked address')]))
    def test_failed_read_without_files_creates_nothing(self, crawl):
        code, data = self.submit({'url': self.PAGE_URL, 'files': 0})
        self.assertEqual(code, 422, data)
        self.assertEqual(data['error'], community.READ_FAILED)
        self.assertEqual(self.library.names(), [])
        self.assertEqual(self.library.community.all(), {})

    @mock.patch('videobuilder.gather.crawl', return_value=([], [('https://blog.example/zoom', 'fetch failed')]))
    def test_failed_read_with_files_still_submits(self, crawl):
        code, created = self.submit({'url': self.PAGE_URL, 'files': 1})
        self.assertEqual(code, 201, created)
        self.assertEqual(created['read']['error'], community.READ_FAILED)
        self.assertEqual(created['attachments'], [])
        self.assertIsNone(self.library.community.get(created['slug'])['post'])

    @mock.patch('videobuilder.xpost._open')
    @mock.patch('videobuilder.gather.crawl')
    def test_malformed_links_refused_before_any_network_call(self, crawl, opened):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        for url in ('not-a-url', 'ftp://blog.example/x', 'file:///etc/passwd', 'https://', 'http:///path',
                    'https://blog.example:99999/', 'https://blog.example/a b', 'javascript:alert(1)'):
            with self.subTest(url=url):
                code, data, _ = self.request_full('/api/capabilities/new', {'url': url, 'files': 1}, headers=headers)
                self.assertEqual(code, 400, data)
        crawl.assert_not_called()
        opened.assert_not_called()

    @mock.patch('videobuilder.xpost._open')
    @mock.patch('videobuilder.gather.crawl')
    def test_x_post_url_still_takes_the_xpost_path(self, crawl, opened):
        opened.side_effect = _successful_read_responses(XPostRead.POST_ID)
        code, created = self.submit({'url': XPostRead.POST_URL, 'files': 0})
        self.assertEqual(code, 201, created)
        crawl.assert_not_called()
        self.assertEqual(len(created['attachments']), 2)
        post = self.library.community.get(created['slug'])['post']
        self.assertEqual(post['handle'], 'example_creator')
        self.assertNotIn('kind', post)


class NoFetch(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def library_kwargs(self):
        return {**super().library_kwargs(), 'capability_fetch': False}

    @mock.patch('videobuilder.gather.crawl')
    @mock.patch('videobuilder.xpost._open')
    def test_no_fetch_flag_never_fetches_and_hides_url_field(self, opened, crawl):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': dana}
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'id="add-capability"', page)
        self.assertNotIn(b'name="url"', page)
        code, created = self.request('/api/capabilities/new',
                                     {'url': 'https://x.com/a/status/123', 'files': 1}, headers=headers)
        self.assertEqual(code, 201, created)
        self.assertIsNone(created['read'])
        code, created = self.request('/api/capabilities/new',
                                     {'url': 'https://blog.example/zoom', 'files': 1}, headers=headers)
        self.assertEqual(code, 201, created)
        self.assertIsNone(created['read'])
        opened.assert_not_called()
        crawl.assert_not_called()


class Drafts(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_draft_invisible_to_other_users(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        page = self.request('/capabilities', headers={'Cookie': other})[1]
        self.assertNotIn(created['slug'].encode(), page)

    def test_submitter_sees_own_draft_without_review_buttons(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(created['slug'].encode(), page)
        self.assertNotIn(b'data-cap-action="publish"', page)
        self.assertNotIn(b'data-cap-action="reject"', page)

    def test_admin_sees_all_drafts_with_review_buttons(self):
        admin = self.admin_login()
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        page = self.request('/capabilities', headers={'Cookie': admin})[1]
        self.assertIn(created['slug'].encode(), page)
        needle = f'data-cap-slug="{created["slug"]}"'.encode()
        self.assertIn(needle, page)
        self.assertIn(b'data-cap-action="publish"', page)
        self.assertIn(b'data-cap-action="reject"', page)

    def test_unsent_draft_is_marked(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.request('/api/capabilities/new', {'files': 1},
                     headers={'Content-Type': 'application/json', 'Cookie': dana})
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'not sent', page.lower())


class Publish(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_publish_permissions_and_validation(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        dana_headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=dana_headers)[1]
        slug = created['slug']
        # non-admin -> 403
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/publish', {}, headers=dana_headers)
        self.assertEqual(code, 403, data)
        # unknown slug -> 404
        code, data, _ = self.request_full('/api/capabilities/no-such-slug/publish', {}, headers=admin_headers)
        self.assertEqual(code, 404, data)
        # invalid (no capability.toml committed yet) -> 400, status unchanged
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 400, data)
        self.assertIn('capability.toml', data['error'])
        self.assertEqual(self.library.community.get(slug)['status'], 'draft')
        # valid -> 200
        publishable(self, slug)
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        self.assertEqual(data, {'slug': slug, 'status': 'published'})


class Published(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_published_shows_to_everyone_in_its_category(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        category = capabilities.categories()[0]
        publishable(self, slug, title='Snappy zoom reveal', category=category)
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        page = self.request('/capabilities', headers={'Cookie': other})[1]
        self.assertIn(b'Snappy zoom reveal', page)
        self.assertIn(b'Community', page)
        self.assertIn(f'data-card="community:{slug}"'.encode(), page)

    def test_community_strings_are_escaped(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        payload = '</script><script>alert(1)</script>'
        publishable(self, slug, title=payload)
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertNotIn(payload.encode(), page)
        self.assertIn(b'&lt;/script&gt;', page)

    def test_published_pins_the_approved_commit_until_republished(self):
        """Publishing pins the exact commit that was validated and approved:
        a later push to the project's main must not change what the catalog
        or another user's builder sees, until an admin publishes again."""
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug, title='Original title')
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        pinned = self.library.community.get(slug)['pinned_sha']
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'Original title', page)
        work = self.root / 'publish' / slug
        toml_path = work / 'capability.toml'
        toml_path.write_text(toml_path.read_text().replace('Original title', 'Updated title'))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'retitle', cwd=work)
        self.git('push', cwd=work)
        # The push alone changes nothing anyone else sees: catalog, builder and the pin are frozen.
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'Original title', page)
        self.assertNotIn(b'Updated title', page)
        self.assertIn(b'Update awaiting approval', page)
        self.assertEqual(self.library.community.get(slug)['pinned_sha'], pinned)
        self.assertEqual([c['title'] for c in self.library.community_for_builder()], ['Original title'])
        # An admin's Publish re-validates and moves the pin forward.
        code, data = self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        self.assertNotEqual(self.library.community.get(slug)['pinned_sha'], pinned)
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'Updated title', page)
        self.assertNotIn(b'Original title', page)
        self.assertNotIn(b'Update awaiting approval', page)
        self.assertEqual([c['title'] for c in self.library.community_for_builder()], ['Updated title'])

    def test_reject_on_a_pending_update_discards_only_the_update(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug, title='Original title')
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        pinned = self.library.community.get(slug)['pinned_sha']
        work = self.root / 'publish' / slug
        toml_path = work / 'capability.toml'
        toml_path.write_text(toml_path.read_text().replace('Original title', 'Sketchy title'))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'retitle', cwd=work)
        self.git('push', cwd=work)
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/reject', {'update': True},
                                          headers=admin_headers)
        self.assertEqual(code, 200, data)
        record = self.library.community.get(slug)
        self.assertEqual(record['status'], 'published')
        self.assertEqual(record['pinned_sha'], pinned)
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'Original title', page)
        self.assertNotIn(b'Sketchy title', page)
        self.assertNotIn(b'Update awaiting approval', page)  # discarded: stops nagging for this sha

    def test_takedown_works_whatever_main_is_doing(self):
        """A plain Reject takes a published capability down even with an
        update pending, and even after a discard and a fresh push: a
        submitter must not be able to dodge a takedown by pushing."""
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug, title='Original title')
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        work = self.root / 'publish' / slug
        toml_path = work / 'capability.toml'
        toml_path.write_text(toml_path.read_text().replace('Original title', 'Sketchy title'))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'retitle', cwd=work)
        self.git('push', cwd=work)
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/reject', {'update': True},
                                          headers=admin_headers)
        self.assertEqual(code, 200, data)
        self.assertEqual(self.library.community.get(slug)['status'], 'published')  # discards only the update
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/reject', {'update': True},
                                          headers=admin_headers)
        self.assertEqual(code, 400, data)  # nothing pending to discard any more
        toml_path.write_text(toml_path.read_text().replace('Sketchy title', 'Sketchier title'))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'retitle again', cwd=work)
        self.git('push', cwd=work)
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/reject', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        self.assertEqual(data['status'], 'rejected')
        self.assertEqual(self.library.community.get(slug)['status'], 'rejected')
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertNotIn(f'data-card="community:{slug}"'.encode(), page)

    def test_published_with_no_render_yet_shows_placeholder(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug)
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        page = self.request('/capabilities', headers={'Cookie': dana})[1]
        self.assertIn(b'clip not built', page)
        data = {e['id']: e for e in _community_data(page)}
        self.assertFalse(data[f'community:{slug}']['available'])

    def test_render_of_an_unapproved_intermediate_commit_is_never_served(self):
        """A render of a commit strictly between the previous pin and the
        new one -- never itself approved -- must not stand in for the new
        pin's own (missing) render: the lookup other users get is exact-sha,
        not "the newest render on an ancestor of the pin"."""
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug, name = created['slug'], created['name']
        publishable(self, slug, title='Original title')
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        work = self.root / 'publish' / slug
        toml_path = work / 'capability.toml'
        # An intermediate commit, pushed and rendered, but never approved as a pin.
        toml_path.write_text(toml_path.read_text().replace('Original title', 'Intermediate title'))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'intermediate', cwd=work)
        self.git('push', cwd=work)
        editor = self.library.editor(name)
        sha = self.git('--git-dir', str(self.library.path(name)), 'rev-parse', 'main').stdout.strip()
        path = editor.renders.path('film', sha, '16x9')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'FAKEMP4DATA' * 4)
        # A further commit, unrendered, approved as the new pin.
        toml_path.write_text(toml_path.read_text().replace('Intermediate title', 'Final title'))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'final', cwd=work)
        self.git('push', cwd=work)
        code, data = self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        other_headers = {'Cookie': other}
        code, body, _ = self.request_full(f'/capabilities/community/{slug}.mp4', headers=other_headers)
        self.assertEqual(code, 404, body)  # the intermediate commit's render must not leak to the new pin
        page = self.request('/capabilities', headers=other_headers)[1]
        card = {e['id']: e for e in _community_data(page)}[f'community:{slug}']
        self.assertFalse(card['available'])

    def test_published_capability_whose_pin_goes_invalid_is_refused_to_others(self):
        """A published capability's pinned commit can go invalid later even
        though its own git content never changes -- e.g. a future built-in
        catalog id clashing with it. Its clip must then stop being served to
        anyone but its submitter and admins, consistent with the grid."""
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug, name = created['slug'], created['name']
        publishable(self, slug, id='clashing-id')
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        sha = self.git('--git-dir', str(self.library.path(name)), 'rev-parse', 'main').stdout.strip()
        path = self.library.editor(name).renders.path('film', sha, '16x9')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'FAKEMP4DATA' * 4)
        self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4',
                                      headers={'Cookie': other})[0], 200)
        with mock.patch('videobuilder.capabilities.ids', return_value=capabilities.ids() + ('clashing-id',)):
            self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4',
                                          headers={'Cookie': other})[0], 404)
            self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4',
                                          headers={'Cookie': dana})[0], 200)
            self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4',
                                          headers=admin_headers)[0], 200)
            page = self.request('/capabilities', headers={'Cookie': other})[1]
            self.assertNotIn(f'data-card="community:{slug}"'.encode(), page)


class Reject(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def test_reject_hides_but_keeps_project(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        dana_headers = {'Content-Type': 'application/json', 'Cookie': dana}
        created = self.request('/api/capabilities/new', {'files': 1}, headers=dana_headers)[1]
        slug = created['slug']
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/reject', {}, headers=dana_headers)
        self.assertEqual(code, 403, data)
        publishable(self, slug)
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        code, data, _ = self.request_full(f'/api/capabilities/{slug}/reject', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        self.assertEqual(data['status'], 'rejected')
        for cookie in (dana, admin):
            page = self.request('/capabilities', headers={'Cookie': cookie})[1]
            self.assertNotIn(f'data-card="community:{slug}"'.encode(), page)
            self.assertNotIn(slug.encode(), page)
        self.assertTrue(self.library.path(created['name']).exists())


class ClipGating(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def _place_render(self, name, data=b'FAKEMP4DATA' * 4):
        editor = self.library.editor(name)
        sha = self.git('--git-dir', str(self.library.path(name)), 'rev-parse', 'main').stdout.strip()
        path = editor.renders.path('film', sha, '16x9')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_community_clip_gating(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        dana_headers = {'Content-Type': 'application/json', 'Cookie': dana}
        _, _, other = self.signup('other', 'longenoughpassword')
        other_headers = {'Cookie': other}
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug, name = created['slug'], created['name']
        self.assertEqual(self.request('/capabilities/community/no-such-slug.mp4', headers=other_headers)[0], 404)
        self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4', headers=dana_headers)[0], 404)
        self._place_render(name)
        self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4', headers=dana_headers)[0], 200)
        self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4', headers=admin_headers)[0], 200)
        self.assertEqual(self.request(f'/capabilities/community/{slug}.mp4', headers=other_headers)[0], 404)
        code, body, headers = self.request_full(f'/capabilities/community/{slug}.mp4')
        self.assertEqual(code, 401, body)
        self.assertEqual(headers.get_content_type(), 'application/json')
        publishable(self, slug)
        self._place_render(name)  # the pin is about to move to publishable()'s new commit -- it needs its own render
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        code, body, _ = self.request_full(f'/capabilities/community/{slug}.mp4', headers=other_headers)
        self.assertEqual(code, 200, body)
        code, body, headers = self.request_full(f'/capabilities/community/{slug}.mp4',
                                                 headers={**other_headers, 'Range': 'bytes=0-3'})
        self.assertEqual(code, 206, body)


class BuilderContext(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def _ordinary_note(self, text='Make the intro punchier'):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        recorder = Recorder()
        self.library.editor('acme/launch').notes.backend = recorder
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': text},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, note)
        return recorder

    def test_published_capability_reaches_other_users_builder(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug, title='Snappy zoom reveal', card='A quick punchy zoom on the mark.')
        code, data = self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        recorder = self._ordinary_note()
        self.assertIsNotNone(recorder.last)
        text = Path(recorder.last['note_file']).read_text()
        self.assertIn('## Community capabilities', text)
        self.assertIn('Snappy zoom reveal', text)
        self.assertIn(f'/attachments/capabilities/{slug}/reference.md', text)
        self.assertIn(f'/attachments/capabilities/{slug}/film.py', text)
        attach_dir = Path(recorder.last['attach_dir'])
        self.assertTrue((attach_dir / 'capabilities' / slug / 'reference.md').is_file())
        self.assertTrue((attach_dir / 'capabilities' / slug / 'film.py').is_file())

    def test_draft_never_reaches_a_builder(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug)  # valid, but never published: still a draft
        recorder = self._ordinary_note()
        text = Path(recorder.last['note_file']).read_text()
        self.assertNotIn('Community capabilities', text)
        attach_dir = recorder.last.get('attach_dir')
        if attach_dir:
            self.assertFalse((Path(attach_dir) / 'capabilities' / slug).exists())

    def test_rejected_never_reaches_a_builder(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self.request('/api/capabilities/new', {'files': 1},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})[1]
        slug = created['slug']
        publishable(self, slug)
        self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.request(f'/api/capabilities/{slug}/reject', {}, headers=admin_headers)
        recorder = self._ordinary_note()
        text = Path(recorder.last['note_file']).read_text()
        self.assertNotIn('Community capabilities', text)
        attach_dir = recorder.last.get('attach_dir')
        if attach_dir:
            self.assertFalse((Path(attach_dir) / 'capabilities' / slug).exists())

    def test_no_published_no_forced_attach_dir(self):
        recorder = self._ordinary_note()
        self.assertIsNone(recorder.last.get('attach_dir'))


LOOK_PY = ('from videobuilder import looks\n\n\ndef paint(cv, scene, t, age):\n    cv.fill("#123")\n\n\n'
           'LOOK = looks.Look("stained-glass", "Stained glass", "panes glow", paint)\n')


def publishable_look(case, slug, **overrides):
    """A valid look: family = "looks", the family's category, and a look.py."""
    return publishable(case, slug, title='Stained glass', id='stained-glass', family='looks',
                       category=capabilities.get('looks').category, files={'look.py': LOOK_PY}, **overrides)


class LookSubmission(fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    """"A new look": the dialog's second choice, through to a published look
    in the Looks section and in every builder's prompt."""

    def _new_look(self, cookie):
        code, created = self.request('/api/capabilities/new', {'files': 1, 'family': 'looks',
                                                               'capture': 'stained glass windows'},
                                     headers={'Content-Type': 'application/json', 'Cookie': cookie})
        self.assertEqual(code, 201, created)
        return created

    def test_the_dialog_offers_a_new_capability_or_a_new_look(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        page = self.request('/capabilities', headers={'Cookie': dana})[1].decode()
        self.assertIn('What are you adding?', page)
        self.assertIn('<input type="radio" name="family" value="" checked><strong>A new capability</strong>', page)
        self.assertIn('<input type="radio" name="family" value="looks"><strong>A new look</strong>', page)
        self.assertIn('data-heading="Add a look"', page)

    def test_a_look_submission_gets_the_look_brief(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        created = self._new_look(dana)
        self.assertEqual(self.library.community.get(created['slug'])['family'], 'looks')
        code, note = self.request(f'/api/capabilities/{created["slug"]}/send', {'attachments': []},
                                  headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 200, note)
        for needle in ('Looks family', 'look.py', 'film.py', 'family = "looks"', 'capability.md',
                       'reference/looks.md', 'looks.lighthouse', 'looks.FLOOR', 'untrusted', 'stained glass windows'):
            self.assertIn(needle, note['text'])

    def test_an_unknown_family_is_refused_before_anything_is_made(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        for family in ('nope', 'eased-entrances', 3, ['looks']):
            with self.subTest(family=family):
                code, data, _ = self.request_full('/api/capabilities/new', {'files': 1, 'family': family},
                                                  headers={'Content-Type': 'application/json', 'Cookie': dana})
                self.assertEqual(code, 400, data)
        self.assertEqual(self.library.names(), [])
        self.assertEqual(self.library.community.all(), {})

    def test_publishing_checks_the_family_and_look_py(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        look_slug = self._new_look(dana)['slug']
        publishable(self, look_slug, title='Stained glass', id='stained-glass',
                    category=capabilities.get('looks').category)         # no family, no look.py
        code, data, _ = self.request_full(f'/api/capabilities/{look_slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 400, data)
        self.assertIn('family must be "looks"', data['error'])
        cap_slug = self.request('/api/capabilities/new', {'files': 1},
                                headers={'Content-Type': 'application/json', 'Cookie': dana})[1]['slug']
        publishable_look(self, cap_slug)                                     # a look, sent as a capability
        code, data, _ = self.request_full(f'/api/capabilities/{cap_slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 400, data)
        self.assertIn('family must be left out', data['error'])

    def test_a_published_look_sits_in_the_looks_section_and_reaches_every_builder(self):
        admin = self.admin_login()
        admin_headers = {'Content-Type': 'application/json', 'Cookie': admin}
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        slug = self._new_look(dana)['slug']
        publishable_look(self, slug)
        code, data = self.request(f'/api/capabilities/{slug}/publish', {}, headers=admin_headers)
        self.assertEqual(code, 200, data)
        page = self.request('/capabilities', headers={'Cookie': other})[1].decode()
        main = page[page.index('<main>'):page.index('</main>')]
        section = main[main.index('<h2>Looks</h2>'):]
        section = section[:section.index('<h2>', 4)]
        self.assertEqual(main.count(f'data-card="community:{slug}"'), 1)
        self.assertIn(f'data-card="community:{slug}"', section)
        self.assertIn('<span class="count">15 looks</span>', section)
        builder = BuilderContext._ordinary_note(self)
        text = Path(builder.last['note_file']).read_text()
        looks_section = text[text.index('## Looks'):text.index('## Look at your work')]
        self.assertIn('Stained glass (`stained-glass`)', looks_section)
        self.assertIn(f'/attachments/capabilities/{slug}/look.py', looks_section)
        self.assertNotIn('## Community capabilities', text)
        staged = Path(builder.last['attach_dir']) / 'capabilities' / slug
        self.assertEqual((staged / 'look.py').read_text(), LOOK_PY)
        self.assertTrue((staged / 'reference.md').is_file())
        self.assertTrue((staged / 'film.py').is_file())

    def test_a_look_published_at_the_old_category_stays_in_the_looks_section(self):
        # Before looks had a category of their own, a look's toml had to say
        # "Imagery and camera"; one pinned there must not drop off the page.
        admin = self.admin_login()
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, _, other = self.signup('other', 'longenoughpassword')
        slug = self._new_look(dana)['slug']
        publishable(self, slug, title='Stained glass', id='stained-glass', family='looks',
                    category='Imagery and camera', files={'look.py': LOOK_PY})
        code, data = self.request(f'/api/capabilities/{slug}/publish', {},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, data)
        page = self.request('/capabilities', headers={'Cookie': other})[1].decode()
        main = page[page.index('<main>'):page.index('</main>')]
        section = main[main.index('<h2>Looks</h2>'):]
        section = section[:section.index('<h2>', 4)]
        self.assertIn(f'data-card="community:{slug}"', section)
        script = page[page.index('<script id="community-data"'):]
        items = json.loads(script[script.index('>') + 1:script.index('</script>')])
        self.assertEqual([i['category'] for i in items if i['id'] == f'community:{slug}'], ['Looks'])


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
