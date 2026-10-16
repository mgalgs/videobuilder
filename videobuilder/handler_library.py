"""Git dispatch, the `/v/<name>` access gate, and the top-level page/account/
video-creation routes. See editor.py's module docstring for route shapes and
the full check order."""
import json
import re
import sys
import traceback
from urllib.parse import parse_qs, quote, unquote, urlparse

from .capabilities import showcase_available
from .editor import HTTPError, _field, _need
from .handler_auth import _key_in_scope
from .library import serve_git, valid_name
from .pages import account_page, signin_page, signup_page
from .sources import CAPTION_MAX_BYTES, TooLarge as SourceTooLarge


class LibraryHandler:
    def _access(self, method, name, user):
        library = self.library
        if method == 'GET':
            record = library.access.get(name, library.accounts)
            can_share = library.access.can_share(name, user, library.accounts)
            return self._json(200, {'owner': record['owner'], 'collaborators': record['collaborators'],
                                    'can_share': can_share})
        body = self._body()
        if not library.access.can_share(name, user, library.accounts):
            raise HTTPError(403, 'only the owner can manage access')
        action = _field(body, 'action', str)
        target = _field(body, 'username', str).strip().lower()
        if action == 'invite':
            if not library.accounts.exists(target):
                raise HTTPError(404, 'no such user')
            library.access.invite(name, target, library.accounts)
        elif action == 'remove':
            library.access.remove(name, target)
        else:
            raise HTTPError(400, 'unknown action')
        record = library.access.get(name, library.accounts)
        return self._json(200, {'owner': record['owner'], 'collaborators': record['collaborators'],
                                'can_share': True})

    def _handle(self, method):
        library = self.library
        url = urlparse(self.path)
        q = {k: v[-1] for k, v in parse_qs(url.query).items()}
        self._key = None  # a key used for this request (git Basic or video-API Bearer), if any
        try:
            identity = self.hook(self)
            route = url.path
            if library and route.startswith('/git/'):
                resolved = self.resolve_identity(route, method, None, None, identity)
                if resolved is None:
                    return
                _, identity, _ = resolved
                # Git POSTs use its own content types; the JSON and Origin rule is for browser edits.
                if serve_git(self, library, method, identity):
                    return
                raise HTTPError(404, 'repository not found')
            # Resolved once, here, so the key gate below and the `/v/<name>` dispatch further
            # down (which reuses video_name/video_subroute) can never disagree about the name.
            video_name, video_subroute = None, None
            if library:
                video_match = re.fullmatch(r'/v/(.+?)(/api(?:/.*)?|/tuning\.html|/director\.(?:js|css)|/)?',
                                           route)
                if video_match and valid_name(video_match.group(1)):
                    video_name, video_subroute = video_match.group(1), video_match.group(2)
            resolved = self.resolve_identity(route, method, video_name, video_subroute, identity)
            if resolved is None:
                return
            user, identity, _ = resolved
            if route == '/api/name':
                if library and library.accounts:
                    if method == 'GET':
                        return self._json(200, {'name': user})
                    self._body()
                    raise HTTPError(409, 'your name comes from your login')
                if method == 'GET':
                    return self._json(200, {'name': identity})
                body = self._body()
                name = _field(body, 'name', str).strip()
                if not 1 <= len(name) <= 40 or any(ord(c) < 32 or ord(c) == 127 for c in name):
                    raise HTTPError(400, 'name must be 1–40 characters without control characters')
                return self._send(200, json.dumps({'name': name}).encode(), 'application/json',
                                  {'Set-Cookie': 'vb_name=' + quote(name, safe='') +
                                   '; Path=/; Max-Age=31536000; SameSite=Lax'})
            active = self.editor
            if library:
                if route in ('/', '/index.html') and method == 'GET':
                    scheme = self.headers.get('X-Forwarded-Proto', 'http').lower()
                    page = library.index(self.headers['Host'], scheme if scheme in ('http', 'https') else 'http',
                                         user)
                    return self._send(200, page, 'text/html; charset=utf-8')
                if library.accounts and route == '/login' and method == 'GET':
                    return self._send(200, signin_page(showcase=showcase_available(library.capabilities_dir)),
                                      'text/html; charset=utf-8')
                if library.accounts and route == '/signup' and method == 'GET':
                    return self._send(200, signup_page(showcase=showcase_available(library.capabilities_dir)),
                                      'text/html; charset=utf-8')
                if route == '/new' and method == 'GET':
                    names = [n for n in library.names()
                            if not library.accounts or library.access.can_access(n, user, library.accounts)]
                    return self._send(200, library.new_video_page(names, user), 'text/html; charset=utf-8')
                if library.accounts and route == '/api/login' and method == 'POST':
                    body = self._body()
                    try:
                        username, token = library.accounts.login(_field(body, 'username', str),
                                                                  _field(body, 'password', str))
                    except ValueError as exc:
                        raise HTTPError(401, str(exc)) from None
                    return self._send(200, json.dumps({'name': username}).encode(), 'application/json',
                                      {'Set-Cookie': self._session_cookie(token)})
                if library.accounts and route == '/api/signup' and method == 'POST':
                    body = self._body()
                    if _field(body, 'password', str) != _field(body, 'confirm', str):
                        raise HTTPError(400, 'passwords do not match')
                    try:
                        username, token = library.accounts.signup(_field(body, 'username', str),
                                                                  _field(body, 'password', str))
                    except ValueError as exc:
                        raise HTTPError(400, str(exc)) from None
                    return self._send(200, json.dumps({'name': username}).encode(), 'application/json',
                                      {'Set-Cookie': self._session_cookie(token)})
                if library.accounts and route == '/api/logout' and method == 'POST':
                    self._body()
                    library.accounts.logout(self._cookie('vb_session'))
                    return self._send(200, b'{}', 'application/json',
                                      {'Set-Cookie': 'vb_session=; Path=/; Max-Age=0; SameSite=Lax'})
                if library.accounts and route == '/account' and method == 'GET':
                    limits = library.admin_limits() if library.accounts.is_admin(user) else None
                    return self._send(200, account_page(user, library.accounts.list_keys(user), limits),
                                      'text/html; charset=utf-8')
                if library.accounts and route == '/api/account/keys' and method == 'POST':
                    body = self._body()
                    scope = body.get('scope')
                    if scope is not None and not isinstance(scope, str):
                        raise HTTPError(400, 'scope must be a string')
                    try:
                        record, secret = library.accounts.create_key(
                            user, _field(body, 'label', str), scope or None, _field(body, 'mode', str))
                    except ValueError as exc:
                        raise HTTPError(400, str(exc)) from None
                    return self._json(201, {**record, 'secret': secret})
                m = re.fullmatch(r'/api/account/keys/([^/]+)/revoke', route)
                if library.accounts and method == 'POST' and m:
                    self._body()
                    try:
                        library.accounts.revoke_key(user, unquote(m.group(1)))
                    except KeyError:
                        raise HTTPError(404, 'no such key') from None
                    return self._json(200, {'revoked': m.group(1)})
                if route == '/api/library/new' and method == 'POST':
                    if library.accounts and not library.accounts.is_admin(user):
                        raise HTTPError(403, 'only an admin may create a project')
                    body = self._body()
                    try:
                        result = library.copied(_field(body, 'from', str), _field(body, 'name', str))
                    except ValueError as exc:
                        raise HTTPError(400, str(exc)) from None
                    if library.accounts:
                        library.access.set_owner(result['name'], user, library.accounts)
                    return self._json(201, result)
                if route == '/api/videos/new' and method == 'POST':
                    # Reachable by any signed-in user (the generic session check above
                    # already refused an anonymous one when accounts are on), unlike the
                    # admin-only /api/library/new: this is the New Video page's own route.
                    # A write key may also reach it, to create a video inside its own scope.
                    body = self._body()
                    name = _field(body, 'name', str)
                    start = _field(body, 'start', str)
                    if start not in ('blank', 'copy'):
                        raise HTTPError(400, 'start must be "blank" or "copy"')
                    if self._key and not _key_in_scope(self._key, name):
                        raise HTTPError(403, f"this key can only create videos under {self._key['scope']}/")
                    try:
                        if start == 'copy':
                            source = _field(body, 'from', str)
                            # Out of the key's scope answers exactly like "not accessible to this
                            # account" below, so a key can't probe for other projects' existence.
                            if self._key and not _key_in_scope(self._key, source):
                                raise HTTPError(404, 'repository has no main branch')
                            if library.accounts and not library.access.can_access(source, user, library.accounts):
                                raise HTTPError(404, 'repository has no main branch')
                            result = {**library.copied(source, name), 'video': None}
                        else:
                            result = library.create_blank(name)
                    except ValueError as exc:
                        raise HTTPError(400, str(exc)) from None
                    if library.accounts:
                        library.access.set_owner(result['name'], user, library.accounts)
                    return self._json(201, result)
                if route == '/api/usage' and method == 'GET':
                    # Shared across the library like /api/name, not per-video: an
                    # account's spending isn't scoped to one project.
                    from .video_api import _is_admin
                    if not _is_admin(self, user):
                        raise HTTPError(403, 'admin only')
                    return self._json(200, library.usage())
                if route == '/api/admin/limits' and method == 'GET':
                    from .video_api import _is_admin
                    if not _is_admin(self, user):
                        raise HTTPError(403, 'admin only')
                    return self._json(200, library.admin_limits())
                if route == '/api/admin/limits' and method == 'POST':
                    from .video_api import _is_admin
                    if not _is_admin(self, user):
                        raise HTTPError(403, 'admin only')
                    body = self._body()
                    if not library.accounts:
                        raise HTTPError(400, 'no such account')
                    target = body.get('user')
                    if not isinstance(target, str):
                        raise HTTPError(400, 'user must be a string')
                    try:
                        limit = library.accounts.set_limit(target, body.get('kind'), body.get('notes'),
                                                            body.get('cost_usd'))
                    except ValueError as exc:
                        raise HTTPError(400, str(exc)) from None
                    return self._json(200, {'user': target.strip().lower(), 'limit': limit})
                if (route != '/healthz' and route != '/capabilities' and not route.startswith('/capabilities/')
                        and route != '/compendium' and not route.startswith('/compendium/')
                        and route != '/api/compendium' and route != '/api/compendium/vote'):
                    if video_name is None:
                        raise HTTPError(404, 'not found')
                    name = video_name
                    if video_subroute is None and method == 'GET':
                        # The page calls a relative api/, which needs the trailing slash.
                        self.send_response(301)
                        self.send_header('Location', route + '/')
                        self.send_header('Content-Length', '0')
                        return self.end_headers()
                    if library.accounts and not library.access.can_access(name, user, library.accounts):
                        raise HTTPError(404, 'repository has no main branch')
                    if video_subroute == '/api/thumbnail' and method == 'GET' and name not in library.editors:
                        # Every card's lazy <img> hits this: answer from disk, without
                        # opening (and so cloning, and spinning up the render-poll thread
                        # of) an Editor that isn't open already, for a video nobody may
                        # ever look at. Falls through to the normal path below only when
                        # that can't be answered unambiguously (library.thumbnails).
                        from .thumbnails import AMBIGUOUS, from_state_dir
                        flat = name.replace('/', '--')
                        data = from_state_dir(library.state_dir / flat, library.path(name))
                        if data is not AMBIGUOUS:
                            if data is None:
                                raise HTTPError(404, 'no render yet')
                            return self._send(200, data, 'image/jpeg')
                    try:
                        active = library.editor(name)
                    except ValueError as exc:
                        raise HTTPError(404, str(exc)) from None
                    route = video_subroute or '/'
                    if library.accounts and route == '/api/access':
                        return self._access(method, name, user)
            if method == 'GET':
                self._get(route, q, active, user)
            elif route == '/api/attachments':
                # Same-origin plus validated magic bytes and forced nosniff make raw uploads safe here;
                # a bearer key carries no ambient credential, so it skips the Origin check like _body().
                if not self._key:
                    self._same_origin()
                upload_name = _need(q, 'name')
                is_zip = upload_name.lower().endswith('.zip')
                limit = active.attachments.zip_max_bytes if is_zip else active.attachments.max_file
                n = int(self.headers.get('Content-Length') or 0)
                if n < 0 or n > limit:
                    raise HTTPError(413, ('zip upload exceeds the size limit' if is_zip else
                                          'attachment exceeds file size limit'))
                body_bytes = self.rfile.read(n)
                if is_zip:
                    self._json(201, active.attachments.upload_zip(_need(q, 'video'), upload_name, body_bytes))
                else:
                    record = active.attachments.upload(_need(q, 'video'), upload_name,
                                                       self.headers.get('Content-Type', ''), body_bytes)
                    self._json(201, record)
            elif route == '/api/sources':
                # Streamed straight to disk in bounded chunks (Sources.stream_upload): a source
                # can be hundreds of MB, so it must never sit in memory whole like the body above.
                if not self._key:
                    self._same_origin()
                n = self.headers.get('Content-Length')
                try:
                    record = active.sources.stream_upload(_need(q, 'video'), _need(q, 'filename'), q.get('name'),
                                                          self.headers.get('Content-Type', ''), self.rfile,
                                                          int(n) if n is not None else -1)
                except SourceTooLarge as exc:
                    raise HTTPError(413, str(exc)) from None
                self._json(201, record)
            elif re.fullmatch(r'/api/sources/[^/]+/caption', route):
                if not self._key:
                    self._same_origin()
                name = route.rsplit('/', 2)[1]
                n = int(self.headers.get('Content-Length') or 0)
                if n < 0 or n > CAPTION_MAX_BYTES:
                    raise HTTPError(413, 'caption file is too large')
                data = self.rfile.read(n)
                record = active.sources.add_caption(_need(q, 'video'), name, _need(q, 'filename'), data)
                self._json(201, record)
            else:
                self._post(route, self._body(), identity or 'anonymous', active, user)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (ValueError, KeyError) as e:
            self._json(400, {'error': str(e)})
        except HTTPError as e:
            self._json(e.code, {'error': str(e)})
        except Exception:
            # The traceback is for the operator's log, never the response: a guest must
            # not see internals, so the body stays as generic as a 500 gets.
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            if self._wants_html(url.path, method):
                self._send(500, b'<!doctype html><title>Error</title><p>Something went wrong.</p>',
                          'text/html; charset=utf-8')
            else:
                self._json(500, {'error': 'internal error'})

    def do_GET(self):
        self._handle('GET')

    def do_POST(self):
        self._handle('POST')
