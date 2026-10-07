import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videobuilder.cli import main

from videobuilder.frames import check, manifest


class FrameManifest(unittest.TestCase):
    def test_manifest_and_refusal(self):
        with patch('videobuilder.frames.manifest', return_value='abc  tour/16x9/45\n'):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'frames.sha256'
                with self.assertRaisesRegex(ValueError, 'deliberately regenerate'):
                    check([], path)
                path.write_text('abc  tour/16x9/45\n')
                self.assertEqual(check([], path), path.read_text())
        with self.assertRaisesRegex(ValueError, 'no fixed frame selection'):
            manifest(['other.py'])

    def test_cli_hash_and_check(self):
        with patch('videobuilder.frames.manifest', return_value='abc  tour/16x9/45\n'):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'frames.sha256'
                path.write_text('abc  tour/16x9/45\n')
                with patch('sys.stdout', new_callable=io.StringIO) as output:
                    main(['frames', '--hash', '--check', str(path), 'tour.py'])
                self.assertEqual(output.getvalue(), path.read_text())
                path.write_text('wrong\n')
                with self.assertRaisesRegex(SystemExit, 'deliberately regenerate'):
                    main(['frames', '--hash', '--check', str(path), 'tour.py'])
