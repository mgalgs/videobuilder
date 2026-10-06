import os
import tempfile
import time
import unittest

from PIL import Image as PILImage

from videobuilder import Image


class Load(unittest.TestCase):
    def test_decoded_once_and_again_when_changed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'a.png')
            PILImage.new('RGB', (40, 20), (255, 0, 0)).save(path)
            a = Image.load(path)
            self.assertIs(Image.load(path), a)
            self.assertIs(Image.load(os.path.join(d, '.', 'a.png')), a)  # same file, other spelling
            self.assertEqual((a.w, a.h), (40, 20))
            time.sleep(0.01)
            PILImage.new('RGB', (10, 30), (0, 0, 255)).save(path)
            os.utime(path, ns=(time.time_ns(), time.time_ns() + 10**9))
            b = Image.load(path)
            self.assertIsNot(b, a)
            self.assertEqual((b.w, b.h), (10, 30))
            self.assertEqual([im for p, (_, im) in Image._cache.items() if p == os.path.abspath(path)], [b])
            self.assertNotIn(a, [im for _, im in Image._cache.values()])  # the old decode is dropped

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            Image.load('/nonexistent/a.png')


if __name__ == '__main__':
    unittest.main()
