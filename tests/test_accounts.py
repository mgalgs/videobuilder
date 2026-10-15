"""Accounts: usernames, scrypt hashes, sessions, lockout and admin bootstrap."""
import json
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

from videobuilder.accounts import Accounts, KEY_LAST_USED_FLUSH, LOGIN_LIMIT, SIGNUP_LIMIT, valid_username


class AccountsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)

    def admin_file(self, password):
        path = self.state / 'admin-pass'
        path.write_text(password + '\n')
        return str(path)

    def test_valid_username(self):
        self.assertTrue(valid_username('abc'))
        self.assertTrue(valid_username('a.b_c-9'))
        self.assertFalse(valid_username('ab'))  # too short
        self.assertFalse(valid_username('a' * 33))  # too long
        self.assertFalse(valid_username('Abc'))  # uppercase
        self.assertFalse(valid_username('a b'))
        self.assertFalse(valid_username(''))

    def test_signup_creates_account_and_session_no_plaintext(self):
        accounts = Accounts(str(self.state))
        username, token = accounts.signup('Dana', 'longenoughpassword')
        self.assertEqual(username, 'dana')
        self.assertEqual(accounts.user_for_token(token), 'dana')
        raw = (self.state / 'accounts.json').read_text()
        self.assertNotIn('longenoughpassword', raw)
        record = json.loads(raw)['users']['dana']
        self.assertEqual(record['algorithm'], 'scrypt')
        self.assertIn('salt', record)
        self.assertIn('hash', record)

    def test_signup_refuses_duplicate_case_insensitive(self):
        accounts = Accounts(str(self.state))
        accounts.signup('dana', 'longenoughpassword')
        with self.assertRaises(ValueError):
            accounts.signup('Dana', 'anotherlongpassword')

    def test_signup_refuses_admin_name_short_password_and_bad_username(self):
        accounts = Accounts(str(self.state), [('mgalgs', self.admin_file('adminsecret1'))])
        with self.assertRaises(ValueError):
            accounts.signup('mgalgs', 'longenoughpassword')
        with self.assertRaises(ValueError):
            accounts.signup('MGALGS', 'longenoughpassword')
        with self.assertRaises(ValueError):
            accounts.signup('dana', 'short')
        with self.assertRaises(ValueError):
            accounts.signup('d', 'longenoughpassword')
        with self.assertRaises(ValueError):
            accounts.signup('Has Space', 'longenoughpassword')

    def test_signup_throttle(self):
        accounts = Accounts(str(self.state))
        for i in range(SIGNUP_LIMIT):
            accounts.signup(f'user{i}', 'longenoughpassword')
        with self.assertRaises(ValueError):
            accounts.signup('oneoverthelimit', 'longenoughpassword')

    def test_admin_bootstrap_and_restart_updates_password(self):
        path = self.admin_file('first-password')
        accounts = Accounts(str(self.state), [('mgalgs', path)])
        self.assertTrue(accounts.is_admin('mgalgs'))
        self.assertTrue(accounts.is_admin('MGALGS'))
        self.assertEqual(accounts.verify('mgalgs', 'first-password'), 'mgalgs')
        with self.assertRaises(ValueError):
            accounts.verify('mgalgs', 'wrong-password')
        path_obj = Path(path)
        path_obj.write_text('second-password\n')
        restarted = Accounts(str(self.state), [('mgalgs', path)])
        with self.assertRaises(ValueError):
            restarted.verify('mgalgs', 'first-password')
        self.assertEqual(restarted.verify('mgalgs', 'second-password'), 'mgalgs')

    def test_admin_without_password_file_is_a_startup_error(self):
        with self.assertRaises(ValueError):
            Accounts(str(self.state), [('mgalgs', None)])
        with self.assertRaises(ValueError):
            Accounts(str(self.state), [('mgalgs', str(self.state / 'does-not-exist'))])

    def test_login_lockout_and_logout(self):
        accounts = Accounts(str(self.state))
        accounts.signup('dana', 'longenoughpassword')
        for _ in range(LOGIN_LIMIT):
            with self.assertRaises(ValueError):
                accounts.login('dana', 'wrong')
        with self.assertRaises(ValueError) as caught:
            accounts.login('dana', 'longenoughpassword')
        self.assertIn('too many attempts', str(caught.exception))

    def test_lockout_does_not_reveal_username_existence(self):
        accounts = Accounts(str(self.state))
        accounts.signup('dana', 'longenoughpassword')
        real_error = None
        with self.assertRaises(ValueError) as caught:
            accounts.login('dana', 'wrong')
        real_error = str(caught.exception)
        with self.assertRaises(ValueError) as caught2:
            accounts.login('nosuchuser', 'wrong')
        self.assertEqual(real_error, str(caught2.exception))

    def test_logout_ends_session(self):
        accounts = Accounts(str(self.state))
        _, token = accounts.signup('dana', 'longenoughpassword')
        self.assertEqual(accounts.user_for_token(token), 'dana')
        accounts.logout(token)
        self.assertIsNone(accounts.user_for_token(token))

    def test_expired_session_is_rejected(self):
        accounts = Accounts(str(self.state))
        _, token = accounts.signup('dana', 'longenoughpassword')
        import hashlib
        key = hashlib.sha256(token.encode()).hexdigest()
        accounts._data['sessions'][key]['expires'] = time.time() - 1
        accounts._save()
        self.assertIsNone(accounts.user_for_token(token))


class KeysTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        self.accounts = Accounts(str(self.state))
        self.accounts.signup('dana', 'longenoughpassword')

    def test_create_returns_secret_once_and_file_holds_only_its_hash(self):
        record, secret = self.accounts.create_key('dana', 'laptop', None, 'write')
        self.assertTrue(secret.startswith('vbk_'))
        self.assertGreaterEqual(len(secret), 36)
        self.assertEqual(record['label'], 'laptop')
        self.assertIsNone(record['scope'])
        self.assertEqual(record['mode'], 'write')
        self.assertNotIn('secret', record)
        self.assertNotIn('username', record)  # the public record; not identity
        raw = (self.state / 'accounts.json').read_text()
        self.assertNotIn(secret, raw)
        found = self.accounts.key_for_secret(secret)
        self.assertEqual(found['id'], record['id'])
        self.assertEqual(found['username'], 'dana')  # key_for_secret says who it acts as; list_keys doesn't need to

    def test_list_never_shows_a_secret(self):
        self.accounts.create_key('dana', 'laptop', None, 'write')
        self.accounts.create_key('dana', 'phone', 'gardening', 'read')
        listed = self.accounts.list_keys('dana')
        self.assertEqual(len(listed), 2)
        for record in listed:
            self.assertNotIn('secret', record)
            self.assertNotIn('uid', record)

    def test_revoke_works_on_the_next_request(self):
        _, secret = self.accounts.create_key('dana', 'laptop', None, 'write')
        self.assertIsNotNone(self.accounts.key_for_secret(secret))
        record = self.accounts.list_keys('dana')[0]
        self.accounts.revoke_key('dana', record['id'])
        self.assertIsNone(self.accounts.key_for_secret(secret))
        self.assertEqual(self.accounts.list_keys('dana'), [])

    def test_revoke_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.accounts.revoke_key('dana', 'nosuchid')

    def test_deleted_and_recreated_account_kills_its_old_keys(self):
        _, secret = self.accounts.create_key('dana', 'laptop', None, 'write')
        del self.accounts._data['users']['dana']
        self.accounts._save()
        self.accounts.signup('dana', 'anotherlongpassword')
        self.assertIsNone(self.accounts.key_for_secret(secret))
        self.assertEqual(self.accounts.list_keys('dana'), [])

    def test_bad_secret_is_rejected(self):
        self.assertIsNone(self.accounts.key_for_secret('vbk_nosuchkey'))
        self.assertIsNone(self.accounts.key_for_secret('not-even-key-shaped'))
        self.assertIsNone(self.accounts.key_for_secret(None))

    def test_label_scope_mode_validation(self):
        with self.assertRaises(ValueError):
            self.accounts.create_key('dana', '', None, 'write')
        with self.assertRaises(ValueError):
            self.accounts.create_key('dana', 'a' * 41, None, 'write')
        with self.assertRaises(ValueError):
            self.accounts.create_key('dana', 'has (parens)', None, 'write')
        with self.assertRaises(ValueError):
            self.accounts.create_key('dana', 'ok', 'Bad Scope', 'write')
        with self.assertRaises(ValueError):
            self.accounts.create_key('dana', 'ok', None, 'delete')
        record, _ = self.accounts.create_key('dana', 'ok', 'gardening', 'read')
        self.assertEqual(record['scope'], 'gardening')

    def test_create_key_requires_existing_account(self):
        with self.assertRaises(ValueError):
            self.accounts.create_key('nosuchuser', 'laptop', None, 'write')

    def test_last_used_updates_in_memory_but_flushes_at_most_hourly(self):
        _, secret = self.accounts.create_key('dana', 'laptop', None, 'write')
        self.accounts.key_for_secret(secret)
        digest = next(iter(self.accounts._data['keys']))
        first_flush = self.accounts._key_flushed[digest]
        on_disk = json.loads((self.state / 'accounts.json').read_text())
        self.assertIsNotNone(next(iter(on_disk['keys'].values()))['last_used'])
        soon_after = first_flush + 10
        with unittest.mock.patch('time.time', return_value=soon_after):
            self.accounts.key_for_secret(secret)
        # The in-memory record moved, but the flush timestamp (and so the on-disk copy) did not.
        self.assertEqual(self.accounts._data['keys'][digest]['last_used'], soon_after)
        self.assertEqual(self.accounts._key_flushed[digest], first_flush)
        on_disk = json.loads((self.state / 'accounts.json').read_text())
        self.assertNotEqual(next(iter(on_disk['keys'].values()))['last_used'], soon_after)
        much_later = first_flush + KEY_LAST_USED_FLUSH + 1
        with unittest.mock.patch('time.time', return_value=much_later):
            self.accounts.key_for_secret(secret)
        self.assertEqual(self.accounts._key_flushed[digest], much_later)


if __name__ == '__main__':
    unittest.main()
