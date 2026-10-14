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


_AUTH_STYLE = ('<style>body{font:16px system-ui;background:#181b20;color:#eee;max-width:420px;margin:4rem auto;'
              'padding:0 1rem}input,button{display:block;width:100%;margin:.4rem 0;padding:.7rem;font-size:16px;'
              'box-sizing:border-box;border-radius:6px;border:1px solid #333;background:#20242b;color:#eee;'
              'min-height:44px}button{background:#2d6cdf;border:none;color:#fff;font-weight:600;cursor:pointer}'
              'a{color:#88cafa}#error{color:#f88;min-height:1.2em}'
              '@media (max-width:700px){body{margin:2rem auto}}</style>')


def signin_page(error=None):
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Sign in · Video library</title>'
           '<meta name="viewport" content="width=device-width, initial-scale=1">' + _AUTH_STYLE +
           '</head><body><h1>Video library</h1><form id="f">'
           '<label>Username<input name="username" autocomplete="username" required></label>'
           '<label>Password<input name="password" type="password" autocomplete="current-password" required>'
           '</label><button>Sign in</button></form><p id="error"></p><p><a href="/signup">Sign up</a></p>'
           '<script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();'
           'const form=new FormData(e.target);const r=await fetch("/api/login",{method:"POST",'
           'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
           'if(r.ok)location.href="/";else document.querySelector("#error").textContent=(await r.json()).error};'
           '</script></body></html>').encode()


def signup_page():
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Sign up · Video library</title>'
           '<meta name="viewport" content="width=device-width, initial-scale=1">' + _AUTH_STYLE +
           '</head><body><h1>Video library</h1><form id="f">'
           '<label>Username<input name="username" autocomplete="username" required></label>'
           '<label>Password<input name="password" type="password" autocomplete="new-password" required></label>'
           '<label>Confirm password<input name="confirm" type="password" autocomplete="new-password" required>'
           '</label><button>Sign up</button></form><p id="error"></p><p><a href="/login">Sign in</a></p>'
           '<script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();'
           'const form=new FormData(e.target);const r=await fetch("/api/signup",{method:"POST",'
           'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
           'if(r.ok)location.href="/";else document.querySelector("#error").textContent=(await r.json()).error};'
           '</script></body></html>').encode()


def run(*argv, cwd=None, input=None, env=None):
    result = subprocess.run(argv, cwd=cwd, input=input, env=env, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or 'git failed')
    return result.stdout.strip()


