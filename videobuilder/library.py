"""Per-video bare repositories, managed by the `Library` class; the git smart
HTTP bridge and the library's HTML pages live in git_bridge.py and pages.py,
re-exported below so existing imports keep working."""
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time

from . import community, pages
from .gitutil import git
from .git_bridge import git_route, serve_git, _copy_body
from .pages import signin_page, signup_page


PART = re.compile(r'[a-z0-9][a-z0-9._-]{0,62}\Z')
# versions.history also matches this subject, for blank videos made before
# the commit carried a Version-kind trailer.
BLANK_SUMMARY = 'Start a new video'
# A non-X capability link is read synchronously inside the request, like xpost.read_post (60s/15s).
CAPABILITY_PAGE_BUDGET = 30
CAPABILITY_PAGE_TIMEOUT = 15
# A deleted video waits this long in <root>/trash before purge_trash removes it for good.
TRASH_DAYS = 30
TRASH_STAMP = '%Y%m%dT%H%M%SZ'
# purge_trash runs from tick, every few seconds: it looks at the trash at most this often.
PURGE_EVERY = 60 * 60


def valid_name(name):
    return (isinstance(name, str) and len(name.split('/')) in (1, 2) and
            all(PART.fullmatch(p) and not p.endswith('.git') and '..' not in p for p in name.split('/')))


