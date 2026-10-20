"""Director API and automatic version integration."""
import json
import shutil
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from tests import fixtures
from tests.test_project import TempProject
from tests.test_project import git
from videobuilder import thumbnails
from videobuilder.agents import FakeBackend
from videobuilder.editor import Editor
from videobuilder.notes import AgentBackend, AgentStatus


class AskAndCommitBackend(AgentBackend):
    """A builder that asks a question but, against instructions, commits a change
    anyway: used to check that those commits still land like an ordinary reply's."""
    name = 'fake'

    def submit(self, note):
        root = note['project']
        branch = note['draft'] or 'vb-draft/ask-' + note['id']
        work = Path(note['state_dir']) / 'ask-work'
        if not note['draft']:
            git(root, 'branch', branch, 'main')
        git(root, 'worktree', 'add', str(work), branch)
        try:
            film = work / note['film']
            film.write_text(film.read_text() + '\n# committed while asking\n')
            git(work, 'add', '--', note['film'])
            git(work, '-c', 'user.name=Demo agent', '-c', 'user.email=agent@example.com',
                'commit', '-qm', 'agent: committed while asking')
        finally:
            git(root, 'worktree', 'remove', '--force', str(work))
        self.branch = branch
        return 'handle'

    def poll(self, handle):
        reply = 'Quick check:\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) + '\n```\n'
        return AgentStatus('replied', reply, self.branch)


class Director(TempProject):
    start = fixtures.API.start
    get = fixtures.API.get
    post = fixtures.API.post
    def tearDown(self):
        self.editor.renders.close()
        super().tearDown()

    def setUp(self):
        super().setUp()
        git(self.root, "branch", "-M", "main")
        self.start()
        self.editor.auto_land = True

    def test_auto_land_version_and_reply_only(self):
        self.editor.notes.backend = FakeBackend(delay=0)
        old = git(self.root, 'rev-parse', 'main').strip()
        note = self.post('/api/notes', {'video':'promo/film','text':'Highlight'})[1]
        self.get('/api/notes')
        landed = self.editor.notes.get(note['id'])
        self.assertEqual(landed['state'], 'landed')
        new = git(self.root, 'rev-parse', 'main').strip()
        self.assertNotEqual(old, new)
        self.assertEqual(landed['version']['commit'], new)
        log = git(self.root, 'show', '-s', '--format=%B', new)
        self.assertIn('Version-kind: builder', log)
        self.assertIn('Directed-by: anonymous', log)
        self.assertIn('Note: ' + note['id'], log)
        versions = self.get('/api/versions?video=promo/film')['versions']
        self.assertEqual(versions[0]['kind'], 'builder')
        self.assertEqual(versions[0]['commit'], new)
        self.assertEqual(versions[0]['n'], versions[1]['n'] + 1)

    def test_log_route_pages_entries_and_reports_done(self):
        note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Change'})[1]
        stored = self.editor.notes.get(note['id'])
        handle_dir = self.editor.notes.session_dir('promo/film') / 'run'
        handle_dir.mkdir()
        (handle_dir / 'events.jsonl').write_text(json.dumps(
            {'type': 'assistant', 'message': {'role': 'assistant',
             'content': [{'type': 'text', 'text': 'Looking at it'}]}}) + '\n')
        stored['handle'] = str(handle_dir)
        stored['state'] = 'working'
        self.editor.notes._save(stored)
        data = self.get(f'/api/notes/{note["id"]}/log')
        self.assertEqual([e['text'] for e in data['entries']], ['Building', 'Looking at it'])
        self.assertEqual(data['next'], 2)
        self.assertFalse(data['done'])
        paged = self.get(f'/api/notes/{note["id"]}/log?after=1')
        self.assertEqual([e['text'] for e in paged['entries']], ['Looking at it'])
        self.assertEqual(paged['next'], 2)
        stored['state'] = 'landed'
        self.editor.notes._save(stored)
        self.assertTrue(self.get(f'/api/notes/{note["id"]}/log')['done'])

    def test_log_route_uses_live_bytes_for_a_cluster_run_then_prefers_landed_files(self):
        class PeekBackend(AgentBackend):
            name = 'fork-sandbox'

            def __init__(self):
                self.calls = []

            def submit(self, note):
                return 'handle'

            def poll(self, handle):
                return AgentStatus('working')

            def peek(self, handle, file=None, after=0):
                self.calls.append((handle, file, after))
                return (json.dumps({'type': 'assistant', 'message': {'role': 'assistant',
                        'content': [{'type': 'text', 'text': 'Working on it live'}]}}).encode() + b'\n',
                        'events.jsonl', 999)

        backend = PeekBackend()
        self.editor.notes.backend = backend
        note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Change'})[1]
        stored = self.editor.notes.get(note['id'])
        handle_dir = self.editor.notes.session_dir('promo/film') / 'cluster-run'
        stored['handle'] = str(handle_dir)
        stored['state'] = 'working'
        self.editor.notes._save(stored)
        data = self.get(f'/api/notes/{note["id"]}/log')
        self.assertEqual([e['text'] for e in data['entries']], ['Building', 'Working on it live'])
        self.assertEqual(len(backend.calls), 1)
        handle_dir.mkdir()
        (handle_dir / 'events.jsonl').write_text(json.dumps(
            {'type': 'assistant', 'message': {'role': 'assistant',
             'content': [{'type': 'text', 'text': 'Landed from file'}]}}) + '\n')
        landed = self.get(f'/api/notes/{note["id"]}/log')
        self.assertEqual([e['text'] for e in landed['entries']], ['Building', 'Landed from file'])

    def test_log_route_restarts_a_cursor_counted_on_the_other_source(self):
        note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Change'})[1]
        stored = self.editor.notes.get(note['id'])
        handle_dir = self.editor.notes.session_dir('promo/film') / 'cluster-run'
        handle_dir.mkdir()
        (handle_dir / 'events.jsonl').write_text(json.dumps(
            {'type': 'assistant', 'message': {'role': 'assistant',
             'content': [{'type': 'text', 'text': 'Landed from file'}]}}) + '\n')
        stored['handle'] = str(handle_dir)
        self.editor.notes._save(stored)
        # A client that counted 5 live entries must not get files' entries[5:].
        moved = self.get(f'/api/notes/{note["id"]}/log?after=5&source=live')
        self.assertTrue(moved['reset'])
        self.assertEqual(moved['source'], 'files')
        self.assertEqual([e['text'] for e in moved['entries']], ['Building', 'Landed from file'])
        same = self.get(f'/api/notes/{note["id"]}/log?after=1&source=files')
        self.assertFalse(same['reset'])
        self.assertEqual([e['text'] for e in same['entries']], ['Landed from file'])

    def test_log_route_unknown_note_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get('/api/notes/does-not-exist/log')
        with caught.exception:
            self.assertEqual(caught.exception.code, 404)

    def test_log_route_with_no_handle_is_empty(self):
        note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Change'})[1]
        stored = self.editor.notes.get(note['id'])
        stored['handle'] = None
        self.editor.notes._save(stored)
        self.assertEqual(self.get(f'/api/notes/{note["id"]}/log'),
                         {'entries': [], 'next': 0, 'done': False, 'source': 'live', 'reset': False})

    def test_tick_lands_without_a_page_poll(self):
        self.editor.notes.backend = FakeBackend(delay=0)
        note = self.post('/api/notes', {'video':'promo/film','text':'Highlight'})[1]
        self.assertNotEqual(self.editor.notes.get(note['id'])['state'], 'landed')
        self.editor.notes.tick()
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'landed')
        self.assertEqual(self.editor.notes.pending(), [])

    def test_a_questions_reply_with_a_branch_still_lands(self):
        self.editor.notes.backend = AskAndCommitBackend()
        old = git(self.root, 'rev-parse', 'main').strip()
        note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Make the logo pop'})[1]
        self.editor.notes.tick()
        stored = self.editor.notes.get(note['id'])
        self.assertEqual(stored['state'], 'landed')
        self.assertEqual(stored['questions'], [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}])
        new = git(self.root, 'rev-parse', 'main').strip()
        self.assertNotEqual(old, new)
        self.assertEqual(stored['version']['commit'], new)

    def test_multi_commit_turn_is_one_version(self):
        self.editor.notes.backend = FakeBackend(delay=0, commits=3)
        old = git(self.root, 'rev-parse', 'main').strip()
        note = self.post('/api/notes', {'video':'promo/film','text':'Three edits'})[1]
        self.get('/api/notes')
        new = git(self.root, 'rev-parse', 'main').strip()
        self.assertEqual(git(self.root, 'rev-list', '--count', old + '..' + new).strip(), '1')
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'landed')

    def test_refused_turn_and_next_note(self):
        self.editor.notes.backend = FakeBackend(delay=0, extra_path='README.md')
        old = git(self.root, 'rev-parse', 'main').strip()
        note = self.post('/api/notes', {'video':'promo/film','text':'Try change'})[1]
        self.get('/api/notes')
        refused = self.editor.notes.get(note['id'])
        self.assertEqual(refused['state'], 'refused')
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), old)
        self.assertEqual(git(self.root, 'rev-parse', refused['branch']).strip(), old)
        self.editor.notes.backend = FakeBackend(delay=10)
        following = self.post('/api/notes', {'video':'promo/film','text':'Try again'})[1]
        markdown = (self.editor.notes.session_dir('promo/film') / (following['id'] + '.md')).read_text()
        self.assertIn('Your previous change was not kept: it touched README.md', markdown)

    def test_conflict_retries_once_then_stops(self):
        self.editor.notes.backend = FakeBackend(delay=0)
        note = self.post('/api/notes', {'video':'promo/film','text':'Change ending'})[1]
        self.editor.notes.backend.poll(note['handle'])
        self.film.write_text(self.film.read_text() + '\n# competing main edit\n')
        git(self.root, 'commit', '-am', 'main changed')
        self.get('/api/notes')
        automatic = [n for n in self.editor.notes.list(refresh=False) if n.get('automatic')]
        self.assertEqual(len(automatic), 1)
        self.assertEqual(automatic[0]['text'], 'rebase your draft onto main')
        self.editor.notes.list()
        self.editor.notes.list()
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'conflict')
        self.assertEqual(len([n for n in self.editor.notes.list(refresh=False) if n.get('automatic')]), 1)

    # Reads a file the builder never committed, as when its .gitignore says *.png.
    MISSING = ("\nimport pathlib\n"
               "_CLIP = (pathlib.Path(__file__).parent / 'assets' / 'webclip.png').read_bytes()\n")

    def broken_draft(self, change=MISSING):
        self.editor.notes.backend = FakeBackend(delay=0, change=change)
        note = self.post('/api/notes', {'video': 'promo/film', 'text': 'Use the clip'})[1]
        self.editor.notes.backend.poll(note['handle'])
        return note

    def fix_notes(self):
        return [n for n in self.editor.notes.list(refresh=False) if n.get('automatic')]

    def test_a_draft_that_does_not_load_asks_for_one_fix_that_lands(self):
        note = self.broken_draft()
        main = git(self.root, 'rev-parse', 'main').strip()
        self.editor.notes.backend = FakeBackend(delay=10)
        self.get('/api/notes')
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)
        original = self.editor.notes.get(note['id'])
        self.assertEqual((original['state'], original['message']),
                         ('replied', "The builder's change didn't load; it's fixing it."))
        self.assertNotIn('version', original)
        self.assertFalse([k for k in self.editor.pool.workers if k[1].endswith('accept-work')])
        self.assertNotEqual(git(self.root, 'rev-parse', original['branch']).strip(), main)
        [fix] = self.fix_notes()
        self.assertEqual((fix['author'], fix['retry_for']), ('editor', note['id']))
        self.assertIn('did not load in a clean checkout', fix['text'])
        self.assertIn('FileNotFoundError', fix['text'])
        self.assertIn('webclip.png', fix['text'])
        self.assertIn('webclip.png', fix['said'])
        markdown = (self.editor.notes.session_dir('promo/film') / (fix['id'] + '.md')).read_text()
        self.assertIn('draft: ' + original['branch'], markdown)
        handle = Path(fix['handle'])
        handle.write_text(json.dumps({**json.loads(handle.read_text()), 'ready': 0}))
        self.editor.notes.backend = FakeBackend(delay=0, change='\n', extra_path='promo/assets/webclip.png')
        self.get('/api/notes')
        fixed, original = self.editor.notes.get(fix['id']), self.editor.notes.get(note['id'])
        self.assertEqual((fixed['state'], original['state']), ('landed', 'landed'))
        self.assertEqual(original['version'], fixed['version'])
        self.assertIsNone(original['message'])
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), fixed['version']['commit'])
        self.assertIn('promo/assets/webclip.png', self.files_in('main'))
        self.assertEqual(len(self.fix_notes()), 1)

    def test_a_fix_that_still_does_not_load_fails_both_notes(self):
        note = self.broken_draft()
        main = git(self.root, 'rev-parse', 'main').strip()
        for _ in range(3):
            self.get('/api/notes')
        [fix] = self.fix_notes()
        for n in (self.editor.notes.get(note['id']), self.editor.notes.get(fix['id'])):
            self.assertEqual(n['state'], 'failed')
            self.assertTrue(n['message'].startswith("The builder's change still didn't load: FileNotFoundError"))
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)
        self.assertEqual(len(self.fix_notes()), 1)
        self.assertEqual(self.editor.notes.pending(), [])

    def test_a_rebase_request_that_does_not_load_still_gets_its_one_fix(self):
        note = self.broken_draft()
        self.film.write_text(self.film.read_text() + '\n# competing main edit\n')
        git(self.root, 'commit', '-am', 'main changed')
        self.editor.notes.backend = FakeBackend(delay=10, change='\n')
        self.get('/api/notes')
        [rebase] = self.fix_notes()
        self.assertEqual(rebase['text'], 'rebase your draft onto main')
        # The builder rebases cleanly but still leaves the ignored file out.
        branch = self.editor.notes.get(note['id'])['branch']
        work = self.root.parent / 'rebased'
        git(self.root, 'worktree', 'add', '--detach', str(work), 'main')
        film = work / self.film.relative_to(self.root)
        film.write_text(film.read_text() + self.MISSING)
        git(work, 'commit', '-qam', 'agent: rebased')
        git(self.root, 'update-ref', 'refs/heads/' + branch, git(work, 'rev-parse', 'HEAD').strip())
        git(self.root, 'worktree', 'remove', '--force', str(work))
        main = git(self.root, 'rev-parse', 'main').strip()
        handle = Path(rebase['handle'])
        handle.write_text(json.dumps({**json.loads(handle.read_text()), 'ready': 0}))
        self.get('/api/notes')
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)
        original = self.editor.notes.get(note['id'])
        self.assertEqual((original['state'], original['message']),
                         ('replied', "The builder's change didn't load; it's fixing it."))
        self.assertNotEqual(self.editor.notes.get(rebase['id'])['state'], 'failed')
        [fix] = [n for n in self.fix_notes() if n['id'] != rebase['id']]
        self.assertEqual(fix['retry_for'], note['id'])
        self.assertIn('webclip.png', fix['text'])

    def test_a_film_that_loads_but_cannot_draw_is_caught(self):
        note = self.broken_draft('\ndef _draft_draw(n, cv):\n    raise RuntimeError("no font at assets/Brand.otf")\n'
                                 'FILM.draw = _draft_draw\n')
        main = git(self.root, 'rev-parse', 'main').strip()
        self.editor.notes.backend = FakeBackend(delay=10)
        self.get('/api/notes')
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'replied')
        [fix] = self.fix_notes()
        self.assertIn('no font at assets/Brand.otf', fix['text'])

    def test_manual_accept_refuses_a_draft_that_does_not_load(self):
        self.editor.auto_land = False
        self.broken_draft()
        self.get('/api/notes')
        main = git(self.root, 'rev-parse', 'main').strip()
        code, body = self.post('/api/draft/accept', {'video': 'promo/film'})
        self.assertEqual(code, 400)
        self.assertIn("This draft doesn't load: FileNotFoundError", body['error'])
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)
        self.assertEqual(self.fix_notes(), [])

    def test_a_worker_that_cannot_start_does_not_block_landing(self):
        self.editor.unsandboxed_previews = False
        note = self.broken_draft()
        with patch('videobuilder.workers.shutil.which', return_value=None):
            self.get('/api/notes')
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'landed')

    def test_retry_conflicted_note_on_main(self):
        self.editor.notes.backend = FakeBackend(delay=0)
        note = self.post('/api/notes', {'video':'promo/film','text':'Change ending','time':0.4})[1]
        self.editor.notes.backend.poll(note['handle'])
        self.film.write_text(self.film.read_text() + '\n# competing main edit\n')
        git(self.root, 'commit', '-am', 'main changed')
        self.get('/api/notes')
        self.editor.notes.list()
        automatic = next(n for n in self.editor.notes.list(refresh=False) if n.get('automatic'))
        self.assertEqual(self.post(f'/api/notes/{automatic["id"]}/retry', {})[0], 400)
        self.assertEqual(self.post('/api/notes/nosuchnote/retry', {})[0], 404)
        main = git(self.root, 'rev-parse', 'main').strip()
        code, retried = self.post(f'/api/notes/{note["id"]}/retry', {})
        self.assertEqual(code, 200)
        self.assertEqual((retried['text'], retried['frame'], retried['retried_from']),
                         ('Change ending', note['frame'], note['id']))
        self.assertEqual(self.editor.notes.get(note['id'])['retried'], retried['id'])
        self.assertEqual(self.editor.notes.image(retried['id']), self.editor.notes.image(note['id']))
        markdown = (self.editor.notes.session_dir('promo/film') / (retried['id'] + '.md')).read_text()
        self.assertIn('draft: None', markdown)
        self.assertEqual(self.post(f'/api/notes/{note["id"]}/retry', {})[0], 400)
        self.get('/api/notes')
        landed = self.editor.notes.get(retried['id'])
        self.assertEqual(landed['state'], 'landed')
        self.assertEqual(git(self.root, 'rev-parse', 'main^').strip(), main)

    def test_pinned_frame_reaches_the_runner(self):
        from videobuilder.attachments import FRAME_NAME
        self.editor.notes.backend = FakeBackend(delay=0)
        note = self.post('/api/notes', {'video':'promo/film','text':'Muddled','time':0.4})[1]
        self.get('/api/notes')
        markdown = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn(f'image: /attachments/{FRAME_NAME}', markdown)
        self.assertIn('iterate visually', markdown)
        staged = self.editor.notes.session_dir('promo/film') / ('attachments-' + note['id']) / FRAME_NAME
        self.assertEqual(staged.read_bytes(), self.editor.notes.image(note['id']))
        plain = self.post('/api/notes', {'video':'promo/film','text':'No frame'})[1]
        markdown = (self.editor.notes.session_dir('promo/film') / (plain['id'] + '.md')).read_text()
        self.assertIn('image: None', markdown)

    def test_retry_failed_note(self):
        class Broken(FakeBackend):
            def submit(self, note):
                raise RuntimeError('runner down')
        self.editor.notes.backend = Broken(delay=0)
        note = self.post('/api/notes', {'video':'promo/film','text':'Change ending'})[1]
        self.get('/api/notes')
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'failed')
        self.editor.notes.backend = FakeBackend(delay=0)
        code, retried = self.post(f'/api/notes/{note["id"]}/retry', {})
        self.assertEqual((code, retried['retried_from']), (200, note['id']))
        self.get('/api/notes')
        self.assertEqual(self.editor.notes.get(retried['id'])['state'], 'landed')
        self.assertEqual(self.post(f'/api/notes/{retried["id"]}/retry', {})[0], 400)

    def test_missing_draft_branch_starts_from_main(self):
        state = self.editor.notes.session('promo/film')
        state['draft'] = 'k8s-never-created'
        self.editor.notes.save_session('promo/film', state)
        self.assertIsNone(self.get('/api/draft?video=promo/film'))
        self.editor.notes.backend = FakeBackend(delay=10)
        note = self.post('/api/notes', {'video':'promo/film','text':'Faster'})[1]
        markdown = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('draft: None', markdown)
        self.assertIsNone(self.editor.notes.session('promo/film')['draft'])

    def test_render_jobs_follow_cgroup_quota(self):
        import tempfile
        from videobuilder.render import default_jobs
        with tempfile.NamedTemporaryFile('w', suffix='cpu.max') as fh:
            fh.write('100000 100000\n')
            fh.flush()
            self.assertEqual(default_jobs(fh.name), 1)
        with tempfile.NamedTemporaryFile('w', suffix='cpu.max') as fh:
            fh.write('max 100000\n')
            fh.flush()
            self.assertEqual(default_jobs(fh.name), len(__import__('os').sched_getaffinity(0)))

    def test_clean_rebase_and_reply_only(self):
        self.editor.notes.backend = FakeBackend(delay=0)
        note = self.post('/api/notes', {'video':'promo/film','text':'Change'})[1]
        self.editor.notes.backend.poll(note['handle'])
        (self.root / 'README.md').write_text('A newer main\n')
        git(self.root, 'commit', '-am', 'main changed')
        middle = git(self.root, 'rev-parse', 'main').strip()
        self.get('/api/notes')
        self.assertEqual(self.editor.notes.get(note['id'])['state'], 'landed')
        self.assertEqual(git(self.root, 'rev-parse', 'main^').strip(), middle)
        self.editor.notes.backend = FakeBackend(delay=0, commits=0)
        before = git(self.root, 'rev-parse', 'main').strip()
        plain = self.post('/api/notes', {'video':'promo/film','text':'Just answer'})[1]
        self.get('/api/notes')
        self.assertEqual(self.editor.notes.get(plain['id'])['state'], 'replied')
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), before)

    def test_draft_advances_before_followup(self):
        self.editor.notes.backend = FakeBackend(delay=0)
        first = self.post('/api/notes', {'video':'promo/film','text':'Change'})[1]
        self.get('/api/notes')
        branch = self.editor.notes.get(first['id'])['branch']
        self.post('/api/copy', {'video':'promo/film','segment':'intro','key':'title','value':'Newest'})
        main = git(self.root, 'rev-parse', 'main').strip()
        self.editor.notes.backend = FakeBackend(delay=10)
        self.post('/api/notes', {'video':'promo/film','text':'Follow up'})
        self.assertEqual(git(self.root, 'rev-parse', branch).strip(), main)

    def test_restore_and_name(self):
        first = git(self.root, 'rev-parse', 'main').strip()
        self.assertEqual(self.get('/api/name'), {'name': None})
        code, name = self.post('/api/name', {'name': '  Dana  '})
        self.assertEqual((code, name), (200, {'name':'Dana'}))
        self.post('/api/copy', {'video':'promo/film','segment':'intro','key':'title','value':'Changed'})
        newest = git(self.root, 'rev-parse', 'main').strip()
        result = self.post('/api/versions/restore', {'video':'promo/film','commit':first})[1]
        self.assertTrue(result['changed'])
        self.assertNotEqual(result['commit'], newest)
        self.assertEqual(git(self.root, 'rev-parse', result['commit'] + ':promo').strip(),
                         git(self.root, 'rev-parse', first + ':promo').strip())
        self.assertEqual(self.post('/api/versions/restore', {'video':'promo/film','commit':result['commit']})[1]['changed'], False)
        self.assertEqual(self.get('/api/versions?video=promo/film')['versions'][0]['kind'], 'restore')

    def _pin(self, text, where='promo'):
        def no_env(target, pin):
            raise ValueError('no environments in tests')
        self.editor.envs.builder = no_env
        (self.root / where / 'requirements.txt').write_text(text)
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'pin')

    def test_upgrade_rewrites_only_the_pin(self):
        from videobuilder import __version__
        text = ('numpy==1.26\nvideobuilder @ git+https://example.com/vb.git@v0.1.9#egg=videobuilder ; python_version>"3"\n'
                '# videobuilder@v0.1.9 again\n')
        self._pin(text)
        project = self.get('/api/project')
        self.assertEqual(project['version'], __version__)
        self.assertEqual(project['videos'][0]['pin'], '0.1.9')
        self.assertEqual(project['videos'][0]['upgrade'], {'from': '0.1.9', 'to': __version__})
        old = git(self.root, 'rev-parse', 'main').strip()
        code, result = self.post('/api/upgrade', {'video': 'promo/film'}, {'Content-Type': 'application/json',
                                                                         'Cookie': 'vb_name=Dana'})
        self.assertEqual(code, 200)
        self.assertEqual((result['from'], result['to']), ('0.1.9', __version__))
        self.assertEqual(git(self.root, 'rev-parse', 'main^').strip(), old)
        self.assertEqual(result['commit'], git(self.root, 'rev-parse', 'main').strip())
        self.assertEqual((self.root / 'promo' / 'requirements.txt').read_text(), text.replace(
            'vb.git@v0.1.9#', f'vb.git@v{__version__}#'))
        self.assertEqual(git(self.root, 'show', '--name-only', '--format=', 'main').split(), ['promo/requirements.txt'])
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        log = git(self.root, 'show', '-s', '--format=%B', 'main')
        self.assertIn(f'Upgrade videobuilder 0.1.9 → {__version__}', log)
        self.assertIn('Version-kind: upgrade', log)
        self.assertIn('Directed-by: Dana', log)
        latest = self.get('/api/versions?video=promo/film')['versions'][0]
        self.assertEqual((latest['kind'], latest['commit'], latest['n']), ('upgrade', result['commit'], result['n']))
        self.assertIsNone(self.get('/api/project')['videos'][0]['upgrade'])
        code, refused = self.post('/api/upgrade', {'video': 'promo/film'})
        self.assertEqual(code, 409)
        self.assertIn('already uses', refused['error'])

    def test_upgrade_equals_pin_and_refusals(self):
        from videobuilder import __version__
        self._pin('videobuilder==0.1.9  # pinned\nrich\n')
        self.assertEqual(self.post('/api/upgrade', {'video': 'promo/film'})[0], 200)
        self.assertEqual((self.root / 'promo' / 'requirements.txt').read_text(),
                         f'videobuilder=={__version__}  # pinned\nrich\n')
        major, minor, patch = map(int, __version__.split('.'))
        self._pin(f'videobuilder=={major}.{minor}.{patch + 1}\n')
        code, refused = self.post('/api/upgrade', {'video': 'promo/film'})
        self.assertEqual(code, 409)
        self.assertIsNone(self.get('/api/project')['videos'][0]['upgrade'])
        self._pin('numpy\n')
        code, refused = self.post('/api/upgrade', {'video': 'promo/film'})
        self.assertEqual(code, 409)
        self.assertIn('does not pin', refused['error'])
        (self.root / 'promo' / 'requirements.txt').unlink()
        git(self.root, 'commit', '-qam', 'unpin')
        self.assertEqual(self.post('/api/upgrade', {'video': 'promo/film'})[0], 409)
        self.assertEqual(git(self.root, 'log', '-1', '--format=%s', 'main').strip(), 'unpin')

    def test_upgrade_refuses_a_shared_pin(self):
        self._pin('videobuilder==0.1.9\n', where='.')
        self.assertEqual(self.get('/api/project')['videos'][0]['pin'], '0.1.9')
        self.assertIsNone(self.get('/api/project')['videos'][0]['upgrade'])
        main = git(self.root, 'rev-parse', 'main').strip()
        code, refused = self.post('/api/upgrade', {'video': 'promo/film'})
        self.assertEqual(code, 409)
        self.assertIn('shared with other videos; upgrade it by hand', refused['error'])
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)

    def test_upgrade_not_offered_at_the_floor(self):
        from videobuilder import __version__
        from videobuilder.versions import MIN_PIN
        self._pin(f'videobuilder=={MIN_PIN}\n')
        self.assertIsNone(self.get('/api/project')['videos'][0]['upgrade'])
        if MIN_PIN != __version__:
            self.assertEqual(self.post('/api/upgrade', {'video': 'promo/film'})[0], 200)

    def test_upgrade_waits_for_running_notes(self):
        self.editor.notes.backend = FakeBackend(delay=10)
        self.post('/api/notes', {'video': 'promo/film', 'text': 'Faster'})
        self._pin('videobuilder==0.1.9\n')
        main = git(self.root, 'rev-parse', 'main').strip()
        code, refused = self.post('/api/upgrade', {'video': 'promo/film'})
        self.assertEqual(code, 409)
        self.assertIn('queued and working notes', refused['error'])
        self.assertEqual(git(self.root, 'rev-parse', 'main').strip(), main)
        self.assertEqual(self.get('/api/project')['videos'][0]['upgrade']['from'], '0.1.9')

    def test_name_cookie_and_hook_precedence(self):
        req = urllib.request.Request(self.base + '/api/name', json.dumps({'name':'Dana Lee'}).encode(),
                                     method='POST', headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as response:
            cookie = response.headers['Set-Cookie'].split(';', 1)[0]
        req = urllib.request.Request(self.base + '/api/name', headers={'Cookie':cookie})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(json.loads(response.read())['name'], 'Dana Lee')
        req = urllib.request.Request(self.base + '/api/notes',
                                     json.dumps({'video':'promo/film','text':'Hello'}).encode(), method='POST',
                                     headers={'Content-Type':'application/json','Cookie':cookie})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(json.loads(response.read())['author'], 'Dana Lee')

    def test_versions_cursor_and_foreign_restore(self):
        self.post('/api/copy', {'video':'promo/film','segment':'intro','key':'title','value':'Two'})
        self.post('/api/copy', {'video':'promo/film','segment':'intro','key':'title','value':'Three'})
        first = self.get('/api/versions?video=promo/film&limit=1')['versions'][0]
        older = self.get('/api/versions?video=promo/film&limit=1&before=' + first['commit'])['versions'][0]
        self.assertEqual(first['n'], older['n'] + 1)
        self.assertEqual(first['kind'], 'edit')
        self.assertEqual(self.post('/api/versions/restore', {'video':'promo/film','commit':'0' * 40})[0], 400)

    def test_attachments_and_timestamp(self):
        data = b'\x89PNG\r\n\x1a\n' + b'abc'
        req = urllib.request.Request(self.base + '/api/attachments?video=promo/film&name=dir%2Fshot.png',
                                     data=data, method='POST', headers={'Content-Type':'image/png'})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 201)
            uploaded = json.loads(response.read())
        self.assertEqual(uploaded['name'], 'shot.png')
        with urllib.request.urlopen(self.base + '/api/attachments/' + uploaded['id']) as response:
            self.assertEqual(response.headers['Content-Security-Policy'], 'sandbox')
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        note = self.post('/api/notes', {'video':'promo/film','text':'Use this','format':'1x1',
                                        'time':0.4,'attachments':[uploaded['id']]})[1]
        self.assertEqual(note['frame'], 12)
        self.assertEqual(note['attachments'][0]['id'], uploaded['id'])
        self.assertTrue((self.editor.notes.session_dir('promo/film') / ('attachments-' + note['id']) / 'shot.png').is_file())
        markdown = (self.editor.notes.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('At 0:00 (frame 12', markdown)
        self.assertIn('/attachments/shot.png', markdown)
        plain = self.post('/api/notes', {'video':'promo/film','text':'General note'})[1]
        self.assertIsNone(plain['frame'])
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get('/api/notes/' + plain['id'] + '.png')
        caught.exception.close()
        self.assertEqual(caught.exception.code, 404)

    def test_cross_origin_attachment_upload_refused_and_content_disposition(self):
        data = b'\x89PNG\r\n\x1a\n' + b'abc'
        req = urllib.request.Request(self.base + '/api/attachments?video=promo/film&name=shot.png',
                                     data=data, method='POST',
                                     headers={'Content-Type': 'image/png', 'Origin': 'http://elsewhere.example'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        with caught.exception:
            self.assertEqual(caught.exception.code, 403)

        req = urllib.request.Request(self.base + '/api/attachments?video=promo/film&name=shot.png',
                                     data=data, method='POST', headers={'Content-Type': 'image/png'})
        with urllib.request.urlopen(req) as response:
            uploaded = json.loads(response.read())
        with urllib.request.urlopen(self.base + '/api/attachments/' + uploaded['id']) as response:
            self.assertEqual(response.headers['Content-Disposition'], 'inline; filename="shot.png"')

        doc = b'%PDF-' + b'abc'
        req = urllib.request.Request(self.base + '/api/attachments?video=promo/film&name=doc.pdf',
                                     data=doc, method='POST', headers={'Content-Type': 'application/pdf'})
        with urllib.request.urlopen(req) as response:
            uploaded_doc = json.loads(response.read())
        with urllib.request.urlopen(self.base + '/api/attachments/' + uploaded_doc['id']) as response:
            self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename="doc.pdf"')

    def test_attachment_limits_magic_and_expiry(self):
        attachments = self.editor.attachments
        attachments.max_file = 4
        self.assertEqual(self._upload(b'12345', 'a.txt', 'text/plain'), 413)
        attachments.max_file = 100
        self.assertEqual(self._upload(b'plain', 'a.png', 'image/png'), 400)
        self.assertEqual(self._upload(b'plain', 'a.exe', 'application/octet-stream'), 400)
        one = self._upload(b'text', '../.note.txt', 'text/plain')
        self.assertEqual(one['name'], 'note.txt')
        attachments.max_files = 0
        self.assertEqual(self.post('/api/notes', {'video':'promo/film','text':'Hi',
                                                  'attachments':[one['id']]})[0], 400)
        attachments.max_files = 10
        attachments.max_message = 3
        self.assertEqual(self.post('/api/notes', {'video':'promo/film','text':'Hi',
                                                  'attachments':[one['id']]})[0], 400)
        meta, _ = attachments.get(one['id'])
        meta['created'] = time.time() - 90000
        (attachments.root / one['id'] / 'meta.json').write_text(json.dumps(meta))
        attachments.expire()
        self.assertFalse((attachments.root / one['id']).exists())

    def _upload(self, data, name, ctype):
        from urllib.parse import quote
        req = urllib.request.Request(self.base + '/api/attachments?video=promo/film&name=' + quote(name),
                                     data=data, method='POST', headers={'Content-Type':ctype})
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code

    def test_real_sandbox_render_of_tiny_example(self):
        import shutil
        import tempfile
        import sys
        from videobuilder.workers import sandbox_command
        if shutil.which('ffmpeg') is None:
            self.skipTest('ffmpeg unavailable')
        try:
            with tempfile.TemporaryDirectory() as home:
                sandbox_command(sys.executable, self.root, home)
        except ValueError as exc:
            self.skipTest('bwrap unavailable: ' + str(exc))
        self.film.write_text("""import videobuilder as vb
T = vb.Timeline(vb.Grid(fps=30, bpm=900), [vb.Segment('tiny', 0, 1)], end=1)
def draw(n, cv):
    cv.rect(0, 0, cv.width, cv.height, '#123456')
FILM = vb.Film(draw=draw, timeline=T, formats=('1x1',))
""")
        git(self.root, 'commit', '-am', 'tiny example')
        sha = git(self.root, 'rev-parse', 'main').strip()
        with tempfile.TemporaryDirectory() as output:
            target = Path(output) / 'tiny.mp4.partial'
            self.editor.renders._render('promo/film', sha, '1x1', target)
            self.assertTrue(target.read_bytes().startswith(b'\x00\x00'))
            self.assertGreater(target.stat().st_size, 1000)

    def test_render_queue_partial_and_eviction(self):
        renders = self.editor.renders
        renders.renderer = lambda video, sha, fmt, output: output.write_bytes(b'mp4')
        first = git(self.root, 'rev-parse', 'main').strip()
        state = renders.request('promo/film', first, '1x1')
        self.assertIn(state['state'], ('queued', 'rendering'))
        deadline = time.monotonic() + 3
        while renders.state('promo/film', first, '1x1')['state'] != 'ready' and time.monotonic() < deadline:
            time.sleep(0.01)
        path = renders.path('promo/film', first, '1x1')
        self.assertEqual(path.read_bytes(), b'mp4')
        self.assertFalse(path.with_suffix('.mp4.partial').exists())
        renders.keep = 1
        (self.root / 'README.md').write_text('next')
        git(self.root, 'commit', '-am', 'next')
        renders.evict('promo/film')
        self.assertFalse(path.exists())

    def test_render_queue_is_shared_across_video_editors(self):
        import threading
        from videobuilder.renders import Renders
        first = self.editor.renders
        second = Renders(self.editor, 1, 20)
        self.addCleanup(second.close)
        entered, release, other_started = threading.Event(), threading.Event(), threading.Event()
        def slow(video, sha, fmt, output):
            entered.set()
            release.wait(3)
            output.write_bytes(b'first')
        def other(video, sha, fmt, output):
            other_started.set()
            output.write_bytes(b'second')
        first.renderer, second.renderer = slow, other
        sha = git(self.root, 'rev-parse', 'main').strip()
        first.request('promo/film', sha, '1x1')
        try:
            self.assertTrue(entered.wait(2))
            second.request('promo/film', sha, '16x9')
            self.assertFalse(other_started.wait(0.2))
        finally:
            release.set()
        self.assertTrue(other_started.wait(2))
        second.close()

    def test_video_range_and_failed_render(self):
        sha = git(self.root, 'rev-parse', 'main').strip()
        path = self.editor.renders.path('promo/film', sha, '1x1')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'0123456789')
        def get_range(spec):
            req = urllib.request.Request(self.base + '/api/video?video=promo/film&format=1x1',
                                         headers={'Range':spec})
            try:
                with urllib.request.urlopen(req) as response:
                    return response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                with exc:
                    return exc.code, exc.read(), exc.headers
        self.assertEqual(get_range('bytes=0-')[0:2], (206, b'0123456789'))
        self.assertEqual(get_range('bytes=2-5')[0:2], (206, b'2345'))
        self.assertEqual(get_range('bytes=-3')[0:2], (206, b'789'))
        self.assertEqual(get_range('bytes=20-')[0], 416)
        self.assertEqual(get_range('bytes=2-5')[2]['ETag'], f'"{sha}-1x1"')
        path.unlink()
        self.editor.renders.status[('promo/film', sha, '1x1')] = {'state':'failed','error':'render failed','log':'boom'}
        req = urllib.request.Request(self.base + '/api/video?video=promo/film&format=1x1')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        with caught.exception:
            self.assertIn('boom', caught.exception.read().decode())
        self.editor.renders.renderer = lambda video, sha, fmt, output: output.write_bytes(b'retried')
        code, retried = self.post('/api/video/retry', {'video':'promo/film','commit':sha,'format':'1x1'})
        self.assertEqual(code, 202)
        self.assertIn(retried['state'], ('queued', 'rendering'))
        deadline = time.monotonic() + 3
        while self.editor.renders.state('promo/film', sha, '1x1')['state'] != 'ready' and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(path.read_bytes(), b'retried')

    def test_thumbnail_404s_with_nothing_rendered_yet(self):
        req = urllib.request.Request(self.base + '/api/thumbnail')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        with caught.exception:
            self.assertEqual(caught.exception.code, 404)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_thumbnail_grabs_a_frame_and_caches_it(self):
        sha = git(self.root, 'rev-parse', 'main').strip()
        path = self.editor.renders.path('promo/film', sha, '16x9')
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=320x180:d=4:r=5',
                        '-pix_fmt', 'yuv420p', str(path)], check=True, capture_output=True)
        with patch('videobuilder.thumbnails._grab_frame', wraps=thumbnails._grab_frame) as spy:
            data = self.get('/api/thumbnail')
            self.assertEqual(data[:3], b'\xff\xd8\xff')  # JPEG magic
            again = self.get('/api/thumbnail')
        self.assertEqual(again, data)
        self.assertEqual(spy.call_count, 1)  # the second request never re-runs ffmpeg

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_thumbnail_survives_its_render_being_evicted(self):
        sha = git(self.root, 'rev-parse', 'main').strip()
        path = self.editor.renders.path('promo/film', sha, '16x9')
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=red:s=320x180:d=4:r=5',
                        '-pix_fmt', 'yuv420p', str(path)], check=True, capture_output=True)
        data = self.get('/api/thumbnail')
        self.editor.renders.keep = 1
        (self.root / 'README.md').write_text('next')
        git(self.root, 'commit', '-am', 'next')
        self.editor.renders.evict('promo/film')
        self.assertFalse(path.exists())  # the render itself is gone
        self.assertEqual(self.get('/api/thumbnail'), data)  # the cached thumbnail still serves

    def test_video_and_retry_refuse_a_commit_not_on_main(self):
        git(self.root, 'checkout', '-b', 'side')
        (self.root / 'promo' / 'extra.txt').write_text('x')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'side commit')
        off_main = git(self.root, 'rev-parse', 'HEAD').strip()
        git(self.root, 'checkout', 'main')
        req = urllib.request.Request(self.base + f'/api/video?video=promo/film&commit={off_main}&format=1x1')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        with caught.exception:
            self.assertEqual(caught.exception.code, 400)
        code, err = self.post('/api/video/retry', {'video': 'promo/film', 'commit': off_main, 'format': '1x1'})
        self.assertEqual(code, 400, err)
