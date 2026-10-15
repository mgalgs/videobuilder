"""User accounts and sessions for library auth (off unless admins are given).

One JSON file under the library state dir holds everyone: usernames, scrypt
password hashes (never plaintext, except the admin password files the
operator supplies), sessions keyed by the session token's SHA-256, and API
keys keyed by the key secret's SHA-256, so the file never holds a usable
token or key. Login lockout and sign-up throttling are in memory and reset
on restart.

Each account also gets a random `uid` at creation, stable across restarts,
that never gets reused even if the username is. Sessions, access grants and
keys record the uid they were issued to, not just the username, so deleting
a user's record (by hand, with the editor stopped) invalidates their
outstanding sessions and keys, and a later sign-up under the same name
starts with no borrowed access. The file is only read at startup: editing it
while the editor is running will be overwritten by its next write.

A key acts as the account it belongs to, narrowed by its own scope
(a project namespace, or none for every project the account can reach) and
mode (`read` or `write`). The secret is high-entropy (`vbk_` plus at least
32 random bytes), so a plain SHA-256 and direct lookup are enough: no
per-key lockout. `last_used` is updated in memory on every use but flushed
to disk at most once an hour per key, to keep that from being a write on
every request.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time

from .atomic import write_json_atomic

USERNAME = re.compile(r'[a-z0-9._-]{3,32}\Z')
# Same shape as a project namespace (videobuilder.library.PART); duplicated here rather
# than imported, since library.py imports this module.
SCOPE = re.compile(r'[a-z0-9][a-z0-9._-]{0,62}\Z')

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
SESSION_TTL = 30 * 24 * 3600
LOGIN_WINDOW = 15 * 60
LOGIN_LIMIT = 5
SIGNUP_WINDOW = 60 * 60
SIGNUP_LIMIT = 20

KEY_PREFIX = 'vbk_'
KEY_MODES = ('read', 'write')
KEY_LABEL_MAX = 40
KEY_LAST_USED_FLUSH = 3600  # flush a key's last_used to disk at most this often

LIMIT_KINDS = ('default', 'custom', 'unlimited')
DEFAULT_LIMIT = {'kind': 'default', 'notes': None, 'cost_usd': None}


def _validated_limit_value(value, name, kind):
    """`value` if it is null or a positive `kind` (int, or (int, float) for a
    dollar amount); raises ValueError otherwise."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, kind) or value <= 0:
        article = 'a positive integer' if kind is int else 'a positive number'
        raise ValueError(f'{name} must be null or {article}')
    return value


def valid_label(label):
    return (isinstance(label, str) and 1 <= len(label) <= KEY_LABEL_MAX and
            not any(ord(c) < 32 or ord(c) == 127 or c in '()' for c in label))


