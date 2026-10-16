"""Unit tests for videobuilder/community.py: the reserved namespace, the
agent-args helper, the capability.toml validator and the draft/published
store. No network and no HTTP server here -- see test_community_routes.py
for the end-to-end routes."""
import tempfile
import unittest
from pathlib import Path

from videobuilder import community
from videobuilder.library import Library


class Reserved(unittest.TestCase):
    def test_is_reserved_cases(self):
        for name in ('capabilities', 'capabilities/x', 'capabilities/deep/ly'):
            with self.subTest(name=name):
                self.assertTrue(community.is_reserved(name))
        for name in ('capabilitiesx', 'acme/capabilities', 'capabilities-x', '', None):
            with self.subTest(name=name):
                self.assertFalse(community.is_reserved(name))

    def test_internal_create_allows_reserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            library = Library(Path(tmp) / 'library', envs='current')
            self.addCleanup(library.close)
            with self.assertRaises(ValueError):
                library.create('capabilities/demo')
            library.create('capabilities/demo', allow_reserved=True)
            self.assertTrue(library.path('capabilities/demo').exists())
            with self.assertRaises(ValueError):
                library.create_blank('capabilities/other')
            library.create_blank('capabilities/other', allow_reserved=True)
            self.assertTrue(library.path('capabilities/other').exists())


class AgentArgs(unittest.TestCase):
    def test_capability_agent_args_cases(self):
        cases = [
            (['--model', 'm'], None,
             ['--model', 'm', '--review-loop', '2', '--maintainer-loop', '1',
              '--review-model', 'm', '--maintainer-model', 'm']),
            (['--model=m'], None,
             ['--model=m', '--review-loop', '2', '--maintainer-loop', '1',
              '--review-model', 'm', '--maintainer-model', 'm']),
            (['--k8s'], None, ['--k8s', '--review-loop', '2']),
            (None, None, ['--review-loop', '2']),
            (['--model', 'm'], ['--x', '1'], ['--model', 'm', '--x', '1']),
        ]
        for note_args, capability_args, expected in cases:
            with self.subTest(note_args=note_args, capability_args=capability_args):
                self.assertEqual(community.capability_agent_args(note_args, capability_args), expected)


if __name__ == '__main__':
    unittest.main()
