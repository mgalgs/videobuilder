"""Identity: the session cookie, git Basic auth, API keys, and the one
resolver used for every `/v/<name>` route. See editor.py's module docstring
for the precedence (hook -> git Basic/key -> Bearer key or session cookie
-> library routes)."""
import base64
import re
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, unquote

from .editor import OPEN_ROUTES, HTTPError
from .pages import signin_page


def _key_in_scope(key, name):
    return not key['scope'] or name.startswith(key['scope'] + '/')


def _git_is_push(suffix, query):
    if suffix == '/git-receive-pack':
        return True
    return suffix == '/info/refs' and parse_qs(query).get('service') == ['git-receive-pack']


def _attributed(username, key):
    return f"{username} ({key['label']})" if key else username


class AuthHandler:
    def _identity(self, hook_identity):
        # With accounts on, the session is the only source of identity: the hook's
        # return value and the vb_name cookie are both ignored (see _handle).
        if self.library and self.library.accounts:
            return hook_identity
        if hook_identity is not None:
            return hook_identity
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            name = cookie.get('vb_name')
            return unquote(name.value) if name else None
        except Exception:
            return None

    def _session_user(self, accounts):
        return accounts.user_for_token(self._cookie('vb_session'))

    def _basic_auth_user(self, accounts):
        header = self.headers.get('Authorization', '')
        if not header.startswith('Basic '):
            return None
        try:
            decoded = base64.b64decode(header[6:]).decode('utf-8')
        except Exception:
            return None
        username, _, password = decoded.partition(':')
        if password.startswith('vbk_'):
            # The username is ignored for a key: it isn't needed to find or act as the account.
            self._key = accounts.key_for_secret(password)
            return self._key['username'] if self._key else None
        try:
            return accounts.verify(username, password)
        except ValueError:
            return None

    def _wants_html(self, route, method):
        """Whether an unauthenticated request should see the sign-in page rather
        than a JSON 401: a browser navigation (GET), not an API call."""
        if method != 'GET' or route.startswith('/api/'):
            return False
        if re.fullmatch(r'/capabilities/[a-z][a-z0-9-]*\.(mp4|jpg)', route):
            return False
        m = re.fullmatch(r'/v/(.+?)(/api(?:/.*)?|/tuning\.html|/director\.(?:js|css)|/)?', route)
        if m and m.group(2) and m.group(2).startswith('/api'):
            return False
        return True

    def resolve_identity(self, route, method, video_name, video_subroute, identity):
        """Resolves the user and the attributed identity for a library request
        (not a git one, handled earlier in `_handle`). Returns (user, identity),
        or None if a sign-in page was already sent and there is nothing further
        to do. With no accounts configured, returns (None, identity) unchanged:
        every other identity source (the hook, vb_name) still applies via
        `_identity`, called separately where a plain name is needed."""
        user = None
        if self.library and self.library.accounts:
            if route not in OPEN_ROUTES:
                auth = self.headers.get('Authorization', '')
                if auth.startswith('Bearer '):
                    # A bearer key is judged alone: no ambient cookie combines with it. A key
                    # reaches only /v/<name>/api/..., never its own access-management sub-route.
                    eligible = (video_name is not None and video_subroute and
                               video_subroute.startswith('/api/') and video_subroute != '/api/access')
                    self._key = self.library.accounts.key_for_secret(auth[7:].strip()) if eligible else None
                    if eligible and self._key is None:
                        raise HTTPError(401, 'invalid or revoked key')
                    if self._key and not _key_in_scope(self._key, video_name):
                        raise HTTPError(404, 'repository not found')
                    if self._key and self._key['mode'] == 'read' and method != 'GET':
                        raise HTTPError(403, 'this key is read-only')
                    user = self._key['username'] if self._key else None
                elif auth:
                    user = None  # some other credential a key route never accepts
                else:
                    user = self._session_user(self.library.accounts)
                if user is None:
                    if self._wants_html(route, method):
                        self._send(200, signin_page(), 'text/html; charset=utf-8')
                        return None
                    raise HTTPError(401, 'sign in required')
            identity = _attributed(user, self._key)
        return user, identity
