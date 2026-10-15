"""Request parsing and response plumbing shared by every route: the Host
allowlist, JSON/raw body handling, ranged sends and cookies. Mixed into the
composed Handler by `editor.make_handler`."""
import json
import re
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from .editor import MAX_BODY, Forbidden, HTTPError


class BaseHandler(BaseHTTPRequestHandler):
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
            if not valid or not hostname or parsed.username or parsed.password or parsed.path or hostname.lower().rstrip('.') not in self.editor.allowed_hosts:
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

    def _send_ranged(self, data, ctype, headers):
        """`data` as a 200, or a byte-range response (206/416) honouring a
        Range request header: iOS Safari refuses to play an MP4 with no
        Range support."""
        rang = self.headers.get('Range')
        if not rang:
            return self._send(200, data, ctype, headers)
        m = re.fullmatch(r'bytes=(\d*)-(\d*)', rang)
        if not m or (not m[1] and not m[2]):
            return self._send(416, b'', ctype, {**headers, 'Content-Range': f'bytes */{len(data)}'})
        if m[1]:
            start = int(m[1])
            end = int(m[2]) if m[2] else len(data) - 1
        else:
            count = int(m[2])
            start = max(0, len(data) - count)
            end = len(data) - 1
        if start >= len(data) or end < start or (not m[1] and not count):
            return self._send(416, b'', ctype, {**headers, 'Content-Range': f'bytes */{len(data)}'})
        end = min(end, len(data) - 1)
        return self._send(206, data[start:end + 1], ctype,
                          {**headers, 'Content-Range': f'bytes {start}-{end}/{len(data)}'})

    def _same_origin(self):
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            raise HTTPError(403, 'cross-origin request refused')

    def _cookie(self, name):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            field = cookie.get(name)
            return field.value if field else None
        except Exception:
            return None

    def _session_cookie(self, token):
        secure = '; Secure' if self.headers.get('X-Forwarded-Proto', '').lower() == 'https' else ''
        return f'vb_session={token}; Path=/; Max-Age={30*24*3600}; HttpOnly; SameSite=Lax{secure}'

    def _body(self):
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            raise HTTPError(415, 'send JSON (Content-Type: application/json)')
        if not self._key:
            # A bearer key carries no ambient browser credential, so CSRF doesn't apply.
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
