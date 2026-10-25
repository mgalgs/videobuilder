"""A note's font/sfx/music chips (suggest.js): picked only, never typed; their
ids are never trusted blind either -- editor.add_note/start_video re-check
each one against the real catalog (fonts.ids(), the sfx pack, the configured
music sources) before it ever reaches a note, the same way _note_capabilities
re-checks a capability id (see test_note_capabilities.py)."""
import unittest

from videobuilder.editor import Editor, HTTPError
from videobuilder.music import MusicLibrary, Source
from tests.fixtures import settle
from tests.test_editor import _MusicServer
from tests.test_notes import FakeAgent
from tests.test_project import TempProject

# A closed local port: refused instantly, unlike a DNS name, so a test that never
# means to actually fetch audio doesn't pay FETCH_TIMEOUT for every note it adds.
TRACK = {'id': 'track-1', 'title': 'Theme', 'audio_url': 'http://127.0.0.1:1/t.mp3', 'tags': ['calm']}


def _music_library(on_fetch=None, tracks=None):
    def func(cfg):
        if on_fetch:
            on_fetch()
        return tracks if tracks is not None else [TRACK]
    source = Source('test-source', 'Test Music', 'CC0', 'entry_point', func=func, config=None)
    return MusicLibrary([source])


class NoteAssets(TempProject):
    def setUp(self):
        super().setUp()
        self.backend = FakeAgent()
        self.editor = Editor(self.root, backend=self.backend, unsandboxed_previews=True, auto_land=False,
                             music=_music_library())
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)
        self.editors = [self.editor]

    def tearDown(self):
        settle(*self.editors)  # before the project dir goes: a submitter may still be writing to it
        super().tearDown()

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
        self.editors.append(editor)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        note = editor.add_note(dict(video='promo/film', frame=0, text='x', music=['track-1']), 'reviewer')
        self.assertEqual(note['music'], [])

    def test_a_note_with_no_music_pick_never_fetches_the_catalog(self):
        fetches = []
        backend = FakeAgent()
        editor = Editor(self.root, backend=backend, unsandboxed_previews=True, auto_land=False,
                        music=_music_library(on_fetch=lambda: fetches.append(1)))
        self.editors.append(editor)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        note = editor.add_note(dict(video='promo/film', frame=0, text='Just text'), 'reviewer')
        self.assertEqual(note['music'], [])
        settle(editor)  # nor does its background submission
        self.assertEqual(fetches, [])


