"""Agent loop contracts and git safety on real temporary repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tests.test_project import TempProject, git
from tests.test_notes import FakeAgent
from tests.test_sources import _Rfile
from videobuilder import agents, transcript
from videobuilder.agents import CommandBackend, FakeBackend, ForkSandboxBackend
from videobuilder.drafts import inspect
from videobuilder.editor import Editor
from videobuilder.notes import NoteStore, AgentStatus
from videobuilder import sources
from videobuilder.transcript import read_feed
from videobuilder.workers import child_environment


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

    def test_current_polls_the_backend(self):
        backend = FakeAgent()
        store = NoteStore(self.root / '.vb-editor/notes', backend)
        note = store.add('a', '1x1', 0, None, 'first', b'')
        backend.states[note['handle']] = AgentStatus('replied', 'done', 'draft/a')
        self.assertEqual(store.get(note['id'])['state'], 'queued')
        self.assertEqual(store.current(note['id'])['reply'], 'done')

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
        backend.submit(dict(state_dir='/state', project='/project', note_file='/note',
                            attach_dir='/var/tmp/claude-scratch/attach'))
        run.assert_called_with(['runner', 'start', '--resume', '/state', '--local', '--attach-dir',
                                '/var/tmp/claude-scratch/attach', '/project', '/note'])
        backend.submit(dict(state_dir='/state', project='/project', note_file='/note'))
        self.assertNotIn('--attach-dir', run.call_args.args[0])  # nothing staged: argv unchanged
        run.return_value = json.dumps(dict(state='replied', branch='draft/a', reply='done'))
        self.assertEqual(backend.poll('/run/example').reply, 'done')
        run.assert_called_with(['runner', 'query', '--json', '/run/example'])
        run.return_value = json.dumps(dict(state='replied', reply='== result: success · 2 turns · $1 ==\ndone\n'))
        self.assertEqual(backend.poll('/run/example').reply, 'done\n')

    @patch('videobuilder.agents.run')
    def test_fork_sandbox_cost_and_tokens_from_status_json(self, run):
        backend = ForkSandboxBackend('runner', ['start'], ['query', '--json'])
        usage = {'input_tokens': 402, 'output_tokens': 107528, 'total_tokens': 40172222}
        run.return_value = json.dumps(dict(state='replied', reply='done', cost_usd=10.13,
                                           total_cost_usd=15.39, usage=usage))
        status = backend.poll('/run/example')
        self.assertEqual((status.cost_usd, status.tokens), (15.39, usage))
        run.return_value = json.dumps(dict(state='replied', reply='done', cost_usd=2.5))
        self.assertEqual((backend.poll('/run/example').cost_usd, backend.poll('/run/example').tokens), (2.5, None))
        run.return_value = json.dumps(dict(state='replied', reply='done', total_cost_usd='n/a', usage=[1, 2]))
        status = backend.poll('/run/example')
        self.assertEqual((status.cost_usd, status.tokens), (None, None))

    @patch('videobuilder.agents.run')
    def test_fork_sandbox_failed_with_reason_gets_plain_text(self, run):
        backend = ForkSandboxBackend('runner', ['start'], ['query', '--json'])
        run.return_value = json.dumps(dict(state='failed', reason='the pod finished before anything collected it'))
        status = backend.poll('/run/example')
        self.assertEqual(status.state, 'failed')
        self.assertIn("couldn't be recovered", status.reply)
        self.assertIn('Retry the note', status.reply)

    @patch('videobuilder.agents.run')
    def test_fork_sandbox_failed_without_reason_is_unchanged(self, run):
        backend = ForkSandboxBackend('runner', ['start'], ['query', '--json'])
        run.return_value = json.dumps(dict(state='failed', reply='could not apply the patch'))
        self.assertEqual(backend.poll('/run/example').reply, 'could not apply the patch')
        run.return_value = json.dumps(dict(state='failed'))
        self.assertIsNone(backend.poll('/run/example').reply)

    def test_orphaned_starts_one_adopt_and_a_later_poll_lands_normally(self):
        """A dead k8s driver with its pod still alive (see agents.py's class
        docstring): `status --json` reports "orphaned" until `adopt` has
        collected the run, at which point it reports the ordinary final
        state. Repeated polls while adopt is still running must not start a
        second one, and the note must not surface "orphaned" itself."""
        marker = self.root / 'adopted'
        calls = self.root / 'adopt-calls.log'
        script = self.root / 'status.py'
        script.write_text(f'''#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

marker = Path({str(marker)!r})
calls = Path({str(calls)!r})
if sys.argv[1] == 'adopt':
    with calls.open('a') as fh:
        fh.write(sys.argv[2] + chr(10))
    time.sleep(0.3)
    marker.write_text('done')
else:
    if marker.exists():
        print(json.dumps(dict(state='replied', reply='done', branch='draft/a')))
    else:
        print(json.dumps(dict(state='orphaned')))
''')
        os.chmod(script, 0o755)
        backend = ForkSandboxBackend(str(script))
        first = backend.poll('/run/example')
        second = backend.poll('/run/example')
        self.assertEqual((first.state, second.state), ('working', 'working'))
        deadline = time.time() + 5
        while not marker.exists() and time.time() < deadline:
            time.sleep(0.02)
        self.assertTrue(marker.exists())
        # Only now: on a loaded box the adopt process may not have started by the second poll.
        self.assertEqual(calls.read_text().splitlines(), ['/run/example'])
        time.sleep(0.1)  # give the now-finished adopt process time to actually exit
        third = backend.poll('/run/example')
        self.assertEqual((third.state, third.reply, third.branch), ('replied', 'done', 'draft/a'))
        self.assertEqual(backend._adopting, {})

    def test_orphaned_adopt_refused_is_not_retried_on_later_polls(self):
        """If `adopt` refuses right away (e.g. another adopt is already
        driving the run, or the status read was stale) and the pod keeps
        reporting "orphaned" because nothing is actually driving it, the
        backend must not spawn a fresh adopt on every poll -- "at most once
        per run per editor process" (see agents.py's class docstring), not
        "at most once while the last attempt is still alive"."""
        calls = self.root / 'adopt-calls.log'
        script = self.root / 'status.py'
        script.write_text(f'''#!/usr/bin/env python3
import sys
import json
from pathlib import Path

calls = Path({str(calls)!r})
if sys.argv[1] == 'adopt':
    with calls.open('a') as fh:
        fh.write(sys.argv[2] + chr(10))
    sys.exit(1)
else:
    print(json.dumps(dict(state='orphaned')))
''')
        os.chmod(script, 0o755)
        backend = ForkSandboxBackend(str(script))
        for _ in range(5):
            status = backend.poll('/run/example')
            time.sleep(0.05)
        self.assertEqual(status.state, 'working')
        self.assertEqual(calls.read_text().splitlines(), ['/run/example'])

    def _peek_script(self, body):
        script = self.root / 'peek.py'
        script.write_text('#!/usr/bin/env python3\n' + body)
        os.chmod(script, 0o755)
        return script

    def test_non_cluster_backend_has_no_peek(self):
        backend = ForkSandboxBackend('runner', ['start'], ['query', '--json'], ['--local'])
        self.assertFalse(hasattr(backend, 'peek'))

    def test_peek_argv_and_status_line_parsing(self):
        script = self._peek_script('''import sys
assert sys.argv[1:3] == ["k8s", "peek"], sys.argv
sys.stdout.write("some transcript bytes")
sys.stdout.flush()
print("peek: file=events.jsonl next=42", file=sys.stderr)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        data, file, next_offset = backend.peek('/run/example')
        self.assertEqual((data, file, next_offset), (b'some transcript bytes', 'events.jsonl', 42))

    def test_peek_follows_file_and_after_across_polls(self):
        calls_log = self.root / 'calls.log'
        script = self._peek_script(f'''import sys
with open({str(calls_log)!r}, 'a') as fh:
    fh.write(repr(sys.argv[1:]) + chr(10))
print("peek: file=events-review-1.jsonl next=99", file=sys.stderr)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        backend.peek('/run/example', file='events.jsonl', after=10)
        calls = [eval(line) for line in calls_log.read_text().splitlines()]
        self.assertEqual(calls, [['k8s', 'peek', '/run/example', '--after', '10', '--file', 'events.jsonl']])

    def test_peek_silent_empty_exit_is_not_an_error(self):
        script = self._peek_script('''import sys
sys.exit(0)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        data, file, next_offset = backend.peek('/run/example', file='events.jsonl', after=7)
        self.assertEqual((data, file, next_offset), (b'', 'events.jsonl', 7))

    def test_peek_nonzero_exit_raises_with_reason(self):
        script = self._peek_script('''import sys
print("boom: unreachable cluster", file=sys.stderr)
sys.exit(1)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        with self.assertRaisesRegex(ValueError, 'unreachable cluster'):
            backend.peek('/run/example')

    def test_peek_unparseable_status_line_raises(self):
        script = self._peek_script('''import sys
print("garbage", file=sys.stderr)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        with self.assertRaisesRegex(ValueError, 'unparseable'):
            backend.peek('/run/example')

    def test_peek_timeout_raises(self):
        script = self._peek_script('''import time
time.sleep(1)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        with patch.object(agents, '_PEEK_TIMEOUT', 0.05):
            with self.assertRaisesRegex(ValueError, 'timed out'):
                backend.peek('/run/example')

    def test_read_feed_through_real_backend_follows_file_and_after_across_polls(self):
        """read_feed's live cache, driven by a real subprocess backend (not a
        hand-fed FakePeek), must hand back exactly the file/after the
        previous `peek` call returned -- including across a leg change."""
        first = json.dumps({'type': 'assistant',
                             'message': {'content': [{'type': 'text', 'text': 'Looking at the frame now.'}]}})
        second = json.dumps({'type': 'assistant',
                              'message': {'content': [{'type': 'text', 'text': 'Step: next'}]}})
        script = self._peek_script(f'''import sys
args = sys.argv[1:]
after = args[args.index("--after") + 1]
file = args[args.index("--file") + 1] if "--file" in args else None
responses = {{
    (None, "0"): ({first!r}, "events.jsonl", 40),
    ("events.jsonl", "40"): ({second!r}, "events-review-1.jsonl", 5),
}}
key = (file, after)
if key not in responses:
    print(f"unexpected call file={{file}} after={{after}}", file=sys.stderr)
    sys.exit(1)
text, name, next_offset = responses[key]
sys.stdout.write(text + chr(10))
print(f"peek: file={{name}} next={{next_offset}}", file=sys.stderr)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        handle = '/fake/handle/' + self.id()
        self.addCleanup(transcript._drop_live, handle)
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0):
            with self.assertNoLogs('videobuilder.transcript', level='WARNING'):
                read_feed(handle, peek=backend.peek)
                entries = read_feed(handle, peek=backend.peek)
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'leg'], ['Building', 'Review 1'])
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'text'], ['Looking at the frame now.'])
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'step'], ['next'])

    def test_failing_peek_through_real_backend_is_logged_once(self):
        script = self._peek_script('''import sys
print("boom: unreachable cluster", file=sys.stderr)
sys.exit(1)
''')
        backend = ForkSandboxBackend(str(script), extra_args=['--k8s'])
        handle = '/fake/handle/' + self.id()
        self.addCleanup(transcript._drop_live, handle)
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0):
            with self.assertLogs('videobuilder.transcript', level='WARNING') as captured:
                first = read_feed(handle, peek=backend.peek)
                second = read_feed(handle, peek=backend.peek)
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(len(captured.records), 1)


class DraftLoop(TempProject):
    def tearDown(self):
        self.editor.renders.close()
        super().tearDown()

    def setUp(self):
        super().setUp()
        git(self.root, 'branch', '-M', 'main')
        self.editor = Editor(self.root, backend=FakeBackend(delay=0), unsandboxed_previews=True, auto_land=False)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)

    def draft(self):
        n = self.editor.add_note(dict(video='promo/film', frame=0, text='Add a highlight'), 'reviewer')
        self.editor.notes.list()
        return self.editor.notes.get(n['id'])

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_note_with_sources_gets_a_prompt_section_and_the_draft_sees_it(self):
        clip = Path(self.tmp.name) / 'clip.mp4'
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=red:s=32x32:d=1:r=5',
                       '-pix_fmt', 'yuv420p', str(clip)], check=True, capture_output=True)
        data = clip.read_bytes()
        self.editor.sources.stream_upload('promo/film', 'interview.mp4', None, 'video/mp4', _Rfile(data), len(data))
        note = self.draft()
        md = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('## Source videos', md)
        self.assertIn('sources/interview.mp4', md)
        preview = self.editor.drafts._worktree('promo/film', self.editor.drafts.details('promo/film')['tip'])
        self.assertTrue((preview / 'promo' / 'sources' / 'interview.mp4').is_file())

    def test_rejection_reason_for_a_sources_file_names_the_actual_rule(self):
        # A sources/ file sits inside the video's own directory, so the auto-landing
        # rejection text used to call it "outside this video" -- wrong, and silent
        # about the rule (never commit anything under sources/) actually broken.
        note = self.draft()
        self.assertEqual(note['state'], 'replied')
        work = Path(self.tmp.name) / 'bad-work'
        git(self.root, 'worktree', 'add', str(work), note['branch'])
        target = work / 'promo' / 'sources' / 'x.mp4'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('not a real video')
        # -f: a real sources/ commit wouldn't normally get past the git exclude
        # sources.sync() anchors for this video, but the guard must still refuse
        # one that does, and name the right reason, not just "outside this video".
        git(work, 'add', '-f', '--', 'promo/sources/x.mp4')
        git(work, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'bad commit')
        git(self.root, 'worktree', 'remove', '--force', str(work))
        self.editor.drafts.accept('promo/film', None, note)
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'refused')
        rejection = self.editor.notes.session('promo/film')['rejection']
        self.assertIn('promo/sources/x.mp4: source video, never committed', rejection)
        self.assertNotIn('outside this video', rejection)

    def test_note_with_no_sources_has_a_byte_identical_prompt(self):
        with_no_sources = self.draft()
        md = (self.editor.notes.session_dir('promo/film') / (with_no_sources['id'] + '.md')).read_text()
        self.assertNotIn('Source videos', md)

    def _upload_source(self, name, size='32x32'):
        clip = Path(self.tmp.name) / (name + '.mp4')
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=red:s={size}:d=1:r=5',
                       '-pix_fmt', 'yuv420p', str(clip)], check=True, capture_output=True)
        data = clip.read_bytes()
        return self.editor.sources.stream_upload('promo/film', name + '.mp4', name, 'video/mp4',
                                                  _Rfile(data), len(data))

    def _wait_ready(self, name, timeout=10):
        deadline = time.monotonic() + timeout
        while not self.editor.sources.get('promo/film', name)['preview_ready']:
            if time.monotonic() > deadline:
                self.fail(f'preview for {name!r} never became ready')
            time.sleep(0.05)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_attach_dir_gets_ready_source_previews_as_copies_within_budget(self):
        self._upload_source('alpha')
        self._upload_source('beta')
        self._wait_ready('alpha')
        self._wait_ready('beta')
        note = self.draft()
        attach_dir = self.editor.notes.session_dir('promo/film') / ('attachments-' + note['id'])
        for name in ('alpha', 'beta'):
            path = attach_dir / 'sources' / (name + '.mp4')
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.stat().st_nlink, 1)  # a copy, not a hardlink
        md = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertNotIn('not in your sandbox', md)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_source_still_preparing_is_listed_but_not_staged(self):
        with patch('videobuilder.sources.Sources._build_preview', lambda self, video, name: None):
            self._upload_source('alpha')
            # The build itself now runs on a single process-wide background worker
            # (one encode at a time, shared by every editor -- see sources._build_worker),
            # not a thread started with this patched method already bound -- wait for it
            # to actually run the no-op while still patched, or the real _build_preview
            # would run once this `with` block exits instead.
            sources._BUILD_QUEUE.join()
        note = self.draft()
        attach_dir = self.editor.notes.session_dir('promo/film') / ('attachments-' + note['id'])
        self.assertFalse((attach_dir / 'sources' / 'alpha.mp4').exists())
        md = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('not in your sandbox', md)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_source_over_budget_is_listed_but_not_staged(self):
        self._upload_source('alpha')
        self._wait_ready('alpha')
        with patch('videobuilder.notes.ATTACH_DIR_BUDGET', 1):
            note = self.draft()
        attach_dir = self.editor.notes.session_dir('promo/film') / ('attachments-' + note['id'])
        self.assertFalse((attach_dir / 'sources' / 'alpha.mp4').exists())
        md = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('not in your sandbox', md)

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
                           ('promo/uv.lock', 'dependency'), ('promo/link', 'symlink'), ('promo/sub', 'submodule'),
                           ('promo/sources/x.mp4', 'source')]:
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
                    target.parent.mkdir(parents=True, exist_ok=True)
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
