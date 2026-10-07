"""The editor: a local web app to review a project's videos and change them.
A timeline and a scrubbable preview for each video; direct edits (roll a
cut, replace a line of copy) that each become one git commit; and notes
pinned to a frame, kept for an agent to act on.

    python -m videobuilder editor <project-dir> [--host 127.0.0.1] [--port 8100] [--state-dir DIR]

The HTTP API (JSON in and out, except the PNGs; `video` is a video id from
/api/project):

    GET  /                               the page
    GET  /api/project                    the project: name, git, backend, videos
    GET  /api/info?video=V               the preview's /info for V, plus video, edits_file, git, undo
    GET  /api/frame?video=V&frame=n&format=f&scale=s&overlay=1   one frame as PNG
    POST /api/roll   {video, segment, until}       roll a cut, and commit
    POST /api/copy   {video, segment, key, value}  replace a string, and commit
    POST /api/undo   {video}                       reverse the last edit, as a new edit
    GET  /api/notes[?video=V]            notes, oldest first (polls the backend)
    POST /api/notes  {video, format, frame, text}  pin a note at a frame
    GET  /api/notes/<id>                 one note
    GET  /api/notes/<id>.png             the frame it was pinned to
    POST /api/notes/<id>/delete          remove a note (refused for active real runs)
    GET  /api/draft?video=V             branch, tip, commits, files, refused paths (or null)
    GET  /api/draft/info?video=V        isolated draft timeline/info
    GET  /api/draft/frame?video=V&frame=n&format=f&scale=s  isolated draft PNG
    POST /api/draft/accept {video}      accepted, or rebase_requested with automatic note
    POST /api/draft/drop   {video}      delete draft and keep session

An edit answers 200 with {message, commit, warning, changed, undo}, where
`commit` is the new sha (null when it wasn't committed, `warning` says why)
and `undo` is the edit that reverses it. A refused edit answers 400 with
{error} and changes nothing. Other errors answer {error} with 4xx or 500.

Trust. The editor runs each film's Python, as the preview does, so it is for
trusted repos on a trusted network. It binds to 127.0.0.1 by default and has
no authentication: `request_hook` is where a check of a reverse proxy's
identity header belongs. POSTs must be JSON from the editor's own origin, so
another web page can't make edits through a reviewer's browser.

State (notes, for now) lives in `<project>/.vb-editor/` unless `--state-dir`
or `state_dir` in videobuilder.toml says otherwise; it ignores itself in git.
"""
import json
import os
import re
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, unquote, urlparse

