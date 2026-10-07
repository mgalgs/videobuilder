"""Draft scope checks, isolated previews, and local-only git integration.

Every operation resolves a branch to an immutable commit before checking it.
Preview workers reuse preview.Session via stdin/stdout, never import draft
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
        with tempfile.TemporaryDirectory(dir=self.editor.state_dir) as home:
            env = child_environment(home)
            # -I ignores cwd, PYTHONPATH and user site packages. Only the installed
            # framework source is added explicitly, never the draft repository.
            source = str(Path(__file__).resolve().parent.parent)
            code = ('import sys; sys.path.insert(0, ' + repr(source) + '); '
                    'from videobuilder.drafts import worker; worker()')
            command = [sys.executable, '-I', '-c', code]
            wrapper = []
            if shutil.which('bwrap'):
                wrapper = ['bwrap', '--unshare-all', '--new-session', '--die-with-parent', '--tmpfs', '/tmp']
                for system in ('/usr', '/bin', '/lib', '/lib64', '/etc/fonts', '/etc/ld.so.cache'):
                    if os.path.exists(system):
                        wrapper += ['--ro-bind', system, system]
                for path in dict.fromkeys([sys.prefix, source, str(work)]):
                    wrapper += ['--ro-bind', path, path]
                wrapper += ['--bind', home, home, '--proc', '/proc', '--dev', '/dev']
                probe = subprocess.run([*wrapper, '/bin/true'], env=env, cwd=home,
                                       capture_output=True, timeout=10)
                if probe.returncode:
                    wrapper = []
            if not wrapper:
                if not self.editor.unsandboxed_previews:
                    raise ValueError('draft previews need a working bwrap; set unsandboxed_previews '
                                     'only where draft code may read everything the editor can')
                logging.warning('bwrap unavailable or unusable: draft preview is not sandboxed')
            command = wrapper + command
            payload = dict(path=str(work / context['film']), operation=operation, query=query)
            result = subprocess.run(command, input=json.dumps(payload).encode(), env=env,
                                    cwd=home, capture_output=True, timeout=60)
            if result.returncode:
                raise ValueError('draft preview failed: ' + result.stderr.decode(errors='replace'))
            return result.stdout

    def accept(self, video, author):
        e = self.editor
        with e.lock, e.notes.video_lock(video):
            self._idle(video)
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
                e.notes.resolve(video, branch, 'accepted', author)
                e.project.last.pop(video, None)
                return dict(state='accepted', commit=tip)
            finally:
                git(e.root, 'worktree', 'remove', '--force', str(work))

    def drop(self, video, author):
        e = self.editor
        with e.lock, e.notes.video_lock(video):
            self._idle(video)
            branch = e.notes.session(video)['draft']
            branch_tip(e.root, branch)
            for path in e.notes.session_dir(video).glob('preview-*'):
                git(e.root, 'worktree', 'remove', '--force', str(path))
            git(e.root, 'branch', '-D', branch)
            e.notes.resolve(video, branch, 'dropped', author)
            return dict(state='dropped')


def worker():
    from contextlib import redirect_stdout
    from .preview import Session
    request = json.load(sys.stdin)
    with redirect_stdout(sys.stderr):
        session = Session(request['path'])
        q = request['query']
        if request['operation'] == 'info':
            output = json.dumps(session.info()).encode()
        else:
            output = session.png(int(q.get('frame', 0)), q.get('format') or None,
                                 float(q.get('scale', 0.5)))
    sys.stdout.buffer.write(output)
