"""Pinned environments and the persistent film protocol."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from videobuilder.editor import Editor
from videobuilder.preview import Session
from videobuilder.workers import Environments, Worker, pin_for

from tests.test_project import FILM


SOURCE = Path(__file__).resolve().parent.parent / 'videobuilder'


def copy_builder(target, pin):
    subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(target)], check=True)
    site = target / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    shutil.copytree(SOURCE, site / 'videobuilder', ignore=shutil.ignore_patterns('__pycache__'))
    init = site / 'videobuilder' / '__init__.py'
    init.write_text(init.read_text().replace("__version__ = '0.1.2'", "__version__ = '" + pin.read_text().split('==')[1].strip() + "'"))


class PinnedWorkers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.root.mkdir()
        self.state = Path(self.tmp.name) / 'state'
        no_bwrap = mock.patch('videobuilder.workers.shutil.which', return_value=None)
        no_bwrap.start()
        self.addCleanup(no_bwrap.stop)

    def video(self, name, pin):
        directory = self.root / name
        directory.mkdir()
        film = directory / 'film.py'
        film.write_text(FILM + '\nimport os\nopen(' + repr(str(directory / 'pid')) + ', "w").write(str(os.getpid()))\n')
        (directory / 'requirements.txt').write_text('videobuilder==' + pin + '\n')
        return film

    def test_nearest_pin_cache_key_and_atomic_retry(self):
        a = self.video('a', '0.1.2')
        (self.root / 'requirements.txt').write_text('videobuilder==0.1.9\n')
        self.assertEqual(pin_for(a, self.root), a.parent / 'requirements.txt')
        calls = []
        def builder(target, pin):
            calls.append(target)
            if len(calls) == 1:
                raise ValueError('offline pip failure')
            copy_builder(target, pin)
        env = Environments(self.state, builder=builder)
        with self.assertRaisesRegex(ValueError, 'offline pip failure'):
            env.python(a, self.root)
        self.assertEqual(env.describe(a, self.root)['env'], 'failed')
        results = []
        threads = [threading.Thread(target=lambda: results.append(env.python(a, self.root))) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len(calls), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(env.describe(a, self.root)['env'], 'ready')
        (a.parent / 'requirements.txt').write_text('videobuilder==0.1.3\n')
        self.assertNotEqual(env.choice(a, self.root)[2], results[0][1])

    def test_two_versions_and_film_pid(self):
        a, b = self.video('a', '0.1.2'), self.video('b', '0.1.3')
        editor = Editor(self.root, state_dir=self.state, unsandboxed_previews=True, env_builder=copy_builder)
        self.addCleanup(editor.pool.close)
        self.assertEqual([v['pin'] for v in editor.project_info()['videos']], ['0.1.2', '0.1.3'])
        first, second = editor.session('a/film'), editor.session('b/film')
        self.assertEqual((first.version, second.version), ('0.1.2', '0.1.3'))
        self.assertNotEqual(first.process.pid, second.process.pid)
        for name, film in (('a/film', a), ('b/film', b)):
            self.assertEqual(editor.info(name)['frames'], 210)
            self.assertTrue(editor.session(name).request('frame', frame=0, scale=.1).startswith(b'\x89PNG'))
            self.assertNotEqual((film.parent / 'pid').read_text(), str(os.getpid()))

    def test_old_pin_refused_current_escape(self):
        film = self.video('old', '0.1.1')
        editor = Editor(self.root, state_dir=self.state, unsandboxed_previews=True, env_builder=copy_builder)
        self.assertIn('needs ≥ 0.1.2', editor.project_info()['videos'][0]['error'])
        with self.assertRaisesRegex(ValueError, 'upgrade its pin'):
            editor.session('old/film')
        current = Editor(self.root, state_dir=self.state, unsandboxed_previews=True, envs='current')
        self.addCleanup(current.pool.close)
        self.assertEqual(current.info('old/film')['frames'], 210)

    def test_edit_text_and_restart_after_crash(self):
        film = self.video('a', '0.1.2')
        editor = Editor(self.root, state_dir=self.state, unsandboxed_previews=True, env_builder=copy_builder)
        self.addCleanup(editor.pool.close)
        worker = editor.session('a/film')
        result = worker.request('edit', segment='intro', field='until', value=6)
        self.assertEqual(result, {'before': 4, 'toml': '[segments.intro]\nuntil = 6\n'})
        self.assertFalse((film.parent / 'film.edits.toml').exists())
        worker.process.kill()
        worker.process.wait()
        restarted = editor.session('a/film')
        self.assertNotEqual(worker.process.pid, restarted.process.pid)
        self.assertEqual(restarted.request('check')['error'], None)

    def test_handshake_and_unknown_protocol(self):
        film = self.video('a', '0.1.2')
        source = SOURCE.parent
        worker = Worker(sys.executable, self.root, film, unsandboxed=True, source=source)
        self.addCleanup(worker.close)
        self.assertEqual(worker.version, '0.1.2')
        with mock.patch('videobuilder.workers.json.loads', return_value={'protocol': 99, 'version': '0.1.2'}):
            with self.assertRaisesRegex(ValueError, 'unsupported worker protocol'):
                Worker(sys.executable, self.root, film, unsandboxed=True, source=source)

    def test_example_keyframes_are_byte_identical(self):
        import hashlib
        examples = SOURCE.parent / 'examples'
        picks = {'tour': (45, 142, 247, 330), 'benchmark': (60, 230, 330, 500)}
        for name, frames in picks.items():
            film = examples / (name + '.py')
            local = Session(film)
            worker = Worker(sys.executable, examples, film, unsandboxed=True, source=SOURCE.parent)
            try:
                for fmt in (x['name'] for x in local.info()['formats']):
                    for frame in frames:
                        with self.subTest(film=name, format=fmt, frame=frame):
                            expected = hashlib.sha256(local.png(frame, fmt, .25)).hexdigest()
                            actual = hashlib.sha256(worker.request('frame', frame=frame, format=fmt, scale=.25)).hexdigest()
                            self.assertEqual(actual, expected)
            finally:
                worker.close()

    def test_checkout_installs_offline_when_build_tools_exist(self):
        env = Path(self.tmp.name) / 'offline'
        subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(env)], check=True)
        python = str(env / 'bin' / 'python')
        result = subprocess.run([python, '-m', 'pip', 'install', '--no-build-isolation', '--no-index',
                                 str(SOURCE.parent)], capture_output=True, text=True)
        if result.returncode:
            self.skipTest('offline build tools unavailable: ' + (result.stderr or result.stdout)[-300:])
        version = subprocess.check_output([python, '-c', 'import videobuilder; print(videobuilder.__version__)'],
                                          cwd=self.tmp.name, text=True).strip()
        self.assertEqual(version, '0.1.2')
