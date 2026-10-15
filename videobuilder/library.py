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


LIBRARY_STYLE = (
    'body{font:16px/1.4 system-ui,sans-serif;background:#0d0d10;color:#fff;margin:0}'
    'a{color:#88cafa;text-decoration:none}'
    '.lib-page{max-width:900px;margin:0 auto;padding:1rem 1rem 3rem}'
    '.lib-header{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem;margin-bottom:1rem}'
    '.lib-header h1{font-size:1.3rem;margin:0;flex:1 1 auto;min-width:0}'
    '.caps-link{font-size:.85rem;color:#a9a9b2}'
    '.account-bar{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;justify-content:space-between;'
    'border-bottom:1px solid #26262c;padding:.75rem 0;margin-bottom:.5rem}'
    '.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.5rem 1rem;'
    'border-radius:8px;border:1px solid #26262c;background:#141417;color:#fff;font-weight:600;cursor:pointer}'
    '.btn-primary{background:#e5483b;border-color:#e5483b;color:#fff}'
    'button.btn,button#sign-out{font:inherit}'
    '#sign-out{min-height:44px;padding:.5rem 1rem;border-radius:8px;border:1px solid #26262c;background:#141417;'
    'color:#fff}'
    'h2{font-size:1rem;color:#a9a9b2;margin:1.5rem 0 .5rem;text-transform:uppercase;letter-spacing:.04em}'
    '.lib-grid{display:flex;flex-direction:column;gap:.75rem}'
    '.lib-card{border:1px solid #26262c;border-radius:10px;padding:.75rem .9rem;background:#141417;min-width:0}'
    '.lib-card-top{display:flex;align-items:center;justify-content:space-between;gap:.6rem;min-width:0}'
    '.lib-name{overflow-wrap:anywhere;min-width:0}'
    '.lib-empty{color:#a9a9b2}'
    '.lib-git{display:flex;align-items:center;gap:.5rem;margin-top:.5rem;min-width:0}'
    '.lib-url{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;word-break:break-all;font-size:.8rem;color:#bdcaaf;'
    'user-select:all}'
    '.lib-copy{flex:0 0 auto;min-height:36px;padding:.3rem .6rem;border-radius:6px;border:1px solid #26262c;'
    'background:#0d0d10;color:#fff;font-size:.8rem}'
    '@media (max-width:480px){.lib-page{padding:.75rem .75rem 2.5rem}.lib-card-top{flex-wrap:wrap}}'
)

NEW_VIDEO_STYLE = (
    '#new-video [hidden]{display:none !important}'
    '#new-video{display:flex;flex-direction:column;gap:1rem;max-width:560px}'
    '#new-video label{display:flex;flex-direction:column;gap:.35rem;font-size:.9rem;color:#a9a9b2}'
    '#new-video input,#new-video textarea{font:inherit;min-height:44px;padding:.5rem .6rem;border-radius:8px;'
    'border:1px solid #26262c;background:#141417;color:#fff}'
    '#new-video textarea{min-height:88px;resize:vertical}'
    '.start-from{border:1px solid #26262c;border-radius:10px;padding:.6rem .9rem;display:flex;flex-direction:column;'
    'gap:.5rem}'
    '.start-from legend{color:#a9a9b2;font-size:.85rem;padding:0 .3rem}'
    '.radio{flex-direction:row !important;align-items:center;gap:.5rem !important;min-height:44px}'
    '#create{min-height:48px;border-radius:8px;border:1px solid #e5483b;background:#e5483b;color:#fff;'
    'font-weight:600;font-size:1rem}'
    '#error{color:#f88;min-height:1.2em;margin:0}'
)

