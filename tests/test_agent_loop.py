"""Agent loop contracts and git safety on real temporary repositories."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from tests.test_project import TempProject, git
from tests.test_notes import FakeAgent
from videobuilder.agents import CommandBackend, FakeBackend, ForkSandboxBackend
from videobuilder.drafts import inspect, child_environment
from videobuilder.editor import Editor
from videobuilder.notes import NoteStore, AgentStatus


class Queue(TempProject):
    def test_serialization_restart_and_independent_videos(self):
        backend = FakeAgent()
        directory = self.root / '.vb-editor/notes'
        store = NoteStore(directory, backend)
        a = store.add('a', '1x1', 0, None, 'first', b'')
        b = store.add('a', '1x1', 0, None, 'second', b'')
        store.add('b', '1x1', 0, None, 'independent', b'')
        self.assertEqual(len(backend.submitted), 2)
        self.assertIsNone(b['handle'])
        backend.states[a['handle']] = AgentStatus('replied', 'done', 'draft/a')
        restarted = NoteStore(directory, backend)
        restarted.list('a')
        self.assertEqual(len(backend.submitted), 3)
        self.assertEqual(backend.submitted[-1]['draft'], 'draft/a')
        self.assertEqual(restarted.session('a')['session'], store.session('a')['session'])
        self.assertEqual(restarted.get(b['id'])['handle'], 'h3')

    def test_failed_note_releases_queue_and_branch_stays_linear(self):
        backend = FakeAgent()
        store = NoteStore(self.root / '.vb-editor/notes', backend)
        first = store.add('a', '1x1', 0, None, 'first', b'')
        second = store.add('a', '1x1', 0, None, 'second', b'')
        backend.states[first['handle']] = AgentStatus('failed', 'try again')
        store.list('a')
        backend.states[store.get(second['id'])['handle']] = AgentStatus('replied', 'done', 'draft/a')
        store.list('a')
        third = store.add('a', '1x1', 0, None, 'followup', b'')
        backend.states[third['handle']] = AgentStatus('replied', 'done', 'draft/wrong')
        store.list('a')
        self.assertEqual(store.get(third['id'])['state'], 'failed')
        self.assertEqual(store.session('a')['draft'], 'draft/a')

    def test_slow_submission_does_not_block_another_video(self):
        entered, release = threading.Event(), threading.Event()
        class Slow(FakeAgent):
            def submit(self, note):
                if note['video'] == 'slow':
                    entered.set()
                    release.wait(5)
                return super().submit(note)
        store = NoteStore(self.root / '.vb-editor/notes', Slow())
        worker = threading.Thread(target=lambda: store.add('slow', '1x1', 0, None, 'slow', b''))
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            fast = store.add('fast', '1x1', 0, None, 'fast', b'')
            self.assertIsNotNone(fast['handle'])
            self.assertTrue(worker.is_alive())
        finally:
            release.set()
            worker.join(5)

    def test_command_contract(self):
        script = self.root / 'runner.py'
        script.write_text('''import sys, json
from pathlib import Path
if sys.argv[1] == 'submit':
    n = json.loads(Path(sys.argv[2]).read_text())
    assert Path(n['note_file']).exists()
    assert Path(n['image']).exists()
    assert n['video'] == 'promo/film'
    print(json.dumps({'handle': n['id']}))
else:
    print(json.dumps({'state': 'replied', 'reply': 'Done', 'branch': 'draft/test'}))
''')
        backend = CommandBackend([sys.executable, str(script), 'submit'], [sys.executable, str(script), 'poll'])
        editor = Editor(self.root, backend=backend, unsandboxed_previews=True)
        note = editor.add_note(dict(video='promo/film', frame=12, text='Change title'), 'reviewer')
        result = editor.notes.list()[0]
        self.assertEqual(result['reply'], 'Done')
        md = (editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        for part in ('film: promo/film.py', 'frame: 12', 'time: 0.4', 'beat: 0.8', 'final message', 'only under promo'):
            self.assertIn(part, md)

    def test_refused_submit_shows_the_runners_reason(self):
        script = self.root / 'refuse.py'
        script.write_text('import sys\nprint("Error: the project must live under an allowed root", file=sys.stderr)\n'
                          'sys.exit(1)\n')
        command = [sys.executable, str(script)]
        editor = Editor(self.root, backend=CommandBackend(command, command), unsandboxed_previews=True)
        note = editor.add_note(dict(video='promo/film', frame=12, text='Change title'), 'reviewer')
        self.assertEqual(note['state'], 'failed')
        self.assertIn('must live under an allowed root', note['reply'])

    @patch('videobuilder.agents.run')
    def test_fork_sandbox_argv(self, run):
        run.return_value = '/run/example'
        backend = ForkSandboxBackend('runner', ['start'], ['query', '--json'], ['--local'])
        self.assertEqual(backend.submit(dict(state_dir='/state', project='/project', note_file='/note')), '/run/example')
        run.assert_called_with(['runner', 'start', '--resume', '/state', '--local', '/project', '/note'])
        backend.submit(dict(state_dir='/state', project='/project', note_file='/note', draft='draft/a'))
        run.assert_called_with(['runner', 'start', '--resume', '/state', '--base', 'draft/a', '--local',
                                '/project', '/note'])
        run.return_value = json.dumps(dict(state='replied', branch='draft/a', reply='done'))
        self.assertEqual(backend.poll('/run/example').reply, 'done')
        run.assert_called_with(['runner', 'query', '--json', '/run/example'])


class DraftLoop(TempProject):
    def setUp(self):
        super().setUp()
        git(self.root, 'branch', '-M', 'main')
        self.editor = Editor(self.root, backend=FakeBackend(delay=0), poll=0, unsandboxed_previews=True)
        self.addCleanup(self.editor.pool.close)

    def draft(self):
        n = self.editor.add_note(dict(video='promo/film', frame=0, text='Add a highlight'), 'reviewer')
        self.editor.notes.list()
        return self.editor.notes.get(n['id'])

    def test_accept_and_history(self):
        note = self.draft()
        detail = self.editor.drafts.details('promo/film')
        self.assertEqual(detail['files'], ['promo/film.py'])
        preview = self.editor.drafts._worktree('promo/film', detail['tip'])
        self.assertTrue(preview.exists())
        result = self.editor.drafts.accept('promo/film', 'sam')
        self.assertFalse(preview.exists())
        self.assertEqual(result['commit'], git(self.root, 'rev-parse', 'main').strip())
        self.assertIn('agent: Add a highlight', self.log())
        note = self.editor.notes.get(note['id'])
        self.assertEqual(note['state'], 'accepted')
        self.assertEqual(note['history'][-1]['author'], 'sam')
        self.assertIsNone(self.editor.notes.session('promo/film')['draft'])

    def test_startup_prunes_preview_worktrees(self):
        note = self.draft()
        path = self.editor.drafts._worktree('promo/film', self.editor.drafts.details('promo/film')['tip'])
        self.assertTrue(path.exists())
        other = Editor(self.root, unsandboxed_previews=True)
        self.addCleanup(other.pool.close)
        self.assertFalse(path.exists())

    def test_dirty_checkout_refused(self):
        self.draft()
        self.film.write_text(self.film.read_text() + '\n# unsaved\n')
        before = git(self.root, 'rev-parse', 'main')
        with self.assertRaisesRegex(ValueError, 'local changes'):
            self.editor.drafts.accept('promo/film', None)
        self.assertEqual(before, git(self.root, 'rev-parse', 'main'))
        self.assertIn('# unsaved', self.film.read_text())

    def test_conflict_aborted_and_note_queued(self):
        self.draft()
        self.film.write_text(self.film.read_text() + '\n# competing main edit\n')
        git(self.root, 'commit', '-am', 'main changed')
        result = self.editor.drafts.accept('promo/film', None)
        self.assertEqual(result['state'], 'rebase_requested')
        notes = self.editor.notes.list(refresh=False)
        self.assertEqual(notes[-1]['text'], 'rebase your draft onto main')
        self.assertTrue(notes[-1]['automatic'])
        self.assertNotIn('accept-work', git(self.root, 'worktree', 'list'))

    def test_drop_keeps_session_and_next_starts_main(self):
        note = self.draft()
        session = self.editor.notes.session('promo/film')['session']
        self.editor.drafts.drop('promo/film', 'sam')
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'dropped')
        self.assertEqual(self.editor.notes.session('promo/film'), dict(session=session, draft=None))
        self.assertNotIn(note['branch'], git(self.root, 'branch'))
        next_note = self.draft()
        self.assertNotEqual(note['branch'], next_note['branch'])

    def test_followup_linear_branch(self):
        first = self.draft()
        second = self.draft()
        self.assertEqual(first['branch'], second['branch'])
        self.assertEqual(len(self.editor.drafts.details('promo/film')['commits']), 2)

    def test_scope_refusals(self):
        for path, kind in [('README.md', 'outside'), ('promo/requirements-dev.txt', 'dependency'),
                           ('promo/pyproject.toml', 'dependency'), ('promo/poetry.lock', 'dependency'),
                           ('promo/uv.lock', 'dependency'), ('promo/link', 'symlink'), ('promo/sub', 'submodule')]:
            with self.subTest(path=path):
                git(self.root, 'checkout', '-B', 'bad', 'main')
                target = self.root / path
                if kind == 'symlink':
                    target.symlink_to('/etc/passwd')
                    git(self.root, 'add', path)
                elif kind == 'submodule':
                    git(self.root, 'update-index', '--add', '--cacheinfo', '160000',
                        git(self.root, 'rev-parse', 'main').strip(), path)
                else:
                    target.write_text('bad change')
                    git(self.root, 'add', path)
                git(self.root, 'commit', '-qm', 'bad')
                result = inspect(self.root, 'bad', 'promo')
                self.assertTrue(any(path in x and kind in x for x in result['refused']), result)
                git(self.root, 'checkout', 'main')

    def test_preview_child_scrubs_environment_and_renders(self):
        self.editor.notes.backend = FakeBackend(delay=0, change='\nimport os\nassert "VB_SECRET_SENTINEL" not in os.environ\n')
        self.draft()
        self.editor.unsandboxed_previews = True
        with patch.dict(os.environ, VB_SECRET_SENTINEL='secret'), patch('videobuilder.drafts.shutil.which', return_value=None):
            info = json.loads(self.editor.drafts.preview('promo/film', 'info', {}))
            self.assertIsNone(info['error'])
            png = self.editor.drafts.preview('promo/film', 'frame', dict(frame=0, scale=0.1))
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(set(child_environment('/tmp/home')), {'PATH', 'HOME', 'LANG', 'LC_ALL'})

    def test_preview_without_bwrap_refused_unless_opted_in(self):
        self.draft()
        self.editor.unsandboxed_previews = False
        self.editor.pool.unsandboxed = False
        with patch('videobuilder.workers.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'need a working bwrap'):
                self.editor.drafts.preview('promo/film', 'info', {})

    def test_preview_and_accept_reject_guard(self):
        note = self.draft()
        git(self.root, 'checkout', note['branch'])
        (self.root / 'README.md').write_text('escape')
        git(self.root, 'commit', '-am', 'escape')
        git(self.root, 'checkout', 'main')
        for action in (lambda: self.editor.drafts.preview('promo/film', 'info', {}),
                       lambda: self.editor.drafts.accept('promo/film', None)):
            with self.assertRaisesRegex(ValueError, 'README.md'):
                action()
