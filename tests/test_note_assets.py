"""A note's font/sfx/music chips (suggest.js): picked only, never typed; their
ids are never trusted blind either -- editor.add_note/start_video re-check
each one against the real catalog (fonts.ids(), the sfx pack, the configured
music sources) before it ever reaches a note, the same way _note_capabilities
re-checks a capability id (see test_note_capabilities.py)."""
import unittest

from videobuilder.editor import Editor, HTTPError
from videobuilder.music import MusicLibrary, Source
from tests.test_notes import FakeAgent
from tests.test_project import TempProject

TRACK = {'id': 'track-1', 'title': 'Theme', 'audio_url': 'https://example.com/t.mp3', 'tags': ['calm']}


def _music_library():
    source = Source('test-source', 'Test Music', 'CC0', 'entry_point', func=lambda cfg: [TRACK], config=None)
    return MusicLibrary([source])


class NoteAssets(TempProject):
    def setUp(self):
        super().setUp()
        self.backend = FakeAgent()
        self.editor = Editor(self.root, backend=self.backend, unsandboxed_previews=True, auto_land=False,
                             music=_music_library())
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)

    def test_add_note_keeps_only_known_font_ids(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='Set it in a font', fonts=['inter', 'not-a-real-font']),
            'reviewer')
        self.assertEqual(note['fonts'], ['inter'])

    def test_add_note_keeps_only_known_sfx_ids(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='Add a whoosh', sfx=['whoosh_fast/tight', 'not-a-real-sound']),
            'reviewer')
        self.assertEqual(note['sfx'], ['whoosh_fast/tight'])

    def test_add_note_keeps_only_known_music_ids(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='Add music', music=['track-1', 'not-a-real-track']),
            'reviewer')
        self.assertEqual(note['music'], ['track-1'])

    def test_add_note_with_no_fields_gets_empty_lists(self):
        note = self.editor.add_note(dict(video='promo/film', frame=0, text='Just text'), 'reviewer')
        self.assertEqual(note['fonts'], [])
        self.assertEqual(note['sfx'], [])
        self.assertEqual(note['music'], [])

    def test_add_note_rejects_a_non_list_fonts_field(self):
        with self.assertRaises(HTTPError):
            self.editor.add_note(dict(video='promo/film', frame=0, text='x', fonts='inter'), 'reviewer')

    def test_add_note_rejects_a_non_list_sfx_field(self):
        with self.assertRaises(HTTPError):
            self.editor.add_note(dict(video='promo/film', frame=0, text='x', sfx='whoosh_fast/tight'), 'reviewer')

    def test_add_note_rejects_a_non_list_music_field(self):
        with self.assertRaises(HTTPError):
            self.editor.add_note(dict(video='promo/film', frame=0, text='x', music='track-1'), 'reviewer')

    def test_add_note_rejects_a_list_with_a_non_string_entry(self):
        with self.assertRaises(HTTPError):
            self.editor.add_note(dict(video='promo/film', frame=0, text='x', sfx=[1]), 'reviewer')

    def test_add_note_dedups_repeated_ids(self):
        note = self.editor.add_note(
            dict(video='promo/film', frame=0, text='x', fonts=['inter', 'inter']), 'reviewer')
        self.assertEqual(note['fonts'], ['inter'])

    def test_start_video_keeps_only_known_ids(self):
        note = self.editor.start_video(
            dict(description='A promo video', fonts=['inter', 'nope'], sfx=['whoosh_fast/tight', 'nope'],
                music=['track-1', 'nope']), 'reviewer')
        self.assertEqual(note['fonts'], ['inter'])
        self.assertEqual(note['sfx'], ['whoosh_fast/tight'])
        self.assertEqual(note['music'], ['track-1'])

    def test_music_ids_drop_silently_with_no_music_configured(self):
        backend = FakeAgent()
        editor = Editor(self.root, backend=backend, unsandboxed_previews=True, auto_land=False)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        note = editor.add_note(dict(video='promo/film', frame=0, text='x', music=['track-1']), 'reviewer')
        self.assertEqual(note['music'], [])


if __name__ == '__main__':
    unittest.main()
