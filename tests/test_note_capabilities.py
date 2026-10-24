"""A note's #id capability chips (suggest.js): the client's list is never
trusted blind -- editor.add_note/start_video re-check every id against the
catalog and the registry (capabilities.resolve_requested) before it ever
reaches a note, dropping anything unknown, the same way an attachment id is
validated before it is trusted. A chip may also carry an {id, settings}
object (its settings card's non-default picks, e.g. narration's voice and
speed); those values are re-validated too, never the client's own word for
it -- see capabilities/settings.py's validate/non_default."""
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

    def test_add_note_drops_a_capabilitys_settings_that_are_all_default(self):
        # af_heart is narration's only voice in this environment (no Kokoro model installed)
        # and also its default, so an unknown voice falls back to it -- a value equal to the
        # default, dropped same as if the chip's card was never touched.
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='Narrate it',
                capabilities=[{'id': 'narration', 'settings': {'voice': 'not-a-real-voice'}}]), 'reviewer')
        self.assertEqual(note['capabilities'], ['narration'])

    def test_add_note_clamps_an_out_of_range_setting_and_keeps_it(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='Narrate it',
                capabilities=[{'id': 'narration', 'settings': {'speed': 5.0}}]), 'reviewer')
        self.assertEqual(note['capabilities'], [{'id': 'narration', 'settings': {'speed': 2.0}}])

    def test_add_note_drops_an_unknown_capabilitys_settings_too(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='x',
                capabilities=[{'id': 'not-a-real-capability', 'settings': {'speed': 2.0}}]), 'reviewer')
        self.assertEqual(note['capabilities'], [])

    def test_add_note_drops_a_malformed_capability_object(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='x',
                capabilities=[{'id': 123}, {'notid': 'x'}, 'map-route-draw']), 'reviewer')
        self.assertEqual(note['capabilities'], ['map-route-draw'])

    def test_start_video_keeps_capability_settings_too(self):
        note = self.editor.start_video(
            dict(description='A promo video',
                capabilities=[{'id': 'narration', 'settings': {'speed': 0.5}}]), 'reviewer')
        self.assertEqual(note['capabilities'], [{'id': 'narration', 'settings': {'speed': 0.5}}])


if __name__ == '__main__':
    unittest.main()
