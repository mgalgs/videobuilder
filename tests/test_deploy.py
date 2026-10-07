import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobuilder.agents import ForkSandboxBackend, source_pin
from videobuilder.editor import Editor
from videobuilder.sync import ForgeSync, git
from tests.test_project import FILM


def call(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.remote = base / 'remote.git'
        call(base, 'init', '--bare', '-q', str(self.remote))
        seed = base / 'seed'
        call(base, 'clone', '-q', str(self.remote), str(seed))
        call(seed, 'config', 'user.name', 'Test')
        call(seed, 'config', 'user.email', 'test@example.com')
        (seed / 'a').mkdir()
        (seed / 'b').mkdir()
        (seed / 'a' / 'film.py').write_text(FILM)
        (seed / 'b' / 'film.py').write_text(FILM)
        call(seed, 'add', '.')
        call(seed, 'commit', '-qm', 'init')
        call(seed, 'branch', '-M', 'main')
        call(seed, 'push', '-q', 'origin', 'main')
        call(self.remote, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        self.a, self.b = base / 'a-clone', base / 'b-clone'
        for path in (self.a, self.b):
            call(base, 'clone', '-q', str(self.remote), str(path))
            call(path, 'config', 'user.name', 'Test')
            call(path, 'config', 'user.email', 'test@example.com')

    def edit(self, root, name, content):
        (root / name / 'film.py').write_text(content)
        call(root, 'add', '.')
        call(root, 'commit', '-qm', name)

    def test_two_clones_race_and_rebase(self):
        a, b = ForgeSync(self.a, 'origin'), ForgeSync(self.b, 'origin')
        a.before_commit()
        b.before_commit()
        self.edit(self.a, 'a', FILM + '\n# A\n')
        self.edit(self.b, 'b', FILM + '\n# B\n')
        a.after_commit()
        b.after_commit()
        a.refresh(force=True)
        self.assertIn('# A', (self.a / 'a' / 'film.py').read_text())
        self.assertIn('# B', (self.a / 'b' / 'film.py').read_text())
        self.assertEqual(call(self.a, 'rev-parse', 'main'), call(self.remote, 'rev-parse', 'main'))

    def test_conflict_preserves_diff(self):
        a, b = ForgeSync(self.a, 'origin'), ForgeSync(self.b, 'origin')
        self.edit(self.a, 'a', FILM + '\n# local\n')
        self.edit(self.b, 'a', FILM + '\n# remote\n')
        b.after_commit()
        with self.assertRaisesRegex(ValueError, 'rescue-.*Diff:') as error:
            a.before_commit()
        self.assertIn('+# local', str(error.exception))
        self.assertNotIn('# remote', str(error.exception))  # only the local side, from the merge base
        self.assertEqual(call(self.a, 'rev-parse', 'main'), call(self.remote, 'rev-parse', 'main'))

    def test_unreachable_forge_leaves_the_page_working(self):
        editor = Editor(self.a, state_dir=Path(self.tmp.name) / 'state', envs='current', sync_remote='origin')
        self.addCleanup(editor.pool.close)
        call(self.a, 'remote', 'set-url', 'origin', str(Path(self.tmp.name) / 'gone.git'))
        info = editor.project_info()
        self.assertEqual(len(info['videos']), 2)
        self.assertIn('gone.git', info['sync_error'])
        call(self.a, 'remote', 'set-url', 'origin', str(self.remote))
        self.assertIsNone(editor.project_info()['sync_error'])


class AgentSource(unittest.TestCase):
    def test_git_pin_staged_once_and_note_instructs_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / 'videobuilder.git'
            call(base, 'init', '--bare', '-q', str(repo))
            src = base / 'src'
            src.mkdir()
            call(src, 'init', '-q')
            call(src, 'config', 'user.name', 'Test')
            call(src, 'config', 'user.email', 'test@example.com')
            (src / 'skill' / 'make-a-video').mkdir(parents=True)
            (src / 'skill' / 'make-a-video' / 'SKILL.md').write_text('skill')
            call(src, 'add', '.')
            call(src, 'commit', '-qm', 'source')
            call(src, 'tag', 'v0.1.2')
            call(src, 'remote', 'add', 'origin', str(repo))
            call(src, 'push', '-q', 'origin', 'v0.1.2')
            project = base / 'project'
            (project / 'a').mkdir(parents=True)
            (project / 'a' / 'film.py').write_text(FILM)
            pin = project / 'a' / 'requirements.txt'
            pin.write_text('videobuilder @ git+file://' + str(repo) + '@v0.1.2\n')
            note = base / 'note.md'
            note.write_text('Change video\n')
            context = base / 'forks' / 'context'
            with patch('videobuilder.agents.CONTEXT_STAGING_ROOT', base / 'forks'), \
                    patch('videobuilder.agents.run', return_value='handle') as runner:
                backend = ForkSandboxBackend(context_root=context, context_mount='/work/context')
                payload = dict(project=str(project), film='a/film.py', note_file=str(note), state_dir=str(base))
                backend.submit(payload)
                backend.submit(payload)
                self.assertTrue((context / 'v0.1.2' / 'videobuilder' / 'skill' / 'make-a-video' / 'SKILL.md').is_file())
                self.assertIn('PYTHONPATH=/work/context/videobuilder', note.read_text())
                self.assertIn('--context-ro', runner.call_args.args[0])
                self.assertIn(str(context / 'v0.1.2'), runner.call_args.args[0])
            pin.write_text('videobuilder==0.1.2\n')
            self.assertEqual(source_pin(pin, str(repo)), ('0.1.2', str(repo), 'v0.1.2'))

class DeploymentYaml(unittest.TestCase):
    def test_example_parses_and_is_restricted(self):
        try:
            import yaml
        except ImportError:
            self.skipTest('PyYAML unavailable in test environment')
        path = Path(__file__).resolve().parent.parent / 'deploy/k8s/editor.yaml'
        docs = list(yaml.safe_load_all(path.read_text()))
        self.assertEqual([d['kind'] for d in docs],
                         ['ServiceAccount', 'RoleBinding', 'PersistentVolumeClaim',
                          'Deployment', 'Service', 'Ingress'])
        pod = docs[3]['spec']['template']['spec']
        self.assertEqual(pod['securityContext']['seccompProfile']['type'], 'Localhost')
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        self.assertEqual(pod['containers'][0]['securityContext']['capabilities']['drop'], ['ALL'])