class Library:
    def __init__(self, root, checkouts=None, state_dir=None, host='127.0.0.1', allowed_hosts=(),
                 backend=None, agent=None, unsandboxed_previews=False, envs=None, admins=(), capabilities_dir=None,
                 music_sources=None):
        self.capabilities_dir = capabilities_dir
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
        from .music import MusicLibrary
        # Parsed once here, not per-project, so a bad file is a startup error and every
        # project shares one cache instead of fetching and importing per project.
        music = MusicLibrary.from_file(music_sources) if music_sources else None
        self.options = dict(backend=backend, agent=agent, allowed_hosts=allowed_hosts, host=host,
                            unsandboxed_previews=unsandboxed_previews, environments=environments,
                            music=music)
        self.editors = {}
        self.lock = threading.RLock()
        from .accounts import Accounts
        from .access import Access
        self.accounts = Accounts(str(self.state_dir), admins) if admins else None
        self.access = Access(str(self.state_dir))

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
                                            sync_remote='origin', trust_repo_config=False,
                                            **self.options)
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

    def create_blank(self, name):
        """A new repo at `name` (refusing an existing one, like `copied`) with
        one commit: the minimal film and requirements.txt a video needs to be
        built by the builder, pinned to this editor's own videobuilder
        version the way an existing video's requirements.txt pins one (see
        workers.pinned_version). Nothing film-specific: v1 is the builder's
        job."""
        from . import __version__
        target = self.create(name)
        film = (
            "import videobuilder as vb\n\n"
            "T = vb.Timeline(vb.Grid(fps=30, bpm=120), [\n"
            "    vb.Segment('intro', 0, 8, dict(title='New video')),\n"
            "], end=8)\n\n\n"
            "def draw(n, cv):\n"
            "    cv.rect(0, 0, cv.width, cv.height, '#101418')\n\n\n"
            "FILM = vb.Film(draw=draw, timeline=T, formats=('9x16', '16x9'))\n"
        ).encode()
        requirements = f'videobuilder=={__version__}\n'.encode()
        env = {**os.environ, 'GIT_AUTHOR_NAME': 'Video Editor', 'GIT_AUTHOR_EMAIL': 'editor@example.com',
               'GIT_COMMITTER_NAME': 'Video Editor', 'GIT_COMMITTER_EMAIL': 'editor@example.com'}
        film_blob = run('git', '--git-dir', str(target), 'hash-object', '-w', '--stdin', input=film).decode()
        req_blob = run('git', '--git-dir', str(target), 'hash-object', '-w', '--stdin', input=requirements).decode()
        tree_input = f'100644 blob {film_blob}\tfilm.py\n100644 blob {req_blob}\trequirements.txt\n'.encode()
        tree = run('git', '--git-dir', str(target), 'mktree', input=tree_input).decode()
        commit = run('git', '--git-dir', str(target), 'commit-tree', tree,
                    input=b'Start a new video\n', env=env).decode()
        run('git', '--git-dir', str(target), 'update-ref', 'refs/heads/main', commit)
        return {'name': name, 'commit': commit, 'video': 'film'}

    def index(self, host, scheme='http', user=None):
        names = self.names()
        if self.accounts:
            names = [n for n in names if self.access.can_access(n, user, self.accounts)]
        groups = {}
        for name in names:
            namespace = name.split('/')[0] if '/' in name else 'Videos'
            groups.setdefault(namespace, []).append(name)
        rows = []
        for group, group_names in groups.items():
            rows.append(f'<h2>{html.escape(group)}</h2><ul>')
            for name in group_names:
                encoded = '/'.join(quote(p) for p in name.split('/'))
                url = f'{scheme}://{host}/git/{encoded}.git'
                status = (f'<a href="/v/{encoded}/">Open</a>' if self.has_main(name) else 'Empty')
                rows.append(f'<li><strong>{html.escape(name)}</strong> · {status}<br><code>{html.escape(url)}</code></li>')
            rows.append('</ul>')
        account_bar = ''
        body = ''.join(rows)
        if self.accounts:
            account_bar = ('<div class="account-bar"><span>Signed in as <strong>' + html.escape(user) +
                           '</strong></span><button id="sign-out">Sign out</button></div>')
            if not names:
                body = (f'<p>No videos shared with you yet — ask the owner to invite '
                        f'<strong>{html.escape(user)}</strong>.</p>')
            if self.accounts.is_admin(user):
                body += ('<h2>New video from…</h2><form id="new"><input name="from" placeholder="Source repo" required>'
                        '<input name="name" placeholder="New repo" required><button>Create</button></form>'
                        '<p id="error"></p>')
        else:
            body += ('<h2>New video from…</h2><form id="new"><input name="from" placeholder="Source repo" required>'
                    '<input name="name" placeholder="New repo" required><button>Create</button></form>'
                    '<p id="error"></p>')
        script = ('<script>const f=document.querySelector("#new");if(f)f.onsubmit=async e=>{e.preventDefault();'
                  'const form=new FormData(e.target);const r=await fetch("/api/library/new",{method:"POST",'
                  'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
                  'if(r.ok)location.reload();else document.querySelector("#error").textContent=(await r.json()).error;'
                  '};const o=document.querySelector("#sign-out");if(o)o.onclick=async()=>{'
                  'await fetch("/api/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});'
                  'location.href="/login"};</script>')
        return ('<!doctype html><html><head><meta charset="utf-8"><title>Video library</title>'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<style>body{font:16px system-ui;background:#181b20;color:#eee;max-width:900px;margin:4rem auto;'
                'padding:0 1rem}a{color:#88cafa}li{margin:1rem 0}code{color:#bdcaaf}input{margin:.3rem;padding:.5rem}'
                '.account-bar{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;justify-content:space-between;'
                'border-bottom:1px solid #333;padding-bottom:1rem;margin-bottom:1rem}'
                '.account-bar button{min-height:44px;padding:.5rem 1rem;border-radius:6px;border:1px solid #333;'
                'background:#20242b;color:#eee}'
                '@media (max-width:700px){body{margin:2rem auto}}</style>'
                '</head><body>' + account_bar +
                '<h1>Video library <a href="/capabilities" style="font-size:.5em">Capabilities</a></h1>' +
                body + script +
                '</body></html>').encode()

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