class Library:
    def __init__(self, root, checkouts=None, state_dir=None, host='127.0.0.1', allowed_hosts=(),
                 backend=None, agent=None, unsandboxed_previews=False, envs=None, admins=(), capabilities_dir=None,
                 compendium_dir=None, music_sources=None, account_daily_note_cap=None, account_daily_cost_cap_usd=None,
                 compendium_for_builder=None, source_max_mb=None, source_max_total_mb=None,
                 capability_agent_extra_args=None, capability_fetch=True, artbox_url=None,
                 account_daily_picture_cap=None, whats_new_repo=None, whats_new_videos=True, suggest_url=None,
                 suggest_model=None):
        self.capabilities_dir = capabilities_dir
        self.capability_agent_extra_args = capability_agent_extra_args
        self.capability_fetch = capability_fetch
        self.compendium_dir = compendium_dir
        self.root = Path(root).resolve()
        self.repos = self.root / 'repos'
        # Deleted videos (see delete): beside repos/, never in it, so names() can't list one.
        self.trash = self.root / 'trash'
        self._purged_at = 0
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
        # Also a plain attribute (not just in `options`, which only Editor() below reads):
        # New video's suggest catalog (handler_library.py) needs it with no project open yet.
        self.music = music
        from .pictures import Artbox
        artbox = Artbox(artbox_url) if artbox_url else None
        # Built once here, shared by every project's Editor (unlike Pictures/Artbox, the
        # whole feature is shared -- see suggest.py) and reachable library-wide for New
        # video's "In a few words", asked before any project exists (see handler_library.py).
        self.suggest = None
        if suggest_url:
            key = os.environ.get('VIDEOBUILDER_SUGGEST_KEY')
            if key:
                from .suggest import Suggest
                from .suggest_client import SuggestClient
                client = SuggestClient(suggest_url, suggest_model, key)
                self.suggest = Suggest(str(self.state_dir), client, music=music, has_accounts=bool(admins))
            else:
                print('[editor] --suggest-url is set but $VIDEOBUILDER_SUGGEST_KEY is not; '
                     'suggestions stay off', file=sys.stderr, flush=True)
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
                            source_max_total_mb=source_max_total_mb, artbox=artbox, suggest=self.suggest,
                            account_daily_picture_cap=account_daily_picture_cap)
        self.editors = {}
        self.lock = threading.RLock()
        from .accounts import Accounts
        from .access import Access
        self.accounts = Accounts(str(self.state_dir), admins) if admins else None
        self.access = Access(str(self.state_dir))
        self.community = community.Store(str(self.state_dir))
        from .whats_new import DEFAULT_REPO, WhatsNew
        self.whats_new = WhatsNew(self.state_dir, repo=whats_new_repo or DEFAULT_REPO,
                                  remote_videos=whats_new_videos)

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
        # A deleted video's notes still count against its authors' caps (see delete).
        for entry, name in self._trashed():
            notes_dir = entry / 'state' / 'notes'
            if notes_dir.is_dir():
                for note in NoteStore(notes_dir).list(refresh=False):
                    yield name, note

    def _trashed(self):
        """(directory, video name) for every deleted video still in the trash."""
        if not self.trash.is_dir():
            return
        for entry in sorted(self.trash.iterdir()):
            try:
                name = json.loads((entry / 'deleted.json').read_text(encoding='utf-8'))['name']
            except (OSError, ValueError, KeyError, TypeError):
                name = entry.name.rsplit('--', 1)[0].replace('--', '/')
            yield entry, name

    def can_delete(self, name, user):
        """The video's owner or an admin; anyone at all with accounts off."""
        if not self.accounts:
            return True
        if user is None:
            return False
        return self.accounts.is_admin(user) or self.access.get(name, self.accounts)['owner'] == user

    def delete(self, name, user):
        """Moves `name`'s bare repo, checkout and state dir into a new
        <root>/trash/<flat name>--<UTC stamp>/ (as repo.git, checkout and
        state, beside a deleted.json saying whose it was and who deleted it)
        and drops its access record, so the name is free at once and reads
        like one that never existed. purge_trash removes the entry for good
        after TRASH_DAYS. Shuts the video's open Editor down first. KeyError
        for no such video; HTTPError 403 for a capability's name or a caller
        who is neither the owner nor an admin, 409 while a note is still
        being built."""
        from .editor import HTTPError
        from .notes import NoteStore
        repo = self.path(name)
        flat = name.replace('/', '--')
        with self.lock:
            if not repo.is_dir():
                raise KeyError(name)
            if community.is_reserved(name):
                raise HTTPError(403, 'A capability cannot be deleted here.')
            if not self.can_delete(name, user):
                raise HTTPError(403, 'Only the owner of this video can delete it.')
            editor = self.editors.get(name)
            notes_dir = self.state_dir / flat / 'notes'
            store = editor.notes if editor else NoteStore(notes_dir) if notes_dir.is_dir() else None
            if store and store.pending():
                raise HTTPError(409, 'A note is still being built. Wait for it to finish, then delete.')
            if editor:
                del self.editors[name]
                editor.renders.close()
                editor.pool.close()
            now = datetime.datetime.now(datetime.timezone.utc)
            stamp = now.strftime(TRASH_STAMP)
            entry = self.trash / f'{flat}--{stamp}'
            n = 2
            while entry.exists():
                entry = self.trash / f'{flat}--{stamp}.{n}'
                n += 1
            entry.mkdir(parents=True)
            record = self.access.get(name, self.accounts) if self.accounts else {'owner': None, 'collaborators': []}
            (entry / 'deleted.json').write_text(json.dumps({
                'name': name, 'owner': record['owner'], 'collaborators': record['collaborators'],
                'deleted_by': user, 'deleted_at': now.isoformat(timespec='seconds'),
                'access': self.access.drop(name)}, indent=2) + '\n', encoding='utf-8')
            # The repo first: once it is gone, so is the name.
            for source, target in ((repo, 'repo.git'), (self.checkouts / flat, 'checkout'),
                                   (self.state_dir / flat, 'state')):
                if source.exists():
                    shutil.move(str(source), str(entry / target))
        return {'deleted': name}

    def purge_trash(self, force=False):
        """Removes trash entries more than TRASH_DAYS old, judged by the stamp in
        each one's name -- at most once every PURGE_EVERY unless `force`."""
        now = time.time()
        if not force and now - self._purged_at < PURGE_EVERY:
            return
        self._purged_at = now
        if not self.trash.is_dir():
            return
        cutoff = datetime.datetime.fromtimestamp(now - TRASH_DAYS * 86400, datetime.timezone.utc)
        for entry in self.trash.iterdir():
            try:
                stamp = datetime.datetime.strptime(entry.name.rsplit('--', 1)[1][:16], TRASH_STAMP)
            except (IndexError, ValueError):
                continue
            if stamp.replace(tzinfo=datetime.timezone.utc) < cutoff:
                shutil.rmtree(entry, ignore_errors=True)

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
        Editor.usage, which this mirrors for the library-wide `/api/usage` route,
        including the per-account `suggest` totals when a model is configured."""
        from .editor import _account_key, _usage_totals
        has_accounts = bool(self.accounts)
        entries = ((_account_key(n.get('author'), has_accounts),
                   f'{proj}/{n["video"]}' if n.get('video') else None, n)
                  for proj, n in self.account_notes())
        totals = _usage_totals(entries)
        if self.suggest:
            totals['suggest'] = self.suggest.usage_totals()
        return totals

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
        commit = git(None, 'commit-tree', tree, input=f'{BLANK_SUMMARY}\n\nVersion-kind: blank\n', env=env,
                     git_dir=target, hooks=False)
        git(None, 'update-ref', 'refs/heads/main', commit, git_dir=target, hooks=False)
        return {'name': name, 'commit': commit, 'video': 'film'}

    def reserve_capability_slot(self, author, is_admin):
        """Holds one of `author`'s next community.CAPABILITY_DAILY_CAP
        submission slots for the duration of a new capability's create-
        project-and-maybe-read-a-post work (HTTPError 429 once already at
        the cap; a no-op returning None for an admin, who is exempt).
        Unlike a plain count check, this is atomic with every other
        concurrent reservation (community.Store.reserve, under its lock),
        so N simultaneous submissions from the same account can't all pass
        before any of them has a record for a count to see -- at most
        CAPABILITY_DAILY_CAP can hold a slot at once. Pair with
        release_capability_slot when the attempt finishes, successfully or
        not."""
        if is_admin:
            return None
        from .editor import HTTPError
        cutoff = time.time() - 24 * 60 * 60
        token = self.community.reserve(author, community.CAPABILITY_DAILY_CAP, cutoff)
        if token is None:
            raise HTTPError(429, f"You've submitted {community.CAPABILITY_DAILY_CAP} capabilities today. "
                            "Try again tomorrow.")
        return token

    def release_capability_slot(self, token):
        """Releases a reservation made by reserve_capability_slot; a no-op
        for the admin case (token is None)."""
        if token is not None:
            self.community.release(token)

    def submit_capability(self, user, url, capture, files, family=None):
        """Step 1 of the capability-submission flow (POST /api/capabilities/new):
        validate the dialog's fields, enforce `user`'s daily caps (both the
        capability-submission cap and the ordinary note cap), and create the
        reserved `capabilities/<slug>` project and its draft record. `files`
        is how many files the browser is about to upload in step 2 (POST
        /v/capabilities/<slug>/api/attachments, the ordinary upload route); at
        least one of a URL or a file is required. The capability-submission
        slot (reserve_capability_slot) is held for the whole of this call and
        released in a `finally`, so concurrent calls from the same account
        can't all pass the cap before any of them has a record of its own to
        be counted; a failed attempt (any exception, including FailedRead)
        releases its slot rather than spending it.

        When `url` is given and self.capability_fetch is on, it is read right
        here before anything is created: an X post URL (xpost.parse_url) by
        xpost.read_post, any other link as that one page only through
        gather.crawl (guarded, no link-following, no video download). A
        malformed URL raises ValueError (400, no network call ever made --
        community.check_link refuses it first); a URL that reads but fails
        raises FailedRead (422) only when there are no files either -- with
        files given, the project is still created and the failure is reported
        back as `read.error` instead. Fetched media (or a page's text and
        screenshots, via gather.write_attachments) is uploaded as this draft's
        first attachments.
        When fetching is off, `url` is accepted but never read, and the new
        draft's `post` stays null.

        `family`: None for "A new capability", or a catalog family's id
        ('looks', for "A new look"), checked by community.check_family
        (ValueError, 400) before anything else happens; it decides the brief
        the draft is sent with and what its files must be to publish."""
        if not isinstance(files, int) or isinstance(files, bool) or files < 0:
            raise ValueError('files must be a non-negative integer')
        if url is not None and not isinstance(url, str):
            raise ValueError('url must be a string')
        if capture is not None and not isinstance(capture, str):
            raise ValueError('capture must be a string')
        url = url.strip() if url else None
        if not url and files < 1:
            raise ValueError('give a URL or drop at least one file')
        family = community.check_family(family)
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        token = self.reserve_capability_slot(user, is_admin)
        try:
            self.check_note_cap(user, is_admin)
            read = post = None
            media = []
            page = None
            if url and self.capability_fetch:
                from . import xpost
                try:
                    xpost.parse_url(url)
                    is_x = True
                except ValueError:
                    is_x = False
                if is_x:
                    result = xpost.read_post(url)
                    ok = result.ok
                    if result.text or result.handle:
                        post = {'url': url, 'handle': result.handle, 'text': result.text}
                    media = result.media
                else:
                    community.check_link(url)  # malformed -> ValueError (400), before any network call
                    from . import gather
                    crawled, _ = gather.crawl([url], max_pages=1, time_budget=CAPABILITY_PAGE_BUDGET,
                                              page_timeout=CAPABILITY_PAGE_TIMEOUT)
                    ok = bool(crawled)
                    if crawled:
                        page = crawled[0]
                        post = community.page_record(page)
                read = {'error': None if ok else community.READ_FAILED}
                if not ok and files < 1:
                    raise community.FailedRead(community.READ_FAILED)
            slug = community.new_slug()
            name = f'{community.NAMESPACE}/{slug}'
            result = self.create_blank(name, allow_reserved=True)
            if self.accounts:
                self.access.set_owner(name, user, self.accounts)
            fetched_ids = []
            if media:
                editor = self.editor(name)
                vid = editor.project.videos()[0].id
                for media_name, ctype, data in media:
                    # xpost's own video cap (50 MB) is above the attachment store's
                    # default per-file cap (25 MiB): raise it here the same way
                    # gather.write_attachments does, rather than silently dropping a
                    # fetched clip that read_post already reported as fetched.
                    oversize = len(data) > editor.attachments.max_file
                    try:
                        record = editor.attachments.upload(vid, media_name, ctype, data, allow_oversize=oversize)
                    except ValueError:
                        continue
                    fetched_ids.append(record['id'])
            if page:
                from . import gather
                editor = self.editor(name)
                vid = editor.project.videos()[0].id
                # The dropped files arrive in step 2 and share this first note's budget.
                fetched_ids += gather.write_attachments(editor.attachments, vid, [page], [], reserved_files=files,
                                                        max_files=editor.attachments.start_video_max_files,
                                                        max_message=editor.attachments.start_video_max_message)
            self.community.create(slug, user, post=post, capture=(capture.strip() or None) if capture else None,
                                  fetched=fetched_ids, family=family)
        finally:
            self.release_capability_slot(token)
        return {'name': name, 'slug': slug, 'video': result['video'], 'attachments': fetched_ids, 'read': read}

    def send_capability(self, user, slug, attachment_ids):
        """Step 3 (POST /api/capabilities/<slug>/send): creates the draft's
        first note from the brief (community.brief), attaching the record's
        fetched media -- dropping any that expired since step 1 (Attachments
        expires an unreferenced upload after 24h, see attachments.expire) --
        plus whatever ids `attachment_ids` names (the browser's own uploads
        from step 2). Raises KeyError for an unknown slug or for a caller who
        is neither the submitter nor an admin (so the route answers 404, like
        project access everywhere else); ValueError if this draft was already
        sent, or is being sent by a concurrent call right now (claim_send --
        so two near-simultaneous sends can produce at most one note, the
        second always getting back "already sent to the builder"). The note
        is always authored as the submitter and checked against the
        submitter's own daily cap, even when an admin is the one calling
        this on someone else's unsent draft. A claim left by an attempt that
        fails before producing a note (e.g. the note cap) is released so a
        retry isn't blocked forever."""
        record = self.community.get(slug)
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        if record['submitter'] != user and not is_admin:
            raise KeyError(slug)
        submitter = record['submitter']
        submitter_is_admin = bool(self.accounts and self.accounts.is_admin(submitter))
        self.community.claim_send(slug)
        try:
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
            # A retry from the draft card's own "Send to the builder" button (as opposed to
            # the submission dialog that just uploaded them) has no memory of what the
            # browser uploaded in step 2: recover anything still sitting on this video, not
            # just whatever ids the caller happened to name.
            uploaded = editor.attachments.uploaded_for(vid)
            ids = list(dict.fromkeys(fetched + uploaded + list(attachment_ids or [])))
            text = community.brief(record.get('post'), record.get('capture'), bool(ids), family=record.get('family'))
            # Charged to the submitter even when an admin is the one clicking "Send to the
            # builder" on someone else's interrupted draft (capabilities.py's draft card
            # shows that button to admins too) -- an admin sending on another user's behalf
            # must not author the note as themselves or skip that user's own daily cap.
            note = editor.start_capability(text, ids, submitter, submitter_is_admin)
        except Exception:
            self.community.release_send(slug)
            raise
        self.community.set_note(slug, note['id'])
        return note

    def _capability_status(self, slug, claimed_ids, ref='main'):
        """(entry, None) if `slug`'s capability.toml at `ref` validates right
        now, else (None, problem) with community.Invalid's plain message.
        `ref` is 'main' for a live preview (publishing, a brand new draft) or
        a pinned commit sha to check exactly what a published capability
        currently shows everyone else (see community.load). `claimed_ids`:
        ids already claimed by other currently-valid published capabilities
        (see _published_ids) -- an id clash counts as invalid here too, for
        whichever one is checked second."""
        read = community.load(self.path(f'{community.NAMESPACE}/{slug}'), ref=ref)
        family = self.community.all().get(slug, {}).get('family')
        try:
            return community.validate(read, claimed_ids, expected_family=family), None
        except community.Invalid as exc:
            return None, str(exc)

    def _published_ids(self, exclude_slug=None):
        """The catalog ids claimed by every currently-valid published
        capability other than `exclude_slug`, re-validated at its own pinned
        commit, in publish order so the one published first keeps a
        clashing id (see community.validate's published_ids parameter)."""
        records = self.community.all()
        order = sorted((slug for slug, r in records.items()
                        if r['status'] == 'published' and slug != exclude_slug),
                       key=lambda slug: records[slug]['published_at'] or 0)
        claimed = set()
        for slug in order:
            entry, _ = self._capability_status(slug, claimed, ref=records[slug]['pinned_sha'])
            if entry:
                claimed.add(entry['id'])
        return claimed

    def _capability_available(self, slug, ref):
        """Whether `slug`'s project has a finished render for `ref` (its
        pinned commit) -- for community_view's `available`, which decides
        whether a published card shows a player or the same "clip not
        built" placeholder an unbuilt catalog card shows (see
        capabilities.page_html)."""
        from .thumbnails import latest_render
        name = f'{community.NAMESPACE}/{slug}'
        return latest_render(self.state_dir / name.replace('/', '--'), self.path(name), ref=ref) is not None

    def community_view(self, user):
        """The /capabilities page's community section for `user` (a signed-in
        username, or None): whether they can submit one, whether they're an
        admin (who additionally gets Publish/Reject -- see community.py),
        whether the dialog's URL field should show at all, the currently-
        valid published capabilities (grouped into the fixed catalog's
        categories by the page itself), and the drafts `user` may see --
        their own plus, for an admin, everyone's, always excluding rejected
        ones (on nobody's page) and a published one that still validates
        (shown in the grid instead, not here). A published capability shows
        exactly its pinned commit (see publish_capability) -- a published
        entry's `available` is whether that pinned commit has a finished
        render yet, and its `pending_update` (shown only to the submitter and
        admins) is whether the project's main has moved past the pin since,
        awaiting an admin's Publish or Reject. A published capability whose
        *pinned* commit has gone invalid (e.g. an id now clashing with
        another capability published first) shows up in drafts instead, with
        its `problem` set, for its owner and admins to fix."""
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        records = self.community.all()
        published_slugs = sorted((slug for slug, r in records.items() if r['status'] == 'published'),
                                 key=lambda slug: records[slug]['published_at'] or 0)
        published, claimed, broken = [], set(), {}
        for slug in published_slugs:
            record = records[slug]
            pin = record['pinned_sha']
            entry, problem = self._capability_status(slug, claimed, ref=pin)
            if entry:
                claimed.add(entry['id'])
                tip = community.main_sha(self.path(f'{community.NAMESPACE}/{slug}'))
                can_see_update = user == record['submitter'] or is_admin
                pending_update = bool(can_see_update and tip and tip != pin and tip != record['update_rejected_sha'])
                published.append({'slug': slug, **entry, 'available': self._capability_available(slug, pin),
                                  'pending_update': pending_update})
            else:
                broken[slug] = problem
        drafts = []
        if user:
            for slug, record in records.items():
                if record['status'] == 'rejected':
                    continue
                if record['status'] == 'published' and slug not in broken:
                    continue
                if record['submitter'] != user and not is_admin:
                    continue
                title = community.try_title(community.load(self.path(f'{community.NAMESPACE}/{slug}')))
                drafts.append({'slug': slug, 'status': record['status'], 'submitter': record['submitter'],
                              'sent': bool(record['note']), 'problem': broken.get(slug), 'title': title})
            drafts.sort(key=lambda d: records[d['slug']]['created'])
        return {'published': published, 'drafts': drafts, 'can_submit': bool(user), 'is_admin': is_admin,
               'fetch': self.capability_fetch}

    def publish_capability(self, admin, slug):
        """Publishes `slug` (POST /api/capabilities/<slug>/publish), pinning
        it to the project's main right now: KeyError for an unknown slug
        (the route answers 404); community.Invalid for one that doesn't
        validate right now (the route answers 400 with its plain message,
        and the status/pin are left unchanged); otherwise it is validated
        against every other currently-valid published capability's own
        pinned id (the one published first keeps a clashing id), then marked
        published and pinned to that exact commit. Works the same way for a
        brand new draft and for approving a pending update on an
        already-published capability -- either way, everyone else sees
        nothing different until this call succeeds."""
        self.community.get(slug)
        claimed = self._published_ids(exclude_slug=slug)
        repo_path = self.path(f'{community.NAMESPACE}/{slug}')
        sha = community.main_sha(repo_path)
        if sha is None:
            raise community.Invalid('this project has no commits yet')
        read = community.load(repo_path, ref=sha)
        community.validate(read, claimed, expected_family=self.community.get(slug).get('family'))
        return self.community.publish(slug, admin, sha)

    def reject_capability(self, admin, slug, update=False):
        """Rejects `slug` (POST /api/capabilities/<slug>/reject): KeyError
        for an unknown slug. By default a full takedown: hides `slug` from
        every /capabilities page and its clip route, without touching the
        project on disk (ValueError for one that is neither 'draft' nor
        'published'). With `update`, only discards a published capability's
        pending update (community.Store.reject_update) and leaves the pinned
        version published; ValueError when no update is pending.

        The takedown must never depend on the state of main: if it did, a
        submitter who pushes a fresh commit before each Reject would keep
        turning the takedown into another discarded update."""
        record = self.community.get(slug)
        if not update:
            return self.community.reject(slug, admin)
        tip = (community.main_sha(self.path(f'{community.NAMESPACE}/{slug}'))
               if record['status'] == 'published' else None)
        if not tip or tip in (record['pinned_sha'], record['update_rejected_sha']):
            raise ValueError('there is no pending update to discard')
        return self.community.reject_update(slug, admin, tip)

    def community_for_builder(self):
        """Every published, currently-valid community capability, with its
        doc and film.py bytes already read off its pinned commit, oldest-
        published first -- for an Editor's notes.NoteStore to stage under a
        note's /attachments and list in the builder's prompt (see
        notes._stage_community, prompt.render's community section). []
        with nothing published, or nothing currently valid at its pin."""
        records = self.community.all()
        order = sorted((slug for slug, r in records.items() if r['status'] == 'published'),
                       key=lambda slug: records[slug]['published_at'] or 0)
        out, claimed = [], set()
        for slug in order:
            pin = records[slug]['pinned_sha']
            entry, _ = self._capability_status(slug, claimed, ref=pin)
            if not entry:
                continue
            claimed.add(entry['id'])
            read = community.load(self.path(f'{community.NAMESPACE}/{slug}'), ref=pin)
            doc_bytes, film_bytes = read(entry['doc']), read(community.FILM_PATH)
            member = community.MEMBER_PATHS.get(entry['family'])
            member_bytes = read(member) if member else None
            if doc_bytes is None or film_bytes is None or (member and member_bytes is None):
                continue  # vanished between validate() and this read: treat like invalid
            item = {'slug': slug, 'id': entry['id'], 'title': entry['title'], 'card': entry['card'],
                    'family': entry['family'], 'doc_bytes': doc_bytes, 'film_bytes': film_bytes}
            if member:
                item['member'] = (member, member_bytes)   # a look's look.py, staged beside its film
            out.append(item)
        return out

    def community_clip(self, slug, kind, user):
        """Bytes for /capabilities/community/<slug>.(mp4|jpg): KeyError (the
        route answers 404) for an unknown slug, a draft or rejected
        capability `user` may not see (anyone but its submitter and admins),
        a published capability whose pinned commit has gone invalid since
        (served only to its submitter and admins, consistent with the grid
        -- see community_view), or one with no render yet at its pin. The
        submitter and admins always see the pinned commit too -- the project
        page (/v/capabilities/<slug>/) is where they preview an unapproved
        update, not this route."""
        record = self.community.get(slug)
        is_admin = bool(self.accounts and self.accounts.is_admin(user))
        is_owner = record['submitter'] == user or is_admin
        if record['status'] != 'published' and not is_owner:
            raise KeyError(slug)
        ref = record['pinned_sha'] or 'main'
        if record['status'] == 'published' and not is_owner:
            entry, _ = self._capability_status(slug, self._published_ids(exclude_slug=slug), ref=ref)
            if entry is None:
                raise KeyError(slug)
        name = f'{community.NAMESPACE}/{slug}'
        state_dir = self.state_dir / name.replace('/', '--')
        repo_path = self.path(name)
        if kind == 'jpg':
            from .thumbnails import AMBIGUOUS, from_state_dir
            data = from_state_dir(state_dir, repo_path, ref=ref)
            if data is None or data is AMBIGUOUS:
                raise KeyError(slug)
            return data
        from .thumbnails import latest_render
        path = latest_render(state_dir, repo_path, ref=ref)
        if path is None:
            raise KeyError(slug)
        return path.read_bytes()

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
                           showcase=showcase_available(self.capabilities_dir), tour=tour,
                           whats_new=self.whats_new.newest_key())

    def new_video_page(self, names=None, user=None):
        return pages.new_video_page(names if names is not None else self.names(),
                                    user if self.accounts else None, whats_new=self.whats_new.newest_key())

    def tick(self):
        """Advance unfinished notes in every repo, opening an editor only where one is pending."""
        from .notes import NoteStore
        try:
            self.purge_trash()
        except Exception as e:
            print(f'[editor] trash purge failed: {e}', file=sys.stderr, flush=True)
        for name in self.names():
            if name not in self.editors:
                notes = self.state_dir / name.replace('/', '--') / 'notes'
                if not notes.is_dir() or not NoteStore(notes).pending():
                    continue
            try:
                self.editor(name).notes.tick()
            except Exception as e:
                print(f'[editor] {name}: note poll failed: {e}', file=sys.stderr, flush=True)

    def picture_dirs(self):
        """Every project's pictures dir, open or not, deleted ones still in the
        trash included, for the daily picture cap (see
        pictures.Pictures.check_daily_cap), which spans the whole library."""
        return ([self.state_dir / name.replace('/', '--') / 'pictures' for name in self.names()] +
                [entry / 'state' / 'pictures' for entry, _ in self._trashed()])

    def tick_pictures(self):
        """Poll generated pictures in every repo, opening an editor only where a
        set is still on the way -- which is also how they resume after a restart."""
        from .pictures import has_pending
        if not self.options.get('artbox'):
            return
        for name in self.names():
            if name not in self.editors:
                folder = self.state_dir / name.replace('/', '--') / 'pictures'
                if not folder.is_dir() or not has_pending(folder):
                    continue
            try:
                self.editor(name).pictures.tick()
            except Exception as e:
                print(f'[editor] {name}: picture poll failed: {e}', file=sys.stderr, flush=True)

    def close(self):
        for editor in self.editors.values():
            editor.renders.close()
            editor.pool.close()
