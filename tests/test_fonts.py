"""The font list (fonts.py): the suggest prompt and the Fonts picker's one
shared source of what fonts a builder actually has."""
import os
import unittest

from videobuilder import fonts


class Fonts(unittest.TestCase):
    def test_nine_fonts_unique_ids(self):
        all_fonts = fonts.public()
        self.assertEqual(len(all_fonts), 9)
        self.assertEqual(len({f['id'] for f in all_fonts}), 9)

    def test_every_entry_has_family_source_and_about(self):
        for f in fonts.public():
            self.assertTrue(f['family'])
            self.assertTrue(f['source'])
            self.assertTrue(f['about'])
            self.assertNotIn('asset', f)

    def test_get_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            fonts.get('not-a-real-font')
        with self.assertRaises(KeyError):
            fonts.path('not-a-real-font')

    def test_examples_assets_fonts_are_on_disk(self):
        for id in ('inter', 'cantarell', 'source-code-pro'):
            path = fonts.path(id)
            self.assertIsNotNone(path, id)
            self.assertTrue(os.path.isfile(path), path)

    def test_ids_matches_public(self):
        self.assertEqual(fonts.ids(), {f['id'] for f in fonts.public()})


if __name__ == '__main__':
    unittest.main()
