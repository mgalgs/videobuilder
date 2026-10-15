"""The git smart-HTTP bridge: creates a repo on its first authenticated push,
then proxies the request to `git http-backend`."""
import os
import re
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit

GIT_ROUTE = re.compile(r'/git/(.+?)\.git(/.*)?\Z')


def git_route(path):
    from .library import valid_name
    match = GIT_ROUTE.fullmatch(path)
    if not match or not valid_name(match.group(1)):
        return None
    return match.group(1), (match.group(2) or '')


def _copy_body(handler, target):
    if handler.headers.get('Transfer-Encoding', '').lower() == 'chunked':
        while True:
            line = handler.rfile.readline(128)
            size = int(line.split(b';', 1)[0].strip(), 16)
            if size == 0:
                while handler.rfile.readline(65536).strip():
                    pass
                break
            remaining = size
            while remaining:
                chunk = handler.rfile.read(min(65536, remaining))
                if not chunk:
                    raise ConnectionError('incomplete chunked request')
                target.write(chunk)
                remaining -= len(chunk)
            if handler.rfile.read(2) != b'\r\n':
                raise ValueError('invalid chunked request')
    else:
        remaining = int(handler.headers.get('Content-Length') or 0)
        while remaining:
            chunk = handler.rfile.read(min(65536, remaining))
            if not chunk:
                raise ConnectionError('incomplete request')
            target.write(chunk)
            remaining -= len(chunk)


def serve_git(handler, library, method, identity):
    parsed = urlsplit(handler.path)
    route = git_route(parsed.path)
    if route is None:
        return False
    name, suffix = route
    path = library.path(name)
    if not path.exists():
        query = parse_qs(parsed.query)
        # Creating on a GET: require a git client, so a cross-site <img> can't make repos.
        if (method == 'GET' and suffix == '/info/refs' and query.get('service') == ['git-receive-pack']
                and handler.headers.get('User-Agent', '').startswith('git/')):
            try:
                library.create(name)
            except ValueError:
                pass  # another request may have created it
        else:
            handler._json(404, {'error': 'repository not found'})
            return True
    env = {**os.environ, 'GIT_PROJECT_ROOT': str(library.repos), 'GIT_HTTP_EXPORT_ALL': '1',
           'PATH_INFO': '/' + name + '.git' + suffix, 'REQUEST_METHOD': method,
           'QUERY_STRING': parsed.query, 'CONTENT_TYPE': handler.headers.get('Content-Type', ''),
           'HTTP_CONTENT_ENCODING': handler.headers.get('Content-Encoding', ''),
           'REMOTE_ADDR': handler.client_address[0]}
    if identity is not None:
        env['REMOTE_USER'] = str(identity)
    proc = subprocess.Popen(['git', 'http-backend'], env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    feed_error = []
    def feed():
        try:
            _copy_body(handler, proc.stdin)
        except (BrokenPipeError, ConnectionError, ValueError) as exc:
            feed_error.append(exc)
        finally:
            proc.stdin.close()
    feeder = threading.Thread(target=feed)
    feeder.start()
    try:
        headers = []
        while True:
            line = proc.stdout.readline()
            if line in (b'\r\n', b'\n', b''):
                break
            headers.append(line.decode('latin-1').rstrip('\r\n'))
        status = 200
        for header in headers:
            if header.lower().startswith('status:'):
                status = int(header.split(':', 1)[1].strip().split(' ', 1)[0])
        handler.send_response(status)
        for header in headers:
            key, _, value = header.partition(':')
            if key.lower() != 'status':
                handler.send_header(key, value.strip())
        handler.end_headers()
        while chunk := proc.stdout.read(65536):
            handler.wfile.write(chunk)
    finally:
        feeder.join()
        proc.wait()
        proc.stdout.close()
    if method == 'POST' and suffix == '/git-receive-pack' and proc.returncode == 0 and not feed_error:
        if name in library.editors:
            library.editors[name].refresh(force=True)
    return True
