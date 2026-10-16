"""An editor restart (deploy, crash) mid-job: each kind of background work is
picked up again by the next process, or ends visibly, never stuck."""
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from videobuilder.editor import UPDATING, Editor, Server, _drain, make_handler
from tests.test_project import TempProject


class Restart(TempProject):
    def editor(self):
        editor = Editor(self.root, state_dir='state', unsandboxed_previews=True, auto_land=False)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def wait(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(0.05)
        self.fail('timed out')


class Gathering(Restart):
    def test_an_interrupted_crawl_runs_again_at_startup(self):
        # The first process saved the note and then died before its crawl thread finished.
        old = self.editor()
        note = old.notes.start_gathering('promo/film', '16x9', text='A launch video.', attachments=[],
                                         gather={'description': 'A launch video.', 'links': ['https://a.example']})
        with mock.patch('videobuilder.gather.crawl', return_value=([], [('https://a.example', 'timed out')])) as crawl:
            new = self.editor()
            done = self.wait(lambda: (n := new.notes.get(note['id']))['state'] != 'gathering' and n)
        crawl.assert_called_once_with(['https://a.example'])
        self.assertIn('A launch video.', done['text'])
        self.assertIn('- https://a.example: timed out', done['text'])
        self.assertNotIn('interrupted', done['text'])

    def test_a_note_without_its_links_is_queued_on_the_next_tick_not_after_the_stale_window(self):
        old = self.editor()
        note = old.notes.start_gathering('promo/film', '16x9', text='A launch video.')
        new = self.editor()
        new.notes.tick()
        done = new.notes.get(note['id'])
        self.assertNotEqual(done['state'], 'gathering')
        self.assertIn('the crawl was interrupted', done['text'])


class Rendering(Restart):
    def test_a_killed_render_leaves_nothing_that_reads_as_ready_and_is_asked_for_again(self):
        old = self.editor()
        old.renders.close()
        sha = '0' * 40
        output = old.renders.path('promo/film', sha, '16x9')
        output.parent.mkdir(parents=True, exist_ok=True)
        partial = output.with_suffix('.mp4.partial')
        partial.write_bytes(b'half a video')
        scratch = old.renders.root / 'render-abc123'
        (scratch / 'output').mkdir(parents=True)
        new = self.editor()
        new.renders.close()  # keep the worker off the queue, so the state below is just what was asked
        self.assertFalse(partial.exists())
        self.assertFalse(scratch.exists())
        self.assertEqual(new.renders.state('promo/film', sha, '16x9'), {'state': 'none'})
        # The player's next poll (GET api/video) re-requests it.
        self.assertEqual(new.renders.request('promo/film', sha, '16x9')['state'], 'queued')

    def test_a_render_cut_off_by_the_drain_still_reads_as_rendering_not_failed(self):
        editor = self.editor()
        started = threading.Event()

        def renderer(video, sha, fmt, output):
            started.set()
            editor.renders.stopping.wait(10)
            raise ValueError('render stopped')
        editor.renders.renderer = renderer
        sha = '0' * 40
        editor.renders.request('promo/film', sha, '16x9')
        self.assertTrue(started.wait(10))
        editor.renders.close()
        # Reads keep answering during the drain; the tab's poll must not turn into an error.
        self.assertEqual(editor.renders.state('promo/film', sha, '16x9'), {'state': 'rendering'})


class Draining(Restart):
    def setUp(self):
        super().setUp()
        self.release = threading.Event()
        self.started = threading.Event()
        test = self

        class Slow(make_handler(self.editor())):
            def _handle(self, method):
                if method == 'POST' and self.path == '/slow':
                    test.started.set()
                    test.release.wait(10)
                    return self._json(200, {'done': True})
                return super()._handle(method)

        self.httpd = Server(('127.0.0.1', 0), Slow)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.addCleanup(self.release.set)

    def post(self, path):
        req = urllib.request.Request(self.base + path, b'{}', method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_a_write_in_flight_finishes_new_ones_are_refused_and_reads_still_answer(self):
        results = []
        writer = threading.Thread(target=lambda: results.append(self.post('/slow')))
        writer.start()
        self.assertTrue(self.started.wait(10))
        stop, loop = threading.Event(), threading.Thread(target=lambda: None)
        loop.start()
        renders_stopped = []
        drained = []
        drainer = threading.Thread(target=lambda: drained.append(
            _drain(self.httpd, stop, [loop], lambda: renders_stopped.append(True), time.monotonic() + 10)))
        drainer.start()
        self.wait(lambda: self.httpd.draining)
        self.assertEqual(self.post('/api/notes'), (503, {'error': UPDATING}))
        with urllib.request.urlopen(self.base + '/api/project', timeout=20) as r:
            self.assertEqual(r.status, 200)
        # An open tab waiting out the restart must not take the old process for the new one.
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(self.base + '/healthz', timeout=20)
        e.exception.close()
        self.assertEqual(e.exception.code, 503)
        self.assertTrue(drainer.is_alive())
        self.release.set()
        drainer.join(10)
        writer.join(10)
        self.assertEqual(drained, [True])
        self.assertEqual(results, [(200, {'done': True})])
        self.assertTrue(stop.is_set())
        self.assertEqual(renders_stopped, [True])

    def test_a_write_that_never_finishes_does_not_hold_the_drain_past_its_deadline(self):
        threading.Thread(target=self.post, args=('/slow',), daemon=True).start()
        self.assertTrue(self.started.wait(10))
        began = time.monotonic()
        self.assertFalse(_drain(self.httpd, threading.Event(), [], lambda: None, began + 0.5))
        self.assertLess(time.monotonic() - began, 3)


class DirectorDuringARestart(unittest.TestCase):
    def test_a_failed_request_shows_the_banner_pauses_polling_and_keeps_the_draft(self):
        import re
        from pathlib import Path
        pkg = Path(__file__).resolve().parent.parent / 'videobuilder'
        js = (pkg / 'director.js').read_text()
        self.assertIn('id="restart-banner"', (pkg / 'editor.html').read_text())
        body = lambda name: re.search(r'function ' + name + r'\([^)]*\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertIn('await reach(api(path,params)', body('json'))
        # Only the drain's own 503 means a restart; the editor's JSON 502s (music upstream) are real errors.
        self.assertIn('if(draining(r.status,data))return restarting()', body('httpError'))
        self.assertNotIn('GATEWAY', body('httpError'))
        self.assertTrue(UPDATING.startswith(re.search(r"startsWith\('([^']+)'\)", js[js.index('const draining'):])[1]))
        self.assertIn("$('restart-banner').hidden=false", body('restarting'))
        # Only the new process's ok counts: the draining one answers 503 (see _get_healthz).
        self.assertIn("r.ok&&(await r.text()).startsWith('ok ')", body('waitForEditor'))
        back = body('editorBack')
        for call in ("$('restart-banner').hidden=true", 'loadNotes()', 'loadVersions()', 'loadPlayer()'):
            self.assertIn(call, back)
        for guard in ('state.video&&!state.signedOut&&!state.restarting', 'state.signedOut||state.restarting'):
            self.assertIn(guard, js)
        # A render poll cut off by the restart waits for editorBack rather than offering a retry.
        player = body('loadPlayer')
        self.assertLess(player.index('if(state.restarting)return'), player.index("$('retry-render').hidden=false"))
        # The draft, pending list and picked files are cleared only after a send succeeds
        # (pinned in test_editor's signed-out test); a failed upload leaves state.files as it was.
        self.assertNotIn('state.files=', body('uploadFiles'))


class Sigterm(TempProject):
    def test_sigterm_reaches_the_editor_and_it_exits_cleanly(self):
        proc = subprocess.Popen([sys.executable, '-m', 'videobuilder', 'editor', str(self.root), '--port', '0',
                                 '--unsandboxed-previews'],
                                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                stderr=subprocess.PIPE, text=True)
        self.addCleanup(proc.stderr.close)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        url = None
        for line in proc.stderr:
            if m := re.search(r'at (http://\S+/)', line):
                url = m[1]
                break
        self.assertIsNotNone(url)
        with urllib.request.urlopen(url + 'healthz', timeout=20) as r:
            self.assertEqual(r.status, 200)
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=20), 0)
        self.assertIn('finishing work in flight', proc.stderr.read())


if __name__ == '__main__':
    unittest.main()
