"""HTTP editor and director-mode API (stdlib only).

Single-project routes are `/api/...`; library routes are `/v/<name>/api/...`,
except `/api/name`, which is shared across the library. `video` is the id from
`/api/project`. JSON is used for requests and responses except where noted.

GET  /api/project                    project, backend and available videos
GET  /api/info?video=V               timeline, formats, edits and git state
GET  /api/frame?video=V&frame=N&format=F&scale=S&overlay=1  PNG frame
POST /api/roll {video,segment,until}  commit a cut edit
POST /api/copy {video,segment,key,value}  commit a copy edit
POST /api/undo {video}                commit the inverse edit
GET  /api/name                       {name: string|null}
POST /api/name {name}                 200 {name}, Set-Cookie vb_name (Path=/,
                                     one year, SameSite=Lax); 400 invalid name
GET  /api/notes[?video=V]            {notes:[...]}, oldest first; advances runs
POST /api/notes {video,text,format?,time?,attachments?:[id...]}
                                     200 note; `time` is seconds, optional.
                                     Legacy `frame` also works. Without either,
                                     frame/time are null and there is no PNG.
GET  /api/notes/<id>                 note, including time, attachments,
                                     state and, if landed, version {n,commit}
GET  /api/notes/<id>.png             pinned frame or 404
POST /api/notes/<id>/delete          {deleted:id}; active runs cannot be deleted
POST /api/attachments?video=V&name=F  raw body with Content-Type; 201
                                     {id,name,type,size}; 400 bad type/magic,
                                     413 over file limit
GET  /api/attachments/<id>          stored bytes, nosniff, CSP sandbox;
                                     image/video/audio inline, others download
GET  /api/versions?video=V[&limit=50&before=SHA]
                                     {versions:[{n,commit,summary,kind,
                                     author,directed_by,note,restores,time,
                                     renders:{format:state}}]}; newest first.
                                     `before` is exclusive; 400 invalid cursor.
POST /api/versions/restore {video,commit}
                                     200 {commit,changed,n}; 400 foreign sha.
GET  /api/video?video=V&commit=SHA&format=F
                                     commit defaults to main, format to first.
                                     200 MP4 when ready; 206 for one byte Range,
                                     ETag "<sha>-<format>", Accept-Ranges bytes;
                                     416 unsatisfiable; 202 {state,position}
                                     while queued/rendering; 500 {error,log}.
GET  /api/draft?video=V              manual draft detail or null
GET  /api/draft/info?video=V         isolated draft info
GET  /api/draft/frame?video=V&...    isolated draft PNG
POST /api/draft/accept {video}       manual accept (auto_land=false)
POST /api/draft/drop {video}         manual drop

An edit returns {message,commit,warning,changed,undo}. Notes include `id`,
`video`, `text`, `format`, `frame`, `segment`, `time`, `attachments`, `author`,
`state`, `reply`, `branch`, and queue metadata. States are queued, working,
replied, failed, landed, refused, conflict, accepted, dropped. The identity is
the request_hook value, then vb_name cookie, then anonymous. Errors otherwise
return {error}. POSTs require same-origin; all but attachment upload use JSON.

[editor] config: auto_land=true, render_jobs=min(4,cpu_count), render_keep=20,
attachment_max_file=25, attachment_max_files=10, attachment_max_message=100
(the size values are MiB). Film code and MP4 rendering run in bwrap with no
network; the checkout is read-only. Fork-sandbox attachment copies are mounted
read-only at /attachments for only the relevant submission.
"""
import json
import math
from http.cookies import SimpleCookie
from urllib.parse import quote
import os
import re
import sys
import time
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, unquote, urlparse

from . import edits
from .notes import NoteStore
from .agents import backend_from_config
from .drafts import Drafts, git
from .versions import Versions
from .renders import Renders
from .attachments import Attachments
from .workers import Environments, Pool
from .project import Project, read_config
from .sync import ForgeSync

