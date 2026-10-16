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

class CompendiumSource(unittest.TestCase):
    def _staged(self, base, version, with_compendium):
        """A fake pinned videobuilder repo tagged `version`, with or without a
        `compendium/` package at its root, plus a project pinned to it. Returns
        (backend, payload) ready for backend.compendium_source(payload)."""
        repo = base / f'videobuilder-{version}.git'
        call(base, 'init', '--bare', '-q', str(repo))
        src = base / f'src-{version}'
        src.mkdir()
        call(src, 'init', '-q')
        call(src, 'config', 'user.name', 'Test')
        call(src, 'config', 'user.email', 'test@example.com')
        if with_compendium:
            (src / 'videobuilder' / 'compendium').mkdir(parents=True)
            (src / 'videobuilder' / 'compendium' / '__init__.py').write_text('')
        (src / 'README').write_text('seed')
        call(src, 'add', '.')
        call(src, 'commit', '-qm', 'source')
        call(src, 'tag', version)
        call(src, 'remote', 'add', 'origin', str(repo))
        call(src, 'push', '-q', 'origin', version)
        project = base / f'project-{version}'
        (project / 'a').mkdir(parents=True)
        (project / 'a' / 'film.py').write_text(FILM)
        pin = project / 'a' / 'requirements.txt'
        pin.write_text(f'videobuilder @ git+file://{repo}@{version}\n')
        payload = dict(project=str(project), film='a/film.py', state_dir=str(base))
        return payload

    def test_present_when_the_staged_pin_has_a_compendium(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            payload = self._staged(base, 'v1.0.0', with_compendium=True)
            with patch('videobuilder.agents.CONTEXT_STAGING_ROOT', base / 'forks'):
                backend = ForkSandboxBackend(context_root=base / 'forks' / 'context')
                result = backend.compendium_source(payload)
            self.assertEqual(result, base / 'forks' / 'context' / 'v1.0.0' / 'videobuilder' / 'videobuilder' / 'compendium')
            self.assertTrue(result.is_dir())

    def test_none_when_the_staged_pin_predates_the_compendium(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            payload = self._staged(base, 'v0.9.0', with_compendium=False)
            with patch('videobuilder.agents.CONTEXT_STAGING_ROOT', base / 'forks'):
                backend = ForkSandboxBackend(context_root=base / 'forks' / 'context')
                self.assertIsNone(backend.compendium_source(payload))

    def test_none_without_a_context_root_configured(self):
        backend = ForkSandboxBackend()
        self.assertIsNone(backend.compendium_source(dict(project='/nope', film='a/film.py', state_dir='/nope')))

    def test_none_when_the_backend_cannot_stage_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'project' / 'a').mkdir(parents=True)
            (base / 'project' / 'a' / 'film.py').write_text(FILM)  # no requirements.txt pin
            with patch('videobuilder.agents.CONTEXT_STAGING_ROOT', base / 'forks'):
                backend = ForkSandboxBackend(context_root=base / 'forks' / 'context')
                payload = dict(project=str(base / 'project'), film='a/film.py', state_dir=str(base))
                self.assertIsNone(backend.compendium_source(payload))


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


COMPOSE = Path(__file__).resolve().parent.parent / 'deploy/compose'


class ComposeImage(unittest.TestCase):
    def test_fork_sandbox_is_pinned_by_full_sha(self):
        text = (COMPOSE / 'Dockerfile').read_text()
        pins = [line.split('=', 1)[1] for line in text.splitlines() if line.startswith('ARG FORK_SANDBOX_REF=')]
        self.assertEqual(len(pins), 1)
        self.assertRegex(pins[0], r'^[0-9a-f]{40}$')

    def test_claude_code_is_pinned(self):
        text = (COMPOSE / 'Dockerfile').read_text()
        self.assertRegex(text, r'(?m)^ARG CLAUDE_CODE_VERSION=\d+\.\d+\.\d+$')

    def test_local_secrets_stay_out_of_images_and_git(self):
        root = COMPOSE.parent.parent
        ignored = (root / '.dockerignore').read_text().splitlines()
        self.assertIn('deploy/compose/.env', ignored)
        self.assertIn('deploy/compose/admin-password*', ignored)
        self.assertLessEqual({'.env', 'admin-password*'}, set((COMPOSE / '.gitignore').read_text().splitlines()))

    def test_shell_scripts_pass_shellcheck(self):
        if not shutil.which('shellcheck'):
            self.skipTest('shellcheck unavailable')
        scripts = sorted(COMPOSE.glob('*.sh'))
        self.assertTrue(scripts)
        result = subprocess.run(['shellcheck', *map(str, scripts)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_start_refuses_without_an_admin(self):
        env = {'PATH': '/usr/bin:/bin', 'HOME': tempfile.gettempdir()}
        result = subprocess.run([str(COMPOSE / 'start.sh')], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('VB_ADMIN is not set', result.stderr)
        if not Path('/run/secrets/admin_password').exists():
            result = subprocess.run([str(COMPOSE / 'start.sh')], env={**env, 'VB_ADMIN': 'admin'},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('no admin password', result.stderr)


def mkprofile():
    import importlib.util
    spec = importlib.util.spec_from_file_location('mkprofile', COMPOSE.parent / 'seccomp/mkprofile.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOBY_LIKE = {
    'defaultAction': 'SCMP_ACT_ERRNO', 'defaultErrnoRet': 1,
    'archMap': [{'architecture': 'SCMP_ARCH_X86_64', 'subArchitectures': ['SCMP_ARCH_X86']},
                {'architecture': 'SCMP_ARCH_AARCH64', 'subArchitectures': ['SCMP_ARCH_ARM']}],
    'syscalls': [
        {'names': ['read', 'write'], 'action': 'SCMP_ACT_ALLOW'},
        {'names': ['arch_prctl'], 'action': 'SCMP_ACT_ALLOW', 'includes': {'arches': ['amd64']}},
        {'names': ['arm_fadvise64_64'], 'action': 'SCMP_ACT_ALLOW', 'includes': {'arches': ['arm64']}},
        {'names': ['mount', 'unshare'], 'action': 'SCMP_ACT_ALLOW', 'includes': {'caps': ['CAP_SYS_ADMIN']}},
        {'names': ['clone'], 'action': 'SCMP_ACT_ALLOW',
         'args': [{'index': 0, 'value': 2114060288, 'op': 'SCMP_CMP_MASKED_EQ'}],
         'excludes': {'caps': ['CAP_SYS_ADMIN'], 'arches': ['s390', 's390x']}},
        {'names': ['clone3'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 38,
         'excludes': {'caps': ['CAP_SYS_ADMIN']}, 'comment': 'ENOSYS'},
    ]}


class SeccompProfile(unittest.TestCase):
    def test_flattened_form_for_kubernetes_is_amd64_and_capless(self):
        prof = mkprofile().build(MOBY_LIKE)
        self.assertEqual([a['architecture'] for a in prof['archMap']], ['SCMP_ARCH_X86_64'])
        self.assertEqual(prof['syscalls'], [
            {'names': ['read', 'write'], 'action': 'SCMP_ACT_ALLOW'},
            {'names': ['arch_prctl'], 'action': 'SCMP_ACT_ALLOW'},
            {'names': ['clone3'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 38},
            {'names': mkprofile().USERNS, 'action': 'SCMP_ACT_ALLOW'}])

    def test_docker_form_keeps_moby_conditions_and_only_swaps_clone(self):
        module = mkprofile()
        prof = module.build(MOBY_LIKE, docker=True)
        self.assertEqual(prof['archMap'], MOBY_LIKE['archMap'])
        expected = [s for s in MOBY_LIKE['syscalls'] if not s.get('args')]
        self.assertEqual(prof['syscalls'], expected + [{'names': module.USERNS, 'action': 'SCMP_ACT_ALLOW'}])

    def test_vendored_profile_is_moby_default_plus_user_namespaces(self):
        module = mkprofile()
        prof = json.loads((COMPOSE / 'seccomp-bwrap.json').read_text())
        self.assertEqual(prof['defaultAction'], 'SCMP_ACT_ERRNO')
        self.assertLessEqual({'SCMP_ARCH_X86_64', 'SCMP_ARCH_AARCH64'},
                             {a['architecture'] for a in prof['archMap']})
        *moby, ours = prof['syscalls']
        self.assertEqual(ours, {'names': module.USERNS, 'action': 'SCMP_ACT_ALLOW'})
        self.assertLessEqual({'clone', 'unshare'}, set(ours['names']))
        # Everything else is moby's, conditions intact: nothing else grants the
        # namespace syscalls unless the container holds CAP_SYS_ADMIN, and
        # clone is no longer limited by an argument mask.
        for entry in moby:
            if set(entry['names']) & set(module.USERNS) and entry['action'] == 'SCMP_ACT_ALLOW':
                self.assertIn('CAP_SYS_ADMIN', entry['includes']['caps'], entry)
            self.assertFalse('clone' in entry['names'] and entry.get('args'), entry)
        socket_rules = [e for e in moby if e['names'] == ['socket']]
        self.assertTrue(socket_rules and all(e.get('args') for e in socket_rules))
        self.assertIn({'names': ['clone3'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 38,
                       'excludes': {'caps': ['CAP_SYS_ADMIN']}}, moby)
        self.assertTrue(any(e.get('includes', {}).get('arches') for e in moby))
        # The provenance note names the regeneration command, and the licence sits beside it.
        self.assertIn('mkprofile.py --docker', (COMPOSE / 'seccomp-bwrap.NOTICE').read_text())
        self.assertIn('Apache License', (COMPOSE / 'seccomp-bwrap.LICENSE').read_text())


class ComposeStack(unittest.TestCase):
    def setUp(self):
        try:
            import yaml
        except ImportError:
            self.skipTest('PyYAML unavailable in test environment')
        self.text = (COMPOSE / 'compose.yaml').read_text()
        self.compose = yaml.safe_load(self.text)
        self.editor = self.compose['services']['editor']

    def test_every_referenced_file_exists(self):
        root = COMPOSE.parent.parent
        for service in self.compose['services'].values():
            context = (COMPOSE / service['build']['context']).resolve()
            self.assertEqual(context, root)
            self.assertTrue((context / service['build']['dockerfile']).is_file())
        self.assertEqual(self.editor['build']['additional_contexts'], {'base': 'service:base'})
        for opt in self.editor['security_opt']:
            if opt.startswith('seccomp='):
                self.assertTrue((COMPOSE / opt.split('=', 1)[1]).is_file())
        # The one file the operator writes, never committed (see .gitignore).
        self.assertEqual(self.compose['secrets'], {'admin_password': {'file': './admin-password'}})
        for line in (COMPOSE / 'Dockerfile').read_text().splitlines():
            if line.startswith('COPY ') and '--from' not in line and not line.startswith('COPY . '):
                self.assertTrue((root / line.split()[1]).is_file(), line)

    def test_env_example_lists_every_variable_and_no_secret(self):
        import re
        used = set(re.findall(r'\$\{(\w+)', self.text))
        lines = [line for line in (COMPOSE / '.env.example').read_text().splitlines()
                 if line and not line.startswith('#')]
        example = dict(line.split('=', 1) for line in lines)
        self.assertEqual(used, set(example))
        self.assertEqual(example['CLAUDE_CODE_OAUTH_TOKEN'], '')
        for value in example.values():
            self.assertNotRegex(value, r'sk-ant-|[A-Za-z0-9_-]{32,}')

    def test_restricted_but_able_to_sandbox(self):
        editor = self.editor
        self.assertEqual(editor['cap_drop'], ['ALL'])
        self.assertNotIn('cap_add', editor)
        self.assertNotIn('privileged', editor)
        self.assertEqual(editor['user'], '1000:1000')
        self.assertIn('no-new-privileges:true', editor['security_opt'])
        self.assertIn('apparmor=unconfined', editor['security_opt'])
        self.assertNotIn('docker.sock', self.text)
        self.assertNotIn('--k8s', (COMPOSE / 'start.sh').read_text())
        self.assertEqual(editor['ports'], ['127.0.0.1:${VB_PORT:-8100}:8100'])
        self.assertEqual(editor['volumes'], ['data:/var/tmp/claude-scratch'])
        self.assertTrue(editor['tmpfs'][0].startswith('/home/editor:'))
        self.assertEqual(editor['restart'], 'unless-stopped')
        self.assertIn('/healthz', ' '.join(editor['healthcheck']['test']))
        self.assertEqual(self.compose['services']['base']['scale'], 0)


class ComposeGuide(unittest.TestCase):
    def test_guide_covers_setup_and_is_linked(self):
        guide = (COMPOSE / 'README.md').read_text()
        for needed in ('admin-password', 'claude setup-token', 'docker compose up -d', 'git pull',
                       'docker compose build', 'reverse_proxy 127.0.0.1:8100', 'music-sources.toml',
                       'apparmor_restrict_unprivileged_userns'):
            self.assertIn(needed, guide)
        top = (COMPOSE.parent.parent / 'README.md').read_text()
        self.assertLess(top.index('## Self-host with Docker Compose'),
                        top.index('## Deploying the editor on Kubernetes'))
        self.assertIn('deploy/compose/README.md', top)
