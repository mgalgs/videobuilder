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
import subprocess
import sys
import tempfile


def git(root, *args):
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=root,
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def branch_tip(root, branch):
    if not isinstance(branch, str) or branch == 'main':
        raise ValueError('draft must be a local branch other than main')
    git(root, 'check-ref-format', 'refs/heads/' + branch)
    return git(root, 'rev-parse', '--verify', 'refs/heads/' + branch)


PINS = ('requirements*.txt', 'requirements*.in', 'constraints*.txt', 'pyproject.toml',
        '*.lock', 'Pipfile*', 'setup.py', 'setup.cfg', 'package.json', 'package-lock.json',
        'npm-shrinkwrap.json', 'environment*.yml', 'environment*.yaml', '.gitmodules')


def inspect(root, branch, directory):
    tip = branch_tip(root, branch)
    base = git(root, 'merge-base', 'main', tip)
    raw = git(root, 'diff', '--raw', '-z', '--no-renames', base, tip)
    entries = raw.split('\0') if raw else []
    files, refused = [], []
    scope = PurePosixPath(directory)
    for i in range(0, len(entries) - 1, 2):
        meta, path = entries[i:i + 2]
        files.append(path)
        old, new = meta.split()[:2]
        reasons = []
        if scope != PurePosixPath('.') and not PurePosixPath(path).is_relative_to(scope):
            reasons.append('outside video directory')
        if any(fnmatch.fnmatch(PurePosixPath(path).name.lower(), pat.lower()) for pat in PINS):
            reasons.append('dependency pin or lockfile')
        if new == '120000':
            reasons.append('symlink')
        if '160000' in (old.lstrip(':'), new):
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


def child_environment(home):
    return {'PATH': os.defpath, 'HOME': str(home), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}


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

    def details(self, video):
        branch = self.editor.notes.session(video)['draft']
        if not branch:
            return None
        return inspect(self.editor.root, branch, self.context(video)['directory'])

    def _idle(self, video):
        if any(n['state'] not in ('replied', 'failed', 'accepted', 'dropped')
               for n in self.editor.notes.list(video, refresh=False)):
            raise ValueError('wait for queued and working notes before changing the draft')

    def _worktree(self, video, tip):
        root = self.editor.root
        path = self.editor.notes.session_dir(video) / ('preview-' + tip)
        if not path.exists():
            git(root, 'worktree', 'add', '--detach', str(path), tip)
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

    def accept(self, video, author):
        e = self.editor
        with e.lock, e.notes.video_lock(video):
            self._idle(video)
            if e.sync:
                e.sync.before_commit()
            branch = e.notes.session(video)['draft']
            detail = guarded(e.root, branch, self.context(video)['directory'])
            main = git(e.root, 'rev-parse', 'refs/heads/main')
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
                    previous = e.notes.list(video, refresh=False)[-1]
                    e.notes.add(video, previous['format'], previous['frame'], previous['segment'],
                                'rebase your draft onto main', e.notes.image(previous['id']),
                                author='editor', automatic=True)
                    return dict(state='rebase_requested', message='Rebase conflicted; queued a note to the agent.')
                tip = git(work, 'rev-parse', 'HEAD')
                # Validate the rebased result as well, before moving either ref.
                temp_branch = 'vb-accept/' + e.notes.session(video)['session']
                git(e.root, 'branch', temp_branch, tip)
                try:
                    guarded(e.root, temp_branch, self.context(video)['directory'])
                finally:
                    git(e.root, 'branch', '-D', temp_branch)
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
                e.notes.resolve(video, branch, 'accepted', author)
                e.project.last.pop(video, None)
                self._remove_previews(video)
                return dict(state='accepted', commit=tip)
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