STATE_DIR = '.vb-editor'
NOTE_SCALE = 0.5  # the size of a note's saved frame
MAX_BODY = 1 << 20


class HTTPError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Forbidden(HTTPError):
    """Raise from a request hook to turn a request away."""

    def __init__(self, message='forbidden'):
        super().__init__(403, message)


def request_hook(request):
    """Called before every request with the handler (`request.headers`,
    `request.command`, `request.path`, `request.client_address`). Returns the
    reviewer's identity (a string, or None), which is stored as a note's
    author; raises `Forbidden` to refuse the request. This default lets
    everyone in anonymously. Behind a reverse proxy that authenticates, check
    its identity header here, for instance:

        def proxy_identity(request):
            user = request.headers.get('X-Forwarded-User')
            if not user:
                raise Forbidden('no identity from the proxy')
            return user
    """
    return None


class Editor:
    """The project being edited: its videos, a preview Session per open video,
    and the notes. One lock covers every film load and draw."""

    def __init__(self, root, state_dir=None, backend=None, poll=0.25, agent=None, allowed_hosts=(), host='127.0.0.1',
                 unsandboxed_previews=False, envs=None, env_builder=None, sync_remote=None, environments=None, auto_land=None):
        self.root = os.path.abspath(root)
        cfg = read_config(self.root)
        state = state_dir or cfg.get('state_dir') or STATE_DIR
        self.state_dir = os.path.abspath(os.path.join(self.root, state))
        self.lock = threading.RLock()
        remote = sync_remote if sync_remote is not None else cfg.get("sync_remote")
        self.sync = ForgeSync(self.root, remote) if remote else None
        self.sync_error = None
        self.unsandboxed_previews = bool(unsandboxed_previews or cfg.get('unsandboxed_previews', False))
        self.envs = environments or Environments(self.state_dir, envs or cfg.get('envs', 'pinned'), env_builder)
        self.pool = Pool(self.envs, self.unsandboxed_previews)
        self.project = Project(self.root, skip=[self.state_dir], lock=self.lock, worker=self.session)
        self.drafts = Drafts(self)
        self.auto_land = bool(cfg.get('auto_land', True) if auto_land is None else auto_land)
        self.versions = Versions(self)
        agent_cfg = {**cfg.get('agent', {}), **(agent or {})}
        self.notes = NoteStore(os.path.join(self.state_dir, 'notes'),
                               backend or backend_from_config(agent_cfg), context=self.drafts.context,
                               before_submit=self._before_submit, on_reply=self._on_reply)
        self.attachments = Attachments(self, _positive(cfg, 'attachment_max_file', 25) * 1048576,
                                       _positive(cfg, 'attachment_max_files', 10),
                                       _positive(cfg, 'attachment_max_message', 100) * 1048576)
        self.notes.attachments = self.attachments
        self.renders = Renders(self, _positive(cfg, 'render_jobs', min(4, os.cpu_count() or 1)),
                               _positive(cfg, 'render_keep', 20))
        self.allowed_hosts = {h.lower().rstrip('.') for h in
                              ['localhost', '127.0.0.1', '::1', host, *cfg.get('allowed_hosts', []), *allowed_hosts]}
        self.poll = poll
        try:
            self._seen_main = git(self.root, 'rev-parse', '--verify', 'refs/heads/main') if self.project.git else None
        except ValueError:
            self._seen_main = None
        self.drafts.prune()
        _ensure_state_dir(self.state_dir)

    def _before_submit(self, video, note, state):
        self.drafts.before_submit(video, note, state)
        rejection = state.pop('rejection', None)
        if rejection:
            note['rejection'] = rejection
            self.notes.save_session(video, state)

    def _on_reply(self, video, note):
        if self.auto_land and note.get('branch'):
            try:
                self.drafts.accept(video, note.get('author'), note)
            except ValueError as exc:
                note.update(state='conflict', message=str(exc))
                self.notes._save(note)

    def main_moved(self):
        if not self.project.git:
            return
        try:
            sha = git(self.root, 'rev-parse', '--verify', 'refs/heads/main')
        except ValueError:
            return
        if sha != self._seen_main:
            self._seen_main = sha
            for video in self.project.videos():
                self.render_first(video.id, sha)

    def render_first(self, video, commit):
        try:
            fmt = self.session(video).request('info')['formats'][0]['name']
            self.renders.request(video, commit, fmt)
            self._seen_main = commit
        except (ValueError, KeyError, IndexError):
            pass

    def session(self, vid):
        with self.lock:
            try:
                video = self.project.video(vid)
            except KeyError:
                raise HTTPError(404, f'no video {vid!r} in this project') from None
            self.pool.unsandboxed = self.unsandboxed_previews
            return self.pool.get(vid, self.root, video.path, self.root)

    def refresh(self, force=False):
        """Fetch from the forge if due; a failure is reported, never raised, so an
        unreachable forge degrades to a stale view rather than a broken page."""
        if not self.sync:
            return
        try:
            with self.lock:
                self.sync.refresh(force=force)
            self.sync_error = None
            self.main_moved()
        except ValueError as exc:
            self.sync_error = str(exc)
            print(f'[editor] forge sync: {exc}', file=sys.stderr, flush=True)

    def project_info(self):
        self.refresh(force=True)
        self.main_moved()
        try:
            videos = [{**v.to_json(self.root), **self.envs.describe(v.path, self.root)}
                      for v in self.project.videos()]
            error = None
        except ValueError as e:
            videos, error = [], str(e)
        return {'name': os.path.basename(self.root), 'root': self.root, 'git': self.project.git is not None,
                'backend': self.notes.backend.name, 'state_dir': self.state_dir, 'videos': videos, 'error': error,
                'sync_error': self.sync_error}

    def info(self, vid):
        self.refresh()
        self.main_moved()
        s = self.session(vid)
        out = s.request('info')
        out.update(video=vid, edits_file=os.path.relpath(edits.path_for(s.film), self.root),
                   git=self.project.git_info(vid), undo=self.project.last.get(vid))
        return out

    def edit(self, vid, op, body, author=None):
        with self.lock:
            if self.sync:
                self.sync.before_commit()
            s = self.session(vid)
            try:
                if op == 'undo':
                    result = self.project.undo(vid, director=author)
                elif op == 'roll':
                    result = self.project.edit(vid, 'roll', _field(body, 'segment', str),
                                               _field(body, 'until', (int, float)), director=author)
                else:
                    result = self.project.edit(vid, 'copy', _field(body, 'segment', str), _field(body, 'value', str),
                                               key=_field(body, 'key', str), director=author)
            except ValueError as e:
                raise HTTPError(400, _short(str(e), s.film)) from None
            if self.sync and result["commit"]:
                self.sync.after_commit()
            if result['commit']:
                self.render_first(vid, result['commit'])
        if result['warning']:
            print(f'[editor] {result["warning"]}', file=sys.stderr, flush=True)
        return result

    def add_note(self, body, author):
        vid = _field(body, 'video', str)
        s = self.session(vid)
        timestamp = body.get('time')
        if timestamp is not None and (isinstance(timestamp, bool) or not isinstance(timestamp, (int, float))
                                      or not math.isfinite(timestamp) or timestamp < 0):
            raise HTTPError(400, 'time must be a nonnegative number of seconds')
        frame = body.get('frame')
        if frame is not None and (isinstance(frame, bool) or not isinstance(frame, int)):
            raise HTTPError(400, 'frame must be an integer')
        fmt = body.get('format') or None
        try:
            attachments = self.attachments.validate(vid, body.get('attachments', []))
        except (ValueError, KeyError) as exc:
            raise HTTPError(400, str(exc)) from None
        with self.lock:
            info = s.request('info')
            if 'frames' not in info:
                raise HTTPError(409, 'the video does not load; fix it before pinning notes')
            formats = [x['name'] for x in info['formats']]
            fmt = fmt or formats[0]
            if fmt not in formats:
                raise HTTPError(400, f'unknown format {fmt!r}')
            if timestamp is not None:
                frame = round(timestamp * info['fps'])
            if frame is not None:
                frame = max(0, min(info['frames'] - 1, frame))
                timestamp = frame / info['fps']
            tl = info.get('timeline')
            segment = next((x['name'] for x in tl['segments'] if x['start'] <= frame < x['end']), None) if tl and frame is not None else None
            png = s.request('frame', frame=frame, format=fmt, scale=NOTE_SCALE) if frame is not None else None
        try:
            return self.notes.add(vid, fmt, frame, segment, body.get('text'), png, author=author,
                                  time=timestamp, attachments=attachments,
                                  beat=frame / tl['frames_per_beat'] if tl and frame is not None else None)
        except ValueError as e:
            raise HTTPError(400, str(e)) from None


