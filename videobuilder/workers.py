"""Pinned environments and sandboxed persistent worker processes."""
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import time

MINIMUM = '0.1.2'
TIMEOUT = 60
IDLE = 300


def pin_for(film, root):
    directory = Path(film).resolve().parent
    root = Path(root).resolve()
    while directory.is_relative_to(root):
        pin = directory / 'requirements.txt'
        if pin.is_file():
            return pin
        if directory == root:
            break
        directory = directory.parent
    return None


def pinned_version(pin):
    for line in pin.read_text().splitlines():
        match = re.match(r'^\s*videobuilder\s*==\s*([0-9]+(?:\.[0-9]+){1,3})\s*(?:#.*)?$', line, re.I)
        if match:
            return match.group(1)
        if 'videobuilder' in line.lower():
            match = re.search(r'@v?([0-9]+(?:\.[0-9]+){1,3})(?:\b|$)', line)
            if match:
                return match.group(1)
    return 'unknown'


def default_builder(target, pin):
    subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(target)], check=True,
                   capture_output=True)
    subprocess.run([str(target / 'bin' / 'python'), '-m', 'pip', 'install', '-r', str(pin)],
                   check=True, capture_output=True)


class Environments:
    def __init__(self, state, mode='pinned', builder=None):
        if mode not in ('pinned', 'current'):
            raise ValueError('editor.envs must be "pinned" or "current"')
        self.root = Path(state) / 'envs'
        self.mode = mode
        self.builder = builder or default_builder
        self.status = {}
        self.lock = threading.RLock()

    def choice(self, film, root):
        pin = pin_for(film, root) if self.mode == 'pinned' else None
        version = pinned_version(pin) if pin else "editor's own"
        key = hashlib.sha256(pin.read_bytes() + repr(sys.version_info[:3]).encode()).hexdigest() if pin else 'current'
        if pin and version != 'unknown' and tuple(map(int, version.split('.'))) < tuple(map(int, MINIMUM.split('.'))):
            raise ValueError(f'this video pins videobuilder {version}; the editor needs ≥ {MINIMUM}; upgrade its pin to open it')
        return pin, version, key

    def describe(self, film, root):
        try:
            pin, version, key = self.choice(film, root)
            state = 'ready' if not pin or (self.root / key / 'bin' / 'python').exists() else self.status.get(key, 'pending')
            return {'pin': version, 'env': 'failed' if state.startswith('failed: ') else state,
                    'error': state[8:] if state.startswith('failed: ') else None}
        except ValueError as exc:
            return {'pin': pinned_version(pin_for(film, root)), 'env': 'failed', 'error': str(exc)}

    def python(self, film, root):
        pin, version, key = self.choice(film, root)
        if not pin:
            return sys.executable, key, version
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / key
        with self.lock, open(self.root / (key + '.lock'), 'a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not (target / 'bin' / 'python').exists():
                self.status[key] = 'building'
                try:
                    with tempfile.TemporaryDirectory(prefix=key + '-', dir=self.root) as temporary:
                        build = Path(temporary) / 'env'
                        self.builder(build, pin)
                        if not (build / 'bin' / 'python').exists():
                            raise ValueError('environment builder did not create bin/python')
                        build.rename(target)
                except Exception as exc:
                    tail = getattr(exc, 'stderr', b'') or str(exc)
                    if isinstance(tail, bytes):
                        tail = tail.decode(errors='replace')
                    self.status[key] = 'failed: ' + str(tail)[-3000:]
                    raise ValueError(self.status[key]) from None
            self.status[key] = 'ready'
        return str(target / 'bin' / 'python'), key, version


def child_environment(home, source=None):
    env = {'PATH': os.defpath, 'HOME': str(home), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    if source:
        env['PYTHONPATH'] = str(source)
    return env


def sandbox_command(python, checkout, home, unsandboxed=False, source=None):
    command = [python, '-m', 'videobuilder', 'worker']
    wrapper = []
    if shutil.which('bwrap'):
        wrapper = ['bwrap', '--unshare-all', '--new-session', '--tmpfs', '/tmp']
        for system in ('/usr', '/bin', '/lib', '/lib64', '/etc/fonts', '/etc/ld.so.cache'):
            if os.path.exists(system):
                wrapper += ['--ro-bind', system, system]
        for path in dict.fromkeys([sys.prefix, str(Path(python).resolve().parent.parent), str(checkout), str(source or '')]):
            if path and os.path.exists(path):
                wrapper += ['--ro-bind', path, path]
        wrapper += ['--bind', str(home), str(home), '--proc', '/proc', '--dev', '/dev']
        probe = subprocess.run([*wrapper, '/bin/true'], env=child_environment(home, source),
                               cwd=home, capture_output=True, timeout=10)
        if probe.returncode:
            wrapper = []
    if not wrapper:
        if not unsandboxed:
            raise ValueError('film workers need a working bwrap; set unsandboxed_previews only where film code may read editor files')
        logging.warning('bwrap unavailable or unusable: film worker is not sandboxed')
    return wrapper + command


class Worker:
    def __init__(self, python, checkout, film, unsandboxed=False, source=None):
        self.film = str(film)
        self.home = tempfile.TemporaryDirectory()
        command = sandbox_command(python, checkout, self.home.name, unsandboxed, source)
        self.log = tempfile.TemporaryFile()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.log, cwd=self.home.name,
                                        env=child_environment(self.home.name, source), bufsize=0)
        self.buffer = b''
        self.lock = threading.RLock()
        self.used = time.monotonic()
        try:
            hello = json.loads(self._line(time.monotonic() + TIMEOUT))
            if hello.get('protocol') != 1:
                raise ValueError(f'unsupported worker protocol {hello.get("protocol")}; editor needs protocol 1')
            self.version = hello['version']
            try:
                old = tuple(map(int, self.version.split('.'))) < tuple(map(int, MINIMUM.split('.')))
            except ValueError:
                old = False
            if old:
                raise ValueError(f'this video pins videobuilder {self.version}; the editor needs ≥ {MINIMUM}; upgrade its pin to open it')
        except Exception:
            self.close()
            raise

    def _fill(self, n, deadline):
        while len(self.buffer) < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                self.close()
                raise ValueError('film worker timed out')
            chunk = os.read(self.process.stdout.fileno(), max(65536, n - len(self.buffer)))
            if not chunk:
                self.log.seek(0)
                raise ValueError('film worker exited: ' + self.log.read().decode(errors='replace')[-3000:])
            self.buffer += chunk

    def _read(self, n, deadline):
        self._fill(n, deadline)
        result, self.buffer = self.buffer[:n], self.buffer[n:]
        return result

    def _line(self, deadline):
        while b'\n' not in self.buffer:
            self._fill(len(self.buffer) + 1, deadline)
        end = self.buffer.index(b'\n') + 1
        return self._read(end, deadline)

    def request(self, op, **data):
        with self.lock:
            self.used = time.monotonic()
            try:
                self.process.stdin.write(json.dumps({'path': self.film, 'op': op, **data}).encode() + b'\n')
                header = json.loads(self._line(time.monotonic() + TIMEOUT))
                if not header['ok']:
                    raise ValueError(header['error'])
                if 'length' in header:
                    return self._read(header['length'], time.monotonic() + TIMEOUT)
                return header['value']
            except (BrokenPipeError, OSError) as exc:
                raise ValueError(f'film worker failed: {exc}') from None

    def close(self):
        if getattr(self, 'process', None):
            self.process.kill()
            self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
        self.log.close()
        self.home.cleanup()


class Pool:
    def __init__(self, envs, unsandboxed=False):
        self.envs = envs
        self.unsandboxed = unsandboxed
        self.workers = {}
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        threading.Thread(target=self._reap, daemon=True).start()

    def _reap(self):
        while not self.stopping.wait(30):
            with self.lock:
                for identity, (_, _, worker) in list(self.workers.items()):
                    if time.monotonic() - worker.used > IDLE:
                        worker.close()
                        del self.workers[identity]

    def get(self, video, checkout, film, root, revision=None):
        python, key, pin = self.envs.python(film, root)
        identity = (str(video), str(checkout))
        source = Path(__file__).resolve().parent.parent if key == 'current' else None
        with self.lock:
            for old, entry in list(self.workers.items()):
                worker = entry[-1]
                obsolete_draft = revision is not None and old[0] == str(video) and entry[1] is not None and old != identity
                if time.monotonic() - worker.used > IDLE or obsolete_draft or (old == identity and entry[:2] != (key, revision)):
                    worker.close()
                    del self.workers[old]
            entry = self.workers.get(identity)
            if entry and entry[-1].process.poll() is not None:
                entry[-1].close()
                entry = None
            if not entry:
                worker = Worker(python, checkout, film, self.unsandboxed, source)
                self.workers[identity] = (key, revision, worker)
            return self.workers[identity][-1]

    def close_draft(self, video):
        with self.lock:
            for identity, entry in list(self.workers.items()):
                if identity[0] == str(video) and entry[1] is not None:
                    entry[-1].close()
                    del self.workers[identity]

    def close(self):
        self.stopping.set()
        with self.lock:
            for _, _, worker in self.workers.values():
                worker.close()
            self.workers.clear()
