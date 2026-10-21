"""Deleting a video: Library.delete, its trash and purge, and POST /api/videos/delete."""
import datetime
import json
import time
import unittest

from videobuilder.editor import HTTPError
from videobuilder.library import TRASH_DAYS, TRASH_STAMP
from tests.fixtures import AccountMixin, LibraryFixture

PASSWORD = 'gardening-pw-1'


def write_note(notes_dir, nid, state, author=None, created=None):
    notes_dir.mkdir(parents=True, exist_ok=True)
    created = created or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    (notes_dir / f'{nid}.json').write_text(json.dumps(
        {'id': nid, 'video': 'film', 'state': state, 'author': author, 'created': created, 'text': 'x'}))


class DeleteWithAccounts(AccountMixin, LibraryFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.dana = self.signup('dana', PASSWORD)[2]
        self.erin = self.signup('erin', PASSWORD)[2]
        self.fred = self.signup('fred', PASSWORD)[2]
        code, data = self.request('/api/videos/new', {'name': 'acme/launch', 'start': 'blank'},
                                  headers=self.as_user(self.dana))
        self.assertEqual(code, 201, data)
        code, data = self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'erin'},
                                  headers=self.as_user(self.dana))
        self.assertEqual(code, 200, data)

    def as_user(self, cookie):
        return {'Content-Type': 'application/json', 'Cookie': cookie}

    def delete(self, cookie, name='acme/launch'):
        return self.request('/api/videos/delete', {'name': name}, headers=self.as_user(cookie))

    def test_owner_deletes_into_the_trash(self):
        editor = self.library.editor('acme/launch')    # makes the checkout and state dir
        write_note(self.library.state_dir / 'acme--launch' / 'notes', 'n1', 'landed', author='dana')
        code, data = self.request('/v/acme/launch/api/access', headers={'Cookie': self.dana})
        self.assertTrue(data['can_delete'])
        code, data = self.delete(self.dana)
        self.assertEqual((code, data), (200, {'deleted': 'acme/launch'}))
        self.assertNotIn('acme/launch', self.library.names())
        self.assertNotIn('acme/launch', self.library.editors)
        self.assertFalse(editor.renders.thread.is_alive())
        for path in (self.library.path('acme/launch'), self.library.checkouts / 'acme--launch',
                     self.library.state_dir / 'acme--launch'):
            self.assertFalse(path.exists(), path)
        [entry] = list(self.library.trash.iterdir())
        self.assertTrue(entry.name.startswith('acme--launch--'))
        self.assertTrue((entry / 'repo.git' / 'HEAD').is_file())
        self.assertTrue((entry / 'checkout' / 'film.py').is_file())
        self.assertTrue((entry / 'state' / 'notes' / 'n1.json').is_file())
        record = json.loads((entry / 'deleted.json').read_text())
        self.assertEqual((record['name'], record['owner'], record['collaborators'], record['deleted_by']),
                         ('acme/launch', 'dana', ['erin'], 'dana'))
        self.assertIn('owner_uid', record['access'])
        self.assertNotIn('acme/launch', json.loads((self.library.state_dir / 'access.json').read_text()))
        # Gone exactly like a name that never existed.
        self.assertEqual(self.request('/v/acme/launch/', headers={'Cookie': self.dana})[0], 404)
        self.assertEqual(self.request('/v/acme/launch/api/project', headers={'Cookie': self.dana})[0], 404)
        clone = self.git('clone', self.url('acme/launch'), str(self.root / 'clone'), ok=False)
        self.assertNotEqual(clone.returncode, 0)
        self.assertIn('not found', clone.stderr)
        self.assertEqual(self.delete(self.dana)[0], 404)
        # The name is free again, and the new video starts with nothing of the old one.
        code, data = self.request('/api/videos/new', {'name': 'acme/launch', 'start': 'blank'},
                                  headers=self.as_user(self.fred))
        self.assertEqual(code, 201, data)
        self.assertEqual(self.library.access.get('acme/launch', self.library.accounts),
                         {'owner': 'fred', 'collaborators': []})
        self.assertEqual(self.library.editor('acme/launch').notes.list(refresh=False), [])

    def test_collaborator_and_stranger_are_refused(self):
        code, data = self.delete(self.erin)
        self.assertEqual(code, 403)
        self.assertIn('Only the owner', json.loads(data)['error'])
        # A stranger can't tell the video exists, as at /v/<name>/.
        self.assertEqual(self.delete(self.fred)[0], 404)
        code, data = self.request('/v/acme/launch/api/access', headers={'Cookie': self.erin})
        self.assertFalse(data['can_delete'])
        self.assertIn('acme/launch', self.library.names())

    def test_admin_may_delete(self):
        code, data = self.delete(self.admin_login())
        self.assertEqual(code, 200, data)
        record = json.loads(next(self.library.trash.iterdir()).joinpath('deleted.json').read_text())
        self.assertEqual((record['owner'], record['deleted_by']), ('dana', 'mgalgs'))

    def test_a_key_cannot_delete(self):
        _, secret = self.library.accounts.create_key('dana', 'writer', None, 'write')
        code, _ = self.request('/api/videos/delete', {'name': 'acme/launch'},
                               headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {secret}'})
        self.assertEqual(code, 401)
        self.assertIn('acme/launch', self.library.names())

    def test_unfinished_note_refuses(self):
        write_note(self.library.state_dir / 'acme--launch' / 'notes', 'n1', 'queued', author='dana')
        code, data = self.delete(self.dana)
        self.assertEqual(code, 409)
        self.assertEqual(json.loads(data)['error'],
                         'A note is still being built. Wait for it to finish, then delete.')
        self.assertIn('acme/launch', self.library.names())

    def test_capability_name_refused(self):
        self.library.create_blank('capabilities/abc', allow_reserved=True)
        self.library.access.set_owner('capabilities/abc', 'dana', self.library.accounts)
        code, _ = self.delete(self.dana, 'capabilities/abc')
        self.assertEqual(code, 403)
        self.assertIn('capabilities/abc', self.library.names())

    def test_deleted_notes_still_count_against_the_cap(self):
        write_note(self.library.state_dir / 'acme--launch' / 'notes', 'n1', 'landed', author='dana')
        self.assertEqual(self.delete(self.dana)[0], 200)
        self.assertEqual([(n, note['id']) for n, note in self.library.account_notes()], [('acme/launch', 'n1')])
        self.library.account_daily_note_cap = 1
        with self.assertRaises(HTTPError) as caught:
            self.library.check_note_cap('dana', False)
        self.assertEqual(caught.exception.code, 429)


class DeleteWithoutAccounts(LibraryFixture, unittest.TestCase):
    def test_anyone_may_delete(self):
        code, data = self.request('/api/videos/new', {'name': 'gardening', 'start': 'blank'})
        self.assertEqual(code, 201, data)
        code, data = self.request('/v/gardening/api/access')
        self.assertEqual((code, data['can_delete'], data['can_share']), (200, True, False))
        self.assertEqual(self.request('/api/videos/delete', {'name': 'gardening'}), (200, {'deleted': 'gardening'}))
        self.assertEqual(self.library.names(), [])
        record = json.loads(next(self.library.trash.iterdir()).joinpath('deleted.json').read_text())
        self.assertEqual((record['name'], record['owner'], record['access']), ('gardening', None, None))

    def test_must_be_json_from_this_origin(self):
        self.request('/api/videos/new', {'name': 'gardening', 'start': 'blank'})
        code, _ = self.request('/api/videos/delete', {'name': 'gardening'},
                               headers={'Content-Type': 'application/json', 'Origin': 'http://evil.example'})
        self.assertEqual(code, 403)
        self.assertEqual(self.library.names(), ['gardening'])

    def test_purge_removes_only_old_entries(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        old = self.library.trash / ('gardening--' + (now - datetime.timedelta(days=TRASH_DAYS + 1)).strftime(TRASH_STAMP))
        new = self.library.trash / ('acme--launch--' + (now - datetime.timedelta(days=TRASH_DAYS - 1)).strftime(TRASH_STAMP))
        for entry in (old, new):
            (entry / 'state').mkdir(parents=True)
        self.library.purge_trash()
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())
        # Checked at most hourly: a second tick soon after looks at nothing.
        newer_old = self.library.trash / ('acme--old--' + (now - datetime.timedelta(days=40)).strftime(TRASH_STAMP))
        newer_old.mkdir()
        self.library.tick()
        self.assertTrue(newer_old.exists())
        self.library.purge_trash(force=True)
        self.assertFalse(newer_old.exists())


if __name__ == '__main__':
    unittest.main()
