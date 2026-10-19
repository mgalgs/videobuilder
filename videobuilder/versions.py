"""First-parent video versions and content-preserving restore commits."""
import os
from pathlib import Path, PurePosixPath
import subprocess

from .drafts import git
from .library import BLANK_SUMMARY
from .notes import FINAL
from . import pins
from .workers import pin_for, pinned_version


# The director is offered an upgrade only below this pin. Raise it when a release
# fixes rendering for videos already pinned; POST /api/upgrade still works above it.
MIN_PIN = '0.1.23'


class Refused(ValueError):
    """A request that cannot be done in the video's current state (409)."""


def trailers(message):
    out = {}
    for line in message.splitlines():
        key, sep, value = line.partition(': ')
        if sep and key in ('Version-kind', 'Directed-by', 'Note', 'Restores'):
            out[key] = value
    return out


class Versions:
    def __init__(self, editor):
        self.editor = editor

    def history(self, video, limit=50, before=None):
        if not 1 <= limit <= 200:
            raise ValueError('limit must be between 1 and 200')
        root = self.editor.root
        directory = self.editor.drafts.context(video)['directory']
        commits = git(root, 'rev-list', '--first-parent', '--reverse', 'main').splitlines()
        if before:
            if before not in commits:
                raise ValueError('before is not on main')
            commits = commits[:commits.index(before)]
        result = []
        for n, sha in reversed(list(enumerate(commits, 1))):
            if directory != '.':
                parent = git(root, 'rev-parse', sha + '^') if n > 1 else None
                changed = git(root, 'diff-tree', '--no-commit-id', '--name-only', '-r',
                              *( [parent, sha] if parent else ['--root', sha]), '--', directory)
                if not changed:
                    continue
            raw = git(root, 'show', '-s', '--format=%s%x00%an%x00%aI%x00%B', sha).split('\0')
            meta = trailers(raw[3])
            kind = meta.get('Version-kind', 'push')
            if n == 1 and kind == 'push' and raw[0] == BLANK_SUMMARY and raw[1] == 'Video Editor':
                kind = 'blank'
            result.append(dict(n=n, commit=sha, summary=raw[0], kind=kind,
                               author=raw[1], directed_by=meta.get('Directed-by'), note=meta.get('Note'),
                               restores=meta.get('Restores'), time=raw[2],
                               renders=self.editor.renders.states(video, sha)))
            if len(result) >= limit:
                break
        return {'versions': result}

    def number(self, sha):
        commits = git(self.editor.root, 'rev-list', '--first-parent', '--reverse', 'main').splitlines()
        return commits.index(sha) + 1

    def restore(self, video, target, author):
        e = self.editor
        with e.lock, e.notes.video_lock(video):
            directory = e.drafts.context(video)['directory']
            commits = git(e.root, 'rev-list', '--first-parent', 'main').splitlines()
            if target not in commits:
                raise ValueError('commit is not on main')
            if e.sync:
                e.sync.before_commit()
            main = git(e.root, 'rev-parse', 'main')
            if target == main:
                return {'commit': main, 'changed': False, 'n': self.number(main)}
            if git(e.root, 'status', '--porcelain'):
                raise ValueError('main checkout has local changes')
            # Restore exactly the selected scope, including deletions, without moving history.
            pathspec = '.' if directory == '.' else directory
            git(e.root, 'restore', '--source', target, '--staged', '--worktree', '--', pathspec)
            changed = bool(git(e.root, 'diff', '--cached', '--name-only'))
            if not changed:
                return {'commit': main, 'changed': False, 'n': self.number(main)}
            message = f'Restore {target[:12]}\n\nVersion-kind: restore\nRestores: {target}\nDirected-by: {author}'
            git(e.root, 'commit', '-m', message)
            commit = git(e.root, 'rev-parse', 'main')
            e.project.last.pop(video, None)
            if e.sync:
                e.sync.after_commit()
            e.render_first(video, commit)
            return {'commit': commit, 'changed': True, 'n': self.number(commit)}

    def upgradable(self, video):
        """(pin, from, to) when the video's own pin is older than the editor; otherwise
        raise Refused with the reason."""
        from . import __version__
        e = self.editor
        context = e.drafts.context(video)
        pin = pin_for(os.path.join(e.root, context['film']), e.root)
        if pin is None:
            raise Refused('this video has no requirements.txt pinning videobuilder')
        old = pinned_version(pin)
        if old == 'unknown':
            raise Refused(f'{pin.relative_to(Path(e.root).resolve())} does not pin a videobuilder version')
        if pin.parent != (Path(e.root) / context['directory']).resolve():
            raise Refused('this pin is shared with other videos; upgrade it by hand')
        if pins.numbers(old) >= pins.numbers(__version__):
            raise Refused(f'this video already uses videobuilder {old}; the editor runs {__version__}')
        return pin, old, __version__

    def upgrade_info(self, video):
        """The chip's offer: only for an upgradable pin below MIN_PIN."""
        if self.editor.envs.mode != 'pinned':
            return None
        try:
            _, old, new = self.upgradable(video)
        except ValueError:
            return None
        if pins.numbers(old) >= pins.numbers(MIN_PIN):
            return None
        return {'from': old, 'to': new}

    def upgrade(self, video, author):
        e = self.editor
        with e.lock, e.notes.video_lock(video):
            if any(n['state'] not in FINAL for n in e.notes.list(video, refresh=False)):
                raise Refused('wait for queued and working notes before upgrading')
            if e.sync:
                e.sync.before_commit()
            pin, old, new = self.upgradable(video)
            if git(e.root, 'status', '--porcelain'):
                raise Refused('main checkout has local changes')
            pin.write_bytes(pins.repin(pin.read_bytes().decode(), new).encode())
            relative = str(PurePosixPath(pin.relative_to(Path(e.root).resolve())))
            git(e.root, 'add', '--', relative)
            git(e.root, 'commit', '-m', f'Upgrade videobuilder {old} → {new}\n\n'
                f'Version-kind: upgrade\nDirected-by: {author}', '--', relative)
            commit = git(e.root, 'rev-parse', 'main')
            e.project.last.pop(video, None)
            if e.sync:
                e.sync.after_commit()
            e.render_first(video, commit)
            return {'commit': commit, 'n': self.number(commit), 'from': old, 'to': new}