NEW_VIDEO_SCRIPT = (
    '<script>'
    'const form=document.querySelector("#new-video");'
    'const sourceField=document.querySelector("#source-field");'
    'const scratchFields=document.querySelector("#scratch-fields");'
    'for(const r of form.querySelectorAll("input[name=start]"))r.onchange=()=>{'
    'const copy=form.start.value==="copy";sourceField.hidden=!copy;scratchFields.hidden=copy};'
    'function splitLines(s){return (s||"").split("\\n").map(x=>x.trim()).filter(Boolean)}'
    'async function uploadAll(name,video,files){'
    'const ids=[];'
    'for(const file of files){'
    'const r=await fetch(`/v/${encodeURIComponent(name)}/api/attachments?`+new URLSearchParams('
    '{video,name:file.name}),{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream"},'
    'body:file});'
    'const data=await r.json();'
    'if(!r.ok)throw Error(data.error||"could not upload "+file.name);'
    'ids.push(data.id)}'
    'return ids}'
    'form.onsubmit=async e=>{'
    'e.preventDefault();'
    'const error=document.querySelector("#error"),button=document.querySelector("#create");'
    'error.textContent="";button.disabled=true;'
    'const data=new FormData(form);'
    'const name=data.get("name").trim(),start=data.get("start");'
    'try{'
    'const body={name,start};'
    'if(start==="copy")body.from=data.get("from").trim();'
    'const r=await fetch("/api/videos/new",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify(body)});'
    'const result=await r.json();'
    'if(!r.ok)throw Error(result.error||"could not create the video");'
    'if(start==="blank"){'
    'const description=data.get("description")||"";'
    'const links=splitLines(data.get("links"));'
    'const files=data.getAll("files").filter(f=>f&&f.size);'
    'if(description.trim()||links.length||files.length){'
    'button.textContent="Uploading…";'
    'const attachments=await uploadAll(name,result.video,files);'
    'button.textContent="Starting…";'
    'const path=name.split("/").map(encodeURIComponent).join("/");'
    'const r2=await fetch(`/v/${path}/api/videos/first-note`,{method:"POST",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify({description,attachments,links})});'
    'const note=await r2.json();'
    'if(!r2.ok)throw Error(note.error||"could not start the video")'
    '}}'
    'location.href="/v/"+name.split("/").map(encodeURIComponent).join("/")+"/"'
    '}catch(err){error.textContent=err.message;button.disabled=false;button.textContent="Create"}'
    '}'
    '</script>'
)


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
            rows.append(f'<h2>{html.escape(group)}</h2><div class="lib-grid">')
            for name in group_names:
                encoded = '/'.join(quote(p) for p in name.split('/'))
                url = f'{scheme}://{host}/git/{encoded}.git'
                open_or_empty = (f'<a class="btn" href="/v/{encoded}/">Open</a>' if self.has_main(name)
                                 else '<span class="lib-empty">Empty</span>')
                rows.append('<div class="lib-card"><div class="lib-card-top">'
                           f'<strong class="lib-name">{html.escape(name)}</strong>{open_or_empty}</div>'
                           f'<div class="lib-git"><code class="lib-url">{html.escape(url)}</code>'
                           f'<button class="lib-copy" type="button" data-url="{html.escape(url)}" '
                           'aria-label="Copy git URL">Copy</button></div></div>')
            rows.append('</div>')
        account_bar = ''
        body = ''.join(rows)
        can_create = bool(user) if self.accounts else True
        if self.accounts:
            account_bar = ('<div class="account-bar"><span>Signed in as <strong>' + html.escape(user) +
                           '</strong></span><button id="sign-out">Sign out</button></div>')
            if not names:
                body = (f'<p>No videos shared with you yet — ask the owner to invite '
                        f'<strong>{html.escape(user)}</strong>.</p>')
        new_video = '<a class="btn btn-primary new-video" href="/new">+ New video</a>' if can_create else ''
        script = ('<script>'
                  'for(const b of document.querySelectorAll(".lib-copy"))b.onclick=async()=>{'
                  'try{await navigator.clipboard.writeText(b.dataset.url);const t=b.textContent;'
                  'b.textContent="Copied";setTimeout(()=>b.textContent=t,1200)}catch(_){}};'
                  'const o=document.querySelector("#sign-out");if(o)o.onclick=async()=>{'
                  'await fetch("/api/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});'
                  'location.href="/login"};</script>')
        return ('<!doctype html><html><head><meta charset="utf-8"><title>Video library</title>'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<style>' + LIBRARY_STYLE + '</style>'
                '</head><body><div class="lib-page">' + account_bar +
                '<header class="lib-header"><h1>Video library</h1>' + new_video +
                '<a class="caps-link" href="/capabilities">Capabilities</a></header>' +
                body + script +
                '</div></body></html>').encode()

    def new_video_page(self, names=None):
        options = ''.join(f'<option value="{html.escape(n)}"></option>' for n in (names or self.names()))
        return ('<!doctype html><html><head><meta charset="utf-8"><title>New video · Video library</title>'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<style>' + LIBRARY_STYLE + NEW_VIDEO_STYLE + '</style></head><body><div class="lib-page">'
                '<header class="lib-header"><a class="btn" href="/">&larr; Library</a>'
                '<h1>New video</h1></header>'
                '<form id="new-video">'
                '<label>Name<input name="name" placeholder="namespace/name" required autocapitalize="off" '
                'autocorrect="off" spellcheck="false"></label>'
                '<fieldset class="start-from"><legend>Start from</legend>'
                '<label class="radio"><input type="radio" name="start" value="blank" checked> Blank</label>'
                '<label class="radio"><input type="radio" name="start" value="copy"> A copy of an existing video</label>'
                '</fieldset>'
                f'<label id="source-field" hidden>Source video<input name="from" list="existing-videos" '
                f'placeholder="namespace/name"><datalist id="existing-videos">{options}</datalist></label>'
                '<div id="scratch-fields">'
                '<label>Description<textarea name="description" rows="5" '
                'placeholder="What is this video for? Who is it for?"></textarea></label>'
                '<label>Files<input name="files" type="file" multiple '
                'accept="image/*,video/*,audio/*,.pdf,.txt,.md"></label>'
                '<label>Links (one per line)<textarea name="links" rows="3" '
                'placeholder="https://example.com/the-feature"></textarea></label>'
                '</div>'
                '<button id="create" type="submit">Create</button>'
                '<p id="error" role="alert"></p>'
                '</form></div>' + NEW_VIDEO_SCRIPT + '</body></html>').encode()

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
