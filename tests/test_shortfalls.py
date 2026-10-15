"""Machine-readable shortfall records on builder replies: parsing and storage
(strip_shortfalls, NoteStore), and the fake agent's test support for it."""
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_notes import FakeAgent
from tests.test_project import TempProject, git
from videobuilder.agents import FakeBackend
from videobuilder.editor import Editor
from videobuilder.notes import AgentStatus, NoteStore, strip_shortfalls


def block(items):
    return '```shortfalls\n' + json.dumps({'shortfalls': items}) + '\n```\n'


class StripShortfalls(unittest.TestCase):
    def test_a_valid_block_is_parsed_and_removed(self):
        reply = ('Could not find real footage; built a stylized stand-in instead.\n\n' +
                block([{'kind': 'cannot', 'what': 'film real people on location'}]) +
                'Summary: built a stand-in.')
        cleaned, shortfalls = strip_shortfalls(reply)
        self.assertEqual(shortfalls, [{'kind': 'cannot', 'what': 'film real people on location'}])
        self.assertNotIn('```', cleaned)
        self.assertNotIn('"kind"', cleaned)
        self.assertIn('Summary: built a stand-in.', cleaned)

    def test_two_entries_both_kinds(self):
        items = [{'kind': 'cannot', 'what': 'a real human voice'}, {'kind': 'weak', 'what': 'lip sync timing'}]
        cleaned, shortfalls = strip_shortfalls('Done.\n\n' + block(items))
        self.assertEqual(shortfalls, items)
        self.assertEqual(cleaned, 'Done.')

    def test_no_block_is_an_ordinary_reply(self):
        self.assertEqual(strip_shortfalls('Just a plain reply.'), ('Just a plain reply.', None))
        self.assertEqual(strip_shortfalls(None), (None, None))
        self.assertEqual(strip_shortfalls(''), ('', None))

    def test_malformed_json_is_stripped_but_not_recorded(self):
        cleaned, shortfalls = strip_shortfalls('Done.\n\n```shortfalls\nnot json\n```\nSummary: done.')
        self.assertIsNone(shortfalls)
        self.assertNotIn('```', cleaned)
        self.assertNotIn('not json', cleaned)

    def test_wrong_top_level_shape_is_invalid(self):
        self.assertIsNone(strip_shortfalls('Done.\n\n```shortfalls\n' + json.dumps([1, 2]) + '\n```\n')[1])
        self.assertIsNone(strip_shortfalls('Done.\n\n```shortfalls\n' +
                                           json.dumps({'shortfalls': 'nope'}) + '\n```\n')[1])

    def test_bad_kind_is_invalid(self):
        _, shortfalls = strip_shortfalls('Done.\n\n' + block([{'kind': 'nope', 'what': 'x'}]))
        self.assertIsNone(shortfalls)

    def test_empty_or_overlong_what_is_invalid(self):
        for what in ('', '   ', 'x' * 161):
            _, shortfalls = strip_shortfalls('Done.\n\n' + block([{'kind': 'cannot', 'what': what}]))
            self.assertIsNone(shortfalls, what)

    def test_zero_or_six_entries_is_invalid(self):
        _, shortfalls = strip_shortfalls('Done.\n\n```shortfalls\n' + json.dumps({'shortfalls': []}) + '\n```\n')
        self.assertIsNone(shortfalls)
        six = [{'kind': 'weak', 'what': f'thing {i}'} for i in range(6)]
        _, shortfalls = strip_shortfalls('Done.\n\n' + block(six))
        self.assertIsNone(shortfalls)

    def test_one_to_five_entries_is_valid(self):
        five = [{'kind': 'weak', 'what': f'thing {i}'} for i in range(5)]
        _, shortfalls = strip_shortfalls('Done.\n\n' + block(five))
        self.assertEqual(shortfalls, five)

    def test_last_block_wins(self):
        reply = block([{'kind': 'cannot', 'what': 'first'}]) + '\n' + block([{'kind': 'weak', 'what': 'second'}])
        _, shortfalls = strip_shortfalls(reply)
        self.assertEqual(shortfalls, [{'kind': 'weak', 'what': 'second'}])

    def test_what_and_kind_are_trimmed_of_surrounding_whitespace(self):
        _, shortfalls = strip_shortfalls('Done.\n\n' + block([{'kind': 'weak', 'what': '  a rough edge  '}]))
        self.assertEqual(shortfalls, [{'kind': 'weak', 'what': 'a rough edge'}])