def _positive(cfg, name, default):
    value = cfg.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f'editor.{name} must be a positive integer')
    return value


def _ensure_state_dir(path):
    os.makedirs(path, exist_ok=True)
    ignore = os.path.join(path, '.gitignore')
    if not os.path.exists(ignore):
        with open(ignore, 'w') as fh:
            fh.write('# videobuilder editor state: not for git\n*\n')


def _field(body, name, kind):
    if body.get(name) is None and kind is not str:
        raise HTTPError(400, f'missing {name}')
    v = body.get(name)
    if isinstance(v, bool) or not isinstance(v, kind):
        raise HTTPError(400, f'{name} must be {"a string" if kind is str else "a number"}')
    return v


def _short(message, film_path):
    """An edit refusal without the edits file's absolute path in front."""
    return message.removeprefix(edits.path_for(film_path) + ': ').removeprefix(film_path + ': ')


def _page():
    return resources.files(__package__).joinpath('editor.html').read_bytes()


def make_handler(editor, hook=request_hook):
    from .library import Library, git_route, serve_git, valid_name
    library = editor if isinstance(editor, Library) else None
    class Handler(BaseHTTPRequestHandler):
        def parse_request(self):
            if not super().parse_request():
                return False
            try:
                hosts = self.headers.get_all('Host', [])
                try:
                    parsed = urlparse('//' + (hosts[0] if len(hosts) == 1 else ''))
                    hostname = parsed.hostname
                    valid = parsed.port is None or 0 < parsed.port < 65536
                except ValueError:
                    hostname, valid = None, False
                if self.path.split('?', 1)[0] == '/healthz':
                    return True
                if not valid or not hostname or parsed.username or parsed.password or parsed.path or hostname.lower().rstrip('.') not in editor.allowed_hosts:
                    raise Forbidden('Host is not allowed; configure --allow-host for this name')
            except Forbidden as e:
                self._json(e.code, {'error': str(e)})
                return False
            return True

        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype, headers=None):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj).encode(), 'application/json')

        def _same_origin(self):
            origin = self.headers.get('Origin')
            if origin and urlparse(origin).netloc != self.headers.get('Host'):
                raise HTTPError(403, 'cross-origin request refused')

        def _identity(self, hook_identity):
            if hook_identity is not None:
                return hook_identity
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
                name = cookie.get('vb_name')
                return unquote(name.value) if name else None
            except Exception:
                return None

        def _body(self):
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise HTTPError(415, 'send JSON (Content-Type: application/json)')
            self._same_origin()
            n = int(self.headers.get('Content-Length') or 0)
            if n > MAX_BODY:
                raise HTTPError(413, 'request too large')
            try:
                body = json.loads(self.rfile.read(n) or b'{}')
            except ValueError:
                raise HTTPError(400, 'the body is not JSON') from None
            if not isinstance(body, dict):
                raise HTTPError(400, 'the body must be a JSON object')
            return body

        def _handle(self, method):
            url = urlparse(self.path)
            q = {k: v[-1] for k, v in parse_qs(url.query).items()}
            try:
                identity = hook(self)
                route = url.path
                if route == '/api/name':
                    if method == 'GET':
                        return self._json(200, {'name': self._identity(identity)})
                    body = self._body()
                    name = _field(body, 'name', str).strip()
                    if not 1 <= len(name) <= 40 or any(ord(c) < 32 or ord(c) == 127 for c in name):
                        raise HTTPError(400, 'name must be 1–40 characters without control characters')
                    return self._send(200, json.dumps({'name': name}).encode(), 'application/json',
                                      {'Set-Cookie': 'vb_name=' + quote(name, safe='') +
                                       '; Path=/; Max-Age=31536000; SameSite=Lax'})
                active = editor
                if library:
                    if route.startswith('/git/'):
                        # Git POSTs use its own content types; the JSON and Origin rule is for browser edits.
                        if serve_git(self, library, method, identity):
                            return
                        raise HTTPError(404, 'repository not found')
                    if route in ('/', '/index.html') and method == 'GET':
                        scheme = self.headers.get('X-Forwarded-Proto', 'http').lower()
                        page = library.index(self.headers['Host'], scheme if scheme in ('http', 'https') else 'http')
                        return self._send(200, page, 'text/html; charset=utf-8')
                    if route == '/api/library/new' and method == 'POST':
                        body = self._body()
                        try:
                            return self._json(201, library.copied(_field(body, 'from', str),
                                                                   _field(body, 'name', str)))
                        except ValueError as exc:
                            raise HTTPError(400, str(exc)) from None
                    if route != '/healthz':
                        match = re.fullmatch(r'/v/(.+?)(/api(?:/.*)?|/)?', route)
                        if not match or not valid_name(match.group(1)):
                            raise HTTPError(404, 'not found')
                        if match.group(2) is None and method == 'GET':
                            # The page calls a relative api/, which needs the trailing slash.
                            self.send_response(301)
                            self.send_header('Location', route + '/')
                            self.send_header('Content-Length', '0')
                            return self.end_headers()
                        try:
                            active = library.editor(match.group(1))
                        except ValueError as exc:
                            raise HTTPError(404, str(exc)) from None
                        route = match.group(2) or '/'
                if method == 'GET':
                    self._get(route, q, active)
                elif route == '/api/attachments':
                    # Same-origin plus validated magic bytes and forced nosniff make raw uploads safe here.
                    self._same_origin()
                    n = int(self.headers.get('Content-Length') or 0)
                    if n < 0 or n > active.attachments.max_file:
                        raise HTTPError(413, 'attachment exceeds file size limit')
                    record = active.attachments.upload(_need(q, 'video'), _need(q, 'name'),
                                                       self.headers.get('Content-Type', ''), self.rfile.read(n))
                    self._json(201, record)
                else:
                    self._post(route, self._body(), self._identity(identity) or 'anonymous', active)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except (ValueError, KeyError) as e:
                self._json(400, {'error': str(e)})
            except HTTPError as e:
                self._json(e.code, {'error': str(e)})
            except Exception:
                self._json(500, {'error': traceback.format_exc()})

        def do_GET(self):
            self._handle('GET')

        def do_POST(self):
            self._handle('POST')

        def _get(self, route, q, editor):
            if route == '/healthz':
                from . import __version__
                return self._send(200, ('ok ' + __version__).encode(), 'text/plain; charset=utf-8')
            if route in ('/', '/index.html'):
                return self._send(200, _page(), 'text/html; charset=utf-8')
            if route == '/api/versions':
                editor.main_moved()
                try:
                    return self._json(200, editor.versions.history(_need(q, 'video'), int(q.get('limit', 50)), q.get('before')))
                except ValueError as exc:
                    raise HTTPError(400, str(exc)) from None
            if route == '/api/video':
                editor.main_moved()
                video = _need(q, 'video')
                editor.project.video(video)
                sha = q.get('commit') or git(editor.root, 'rev-parse', 'main')
                if sha not in git(editor.root, 'rev-list', '--first-parent', 'main').splitlines():
                    raise HTTPError(400, 'commit is not on main')
                formats = [f['name'] for f in editor.info(video)['formats']]
                fmt = q.get('format') or formats[0]
                if fmt not in formats:
                    raise HTTPError(400, 'unknown format')
                state = editor.renders.request(video, sha, fmt)
                if state['state'] == 'failed':
                    return self._json(500, {'error': state['error'], 'log': state['log']})
                if state['state'] != 'ready':
                    return self._json(202, {'state': state['state'], 'position': state['position']})
                data = editor.renders.path(video, sha, fmt).read_bytes()
                headers = {'Accept-Ranges': 'bytes', 'ETag': f'"{sha}-{fmt}"'}
                rang = self.headers.get('Range')
                if rang:
                    m = re.fullmatch(r'bytes=(\d*)-(\d*)', rang)
                    if not m or (not m[1] and not m[2]):
                        return self._send(416, b'', 'video/mp4', {**headers, 'Content-Range': f'bytes */{len(data)}'})
                    if m[1]:
                        start = int(m[1]); end = int(m[2]) if m[2] else len(data) - 1
                    else:
                        count = int(m[2]); start = max(0, len(data) - count); end = len(data) - 1
                    if start >= len(data) or end < start or (not m[1] and not count):
                        return self._send(416, b'', 'video/mp4', {**headers, 'Content-Range': f'bytes */{len(data)}'})
                    end = min(end, len(data) - 1)
                    headers['Content-Range'] = f'bytes {start}-{end}/{len(data)}'
                    return self._send(206, data[start:end+1], 'video/mp4', headers)
                return self._send(200, data, 'video/mp4', headers)
            m = re.fullmatch(r'/api/attachments/([0-9a-f]+)', route)
            if m:
                try:
                    meta, path = editor.attachments.get(m[1])
                except KeyError:
                    raise HTTPError(404, 'attachment not found') from None
                inline = meta['type'].startswith(('image/', 'video/', 'audio/'))
                return self._send(200, path.read_bytes(), meta['type'],
                                  {'Content-Security-Policy': 'sandbox',
                                   'Content-Disposition': ('inline' if inline else 'attachment') +
                                   '; filename="' + meta['name'] + '"'})
            if route == '/api/draft':
                return self._json(200, editor.drafts.details(_need(q, 'video')))
            if route in ('/api/draft/info', '/api/draft/frame'):
                op = route.rsplit('/', 1)[1]
                data = editor.drafts.preview(_need(q, 'video'), op, q)
                return self._send(200, data, 'application/json' if op == 'info' else 'image/png')
            if route == '/api/project':
                return self._json(200, editor.project_info())
            if route == '/api/info':
                return self._json(200, editor.info(_need(q, 'video')))
            if route == '/api/frame':
                s = editor.session(_need(q, 'video'))
                try:
                    png = s.request('frame', frame=int(q.get('frame', 0)), format=q.get('format') or None,
                                    scale=float(q.get('scale', 0.5)), overlay=q.get('overlay') in ('1', 'true'))
                except ValueError as e:
                    raise HTTPError(400, str(e)) from None
                return self._send(200, png, 'image/png')
            if route == '/api/notes':
                return self._json(200, {'notes': editor.notes.list(q.get('video'))})
            m = re.fullmatch(r'/api/notes/([^/]+?)(\.png)?', route)
            if m:
                nid = unquote(m.group(1))
                try:
                    if m.group(2):
                        return self._send(200, editor.notes.image(nid), 'image/png')
                    return self._json(200, editor.notes.current(nid))
                except KeyError:
                    raise HTTPError(404, f'no note {nid!r}') from None
            raise HTTPError(404, 'not found')

        def _post(self, route, body, identity, editor):
            if route == '/api/versions/restore':
                try:
                    return self._json(200, editor.versions.restore(_field(body, 'video', str),
                                                                    _field(body, 'commit', str), identity))
                except ValueError as exc:
                    raise HTTPError(400, str(exc)) from None
            if route in ('/api/draft/accept', '/api/draft/drop'):
                action = getattr(editor.drafts, route.rsplit('/', 1)[1])
                return self._json(200, action(_field(body, 'video', str), identity))
            if route in ('/api/roll', '/api/copy', '/api/undo'):
                return self._json(200, editor.edit(_field(body, 'video', str), route[5:], body, identity))
            if route == '/api/notes':
                return self._json(200, editor.add_note(body, identity))
            m = re.fullmatch(r'/api/notes/([^/]+)/delete', route)
            if m:
                try:
                    editor.notes.delete(unquote(m.group(1)))
                except KeyError:
                    raise HTTPError(404, f'no note {m.group(1)!r}') from None
                return self._json(200, {'deleted': m.group(1)})
            raise HTTPError(404, 'not found')

    return Handler


