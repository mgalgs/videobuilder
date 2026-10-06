"""Golden stills of the example film: a few frames per format, compared by PSNR.

Text rasterisation shifts a little between FreeType/Pango versions, so frames
are compared by peak signal-to-noise ratio, not byte for byte. To accept new
output after a deliberate change:

    VIDEOBUILDER_UPDATE_GOLDEN=1 python -m unittest tests.test_golden
"""
import math
import os
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from videobuilder import load

ROOT = Path(__file__).resolve().parent.parent
FILM_PATH = ROOT / 'examples' / 'tour.py'
GOLDEN = Path(__file__).resolve().parent / 'golden'
FRAMES = (45, 142, 247, 330)  # one in each segment, mid-motion
MIN_PSNR = 32.0  # dB; an unchanged film scores inf, a moved card or wrong colour well under 25


def psnr(a, b):
    """PSNR in dB of two same-size RGB images (inf when identical), without numpy."""
    if a.size != b.size:
        return 0.0
    hist = ImageChops.difference(a, b).histogram()  # 256 bins per channel
    sq = sum(count * (i % 256) ** 2 for i, count in enumerate(hist))
    mse = sq / (a.size[0] * a.size[1] * 3)
    return math.inf if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def to_rgb(canvas):
    s = canvas.surface
    s.flush()
    return Image.frombuffer('RGBA', (s.get_width(), s.get_height()), bytes(s.get_data()),
                            'raw', 'BGRA', s.get_stride(), 1).convert('RGB')


class GoldenStills(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.film = load(FILM_PATH)
        cls.update = bool(os.environ.get('VIDEOBUILDER_UPDATE_GOLDEN'))

    def test_frames(self):
        GOLDEN.mkdir(exist_ok=True)
        for fmt in self.film.formats:
            for n in FRAMES:
                with self.subTest(format=fmt.name, frame=n):
                    path = GOLDEN / f'tour-{fmt.name}-f{n:04d}.png'
                    got = to_rgb(self.film.frame(n, fmt))
                    if self.update or not path.exists():
                        got.save(path, optimize=True)
                        if not self.update:
                            self.fail(f'no golden at {path}; wrote one, check it and commit it')
                        continue
                    want = Image.open(path).convert('RGB')
                    score = psnr(got, want)
                    if score < MIN_PSNR:
                        got.save(path.with_suffix('.actual.png'))
                    self.assertGreaterEqual(score, MIN_PSNR, f'{path.name}: PSNR {score:.1f} dB; '
                                            f'actual frame saved beside it as .actual.png')

    def test_psnr_detects_change(self):
        # The threshold has teeth: the same frame a few px off scores under it.
        a = to_rgb(self.film.frame(142, '16x9'))
        b = ImageChops.offset(a, 6, 0)
        self.assertEqual(psnr(a, a), math.inf)
        self.assertLess(psnr(a, b), MIN_PSNR)


if __name__ == '__main__':
    unittest.main()
