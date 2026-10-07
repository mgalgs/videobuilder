"""Opt-in synchronization of the editor's main checkout with a forge."""
import os
import subprocess
import time
from pathlib import Path


def git(root, *args, check=True):
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=root,
                            capture_output=True, text=True)
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip() if check else result


class ForgeSync:
    def __init__(self, root, remote, interval=30):
        self.root, self.remote, self.interval = str(root), remote, interval
        self.fetched_at = 0
        if not remote or remote.startswith('-') or '/' in remote:
            raise ValueError('editor.sync_remote must be a git remote name')
        git(root, 'remote', 'get-url', remote)
        if git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD') != 'main':
            raise ValueError('sync_remote requires main to be checked out')

    @property
    def upstream(self):
        return 'refs/remotes/' + self.remote + '/main'

    def _clean(self):
        return not git(self.root, 'status', '--porcelain')

    def fetch(self):
        git(self.root, 'fetch', self.remote, '+refs/heads/main:' + self.upstream)
        self.fetched_at = time.monotonic()

    def _integrate(self):
        remote = git(self.root, 'rev-parse', self.upstream)
        local = git(self.root, 'rev-parse', 'main')
        if remote == local:
            return
        if not self._clean():
            return
        base = git(self.root, 'merge-base', 'main', self.upstream)
        if base == local:
            git(self.root, 'merge', '--ff-only', self.upstream)
            return
        if base == remote:
            return
        backup = 'refs/vb-sync/rescue-' + str(time.time_ns())
        git(self.root, 'update-ref', backup, local)
        result = git(self.root, 'rebase', self.upstream, check=False)
        if result.returncode:
            diff = git(self.root, 'diff', '--binary', base, backup)
            git(self.root, 'rebase', '--abort')
            git(self.root, 'reset', '--hard', remote)
            raise ValueError(f'main rebase conflicted; main reset to {self.remote}/main. '
                             f'Your commits remain at {backup}. Diff:\n{diff}')

    def before_commit(self):
        if not self._clean():
            raise ValueError('main checkout has local changes; save them before a synced edit')
        self.fetch()
        self._integrate()

    def refresh(self, force=False):
        if force or time.monotonic() - self.fetched_at >= self.interval:
            self.fetch()
            self._integrate()

    def after_commit(self):
        for attempt in range(3):
            result = git(self.root, 'push', self.remote, 'main:main', check=False)
            if result.returncode == 0:
                return
            if attempt == 2:
                raise ValueError(f'push failed after 3 attempts: {result.stderr.strip()}')
            self.fetch()
            self._integrate()
