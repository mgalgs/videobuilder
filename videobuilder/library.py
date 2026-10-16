"""Per-video bare repositories, managed by the `Library` class; the git smart
HTTP bridge and the library's HTML pages live in git_bridge.py and pages.py,
re-exported below so existing imports keep working."""
import os
from pathlib import Path
import re
import sys
import threading

from . import community, pages
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
                 compendium_for_builder=None, source_max_mb=None, source_max_total_mb=None,
                 capability_agent_extra_args=None):
        self.capabilities_dir = capabilities_dir
        self.capability_agent_extra_args = capability_agent_extra_args
        self.capability_fetch = True
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
                            compendium_for_builder=compendium_for_builder, source_max_mb=source_max_mb,
                            source_max_total_mb=source_max_total_mb)
        self.editors = {}
        self.lock = threading.RLock()
        from .accounts import Accounts
        from .access import Access
        self.accounts = Accounts(str(self.state_dir), admins) if admins else None
        self.access = Access(str(self.state_dir))
        self.community = community.Store(str(self.state_dir))

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

    def last_commit(self, name):
        """(unix seconds, subject) of main's newest commit, straight off the bare
        repo -- one cheap `git log`, cheap enough to run for every card when the
        library page is built. None without a main branch to read."""
        result = git(None, 'log', '-1', '--format=%ct%x1f%s', 'main',
                     git_dir=self.path(name), hooks=False, check=False)
        if result.returncode or not result.stdout.strip():
            return None
        ts, _, subject = result.stdout.strip().partition('\x1f')
        try:
            return int(ts), subject
        except ValueError:
            return None

    def create(self, name, allow_reserved=False):
        if not allow_reserved and community.is_reserved(name):
            raise ValueError('that name is reserved for capabilities')
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
                options = self.options
                if community.is_reserved(name):
                    # The capability pipeline is heavier than an ordinary note's (see
                    # community.capability_agent_args): this project's own Editor gets the
                    # heavier args instead of the library's ordinary --agent-extra-arg list.
                    agent = dict(options.get('agent') or {})
                    agent['extra_args'] = community.capability_agent_args(
                        agent.get('extra_args'), self.capability_agent_extra_args)
                    options = {**options, 'agent': agent}
                self.editors[name] = Editor(checkout, state_dir=self.state_dir / flat,
                                            sync_remote='origin', trust_repo_config=False,
                                            **options)
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

    def check_note_cap(self, author, is_admin):
        """Mirrors Editor.check_note_cap, for the library-wide capability-
        submission routes, which add a note before any per-project Editor
        is open: the same effective-cap logic (see editor._check_note_cap),
        over every project's notes in the library."""
        from .editor import _check_note_cap
        notes = (n for _, n in self.account_notes())
        _check_note_cap(self.accounts, notes, self.account_daily_note_cap,
                        self.account_daily_cost_cap_usd, author, is_admin)

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

    def copied(self, source, name, allow_reserved=False):
        if not valid_name(source) or not valid_name(name):
            raise ValueError('invalid repository name')
        if not self.has_main(source):
            raise ValueError('source has no main branch')
        source_path = self.path(source)
        sha = git(None, 'rev-parse', 'refs/heads/main', git_dir=source_path, hooks=False)
        tree = git(None, 'rev-parse', sha + '^{tree}', git_dir=source_path, hooks=False)
        target = self.create(name, allow_reserved=allow_reserved)
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

    def create_blank(self, name, allow_reserved=False):
        """A new repo at `name` (refusing an existing one, like `copied`) with
        one commit: the minimal film and requirements.txt a video needs to be
        built by the builder, pinned to this editor's own videobuilder
        version the way an existing video's requirements.txt pins one (see
        workers.pinned_version). Nothing film-specific: v1 is the builder's
        job."""
        from . import __version__
        target = self.create(name, allow_reserved=allow_reserved)
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

    def submit_capability(self, user, url, capture, files):
        """Step 1 of the capability-submission flow (POST /api/capabilities/new):
        validate the dialog's fields, enforce `user`'s daily note cap, and create
        the reserved `capabilities/<slug>` project and its draft record. `files`
        is how many files the browser is about to upload in step 2 (POST
        /v/capabilities/<slug>/api/attachments, the ordinary upload route); at
        least one of a URL or a file is required. Reading `url` (when the
        editor's fetch flag allows it) happens in this same method once
        xpost.py exists; until then it is accepted but never fetched, and the
        new draft's `post` stays null."""
        if not isinstance(files, int) or isinstance(files, bool) or files < 0:
            raise ValueError('files must be a non-negative integer')
        if url is not None and not isinstance(url, str):
            raise ValueError('url must be a string')
        if capture is not None and not isinstance(capture, str):
            raise ValueError('capture must be a string')
        if not (url and url.strip()) and files < 1:
            raise ValueError('give a URL or drop at least one file')
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        self.check_note_cap(user, is_admin)
        slug = community.new_slug()
        name = f'{community.NAMESPACE}/{slug}'
        result = self.create_blank(name, allow_reserved=True)
        if self.accounts:
            self.access.set_owner(name, user, self.accounts)
        self.community.create(slug, user, capture=(capture.strip() or None) if capture else None)
        return {'name': name, 'slug': slug, 'video': result['video'], 'attachments': [], 'read': None}

    def send_capability(self, user, slug, attachment_ids):
        """Step 3 (POST /api/capabilities/<slug>/send): creates the draft's
        first note from the brief (community.brief), attaching the record's
        fetched media -- dropping any that expired since step 1 (Attachments
        expires an unreferenced upload after 24h, see attachments.expire) --
        plus whatever ids `attachment_ids` names (the browser's own uploads
        from step 2). Raises KeyError for an unknown slug or for a caller who
        is neither the submitter nor an admin (so the route answers 404, like
        project access everywhere else); ValueError if this draft was already
        sent."""
        record = self.community.get(slug)
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        if record['submitter'] != user and not is_admin:
            raise KeyError(slug)
        if record.get('note'):
            raise ValueError('already sent to the builder')
        name = f'{community.NAMESPACE}/{slug}'
        editor = self.editor(name)
        vid = editor.project.videos()[0].id
        fetched = []
        for ident in record.get('fetched') or []:
            try:
                editor.attachments.get(ident, vid)
            except KeyError:
                continue  # expired since step 1: left out, not a failed send
            fetched.append(ident)
        ids = list(dict.fromkeys(fetched + list(attachment_ids or [])))
        text = community.brief(record.get('post'), record.get('capture'), bool(ids))
        note = editor.start_capability(text, ids, user, is_admin)
        self.community.set_note(slug, note['id'])
        return note

    def community_view(self, user):
        """The /capabilities page's community section for `user` (a signed-in
        username): whether they can submit one, whether they're an admin
        (who additionally gets Publish/Reject -- see community.py), whether
        the dialog's URL field should show at all, and the draft/published
        lists (added once the store holds more than bare records)."""
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        return {'published': [], 'drafts': [], 'can_submit': bool(user), 'is_admin': is_admin,
               'fetch': self.capability_fetch}

    def index(self, host, scheme='http', user=None):
        names = self.names()
        if self.accounts:
            names = [n for n in names if self.access.can_access(n, user, self.accounts)]
        from .capabilities import showcase_available
        entries = []
        for n in names:
            has_main = self.has_main(n)
            commit = self.last_commit(n) if has_main else None
            entries.append({'name': n, 'has_main': has_main,
                            'updated': commit[0] if commit else None,
                            'subject': commit[1] if commit else None})
        tour = bool(self.accounts and user and not self.accounts.tour_seen(user))
        return pages.index(entries, self.accounts is not None, user, host, scheme,
                           showcase=showcase_available(self.capabilities_dir), tour=tour)

    def new_video_page(self, names=None, user=None):
        return pages.new_video_page(names if names is not None else self.names(),
                                    user if self.accounts else None)

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
