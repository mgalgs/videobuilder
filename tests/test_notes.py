"""Review notes: the store, the AgentBackend interface and the null backend."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from videobuilder.notes import AgentBackend, AgentStatus, NoteStore, NullBackend, parse_questions


class FakeAgent(AgentBackend):
    name = 'fake'

    def __init__(self):
        self.submitted = []
        self.states = {}

    def submit(self, note):
        self.submitted.append(note)
        self.states[f'h{len(self.submitted)}'] = AgentStatus('queued')
        return f'h{len(self.submitted)}'

    def poll(self, handle):
        return self.states[handle]


class Notes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name, 'notes')

    def tearDown(self):
        self.tmp.cleanup()

    def test_store_with_the_null_backend(self):
        store = NoteStore(self.dir)
        self.assertEqual(store.list(), [])
        n = store.add('promo/film', '16x9', 12, 'intro', '  Bigger title  ', b'png-bytes', author='sam')
        self.assertEqual({k: n[k] for k in ('video', 'format', 'frame', 'segment', 'text', 'author', 'backend',
                                            'handle', 'state', 'reply', 'branch')},
                         {'video': 'promo/film', 'format': '16x9', 'frame': 12, 'segment': 'intro',
                          'text': 'Bigger title', 'author': 'sam', 'backend': 'null', 'handle': f'null:{n["id"]}',
                          'state': 'queued', 'reply': None, 'branch': None})
        self.assertEqual(store.get(n['id']), n)
        self.assertEqual(store.image(n['id']), b'png-bytes')
        self.assertEqual(sorted(os.listdir(self.dir)), [f'{n["id"]}.json', f'{n["id"]}.png'])
        m = store.add('other/film', '1x1', 0, None, 'x', b'')
        self.assertEqual([x['id'] for x in store.list()], [n['id'], m['id']])
        self.assertEqual([x['id'] for x in store.list('other/film')], [m['id']])
        store.delete(n['id'])
        self.assertEqual([x['id'] for x in store.list()], [m['id']])
        for bad in (lambda: store.get(n['id']), lambda: store.delete(n['id']), lambda: store.get('../escape')):
            with self.assertRaises(KeyError):
                bad()
        with self.assertRaisesRegex(ValueError, 'some text'):
            store.add('promo/film', '16x9', 0, None, '   ', b'')

    def test_null_backend(self):
        b = NullBackend()
        h = b.submit({'id': 'abc'})
        self.assertEqual(h, 'null:abc')
        self.assertEqual(b.poll(h), AgentStatus('queued', None, None))
        with self.assertRaises(ValueError):
            AgentStatus('lost')

    def test_a_backend_moves_notes_along(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        n = store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png')
        self.assertEqual(agent.submitted[0]['image'], str(self.dir / f'{n["id"]}.png'))
        self.assertEqual(agent.submitted[0]['text'], 'Shorter')
        self.assertEqual(store.get(n['id'])['handle'], 'h1')
        agent.states['h1'] = AgentStatus('replied', 'Done: cut two words.', 'notes/shorter')
        got = store.list()[0]
        self.assertEqual((got['state'], got['reply'], got['branch']), ('replied', 'Done: cut two words.', 'notes/shorter'))
        self.assertEqual(store.get(n['id'])['state'], 'replied')  # stored
        agent.states['h1'] = AgentStatus('working')  # a final state isn't polled again
        self.assertEqual(store.list()[0]['state'], 'replied')

    def test_a_backend_that_fails_to_submit(self):
        class Down(NullBackend):
            def submit(self, note):
                raise ConnectionError('unreachable')
        n = NoteStore(self.dir, Down()).add('v', '16x9', 0, None, 'hello', b'')
        self.assertEqual((n['state'], n['handle']), ('failed', None))
        self.assertIn('unreachable', n['reply'])

    def test_note_file_asks_by_default_then_not_after_an_answer(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make it punchier', b'')
        md = (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('ask the director 1 to 3 short questions', md)
        self.assertNotIn('Do not ask clarifying questions', md)
        self.assertIn('unless you are asking clarifying questions', md)  # no Summary line conflict

        reply = 'Quick check before building:\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) + '\n```\n'
        agent.states[note['handle']] = AgentStatus('replied', reply, None)
        self.assertEqual(store.list('promo/film')[0]['state'], 'questions')

        followup = store.answer(note['id'], False, ['Dark'])
        md2 = (store.session_dir('promo/film') / (followup['id'] + '.md')).read_text()
        self.assertIn('Do not ask clarifying questions', md2)
        self.assertNotIn('ask the director 1 to 3 short questions', md2)
        self.assertIn('End your reply with Summary: <one line>.', md2)
        self.assertNotIn('unless you are asking clarifying questions', md2)

    def test_retry_carries_no_questions_forward(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Build it with your best judgement; do not ask questions.',
                         b'', no_questions=True)
        agent.states[note['handle']] = AgentStatus('failed', 'could not apply')
        failed = store.list('promo/film')[0]
        self.assertEqual(failed['state'], 'failed')
        retried = store.retry(failed['id'])
        self.assertTrue(retried.get('no_questions'))
        md = (store.session_dir('promo/film') / (retried['id'] + '.md')).read_text()
        self.assertIn('No more questions', md)
        self.assertNotIn('Ask first if truly unclear', md)

    def test_a_no_questions_note_never_shows_a_stray_block(self):
        # A backend that ignores the no-questions instruction must not leak the raw
        # block into the reply, and must not put the note back into questions state.
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make it punchier', b'', no_questions=True)
        reply = 'Done.\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) + '\n```\n'
        agent.states[note['handle']] = AgentStatus('replied', reply, 'notes/branch')
        got = store.list('promo/film')[0]
        self.assertEqual(got['state'], 'replied')
        self.assertEqual(got['reply'], 'Done.')
        self.assertNotIn('questions', got)


class Questions(unittest.TestCase):
    def test_a_valid_block_with_choice_and_free_text(self):
        reply = ('Here is a quick check.\n\n```questions\n' + json.dumps({'questions': [
            {'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
            {'text': 'Any specific line of copy?'},
        ]}) + '\n```\n')
        lead_in, questions = parse_questions(reply)
        self.assertEqual(lead_in, 'Here is a quick check.')
        self.assertEqual(questions, [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
                                     {'text': 'Any specific line of copy?', 'choices': []}])

    def test_malformed_json_falls_back_to_an_ordinary_reply(self):
        self.assertIsNone(parse_questions('```questions\nnot json\n```\n'))

    def test_zero_or_four_questions_is_invalid(self):
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': []}) + '\n```\n'))
        four = [{'text': f'Q{i}'} for i in range(4)]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': four}) + '\n```\n'))

    def test_one_or_five_choices_is_invalid(self):
        one = [{'text': 'Q', 'choices': ['A']}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': one}) + '\n```\n'))
        five = [{'text': 'Q', 'choices': ['A', 'B', 'C', 'D', 'E']}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': five}) + '\n```\n'))

    def test_overlong_strings_are_invalid(self):
        long_text = [{'text': 'x' * 500}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': long_text}) + '\n```\n'))
        long_choice = [{'text': 'Q', 'choices': ['ok', 'y' * 200]}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': long_choice}) + '\n```\n'))

    def test_a_missing_block_falls_back_to_an_ordinary_reply(self):
        self.assertIsNone(parse_questions('Just a plain reply, no questions here.'))
        self.assertIsNone(parse_questions(None))

    def test_trailing_text_after_the_block_is_dropped(self):
        reply = ('Quick check:\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) +
            '\n```\n\nSummary: asked about the logo.')
        self.assertEqual(parse_questions(reply),
                         ('Quick check:', [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]))


if __name__ == '__main__':
    unittest.main()
