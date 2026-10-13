"""User accounts and sessions for library auth (off unless admins are given).

One JSON file under the library state dir holds everyone: usernames, scrypt
password hashes (never plaintext, except the admin password files the
operator supplies), and sessions keyed by the session token's SHA-256, so
the file never holds a usable token. Login lockout and sign-up throttling
are in memory and reset on restart.

Each account also gets a random `uid` at creation, stable across restarts,
that never gets reused even if the username is. Sessions and access grants
record the uid they were issued to, not just the username, so deleting a
user's record (by hand, with the editor stopped) invalidates their
outstanding sessions, and a later sign-up under the same name starts with no
borrowed access. The file is only read at startup: editing it while the
editor is running will be overwritten by its next write.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time

USERNAME = re.compile(r'[a-z0-9._-]{3,32}\Z')

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
SESSION_TTL = 30 * 24 * 3600
LOGIN_WINDOW = 15 * 60
LOGIN_LIMIT = 5
SIGNUP_WINDOW = 60 * 60
SIGNUP_LIMIT = 20


def valid_username(name):
    """Whether `name`, already lowercased, is a well-formed username."""
    return isinstance(name, str) and bool(USERNAME.fullmatch(name))


def normalize_username(name):
    """`name` lowercased and validated; raises ValueError if malformed."""
    name = name.lower() if isinstance(name, str) else name
    if not valid_username(name):
        raise ValueError('username must be 3-32 characters of a-z, 0-9, ".", "_" or "-"')
    return name


def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return {'algorithm': 'scrypt', 'n': SCRYPT_N, 'r': SCRYPT_R, 'p': SCRYPT_P,
            'salt': salt.hex(), 'hash': digest.hex()}


def _check_password(password, record):
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(record['salt']),
                            n=record['n'], r=record['r'], p=record['p'], dklen=32)
    return hmac.compare_digest(digest, bytes.fromhex(record['hash']))


class Accounts:
    """Usernames, password hashes and sessions. `admins` is a sequence of
    (name, password_file) pairs: each admin's hash is (re)created from its
    file's first line on every startup, so a changed Secret takes effect on
    restart. An admin name is reserved: sign-up refuses it."""

    def __init__(self, state_dir, admins=()):
        self.path = os.path.join(state_dir, 'accounts.json')
        self.lock = threading.RLock()
        self._data = self._load()
        self._failures = {}
        self._signups = []
        self.admins = set()
        for name, password_file in admins:
            name = normalize_username(name)
            if not password_file:
                raise ValueError(f'--admin {name} needs a matching --admin-password-file')
            try:
                with open(password_file, encoding='utf-8') as fh:
                    password = fh.readline().strip('\r\n')
            except OSError as exc:
                raise ValueError(f'cannot read admin password file for {name}: {exc}') from None
            if not password:
                raise ValueError(f'admin password file for {name} is empty')
            self.admins.add(name)
            with self.lock:
                uid = self._data['users'].get(name, {}).get('uid') or secrets.token_hex(16)
                self._data['users'][name] = {**_hash_password(password), 'admin': True, 'uid': uid}
                self._save()

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as fh:
                return json.load(fh)
        except FileNotFoundError:
            return {'users': {}, 'sessions': {}}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(self._data, fh)
        os.replace(tmp, self.path)

    def is_admin(self, username):
        return isinstance(username, str) and username.lower() in self.admins

    def exists(self, username):
        return isinstance(username, str) and username.lower() in self._data['users']

    def uid(self, username):
        """The account's stable id, or None if there is no such account. Used to
        tell a deleted-and-recreated account apart from the one that held a
        session or an access grant before it was deleted."""
        username = username.lower() if isinstance(username, str) else ''
        record = self._data['users'].get(username)
        return record['uid'] if record else None

    def signup(self, username, password):
        """Create an account and sign it in; (username, session token)."""
        now = time.time()
        with self.lock:
            self._signups = [t for t in self._signups if now - t < SIGNUP_WINDOW]
            if len(self._signups) >= SIGNUP_LIMIT:
                raise ValueError('too many sign-ups right now; try again later')
            self._signups.append(now)
        username = normalize_username(username)
        if username in self.admins:
            raise ValueError('that username is reserved')
        if not isinstance(password, str) or len(password) < 10:
            raise ValueError('password must be at least 10 characters')
        with self.lock:
            if username in self._data['users']:
                raise ValueError('that username is taken')
            self._data['users'][username] = {**_hash_password(password), 'uid': secrets.token_hex(16)}
            self._save()
        return username, self.create_session(username)

    def verify(self, username, password):
        """Check credentials, with login lockout; the username on success."""
        username = username.lower() if isinstance(username, str) else ''
        now = time.time()
        with self.lock:
            attempts = [t for t in self._failures.get(username, []) if now - t < LOGIN_WINDOW]
            self._failures[username] = attempts
            if len(attempts) >= LOGIN_LIMIT:
                raise ValueError('too many attempts; try again later')
        record = self._data['users'].get(username)
        if record is None or not isinstance(password, str) or not _check_password(password, record):
            with self.lock:
                self._failures.setdefault(username, []).append(now)
            raise ValueError('wrong username or password')
        with self.lock:
            self._failures.pop(username, None)
        return username

    def login(self, username, password):
        """(username, session token) on success."""
        username = self.verify(username, password)
        return username, self.create_session(username)

    def create_session(self, username):
        token = secrets.token_hex(32)
        key = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            self._data['sessions'][key] = {'user': username, 'uid': self.uid(username),
                                           'expires': time.time() + SESSION_TTL}
            self._save()
        return token

    def user_for_token(self, token):
        if not token:
            return None
        key = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            session = self._data['sessions'].get(key)
            if not session:
                return None
            # A missing or changed uid means the account was deleted (and maybe
            # recreated under the same name) since this session was issued.
            if session['expires'] < time.time() or session.get('uid') != self.uid(session['user']):
                del self._data['sessions'][key]
                self._save()
                return None
            return session['user']

    def logout(self, token):
        if not token:
            return
        key = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            if self._data['sessions'].pop(key, None) is not None:
                self._save()
