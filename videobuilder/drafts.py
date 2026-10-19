"""Draft scope checks, isolated previews, and local-only git integration.

Every operation resolves a branch to an immutable commit before checking it.
Preview workers use the shared persistent worker pool, never import draft
code into the editor. Without a usable bubblewrap, previews are refused unless
the editor opts in with unsandboxed_previews: environment scrubbing alone is
not a sandbox, and draft code could read any credential file the editor can.
"""
import fnmatch
import json
import logging
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile

from .gitutil import git
from . import pins


def branch_tip(root, branch):
    if not isinstance(branch, str) or branch == 'main':
        raise ValueError('draft must be a local branch other than main')
    git(root, 'check-ref-format', 'refs/heads/' + branch)
    return git(root, 'rev-parse', '--verify', 'refs/heads/' + branch)


PINS = ('requirements*.txt', 'requirements*.in', 'constraints*.txt', 'pyproject.toml',
        '*.lock', 'Pipfile*', 'setup.py', 'setup.cfg', 'package.json', 'package-lock.json',
        'npm-shrinkwrap.json', 'environment*.yml', 'environment*.yaml', '.gitmodules')


def _own_pin_path(directory):
    """The video's own requirements.txt, relative to the repo root (POSIX) --
    the path `workers.pin_for` resolves to for this video whenever it has a
    pin of its own, since pin_for always checks a video's own directory before
    walking up to a shared ancestor's. A pin only inherited from an ancestor
    never shows up at this path in the first place (it lives, and would
    change, somewhere outside this video's own directory instead), so this
    needs no filesystem lookup of its own: a changed path either is this
    video's own pin, or it isn't."""
    return str(PurePosixPath(directory) / 'requirements.txt') if directory != '.' else 'requirements.txt'


def _blob(root, rev, path):
    """`path`'s exact bytes at `rev`, or None if it doesn't exist there --
    `check=False` so gitutil.git returns the raw, unstripped subprocess result
    instead of raising or trimming whitespace that a byte-exact pin comparison
    can't afford to lose."""
    result = git(root, 'show', f'{rev}:{path}', check=False, binary=True)
    return None if result.returncode else result.stdout


def _kept_pin_raise(root, base, tip, path, ceiling):
    """Whether this pin's change from `base` to `tip` is exactly the edit
    `Versions.upgrade` itself would make: only its videobuilder line raised,
    to a version at most `ceiling`."""
    old, new = _blob(root, base, path), _blob(root, tip, path)
    if old is None or new is None:
        return False
    try:
        return pins.raised_only(old.decode(), new.decode(), ceiling) is not None
    except UnicodeDecodeError:
        return False


def inspect(root, branch, directory):
    from . import __version__
    tip = branch_tip(root, branch)
    base = git(root, 'merge-base', 'main', tip)
    raw = git(root, 'diff', '--raw', '-z', '--no-renames', base, tip)
    entries = raw.split('\0') if raw else []
    files, refused = [], []
    scope = PurePosixPath(directory)
    own_pin = _own_pin_path(directory)
    for i in range(0, len(entries) - 1, 2):
        meta, path = entries[i:i + 2]
        files.append(path)
        old_mode, new_mode = meta.split()[:2]
        reasons = []
        p = PurePosixPath(path)
        if scope != PurePosixPath('.') and not p.is_relative_to(scope):
            reasons.append('outside video directory')
        elif (p.relative_to(scope) if scope != PurePosixPath('.') else p).parts[:1] == ('sources',):
            # Never landed, even from inside the video's own directory: sources/ holds
            # hardlinks to creator-uploaded footage (see sources.py), not something a
            # builder commit should ever add, and the editor renders with the originals
            # there, not whatever a builder might have put in their place.
            reasons.append('source video, never committed')
        if any(fnmatch.fnmatch(PurePosixPath(path).name.lower(), pat.lower()) for pat in PINS):
            # A builder's own prompt (prompt.py) tells it to raise this exact pin when its
            # videobuilder is too old for a capability it needs -- the same move
            # POST /api/upgrade makes by hand. Let that specific edit through; anything
            # else touching a pin or lockfile still needs a person.
            kept = (path == own_pin and new_mode != '120000' and '160000' not in (old_mode.lstrip(':'), new_mode)
                    and _kept_pin_raise(root, base, tip, path, __version__))
            if not kept:
                reasons.append('dependency pin or lockfile (only raising the videobuilder '
                               f'version, up to {__version__}, is kept)')
        if new_mode == '120000':
            reasons.append('symlink')
        if '160000' in (old_mode.lstrip(':'), new_mode):
            reasons.append('submodule')
        if reasons:
            refused.append(path + ': ' + ', '.join(reasons))
    return dict(branch=branch, tip=tip, files=files, refused=refused,
                commits=git(root, 'log', '--format=%h %s', base + '..' + tip).splitlines())


