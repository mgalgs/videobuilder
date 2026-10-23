"""A note's #id capability chips (suggest.js): the client's list is never
trusted blind -- editor.add_note/start_video re-check every id against the
catalog and the registry (capabilities.resolve_requested) before it ever
reaches a note, dropping anything unknown, the same way an attachment id is
validated before it is trusted."""
import unittest

from videobuilder.editor import Editor, HTTPError
from tests.test_notes import FakeAgent
from tests.test_project import TempProject


class NoteCapabilities(TempProject):
    def setUp(self):
        super().setUp()
        self.backend = FakeAgent()
        self.editor = Editor(self.root, backend=self.backend, unsandboxed_previews=True, auto_land=False)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)

    def test_add_note_keeps_only_known_capability_ids(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='Add a map',
                capabilities=['map-route-draw', 'not-a-real-capability']), 'reviewer')
        self.assertEqual(note['capabilities'], ['map-route-draw'])

    def test_add_note_with_no_capabilities_field_gets_an_empty_list(self):
        note = self.editor.add_note(dict(video='promo/film', frame=0, text='Just text'), 'reviewer')
        self.assertEqual(note['capabilities'], [])

    def test_add_note_rejects_a_non_list_capabilities_field(self):
        with self.assertRaises(HTTPError):
            self.editor.add_note(dict(video='promo/film', frame=0, text='x', capabilities='map-route-draw'),
                                 'reviewer')

    def test_add_note_rejects_a_list_with_a_non_string_entry(self):
        with self.assertRaises(HTTPError):
            self.editor.add_note(dict(video='promo/film', frame=0, text='x', capabilities=[1]), 'reviewer')

    def test_start_video_keeps_only_known_capability_ids(self):
        note = self.editor.start_video(
            dict(description='A promo video', capabilities=['look-melt', 'not-a-real-capability']), 'reviewer')
        self.assertEqual(note['capabilities'], ['look-melt'])


if __name__ == '__main__':
    unittest.main()
