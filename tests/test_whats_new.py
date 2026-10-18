"""What's new: the state-dir store, its CLI, the page and its routes."""
import contextlib
import io
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from videobuilder import pages
from videobuilder.cli import main
from videobuilder.whats_new import WhatsNew, notes_html

from tests.fixtures import AccountMixin, LibraryFixture

# Enough of an MP4 for the upload check (an `ftyp` box first); the routes never decode it.
MP4 = b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2' + bytes(range(256)) * 40


def cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        main(['whats-new', *args])
    return out.getvalue()


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_cli_add_list_remove(self):
        state = self.root / 'state'
        (self.root / 'notes.txt').write_text('Clips and a song.\n\n- A timeline\n- Beats\n')
        (self.root / 'tall.mp4').write_bytes(MP4)
        (self.root / 'wide.mp4').write_bytes(MP4)
        out = cli('add', '--state', str(state), '--title', 'Older', '--date', '2026-09-01')
        self.assertEqual(out, 'added 2026-09-01\n')
        out = cli('add', '--state', str(state), '--title', 'Clips and a timeline', '--versions', '0.1.81–0.1.88',
                  '--notes', str(self.root / 'notes.txt'), '--date', '2026-10-18',
                  '--video', f'9x16={self.root / "tall.mp4"}', '--video', f'16x9={self.root / "wide.mp4"}')
        self.assertEqual(out, 'added 2026-10-18 with 9x16, 16x9\n')
        self.assertEqual(cli('add', '--state', str(state), '--title', 'Same day', '--date', '2026-10-18'),
                         'added 2026-10-18-02\n')
        self.assertEqual(cli('list', '--state', str(state)).splitlines(),
                         ['2026-10-18-02  Same day', '2026-10-18  Clips and a timeline  (0.1.81–0.1.88 9x16,16x9)',
                          '2026-09-01  Older'])
        folder = state / 'whats-new' / '2026-10-18'
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['16x9.mp4', '9x16.mp4', 'entry.json'])
        entry = json.loads((folder / 'entry.json').read_text())
        self.assertEqual((entry['title'], entry['versions'], entry['notes']),
                         ('Clips and a timeline', '0.1.81–0.1.88', 'Clips and a song.\n\n- A timeline\n- Beats'))
        self.assertEqual((folder / '9x16.mp4').read_bytes(), MP4)
        self.assertEqual(cli('remove', '--state', str(state), '2026-10-18-02'), 'removed 2026-10-18-02\n')
        self.assertEqual([e['id'] for e in WhatsNew(state).list()], ['2026-10-18', '2026-09-01'])
        with self.assertRaises(SystemExit):
            cli('remove', '--state', str(state), '2026-10-18-02')

    def test_cli_add_refuses_a_bad_video_and_leaves_nothing(self):
        state = self.root / 'state'
        (self.root / 'not.mp4').write_bytes(b'<html>not a video</html>')
        for spec in ('9x16=' + str(self.root / 'not.mp4'), '4x3=' + str(self.root / 'not.mp4'),
                     '9x16=' + str(self.root / 'missing.mp4'), 'no-equals'):
            with self.subTest(spec=spec), self.assertRaises(SystemExit):
                cli('add', '--state', str(state), '--title', 'T', '--video', spec)
        self.assertEqual(WhatsNew(state).list(), [])

    def test_fields_are_checked(self):
        store = WhatsNew(self.root)
        for kw in ({'title': ' '}, {'title': 'x' * 121}, {'title': 'T', 'date': '18/10/2026'},
                   {'title': 'T\x00'}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                store.add(kw['title'], '', '', kw.get('date'))
        for bad in ('../x', '2026-10-18/../../etc', 'latest'):
            with self.subTest(bad=bad), self.assertRaises(KeyError):
                store.get(bad)

    def test_notes_are_paragraphs_and_lists_and_nothing_else(self):
        self.assertEqual(notes_html('One\nline two\n\n- a\n* <b>b</b>\nafter'),
                         '<p>One<br>line two</p><ul><li>a</li><li>&lt;b&gt;b&lt;/b&gt;</li></ul><p>after</p>')
        self.assertEqual(notes_html(''), '')


class Page(unittest.TestCase):
    def _entries(self):
        return [{'id': '2026-10-18', 'title': 'Newest <i>one</i>', 'date': '2026-10-18', 'versions': '0.1.81–0.1.88',
                 'notes': 'Hello <script>alert(1)</script>', 'videos': ['9x16', '16x9']},
                {'id': '2026-09-01', 'title': 'Older', 'date': '2026-09-01', 'versions': '', 'notes': '',
                 'videos': []}]

    def test_entries_render_newest_first_with_escaped_notes(self):
        page = pages.whats_new_page(self._entries()).decode()
        self.assertLess(page.index('Newest'), page.index('Older'))
        self.assertIn('Hello &lt;script&gt;alert(1)&lt;/script&gt;', page)
        self.assertIn('Newest &lt;i&gt;one&lt;/i&gt;', page)
        self.assertNotIn('<script>alert', page)
        self.assertIn('18 October 2026', page)
        self.assertIn('/whats-new/2026-10-18/9x16.mp4', page)
        self.assertIn('data-whats-new="2026-10-18"', page)
        self.assertNotIn('id="wn-form"', page)
        self.assertNotIn('changelog', page.lower())

    def test_admin_sees_the_form_and_remove_buttons(self):
        page = pages.whats_new_page(self._entries(), is_admin=True, max_bytes=5 * 1048576).decode()
        self.assertIn('id="wn-form" data-max="5242880"', page)
        self.assertEqual(page.count('class="wn-remove"'), 2)

    def test_app_bar_link_only_with_entries(self):
        self.assertNotIn('/whats-new', pages.app_header('library', 'dana'))
        self.assertIn('href="/whats-new" data-whats-new="2026-10-18"',
                      pages.app_header('library', 'dana', whats_new='2026-10-18'))


class Routes(LibraryFixture, unittest.TestCase):
    """Single-user mode: everyone can read, and everyone is the admin."""

    def test_no_link_until_an_entry_then_page_and_ranged_video(self):
        code, page = self.request('/')
        self.assertEqual(code, 200)
        self.assertNotIn(b'/whats-new', page)
        self.assertNotIn(b'/whats-new', self.request('/new')[1])
        self.assertIn(b'Nothing here yet', self.request('/whats-new')[1])
        entry = self.library.whats_new.add('First', '0.1.1', 'Notes')
        self.library.whats_new.add_video_file(entry['id'], '16x9', self._mp4())
        self.assertIn(b'data-whats-new="' + entry['id'].encode(), self.request('/')[1])
        self.assertIn(b'data-whats-new="' + entry['id'].encode(), self.request('/capabilities')[1])
        url = f'/whats-new/{entry["id"]}/16x9.mp4'
        code, body, headers = self.request_full(url)
        self.assertEqual((code, body, headers['Accept-Ranges']), (200, MP4, 'bytes'))
        code, body, headers = self.request_full(url, headers={'Range': 'bytes=10-19'})
        self.assertEqual((code, body, headers['Content-Range']), (206, MP4[10:20], f'bytes 10-19/{len(MP4)}'))
        code, _, headers = self.request_full(url, headers={'Range': f'bytes={len(MP4)}-'})
        self.assertEqual(code, 416)
        self.assertEqual(self.request(f'/whats-new/{entry["id"]}/9x16.mp4')[0], 404)
        self.assertEqual(self.request('/whats-new/..%2f..%2fstate/16x9.mp4')[0], 404)

    def _mp4(self):
        path = self.root / 'clip.mp4'
        path.write_bytes(MP4)
        return path

    def test_the_form_routes_add_upload_and_remove(self):
        code, entry = self.request('/api/whats-new', {'title': 'Via the page', 'versions': '1–2',
                                                      'notes': 'Hi', 'date': '2026-10-01'})
        self.assertEqual((code, entry['id'], entry['videos']), (201, '2026-10-01', []))
        code, entry = self._upload(entry['id'], '9x16', MP4)
        self.assertEqual((code, entry['videos']), (201, ['9x16']))
        self.assertEqual(self._upload('2026-10-01', '4x3', MP4)[0], 400)
        self.assertEqual(self._upload('2026-10-01', '16x9', b'<html>' * 10)[0], 400)
        self.assertEqual(self._upload('2026-01-01', '16x9', MP4)[0], 404)
        self.assertEqual(self.request('/api/whats-new', {'title': ''})[0], 400)
        code, _ = self.request('/api/whats-new/2026-10-01/remove', {})
        self.assertEqual(code, 200)
        self.assertEqual(self.library.whats_new.list(), [])

    def test_upload_size_cap(self):
        self.library.whats_new.max_video_bytes = len(MP4) - 1
        entry = self.library.whats_new.add('Capped', '', '')
        code, body = self._upload(entry['id'], '9x16', MP4)
        self.assertEqual(code, 413, body)
        self.assertIn('limited to', body['error'])
        self.assertEqual(sorted(p.name for p in (self.library.state_dir / 'whats-new' / entry['id']).iterdir()),
                         ['entry.json'])

    def test_upload_from_another_origin_is_refused(self):
        entry = self.library.whats_new.add('Cross', '', '')
        code, _ = self._upload(entry['id'], '9x16', MP4, {'Origin': 'http://evil.example'})
        self.assertEqual(code, 403)

    def _upload(self, entry_id, fmt, data, headers=None):
        req = urllib.request.Request(f'{self.base}/api/whats-new/{entry_id}/video?format={fmt}', data=data,
                                     method='POST', headers={'Content-Type': 'video/mp4', **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())


class AccountRoutes(AccountMixin, LibraryFixture, unittest.TestCase):
    def test_readers_need_sign_in_and_only_an_admin_adds(self):
        entry = self.library.whats_new.add('First', '', '')
        self.library.whats_new.add_video_file(entry['id'], '9x16', self._mp4())
        self.assertIn(b'Sign in', self.request('/whats-new')[1])
        self.assertEqual(self.request(f'/whats-new/{entry["id"]}/9x16.mp4')[0], 401)
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, page = self.request('/whats-new', headers={'Cookie': dana})
        self.assertEqual(code, 200)
        self.assertIn(b'First', page)
        self.assertNotIn(b'id="wn-form"', page)
        self.assertIn(b'href="/whats-new"', self.request('/', headers={'Cookie': dana})[1])
        self.assertEqual(self.request(f'/whats-new/{entry["id"]}/9x16.mp4', headers={'Cookie': dana})[0], 200)
        json_headers = {'Content-Type': 'application/json', 'Cookie': dana}
        self.assertEqual(self.request('/api/whats-new', {'title': 'Nope'}, headers=json_headers)[0], 403)
        self.assertEqual(self.request(f'/api/whats-new/{entry["id"]}/remove', {}, headers=json_headers)[0], 403)
        req = urllib.request.Request(f'{self.base}/api/whats-new/{entry["id"]}/video?format=16x9', data=MP4,
                                     method='POST', headers={'Content-Type': 'video/mp4', 'Cookie': dana})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=20)
        e.exception.close()
        self.assertEqual(e.exception.code, 403)
        self.assertEqual(len(self.library.whats_new.list()), 1)
        admin = self.admin_login()
        self.assertIn(b'id="wn-form"', self.request('/whats-new', headers={'Cookie': admin})[1])
        code, added = self.request('/api/whats-new', {'title': 'Admin'},
                                   headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 201, added)

    def _mp4(self):
        path = self.root / 'clip.mp4'
        path.write_bytes(MP4)
        return path