def valid_scope(scope):
    return isinstance(scope, str) and bool(SCOPE.fullmatch(scope)) and '..' not in scope and not scope.endswith('.git')


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
        self._key_flushed = {}
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
            return {'users': {}, 'sessions': {}, 'keys': {}}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        write_json_atomic(self.path, self._data)

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

    def get_limit(self, username):
        """`username`'s own daily-cap override ({kind, notes, cost_usd}), or
        None for an unknown or deleted account. An existing account with no
        override of its own gets DEFAULT_LIMIT (kind "default"): the
        library-wide caps apply to it."""
        username = username.lower() if isinstance(username, str) else ''
        if not self.exists(username):
            return None
        return self._data.get('limits', {}).get(username, DEFAULT_LIMIT)

    def set_limit(self, username, kind, notes=None, cost_usd=None):
        """Set or clear `username`'s override; returns the resulting limit
        (see get_limit). `kind` is "default" (clears any override), "custom"
        (notes/cost_usd each cap that one thing, or None for no cap on it) or
        "unlimited" (no cap at all, notes/cost_usd must be left unset)."""
        username = username.lower() if isinstance(username, str) else ''
        if not self.exists(username):
            raise ValueError('no such account')
        if kind not in LIMIT_KINDS:
            raise ValueError('kind must be "default", "custom" or "unlimited"')
        if kind == 'custom':
            notes = _validated_limit_value(notes, 'notes', int)
            cost_usd = _validated_limit_value(cost_usd, 'cost_usd', (int, float))
        elif notes is not None or cost_usd is not None:
            raise ValueError('notes and cost_usd are only valid with kind "custom"')
        with self.lock:
            if kind == 'default':
                self._data.setdefault('limits', {}).pop(username, None)
            else:
                self._data.setdefault('limits', {})[username] = {'kind': kind, 'notes': notes, 'cost_usd': cost_usd}
            self._save()
        return self.get_limit(username)

    def list_accounts(self):
        """Every account -- name, whether it's an admin, and its limit (see
        get_limit) -- sorted by name, for the admin-only limits API."""
        with self.lock:
            names = sorted(self._data['users'])
            limits = self._data.get('limits', {})
            return [{'name': name, 'admin': name in self.admins, 'limit': limits.get(name, DEFAULT_LIMIT)}
                    for name in names]

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

    def _public_key(self, record):
        return {k: record[k] for k in ('id', 'label', 'scope', 'mode', 'created', 'last_used')}

    def create_key(self, username, label, scope, mode):
        """Create a key acting as `username`; (public record, secret). The secret is
        returned only here: the stored record never holds it, only its hash."""
        username = username.lower() if isinstance(username, str) else username
        if not self.exists(username):
            raise ValueError('no such account')
        if not valid_label(label):
            raise ValueError(f'label must be 1-{KEY_LABEL_MAX} characters, with no control characters or parentheses')
        if scope is not None and not valid_scope(scope):
            raise ValueError('scope must look like a project namespace')
        if mode not in KEY_MODES:
            raise ValueError('mode must be "read" or "write"')
        secret = KEY_PREFIX + secrets.token_urlsafe(32)
        digest = hashlib.sha256(secret.encode()).hexdigest()
        with self.lock:
            record = {'id': secrets.token_hex(6), 'username': username, 'uid': self.uid(username),
                      'label': label, 'scope': scope, 'mode': mode, 'created': time.time(), 'last_used': None}
            self._data.setdefault('keys', {})[digest] = record
            self._save()
        return self._public_key(record), secret

    def list_keys(self, username):
        """The account's keys (no secrets), oldest first."""
        username = username.lower() if isinstance(username, str) else ''
        uid = self.uid(username)
        with self.lock:
            records = [r for r in self._data.get('keys', {}).values()
                      if r['username'] == username and r['uid'] == uid]
        return [self._public_key(r) for r in sorted(records, key=lambda r: r['created'])]

    def revoke_key(self, username, key_id):
        """Delete one of the account's keys by its id; raises KeyError if there is none."""
        username = username.lower() if isinstance(username, str) else ''
        uid = self.uid(username)
        with self.lock:
            for digest, record in self._data.get('keys', {}).items():
                if record['id'] == key_id and record['username'] == username and record['uid'] == uid:
                    del self._data['keys'][digest]
                    self._save()
                    return
        raise KeyError(key_id)

    def key_for_secret(self, secret):
        """The record for a live key matching `secret` (its public fields plus the
        `username` it acts as), or None: a bad secret, a revoked key, or a key whose
        account was deleted (and maybe recreated) since."""
        if not isinstance(secret, str) or not secret.startswith(KEY_PREFIX):
            return None
        digest = hashlib.sha256(secret.encode()).hexdigest()
        with self.lock:
            record = self._data.get('keys', {}).get(digest)
            if not record or record['uid'] != self.uid(record['username']):
                return None
            record['last_used'] = now = time.time()
            if now - self._key_flushed.get(digest, 0) >= KEY_LAST_USED_FLUSH:
                self._key_flushed[digest] = now
                self._save()
            return {**self._public_key(record), 'username': record['username']}