class MusicAttach(TempProject):
    """A note's picked music chip reaches the builder the same way the Music
    panel's "use this track" does: added as an ordinary attachment, with its
    credit, and named in the prompt -- see editor._attach_music, music.
    attach_track, and prompt._resolved_assets/_requested_assets_lines."""

    TRACK_MP3 = b'ID3' + b'\x00' * 7 + b'fake mp3 bytes for the test'

    def setUp(self):
        super().setUp()
        self.server = _MusicServer({'/track.mp3': (self.TRACK_MP3, 'audio/mpeg')})
        self.addCleanup(self.server.close)
        self.backend = FakeAgent()
        self.editors = []

    def tearDown(self):
        settle(*self.editors)  # before the project dir goes: a submitter may still be writing to it
        super().tearDown()

    def _editor(self, tracks):
        editor = Editor(self.root, backend=self.backend, unsandboxed_previews=True, auto_land=False,
                        music=_music_library(tracks=tracks))
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        self.editors.append(editor)
        return editor

    def test_a_picked_track_is_attached_with_its_credit(self):
        track = {'id': 'track-1', 'title': 'Theme', 'audio_url': self.server.base + '/track.mp3',
                 'tags': ['calm'], 'creator': 'Jane', 'year': '2020'}
        editor = self._editor([track])
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music', music=['track-1']), 'reviewer')
        self.assertEqual(note['music'], ['track-1'])
        attached = [a for a in note['attachments'] if a.get('music_track') == 'track-1']
        self.assertEqual(len(attached), 1, note['attachments'])
        record = attached[0]
        self.assertEqual(record['name'], 'Theme.mp3')
        self.assertEqual(record['type'], 'audio/mpeg')
        self.assertEqual(record['credit'], {'title': 'Theme', 'creator': 'Jane', 'year': '2020',
                                            'license': 'CC0', 'item_url': None})
        stored = editor.attachments.get(record['id'], 'promo/film')[1].read_bytes()
        self.assertEqual(stored, self.TRACK_MP3)

    def test_a_picked_disputed_tracks_credit_names_the_dispute(self):
        track = {'id': 'track-1', 'title': 'Old Disc', 'audio_url': self.server.base + '/track.mp3',
                 'tags': [], 'license': 'Public domain', 'disputed': True}
        editor = self._editor([track])
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music', music=['track-1']), 'reviewer')
        [record] = [a for a in note['attachments'] if a.get('music_track') == 'track-1']
        self.assertTrue(record['credit']['disputed'])
        from videobuilder import prompt
        md = prompt.render(note, note, None, music=editor.music)
        self.assertIn('-- credit: Old Disc, rights disputed, Public domain', md)

    def test_the_prompt_names_the_attachment(self):
        track = {'id': 'track-1', 'title': 'Theme', 'audio_url': self.server.base + '/track.mp3', 'tags': ['calm']}
        editor = self._editor([track])
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music', music=['track-1']), 'reviewer')
        from videobuilder import prompt
        md = prompt.render(note, note, None, music=editor.music)
        self.assertIn('use /attachments/Theme.mp3 as this track.', md)

    def test_a_note_rejected_by_a_cheap_check_never_fetches_its_track(self):
        from unittest import mock
        from videobuilder import music
        track = {'id': 'track-1', 'title': 'Theme', 'audio_url': self.server.base + '/track.mp3'}
        editor = self._editor([track])
        with mock.patch.object(music, 'attach_track', wraps=music.attach_track) as attach:
            with self.assertRaises(HTTPError):
                editor.add_note(dict(video='promo/film', frame=0, text='x', music=['track-1'],
                                     format='no-such-format'), 'reviewer')
            with self.assertRaises(HTTPError):
                editor.add_note(dict(video='promo/film', text='', music=['track-1'],
                                     links=['https://example.com/']), 'reviewer')
            self.assertEqual(attach.call_count, 0)

    def test_a_failing_fetch_still_adds_the_note_and_the_prompt_says_so(self):
        editor = self._editor([TRACK])  # TRACK's audio_url is a closed local port
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music', music=['track-1']), 'reviewer')
        stored = editor.notes.get(note['id'])  # the note really was added, not just returned
        self.assertEqual(stored['music'], ['track-1'])
        self.assertFalse([a for a in stored['attachments'] if a.get('music_track') == 'track-1'])
        from videobuilder import prompt
        md = prompt.render(note, note, None, music=editor.music)
        self.assertIn('could not be fetched', md)

    def test_two_picks_with_the_same_title_get_distinct_attachment_names(self):
        other = b'ID3' + b'\x00' * 7 + b'different fake mp3 bytes'
        self.server.routes['/track2.mp3'] = (other, 'audio/mpeg')
        track1 = {'id': 'track-1', 'title': 'Theme', 'audio_url': self.server.base + '/track.mp3', 'tags': []}
        track2 = {'id': 'track-2', 'title': 'Theme', 'audio_url': self.server.base + '/track2.mp3', 'tags': []}
        editor = self._editor([track1, track2])
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music',
                                    music=['track-1', 'track-2']), 'reviewer')
        attached = {a['music_track']: a for a in note['attachments'] if a.get('music_track')}
        self.assertEqual(set(attached), {'track-1', 'track-2'})
        names = {a['name'] for a in attached.values()}
        self.assertEqual(len(names), 2, names)  # one must not have overwritten the other's file
        contents = {editor.attachments.get(a['id'], 'promo/film')[1].read_bytes() for a in attached.values()}
        self.assertEqual(contents, {self.TRACK_MP3, other})

    def test_music_picks_are_capped_by_the_note_attachment_file_limit(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\nattachment_max_files = 1\n')
        other = b'ID3' + b'\x00' * 7 + b'different fake mp3 bytes'
        self.server.routes['/track2.mp3'] = (other, 'audio/mpeg')
        track1 = {'id': 'track-1', 'title': 'One', 'audio_url': self.server.base + '/track.mp3', 'tags': []}
        track2 = {'id': 'track-2', 'title': 'Two', 'audio_url': self.server.base + '/track2.mp3', 'tags': []}
        editor = self._editor([track1, track2])
        self.assertEqual(editor.attachments.max_files, 1)
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music',
                                    music=['track-1', 'track-2']), 'reviewer')
        attached = [a for a in note['attachments'] if a.get('music_track')]
        self.assertEqual(len(attached), 1, attached)
        self.assertEqual(sorted(note['music']), ['track-1', 'track-2'])


    def test_a_pick_over_the_file_limit_is_reported_as_over_budget_not_unfetched(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\nattachment_max_files = 1\n')
        other = b'ID3' + b'\x00' * 7 + b'different fake mp3 bytes'
        self.server.routes['/track2.mp3'] = (other, 'audio/mpeg')
        track1 = {'id': 'track-1', 'title': 'One', 'audio_url': self.server.base + '/track.mp3', 'tags': []}
        track2 = {'id': 'track-2', 'title': 'Two', 'audio_url': self.server.base + '/track2.mp3', 'tags': []}
        editor = self._editor([track1, track2])
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music',
                                    music=['track-1', 'track-2']), 'reviewer')
        self.assertEqual(note['music_over_budget'], ['track-2'])
        from videobuilder import prompt
        md = prompt.render(note, note, None, music=editor.music)
        self.assertIn('use /attachments/One.mp3 as this track.', md)
        self.assertIn('"Two" (Test Music): left off because it would exceed this note\'s attachment limits', md)
        self.assertNotIn('could not be fetched', md)

    def test_a_pick_over_the_message_size_limit_is_reported_as_over_budget(self):
        track = {'id': 'track-1', 'title': 'Theme', 'audio_url': self.server.base + '/track.mp3', 'tags': []}
        editor = self._editor([track])
        editor.attachments.max_message = len(self.TRACK_MP3) - 1
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music', music=['track-1']), 'reviewer')
        self.assertFalse([a for a in note['attachments'] if a.get('music_track')])
        self.assertEqual(note['music_over_budget'], ['track-1'])
        from videobuilder import prompt
        md = prompt.render(note, note, None, music=editor.music)
        self.assertIn("left off because it would exceed this note's attachment limits", md)
        self.assertNotIn('could not be fetched', md)

    def test_a_failed_fetch_is_not_marked_over_budget(self):
        editor = self._editor([TRACK])  # TRACK's audio_url is a closed local port
        note = editor.add_note(dict(video='promo/film', frame=0, text='Add music', music=['track-1']), 'reviewer')
        self.assertNotIn('music_over_budget', note)
        from videobuilder import prompt
        md = prompt.render(note, note, None, music=editor.music)
        self.assertIn('could not be fetched', md)
        self.assertNotIn('attachment limits', md)

if __name__ == '__main__':
    unittest.main()
