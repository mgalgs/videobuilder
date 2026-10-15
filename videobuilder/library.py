"""Per-video bare repositories, managed by the `Library` class; the git smart
HTTP bridge and the library's HTML pages live in git_bridge.py and pages.py,
re-exported below so existing imports keep working."""
import os
from pathlib import Path
import re
import sys
import threading

from . import pages
from .gitutil import git
from .git_bridge import git_route, serve_git, _copy_body
from .pages import signin_page, signup_page


PART = re.compile(r'[a-z0-9][a-z0-9._-]{0,62}\Z')


def valid_name(name):
    return (isinstance(name, str) and len(name.split('/')) in (1, 2) and
            all(PART.fullmatch(p) and not p.endswith('.git') and '..' not in p for p in name.split('/')))


class Library:
    def __init__(self, root, checkouts=None, state_dir=None, host='127.0.0.1', allowed_hosts=(),
                 backend=None, agent=None, unsandboxed_previews=False, envs=None, admins=(), capabilities_dir=None,
                 compendium_dir=None, music_sources=None, account_daily_note_cap=None, account_daily_cost_cap_usd=None,
                 compendium_for_builder=None):
        self.capabilities_dir = capabilities_dir
        self.compendium_dir = compendium_dir
        self.root = Path(root).resolve()
        self.repos = self.root / 'repos'
        self.checkouts = Path(checkouts or self.root / 'checkouts').resolve()
        self.state_dir = Path(state_dir or self.root / 'state').resolve()
        for path in (self.repos, self.checkouts, self.state_dir):
            path.mkdir(parents=True, exist_ok=True)
        from .compendium_feed import CompendiumVotes
        self.compendium_votes = CompendiumVotes(str(self.state_dir / 'compendium-votes.jsonl'))
        self.allowed_hosts = {h.lower().rstrip('.') for h in
                              ('localhost', '127.0.0.1', '::1', host, *allowed_hosts)}
        from .workers import Environments
        # Names can't start with '.', so '.shared' never collides with a repo's state dir.
        environments = Environments(self.state_dir / '.shared', envs or 'pinned')
        from .music import MusicLibrary
        # Parsed once here, not per-project, so a bad file is a startup error and every
        # project shares one cache instead of fetching and importing per project.
        music = MusicLibrary.from_file(music_sources) if music_sources else None
        # Also kept as plain attributes (not just in `options`, which only Editor()
        # below reads) so the admin limits API can show the library-wide defaults
        # without opening a project.
        self.account_daily_note_cap = account_daily_note_cap
        self.account_daily_cost_cap_usd = account_daily_cost_cap_usd
        self.options = dict(backend=backend, agent=agent, allowed_hosts=allowed_hosts, host=host,
                            unsandboxed_previews=unsandboxed_previews, environments=environments,
                            music=music, account_daily_note_cap=account_daily_note_cap,
                            account_daily_cost_cap_usd=account_daily_cost_cap_usd,
                            compendium_for_builder=compendium_for_builder)
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
        return path.is_dir() and git(None, 'show-ref', '--verify', '--quiet', 'refs/heads/main',
                                     git_dir=path, hooks=False, check=False).returncode == 0

    def create(self, name):
        path = self.path(name)
        with self.lock:
            if path.exists():
                raise ValueError('repository already exists')
            path.parent.mkdir(parents=True, exist_ok=True)
            git(None, 'init', '--bare', '--initial-branch=main', str(path), hooks=False)
            for key, value in (('http.receivepack', 'true'), ('receive.denyNonFastForwards', 'true'),
                               ('receive.denyDeletes', 'true')):
                git(None, 'config', key, value, git_dir=path, hooks=False)
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
                    git(None, 'clone', str(self.path(name)), str(checkout), hooks=False)
                self.editors[name] = Editor(checkout, state_dir=self.state_dir / flat,
                                            sync_remote='origin', trust_repo_config=False,
                                            **self.options)
                self.editors[name].library = self
            return self.editors[name]

    def account_notes(self):
        """Every note across every project, tagged with its project's name, read
        straight off each project's notes directory the way `tick` does -- without
        opening an Editor for one that isn't already open -- so a cap check or a
        usage total sees every project an account has used, not just whichever one
        is serving the current request."""
        from .notes import NoteStore
        for name in self.names():
            store = self.editors[name].notes if name in self.editors else None
            if store is None:
                notes_dir = self.state_dir / name.replace('/', '--') / 'notes'
                if not notes_dir.is_dir():
                    continue
                store = NoteStore(notes_dir)
            for note in store.list(refresh=False):
                yield name, note

    def usage(self):
        """Per-account and per-video totals across the whole library -- see
        Editor.usage, which this mirrors for the library-wide `/api/usage` route."""
        from .editor import _account_key, _usage_totals
        has_accounts = bool(self.accounts)
        entries = ((_account_key(n.get('author'), has_accounts),
                   f'{proj}/{n["video"]}' if n.get('video') else None, n)
                  for proj, n in self.account_notes())
        return _usage_totals(entries)

    def admin_limits(self):
        """The library-wide default caps and, for every account, its own cap
        override and trailing-24h usage -- see Editor.check_note_cap and
        accounts.Accounts.get_limit -- for the admin-only /api/admin/limits
        route. [] accounts with no `--admin`, where there is nothing to list."""
        defaults = {'notes': self.account_daily_note_cap, 'cost_usd': self.account_daily_cost_cap_usd}
        if not self.accounts:
            return {'defaults': defaults, 'accounts': []}
        usage = self.usage()['accounts']
        accounts = []
        for info in self.accounts.list_accounts():
            totals = usage.get(info['name'], {}).get('last_24h', {'notes': 0, 'cost_usd': 0.0})
            accounts.append({**info, 'usage': {'notes': totals['notes'], 'cost_usd': totals['cost_usd']}})
        return {'defaults': defaults, 'accounts': accounts}

    def copied(self, source, name):
        if not valid_name(source) or not valid_name(name):
            raise ValueError('invalid repository name')
        if not self.has_main(source):
            raise ValueError('source has no main branch')
        source_path = self.path(source)
        sha = git(None, 'rev-parse', 'refs/heads/main', git_dir=source_path, hooks=False)
        tree = git(None, 'rev-parse', sha + '^{tree}', git_dir=source_path, hooks=False)
        target = self.create(name)
        env = {**os.environ, 'GIT_AUTHOR_NAME': 'Video Editor', 'GIT_AUTHOR_EMAIL': 'editor@example.com',
               'GIT_COMMITTER_NAME': 'Video Editor', 'GIT_COMMITTER_EMAIL': 'editor@example.com'}
        git(None, 'fetch', str(source_path), 'refs/heads/main:refs/vb-source', git_dir=target, hooks=False)
        try:
            commit = git(None, 'commit-tree', tree, input=f'New video from {source} ({sha})\n', env=env,
                        git_dir=target, hooks=False)
            git(None, 'update-ref', 'refs/heads/main', commit, git_dir=target, hooks=False)
        finally:
            git(None, 'update-ref', '-d', 'refs/vb-source', git_dir=target, hooks=False)
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
        film_blob = git(None, 'hash-object', '-w', '--stdin', input=film, git_dir=target, hooks=False)
        req_blob = git(None, 'hash-object', '-w', '--stdin', input=requirements, git_dir=target, hooks=False)
        tree_input = f'100644 blob {film_blob}\tfilm.py\n100644 blob {req_blob}\trequirements.txt\n'
        tree = git(None, 'mktree', input=tree_input, git_dir=target, hooks=False)
        commit = git(None, 'commit-tree', tree, input='Start a new video\n', env=env, git_dir=target, hooks=False)
        git(None, 'update-ref', 'refs/heads/main', commit, git_dir=target, hooks=False)
        return {'name': name, 'commit': commit, 'video': 'film'}

    def index(self, host, scheme='http', user=None):
        names = self.names()
        if self.accounts:
            names = [n for n in names if self.access.can_access(n, user, self.accounts)]
        return pages.index([(n, self.has_main(n)) for n in names], self.accounts is not None, user, host, scheme)

    def new_video_page(self, names=None):
        return pages.new_video_page(names if names is not None else self.names())

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