class ShortfallsOnTheNote(unittest.TestCase):
    """Through NoteStore._poll, with a FakeAgent standing in for the backend
    (same pattern as tests/test_notes.py)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name, 'notes')

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_ordinary_reply_with_a_valid_block(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make a photorealistic shot', b'')
        reply = ('Built a stylized version instead.\n\n' +
                block([{'kind': 'cannot', 'what': 'photorealistic rendering'}]) +
                'Summary: used a stylized look instead.')
        agent.states[note['handle']] = AgentStatus('replied', reply, 'notes/branch')
        got = store.list('promo/film')[0]
        self.assertEqual(got['state'], 'replied')
        self.assertNotIn('```', got['reply'])
        self.assertEqual(got['shortfalls'], [{'kind': 'cannot', 'what': 'photorealistic rendering'}])

    def test_a_questions_reply_with_a_valid_block_before_it(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Add a cameo', b'')
        reply = ('Quick check first.\n\n' +
                block([{'kind': 'weak', 'what': 'matching the exact voice'}]) +
                '\n```questions\n' + json.dumps(
                    {'questions': [{'text': 'Use a narrator instead?', 'choices': ['Yes', 'No']}]}) +
                '\n```\n')
        agent.states[note['handle']] = AgentStatus('replied', reply, None)
        got = store.list('promo/film')[0]
        self.assertEqual(got['state'], 'questions')
        self.assertEqual(got['reply'], 'Quick check first.')
        self.assertNotIn('```', got['reply'])
        self.assertEqual(got['shortfalls'], [{'kind': 'weak', 'what': 'matching the exact voice'}])
        self.assertEqual(got['questions'], [{'text': 'Use a narrator instead?', 'choices': ['Yes', 'No']}])

    def test_an_invalid_block_is_stripped_but_not_recorded(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make it louder', b'')
        reply = 'Done.\n\n```shortfalls\nnot json\n```\nSummary: done.'
        agent.states[note['handle']] = AgentStatus('replied', reply, 'notes/branch')
        got = store.list('promo/film')[0]
        self.assertNotIn('shortfalls', got)
        self.assertNotIn('```', got['reply'])

    def test_no_block_means_no_field_at_all(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make it louder', b'')
        agent.states[note['handle']] = AgentStatus('replied', 'Done: made it louder.', 'notes/branch')
        got = store.list('promo/film')[0]
        self.assertNotIn('shortfalls', got)


class FakeBackendShortfallSupport(TempProject):
    """End to end with the real FakeBackend (git commits included), confirming its
    `shortfalls` parameter, and that the field reaches the notes list unchanged --
    video_api._get_notes returns `editor.notes.list()` verbatim, with no route changes."""

    def tearDown(self):
        self.editor.renders.close()
        super().tearDown()

    def setUp(self):
        super().setUp()
        git(self.root, 'branch', '-M', 'main')
        self.editor = Editor(self.root, backend=FakeBackend(delay=0), unsandboxed_previews=True, auto_land=False)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)

    def test_an_ordinary_reply_with_shortfalls_reaches_the_notes_list(self):
        self.editor.notes.backend = FakeBackend(delay=0, shortfalls=[{'kind': 'weak', 'what': 'exact color match'}])
        note = self.editor.add_note(dict(video='promo/film', frame=0, text='Match the brand color exactly'),
                                    'reviewer')
        self.editor.notes.list()
        got = self.editor.notes.get(note['id'])
        self.assertEqual(got['state'], 'replied')
        self.assertNotIn('```', got['reply'])
        self.assertEqual(got['shortfalls'], [{'kind': 'weak', 'what': 'exact color match'}])
        self.assertEqual(self.editor.notes.list('promo/film')[0]['shortfalls'], got['shortfalls'])

    def test_a_questions_reply_with_shortfalls_before_the_block(self):
        self.editor.notes.backend = FakeBackend(
            delay=0, questions=[{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}],
            shortfalls=[{'kind': 'cannot', 'what': 'a licensed soundtrack'}])
        note = self.editor.add_note(dict(video='promo/film', frame=0, text='Add a music track'), 'reviewer')
        self.editor.notes.list()
        got = self.editor.notes.get(note['id'])
        self.assertEqual(got['state'], 'questions')
        self.assertNotIn('```', got['reply'] or '')
        self.assertEqual(got['shortfalls'], [{'kind': 'cannot', 'what': 'a licensed soundtrack'}])


if __name__ == '__main__':
    unittest.main()
