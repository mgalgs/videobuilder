import unittest
from unittest.mock import patch

from videobuilder import Font, text


class FontWarnings(unittest.TestCase):
    def test_missing_family_warns_once_without_changing_description(self):
        with patch.object(text, '_warned_families', set()):
            with self.assertLogs('videobuilder.text', level='WARNING') as logs:
                a = Font('Missing Test Family', 30).description()
                b = Font('Missing Test Family', 60).description()
                Font('Missing Test Family', 30, weight=700).description()
            self.assertEqual(len(logs.output), 1)
            self.assertIn('Pango will fall back', logs.output[0])
            self.assertEqual(a.get_family(), 'Missing Test Family')
            self.assertEqual(b.get_family(), a.get_family())

    def test_registered_and_generic_families_do_not_warn(self):
        from pathlib import Path
        text.register(Path(__file__).resolve().parent.parent / 'examples/assets/Inter-Variable.ttf')
        with self.assertNoLogs('videobuilder.text', level='WARNING'):
            Font('Inter', 30).description()
            Font('Sans', 30).description()
            Font('monospace', 30).description()
