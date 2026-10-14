"""The builder-facing sheet is generated from the catalog; this fails the
moment the committed file drifts from videobuilder/capabilities.py."""
import unittest
from pathlib import Path

from videobuilder import capabilities

ROOT = Path(__file__).resolve().parent.parent


class Sheet(unittest.TestCase):
    def test_sheet_matches_generated(self):
        committed = (ROOT / capabilities.SHEET_PATH).read_text()
        generated = capabilities.sheet_markdown()
        self.assertEqual(committed, generated,
                         f'{capabilities.SHEET_PATH} is stale; regenerate with `{capabilities._REGEN_CMD}` '
                         'and commit the result')


if __name__ == '__main__':
    unittest.main()