def _need(q, name):
    if not q.get(name):
        raise HTTPError(400, f'missing {name}')
    return q[name]


NOTE_TICK = 5


def _ticker(tick, stop):
    """Run the agent loop with no page open: a director may send a note and close the tab."""
    def loop():
        while not stop.wait(NOTE_TICK):
            try:
                tick()
            except Exception as e:
                print(f'[editor] note poll failed: {e}', file=sys.stderr, flush=True)
    threading.Thread(target=loop, daemon=True).start()


def serve(root, host='127.0.0.1', port=8100, state_dir=None, open_browser=False, backend=None,
          hook=request_hook, agent=None, allowed_hosts=(), unsandboxed_previews=False, envs=None, sync_remote=None):
    editor = Editor(root, state_dir=state_dir, backend=backend, agent=agent, allowed_hosts=allowed_hosts, host=host,
                    unsandboxed_previews=unsandboxed_previews, envs=envs, sync_remote=sync_remote)
    httpd = ThreadingHTTPServer((host, port), make_handler(editor, hook))
    httpd.daemon_threads = True
    stop_sync = threading.Event()
    _ticker(editor.notes.tick, stop_sync)
    if editor.sync:
        def periodic_sync():
            while not stop_sync.wait(editor.sync.interval):
                editor.refresh()
        threading.Thread(target=periodic_sync, daemon=True).start()
    url = f'http://{host}:{httpd.server_address[1]}/'
    videos = editor.project_info()['videos']
    print(f'[editor] {editor.root}: {len(videos)} video(s) at {url} (Ctrl-C to stop)', file=sys.stderr, flush=True)
    if host not in ('127.0.0.1', 'localhost', '::1'):
        print('[editor] warning: listening beyond this machine. The editor runs the films\' code and has no '
              'login; use it only on a trusted network.', file=sys.stderr, flush=True)
    if editor.project.git is None:
        print('[editor] warning: not a git repository; edits will be saved but not committed',
              file=sys.stderr, flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_sync.set()
        httpd.server_close()
        editor.renders.close()
        editor.pool.close()


def serve_library(root, host='127.0.0.1', port=8100, checkouts=None, state_dir=None, open_browser=False,
                  hook=request_hook, agent=None, allowed_hosts=(), unsandboxed_previews=False, envs=None):
    from .library import Library
    library = Library(root, checkouts=checkouts, state_dir=state_dir, host=host, agent=agent,
                      allowed_hosts=allowed_hosts, unsandboxed_previews=unsandboxed_previews, envs=envs)
    httpd = ThreadingHTTPServer((host, port), make_handler(library, hook))
    httpd.daemon_threads = True
    stop = threading.Event()
    _ticker(library.tick, stop)
    url = f'http://{host}:{httpd.server_address[1]}/'
    print(f'[editor] library {library.root} at {url} (Ctrl-C to stop)', file=sys.stderr, flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        httpd.server_close()
        library.close()
