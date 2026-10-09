"""Per-video bare repositories and the git smart HTTP CGI bridge."""
import html
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from urllib.parse import parse_qs, quote, urlsplit


PART = re.compile(r'[a-z0-9][a-z0-9._-]{0,62}\Z')
GIT_ROUTE = re.compile(r'/git/(.+?)\.git(/.*)?\Z')


def valid_name(name):
    return (isinstance(name, str) and len(name.split('/')) in (1, 2) and
            all(PART.fullmatch(p) and not p.endswith('.git') and '..' not in p for p in name.split('/')))


def run(*argv, cwd=None, input=None, env=None):
    result = subprocess.run(argv, cwd=cwd, input=input, env=env, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or 'git failed')
    return result.stdout.strip()


class Library:
    def __init__(self, root, checkouts=None, state_dir=None, host='127.0.0.1', allowed_hosts=(),
                 backend=None, agent=None, unsandboxed_previews=False, envs=None):
        self.root = Path(root).resolve()
        self.repos = self.root / 'repos'
        self.checkouts = Path(checkouts or self.root / 'checkouts').resolve()
        self.state_dir = Path(state_dir or self.root / 'state').resolve()
        for path in (self.repos, self.checkouts, self.state_dir):
            path.mkdir(parents=True, exist_ok=True)
        self.allowed_hosts = {h.lower().rstrip('.') for h in
                              ('localhost', '127.0.0.1', '::1', host, *allowed_hosts)}
        from .workers import Environments
        # Names can't start with '.', so '.shared' never collides with a repo's state dir.
        environments = Environments(self.state_dir / '.shared', envs or 'pinned')
        self.options = dict(backend=backend, agent=agent, allowed_hosts=allowed_hosts, host=host,
                            unsandboxed_previews=unsandboxed_previews, environments=environments)
        self.editors = {}
        self.lock = threading.RLock()

    def path(self, name):
        if not valid_name(name):
            raise ValueError('invalid repository name')
        return self.repos / (name + '.git')

    def names(self):
        return sorted(p.relative_to(self.repos).as_posix()[:-4] for p in self.repos.glob('**/*.git')
                      if p.is_dir() and valid_name(p.relative_to(self.repos).as_posix()[:-4]))

    def has_main(self, name):
        path = self.path(name)
        return path.is_dir() and subprocess.run(['git', '--git-dir', str(path), 'show-ref', '--verify', '--quiet',
                                                 'refs/heads/main']).returncode == 0

    def create(self, name):
        path = self.path(name)
        with self.lock:
            if path.exists():
                raise ValueError('repository already exists')
            path.parent.mkdir(parents=True, exist_ok=True)
            run('git', 'init', '--bare', '--initial-branch=main', str(path))
            for key, value in (('http.receivepack', 'true'), ('receive.denyNonFastForwards', 'true'),
                               ('receive.denyDeletes', 'true')):
                run('git', '--git-dir', str(path), 'config', key, value)
        return path

    def editor(self, name):
        from .editor import Editor
        if not self.has_main(name):
            raise ValueError('repository has no main branch')
        with self.lock:
            if name not in self.editors:
                flat = name.replace('/', '--')
                checkout = self.checkouts / flat
                if not (checkout / '.git').exists():
                    if checkout.exists():
                        raise ValueError('checkout path already exists')
                    run('git', 'clone', str(self.path(name)), str(checkout))
                self.editors[name] = Editor(checkout, state_dir=self.state_dir / flat,
                                            sync_remote='origin', **self.options)
            return self.editors[name]

    def copied(self, source, name):
        if not valid_name(source) or not valid_name(name):
            raise ValueError('invalid repository name')
        if not self.has_main(source):
            raise ValueError('source has no main branch')
        source_path = self.path(source)
        sha = run('git', '--git-dir', str(source_path), 'rev-parse', 'refs/heads/main').decode()
        tree = run('git', '--git-dir', str(source_path), 'rev-parse', sha + '^{tree}').decode()
        target = self.create(name)
        env = {**os.environ, 'GIT_AUTHOR_NAME': 'Video Editor', 'GIT_AUTHOR_EMAIL': 'editor@example.com',
               'GIT_COMMITTER_NAME': 'Video Editor', 'GIT_COMMITTER_EMAIL': 'editor@example.com'}
        run('git', '--git-dir', str(target), 'fetch', str(source_path),
            'refs/heads/main:refs/vb-source')
        try:
            commit = run('git', '--git-dir', str(target), 'commit-tree', tree,
                         input=f'New video from {source} ({sha})\n'.encode(), env=env).decode()
            run('git', '--git-dir', str(target), 'update-ref', 'refs/heads/main', commit)
        finally:
            run('git', '--git-dir', str(target), 'update-ref', '-d', 'refs/vb-source')
        return {'name': name, 'commit': commit, 'from': source, 'source_commit': sha}

    def index(self, host, scheme='http'):
        groups = {}
        for name in self.names():
            namespace = name.split('/')[0] if '/' in name else 'Videos'
            groups.setdefault(namespace, []).append(name)
        rows = []
        for group, names in groups.items():
            rows.append(f'<h2>{html.escape(group)}</h2><ul>')
            for name in names:
                encoded = '/'.join(quote(p) for p in name.split('/'))
                url = f'{scheme}://{host}/git/{encoded}.git'
                status = (f'<a href="/v/{encoded}/">Open</a>' if self.has_main(name) else 'Empty')
                rows.append(f'<li><strong>{html.escape(name)}</strong> · {status}<br><code>{html.escape(url)}</code></li>')
            rows.append('</ul>')
        return ('<!doctype html><html><head><meta charset="utf-8"><title>Video library</title>'
                '<style>body{font:16px system-ui;background:#181b20;color:#eee;max-width:900px;margin:4rem auto}'
                'a{color:#88cafa}li{margin:1rem 0}code{color:#bdcaaf}input{margin:.3rem;padding:.5rem}</style>'
                '</head><body><h1>Video library</h1>' + ''.join(rows) +
                '<h2>New video from…</h2><form id="new"><input name="from" placeholder="Source repo" required>'
                '<input name="name" placeholder="New repo" required><button>Create</button></form>'
                '<p id="error"></p><script>document.querySelector("#new").onsubmit=async e=>{e.preventDefault();'
                'const form=new FormData(e.target);const r=await fetch("/api/library/new",{method:"POST",'
                'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
                'if(r.ok)location.reload();else document.querySelector("#error").textContent=(await r.json()).error;'
                '};</script></body></html>').encode()

    def tick(self):
        """Advance unfinished notes in every repo, opening an editor only where one is pending."""
        from .notes import NoteStore
        for name in self.names():
            if name not in self.editors:
                notes = self.state_dir / name.replace('/', '--') / 'notes'
                if not notes.is_dir() or not NoteStore(notes).pending():
                    continue
            try:
                self.editor(name).notes.tick()
            except Exception as e:
                print(f'[editor] {name}: note poll failed: {e}', file=sys.stderr, flush=True)

    def close(self):
        for editor in self.editors.values():
            editor.renders.close()
            editor.pool.close()


def git_route(path):
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
