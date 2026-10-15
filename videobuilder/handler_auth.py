"""Identity: the session cookie, git Basic auth, API keys and the hook/
vb_name fallback, all decided by the one resolver below, `resolve_identity`,
for every route including git. Its precedence: hook() runs first in
`LibraryHandler._handle` and can refuse the request outright (git included);
then, for a `/git/...` route, Basic auth with a password or a `vbk_` key;
then, for everything else, when the library has accounts and the route is
not in OPEN_ROUTES, a Bearer key or the session cookie (judged alone -- a
request carrying Authorization is never combined with a cookie; a key is
accepted only on `/v/<name>/api/...` other than `/api/access`, and any other
Authorization header leaves the request unauthenticated); when the library
has accounts and the route *is* in OPEN_ROUTES, there is no identity at all
(the hook value and vb_name cookie are ignored); otherwise (no accounts, or
no library) the hook's value, falling back to the vb_name cookie."""
import base64
import re
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, unquote, urlparse

from .editor import OPEN_ROUTES, HTTPError
from .library import git_route
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
        """The hook's value, falling back to the vb_name cookie. Used only by
        resolve_identity, for the no-accounts (or no-library) case: with
        accounts on, the session is the only source of identity, decided
        there instead -- and an OPEN_ROUTES request in that case gets no
        identity at all, rather than falling back here."""
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
        if re.fullmatch(r'/(?:capabilities|compendium)/[a-z][a-z0-9-]*\.(mp4|jpg)', route):
            return False
        m = re.fullmatch(r'/v/(.+?)(/api(?:/.*)?|/tuning\.html|/director\.(?:js|css)|/)?', route)
        if m and m.group(2) and m.group(2).startswith('/api'):
            return False
        return True

    def resolve_identity(self, route, method, video_name, video_subroute, hook_identity):
        """Resolves the user, the attributed identity, and the key (if any)
        for every request -- see the module docstring for the precedence.
        Returns (user, identity, key), or None if a response (a git 401/404,
        or a sign-in page) was already sent and there is nothing further to
        do."""
        if self.library and route.startswith('/git/'):
            library = self.library
            if not library.accounts:
                return None, hook_identity, None
            git_user = self._basic_auth_user(library.accounts)
            if git_user is None:
                self._send(401, b'', 'text/plain; charset=utf-8',
                          {'WWW-Authenticate': 'Basic realm="videobuilder"'})
                return None
            parsed = git_route(route)
            if parsed and not library.access.can_access(parsed[0], git_user, library.accounts):
                self._json(404, {'error': 'repository not found'})
                return None
            if self._key and parsed:
                if not _key_in_scope(self._key, parsed[0]):
                    self._json(404, {'error': 'repository not found'})
                    return None
                if self._key['mode'] == 'read' and _git_is_push(parsed[1], urlparse(self.path).query):
                    raise HTTPError(403, 'this key is read-only')
            return git_user, _attributed(git_user, self._key), self._key
        user = None
        identity = hook_identity
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
        else:
            identity = self._identity(hook_identity)
        return user, identity, self._key
