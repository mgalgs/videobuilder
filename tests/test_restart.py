"""An editor restart (deploy, crash) mid-job: each kind of background work is
picked up again by the next process, or ends visibly, never stuck."""
import time
import unittest
from unittest import mock

from videobuilder.editor import Editor
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


if __name__ == '__main__':
    unittest.main()
