"""Live preview: a stdlib HTTP server that draws frames on request, and a page
to scrub, play and step through them. The film file (and any .py file beside
it) is watched; on a change it is re-imported and the page redraws.

    python -m videobuilder preview film.py [--port 8000]

    GET /                                         the page
    GET /info                                     film facts as JSON, plus `version` and `error`
    GET /frame?frame=n&format=f&scale=s&overlay=1 one frame as PNG

It binds to 127.0.0.1 unless told otherwise: it runs the film's code on
request, so it is not for exposing to a network.
"""
import io
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, urlparse

from . import overlay
from .film import Film, load_module


class Session:
    """The film being previewed, reloaded when its files change. Keeps the last
    good film when a reload fails, and reports the error alongside it."""

    def __init__(self, path, poll=0.25):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.poll = poll
        self.lock = threading.RLock()  # one draw at a time: imports and Pango are not thread-safe
        self.film = None
        self.error = None
        self.version = 0
        self._stamp = None
        self._checked = 0.0
        self.check(force=True)

    def _watched(self):
        files = {self.path}
        try:
            files.update(os.path.join(self.dir, f) for f in os.listdir(self.dir) if f.endswith('.py'))
        except OSError:
            pass
        return files

    def _snapshot(self):
        stamp = []
        for f in sorted(self._watched()):
            try:
                st = os.stat(f)
                stamp.append((f, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
        return tuple(stamp)

    def check(self, force=False):
        """Reload if any watched file changed since the last look. Cheap to call often."""
        with self.lock:
            now = time.monotonic()
            if not force and now - self._checked < self.poll:
                return
            self._checked = now
            stamp = self._snapshot()
            if stamp == self._stamp and not force:
                return
            self._stamp = stamp
            self._reload()

    def _reload(self):
        # Forget the film's neighbours too, so an edited helper module is re-imported.
        for name, mod in list(sys.modules.items()):
            f = getattr(mod, '__file__', None)
            if f and os.path.dirname(os.path.abspath(f)) == self.dir:
                del sys.modules[name]
        try:
            film = getattr(load_module(self.path), 'FILM', None)
            if not isinstance(film, Film):
                raise TypeError(f'{self.path} must define FILM = videobuilder.Film(...)')
            self.film, self.error = film, None
        except Exception:
            self.error = traceback.format_exc()
        self.version += 1
        state = 'error' if self.error else 'ok'
        print(f'[preview] loaded v{self.version} ({state})', file=sys.stderr, flush=True)
        if self.error:
            print(self.error, file=sys.stderr, flush=True)

    def info(self):
        with self.lock:
            out = {'version': self.version, 'error': self.error, 'path': self.path}
            f = self.film
            if f is None:
                return out
            out.update(fps=f.fps, frames=f.frames,
                       formats=[{'name': x.name, 'width': x.width, 'height': x.height} for x in f.formats])
            tl = f.timeline
            if tl is not None:
                b = tl.grid.b
                out['timeline'] = {
                    'bpm': tl.grid.bpm, 'frames_per_beat': tl.grid.frames_per_beat, 'end_beat': tl.end,
                    'beats': [b(k) for k in range(int(tl.end) + 1)],
                    'segments': [{'name': s.name, 'start': b(s.at), 'end': b(s.until),
                                  'at': s.at, 'until': s.until} for s in tl.segments],
                }
            return out

    def png(self, n, fmt=None, scale=1.0, show_overlay=False):
        with self.lock:
            film = self.film
            if film is None:
                raise RuntimeError(self.error or 'no film loaded')
            n = max(0, min(film.frames - 1, n))
            cv = film.frame(n, fmt, scale=scale)
            if show_overlay:
                overlay.draw(cv, film, n)
            buf = io.BytesIO()
            cv.surface.write_to_png(buf)
            return buf.getvalue()


def _page():
    return resources.files(__package__).joinpath('preview.html').read_bytes()


def make_handler(session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[-1] for k, v in parse_qs(url.query).items()}
            try:
                session.check()
                if url.path in ('/', '/index.html'):
                    self._send(200, _page(), 'text/html; charset=utf-8')
                elif url.path == '/info':
                    self._send(200, json.dumps(session.info()).encode(), 'application/json')
                elif url.path in ('/frame', '/frame.png'):
                    png = session.png(int(q.get('frame', 0)), q.get('format') or None,
                                      float(q.get('scale', 1.0)), q.get('overlay') in ('1', 'true'))
                    self._send(200, png, 'image/png')
                else:
                    self._send(404, b'not found\n', 'text/plain')
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self._send(500, traceback.format_exc().encode(), 'text/plain; charset=utf-8')

    return Handler


def serve(path, host='127.0.0.1', port=8000, open_browser=False):
    session = Session(path)
    httpd = ThreadingHTTPServer((host, port), make_handler(session))
    httpd.daemon_threads = True
    url = f'http://{host}:{httpd.server_address[1]}/'
    print(f'[preview] {session.path} at {url} (Ctrl-C to stop)', file=sys.stderr, flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