from . import edits
from .notes import NoteStore
from .agents import backend_from_config
from .drafts import Drafts
from .preview import Session
from .project import Project, read_config

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

    def __init__(self, root, state_dir=None, backend=None, poll=0.25, agent=None, allowed_hosts=(), host='127.0.0.1'):
        self.root = os.path.abspath(root)
        cfg = read_config(self.root)
        state = state_dir or cfg.get('state_dir') or STATE_DIR
        self.state_dir = os.path.abspath(os.path.join(self.root, state))
        self.lock = threading.RLock()
        self.project = Project(self.root, skip=[self.state_dir], lock=self.lock)
        self.drafts = Drafts(self)
        agent_cfg = {**cfg.get('agent', {}), **(agent or {})}
        self.notes = NoteStore(os.path.join(self.state_dir, 'notes'),
                               backend or backend_from_config(agent_cfg), context=self.drafts.context)
        self.allowed_hosts = {h.lower().rstrip('.') for h in
                              ['localhost', '127.0.0.1', '::1', host, *cfg.get('allowed_hosts', []), *allowed_hosts]}
        self.poll = poll
        self.sessions = {}
        _ensure_state_dir(self.state_dir)

    def session(self, vid):
        with self.lock:
            try:
                video = self.project.video(vid)
            except KeyError:
                raise HTTPError(404, f'no video {vid!r} in this project') from None
            s = self.sessions.get(vid)
            if s is None or s.path != video.path:
                s = self.sessions[vid] = Session(video.path, poll=self.poll, lock=self.lock)
            return s

    def project_info(self):
        try:
            videos, error = [v.to_json(self.root) for v in self.project.videos()], None
        except ValueError as e:
            videos, error = [], str(e)
        return {'name': os.path.basename(self.root), 'root': self.root, 'git': self.project.git is not None,
                'backend': self.notes.backend.name, 'state_dir': self.state_dir, 'videos': videos, 'error': error}

    def info(self, vid):
        s = self.session(vid)
        s.check()
        out = s.info()
        out.update(video=vid, edits_file=os.path.relpath(edits.path_for(s.path), self.root),
                   git=self.project.git_info(vid), undo=self.project.last.get(vid))
        return out

    def edit(self, vid, op, body):
        s = self.session(vid)
        try:
            if op == 'undo':
                result = self.project.undo(vid)
            elif op == 'roll':
                result = self.project.edit(vid, 'roll', _field(body, 'segment', str),
                                           _field(body, 'until', (int, float)))
            else:
                result = self.project.edit(vid, 'copy', _field(body, 'segment', str), _field(body, 'value', str),
                                           key=_field(body, 'key', str))
        except ValueError as e:
            raise HTTPError(400, _short(str(e), s.path)) from None
        s.check(force=True)
        if result['warning']:
            print(f'[editor] {result["warning"]}', file=sys.stderr, flush=True)
        return result

    def add_note(self, body, author):
        vid = _field(body, 'video', str)
        s = self.session(vid)
        frame = _field(body, 'frame', int)
        fmt = body.get('format') or None
        with self.lock:
            s.check()
            film = s.film
            if film is None:
                raise HTTPError(409, 'the video does not load; fix it before pinning notes')
            frame = max(0, min(film.frames - 1, frame))
            fmt = film.format(fmt).name
            segment = film.timeline.at(frame)[0].name if film.timeline is not None else None
            png = s.png(frame, fmt, NOTE_SCALE)
        try:
            return self.notes.add(vid, fmt, frame, segment, body.get('text'), png, author=author,
                                  time=frame / film.fps,
                                  beat=frame / film.timeline.grid.frames_per_beat if film.timeline else None)
        except ValueError as e:
            raise HTTPError(400, str(e)) from None


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
                if not valid or not hostname or parsed.username or parsed.password or parsed.path or hostname.lower().rstrip('.') not in editor.allowed_hosts:
                    raise Forbidden('Host is not allowed; configure --allow-host for this name')
            except Forbidden as e:
                self._json(e.code, {'error': str(e)})
                return False
            return True

        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj).encode(), 'application/json')

        def _body(self):
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise HTTPError(415, 'send JSON (Content-Type: application/json)')
            origin = self.headers.get('Origin')
            if origin and urlparse(origin).netloc != self.headers.get('Host'):
                raise HTTPError(403, 'cross-origin request refused')
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
                if method == 'GET':
                    self._get(route, q)
                else:
                    self._post(route, self._body(), identity)
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

        def _get(self, route, q):
            if route in ('/', '/index.html'):
                return self._send(200, _page(), 'text/html; charset=utf-8')
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
                s.check()
                try:
                    png = s.png(int(q.get('frame', 0)), q.get('format') or None, float(q.get('scale', 0.5)),
                                q.get('overlay') in ('1', 'true'))
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
                    return self._json(200, editor.notes.get(nid))
                except KeyError:
                    raise HTTPError(404, f'no note {nid!r}') from None
            raise HTTPError(404, 'not found')

        def _post(self, route, body, identity):
            if route in ('/api/draft/accept', '/api/draft/drop'):
                action = getattr(editor.drafts, route.rsplit('/', 1)[1])
                return self._json(200, action(_field(body, 'video', str), identity))
            if route in ('/api/roll', '/api/copy', '/api/undo'):
                return self._json(200, editor.edit(_field(body, 'video', str), route[5:], body))
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


def serve(root, host='127.0.0.1', port=8100, state_dir=None, open_browser=False, backend=None,
          hook=request_hook, agent=None, allowed_hosts=()):
    editor = Editor(root, state_dir=state_dir, backend=backend, agent=agent, allowed_hosts=allowed_hosts, host=host)
    httpd = ThreadingHTTPServer((host, port), make_handler(editor, hook))
    httpd.daemon_threads = True
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
        httpd.server_close()