def guarded(root, branch, directory):
    result = inspect(root, branch, directory)
    if result['refused']:
        raise ValueError('Draft refused:\n' + '\n'.join(result['refused']))
    return result


class Drafts:
    def __init__(self, editor):
        self.editor = editor

    def prune(self):
        if self.editor.project.git is None:
            return
        git(self.editor.root, "worktree", "prune")
        sessions = Path(self.editor.state_dir) / "sessions"
        for path in sessions.glob("*/preview-*"):
            try:
                git(self.editor.root, "worktree", "remove", "--force", str(path))
            except ValueError:
                shutil.rmtree(path)

    def _remove_previews(self, video):
        self.editor.pool.close_draft(video)
        for path in self.editor.notes.session_dir(video).glob("preview-*"):
            git(self.editor.root, "worktree", "remove", "--force", str(path))

    def context(self, video):
        film = os.path.relpath(self.editor.project.video(video).path, self.editor.root)
        return dict(project=self.editor.root, film=film, directory=str(PurePosixPath(film).parent))

    def _exists(self, branch):
        try:
            branch_tip(self.editor.root, branch)
            return True
        except ValueError:
            return False

    def details(self, video):
        branch = self.editor.notes.session(video)['draft']
        if not branch or not self._exists(branch):
            return None
        return inspect(self.editor.root, branch, self.context(video)['directory'])

    def _idle(self, video):
        if any(n['state'] not in ('replied', 'failed', 'accepted', 'dropped', 'questions')
               for n in self.editor.notes.list(video, refresh=False)):
            raise ValueError('wait for queued and working notes before changing the draft')

    def _worktree(self, video, tip):
        root = self.editor.root
        path = self.editor.notes.session_dir(video) / ('preview-' + tip)
        if not path.exists():
            git(root, 'worktree', 'add', '--detach', str(path), tip)
        self.editor.sources.sync(video, root=path)
        return path

    def preview(self, video, operation, query):
        with self.editor.notes.video_lock(video):
            context = self.context(video)
            branch = self.editor.notes.session(video)['draft']
            result = guarded(self.editor.root, branch, context['directory'])
            work = self._worktree(video, result['tip'])
        film = work / context['film']
        self.editor.pool.unsandboxed = self.editor.unsandboxed_previews
        worker = self.editor.pool.get(video, work, film, work, revision=result['tip'])
        if operation == 'info':
            return json.dumps(worker.request('info')).encode()
        return worker.request('frame', frame=int(query.get('frame', 0)),
                              format=query.get('format') or None, scale=float(query.get('scale', 0.5)))

    def before_submit(self, video, note, state):
        branch = state.get('draft')
        if not branch:
            return
        if not self._exists(branch):
            # A failed run can report a branch it never created; start from main.
            state['draft'] = None
            self.editor.notes.save_session(video, state)
            return
        root = self.editor.root
        tip = branch_tip(root, branch)
        main = git(root, 'rev-parse', 'main')
        if git(root, 'merge-base', tip, main) == tip:
            git(root, 'update-ref', 'refs/heads/' + branch, main, tip)

    def accept(self, video, author, note=None):
        e = self.editor
        auto = note is not None
        with e.lock, e.notes.video_lock(video):
            if not auto:
                self._idle(video)
            if e.sync:
                e.sync.before_commit()
            branch = e.notes.session(video)['draft']
            detail = inspect(e.root, branch, self.context(video)['directory'])
            if detail['refused']:
                if not auto:
                    raise ValueError('Draft refused:\n' + '\n'.join(detail['refused']))
                e.notes.update(note, state='refused', refused=detail['refused'])
                git(e.root, 'update-ref', 'refs/heads/' + branch, git(e.root, 'rev-parse', 'main'), detail['tip'])
                state = e.notes.session(video)
                # Each entry is already "path: reason(s)" (see inspect()); using the
                # reason inspect() actually computed, instead of a fixed "outside this
                # video" that's wrong for e.g. a sources/ file inside the video's own
                # directory, tells the next builder what to actually fix.
                state['rejection'] = ('Your previous change was not kept: it touched '
                                      + '; '.join(detail['refused']) + '.')
                e.notes.save_session(video, state)
                return {'state': 'refused', 'refused': detail['refused']}
            main = git(e.root, 'rev-parse', 'refs/heads/main')
            if detail['tip'] == main or git(e.root, 'merge-base', main, detail['tip']) == detail['tip']:
                if auto and detail['tip'] != main:
                    git(e.root, 'update-ref', 'refs/heads/' + branch, main, detail['tip'])
                return {'state': 'replied', 'commit': None}
            main_work = None
            for record in git(e.root, 'worktree', 'list', '--porcelain').split('\n\n'):
                lines = record.splitlines()
                if 'branch refs/heads/main' in lines:
                    main_work = lines[0].removeprefix('worktree ')
            if main_work and git(main_work, 'status', '--porcelain'):
                raise ValueError('main checkout has local changes; commit or stash them before Accept')
            work = e.notes.session_dir(video) / 'accept-work'
            git(e.root, 'worktree', 'add', '--detach', str(work), detail['tip'])
            try:
                try:
                    git(work, 'rebase', main)
                except ValueError:
                    git(work, 'rebase', '--abort')
                    if auto and note.get('automatic'):
                        original = e.notes.get(note['retry_for'])
                        e.notes.update(original, state='conflict',
                                      message='Draft still conflicts with main after one automatic rebase request.')
                        e.notes.update(note, state='conflict', message=original['message'])
                        return {'state': 'conflict', 'message': original['message']}
                    previous = note if auto else e.notes.list(video, refresh=False)[-1]
                    retry = e.notes.add(video, previous['format'], previous['frame'], previous['segment'],
                                        'rebase your draft onto main',
                                        e.notes.image(previous['id']) if previous.get('frame') is not None else None,
                                        author='editor', automatic=True,
                                        retry_for=note['id'] if auto else None)
                    return dict(state='rebase_requested', message='Rebase conflicted; queued a note to the agent.')
                tip = git(work, 'rev-parse', 'HEAD')
                temp_branch = 'vb-accept/' + e.notes.session(video)['session']
                git(e.root, 'branch', temp_branch, tip)
                try:
                    guarded(e.root, temp_branch, self.context(video)['directory'])
                finally:
                    git(e.root, 'branch', '-D', temp_branch)
                if auto:
                    summary = next((x.split(':', 1)[1].strip() for x in reversed((note.get('reply') or '').splitlines())
                                    if x.startswith('Summary: ') and x.split(':', 1)[1].strip()), None)
                    summary = summary or git(work, 'show', '-s', '--format=%s', 'HEAD')
                    builder = git(work, 'show', '-s', '--format=%an <%ae>', 'HEAD')
                    git(work, 'reset', '--soft', main)
                    git(work, 'commit', '--author', builder, '-m',
                        f'{summary}\n\nVersion-kind: builder\nNote: {note["id"]}\nDirected-by: {note.get("author") or "anonymous"}')
                    tip = git(work, 'rev-parse', 'HEAD')
                if git(e.root, 'rev-parse', 'refs/heads/main') != main:
                    raise ValueError('main moved during Accept; retry')
                if main_work:
                    if git(main_work, 'status', '--porcelain'):
                        raise ValueError('main checkout has local changes; retry after saving them')
                    git(main_work, 'merge', '--ff-only', tip)
                else:
                    git(e.root, 'update-ref', 'refs/heads/main', tip, main)
                git(e.root, 'update-ref', 'refs/heads/' + branch, tip, detail['tip'])
                if e.sync:
                    e.sync.after_commit()
                if auto:
                    e.notes.update(note, state='landed', version={'n': e.versions.number(tip), 'commit': tip})
                    if note.get('retry_for'):
                        original = e.notes.get(note['retry_for'])
                        e.notes.update(original, state='landed', version=note['version'])
                else:
                    e.notes.resolve(video, branch, 'accepted', author)
                e.project.last.pop(video, None)
                self._remove_previews(video)
                e.render_first(video, tip)
                return dict(state='landed' if auto else 'accepted', commit=tip)
            finally:
                git(e.root, 'worktree', 'remove', '--force', str(work))

    def drop(self, video, author):
        e = self.editor
        with e.lock, e.notes.video_lock(video):
            self._idle(video)
            branch = e.notes.session(video)['draft']
            branch_tip(e.root, branch)
            self._remove_previews(video)
            git(e.root, 'branch', '-D', branch)
            e.notes.resolve(video, branch, 'dropped', author)
            return dict(state='dropped')
