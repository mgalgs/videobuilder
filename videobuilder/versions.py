"""First-parent video versions and content-preserving restore commits."""
import os
from pathlib import Path
import subprocess

from .drafts import git


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
            result.append(dict(n=n, commit=sha, summary=raw[0], kind=meta.get('Version-kind', 'push'),
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
