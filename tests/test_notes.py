"""Review notes: the store, the AgentBackend interface and the null backend."""
import os
import tempfile
import unittest
from pathlib import Path

from videobuilder.notes import AgentBackend, AgentStatus, NoteStore, NullBackend


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


if __name__ == '__main__':
    unittest.main()
