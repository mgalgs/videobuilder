"""Whip and flash: the reel transitions, assembled."""
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from videobuilder import assembly, timeline_file as tf
from videobuilder.film import Format

HAS_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
SMALL = Format('small', 192, 108)


def solid(path, colour, seconds, size='96x54'):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=0x{colour}:size={size}:rate=30',
                    '-t', str(seconds), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)


def frames_rgb(path, w=16, h=9):
    """Each frame of `path`'s picture as its mean (r, g, b)."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v', '-vf', f'scale={w}:{h}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    size, out = w * h * 3, []
    for k in range(0, len(raw) - size + 1, size):
        px = raw[k:k + size]
        out.append(tuple(sum(px[c::3]) / (w * h) for c in range(3)))
    return out


@unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
class Transitions(unittest.TestCase):
    """Whip and flash assemble: frames either side of the transition are the
    clips' own, and its frames are a slide with a blur along it, or white."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        (cls.root / 'sources').mkdir()
        solid(cls.root / 'sources' / 'red.mp4', 'ff0000', 2)
        solid(cls.root / 'sources' / 'blue.mp4', '0000ff', 2)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def assemble(self, cut, name):
        data = {'version': 1, 'fps': 30, 'clips': [
            {'id': 'red', 'footage': 'sources/red.mp4', 'out': 30},
            {'id': 'blue', 'footage': 'sources/blue.mp4', 'out': 30, 'cut': cut}]}
        out = self.root / f'{name}.mp4'
        frames, _ = assembly.assemble(tf.parse(data), SMALL, out, self.root, {}, log=io.StringIO())
        rgb = frames_rgb(out)
        self.assertEqual((frames, len(rgb)), (60 - cut['frames'],) * 2)
        return rgb

    def is_colour(self, px, colour):
        return all(abs(a - b) < 24 for a, b in zip(px, colour))

    def test_a_flash_cuts_through_white(self):
        rgb = self.assemble({'transition': 'flash', 'frames': 6}, 'flash')
        red, blue, white = (255, 0, 0), (0, 0, 255), (255, 255, 255)
        self.assertTrue(all(self.is_colour(px, red) for px in rgb[:24]), rgb[23])     # before: red
        self.assertTrue(all(self.is_colour(px, blue) for px in rgb[30:]), rgb[30])    # after: blue
        self.assertTrue(self.is_colour(rgb[27], white), rgb[27])                      # its middle: white
        self.assertGreater(rgb[25][1], 100)                                           # whitening red

    def test_a_whip_slides_with_a_blur_along_it(self):
        rgb = self.assemble({'transition': 'whip', 'frames': 8, 'direction': 'left'}, 'whip')
        red, blue = (255, 0, 0), (0, 0, 255)
        self.assertTrue(all(self.is_colour(px, red) for px in rgb[:22]), rgb[21])
        self.assertTrue(all(self.is_colour(px, blue) for px in rgb[30:]), rgb[30])
        # Its middle frame: red still on the left, blue in from the right, smeared where they meet.
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.root / 'whip.mp4'), '-vf',
                              f"select=eq(n\\,26),scale={SMALL.width}:1", '-frames:v', '1', '-f', 'rawvideo',
                              '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
        row = [tuple(raw[k:k + 3]) for k in range(0, len(raw), 3)]
        self.assertTrue(self.is_colour(row[2], red) and self.is_colour(row[-3], blue), (row[2], row[-3]))
        mixed = [px for px in row if px[0] > 40 and px[2] > 40]
        self.assertGreater(len(mixed), 6, 'the edge between them is blurred along the whip')

    def test_a_whip_up_slides_up(self):
        rgb = self.assemble({'transition': 'whip', 'frames': 6, 'direction': 'up'}, 'whip-up')
        self.assertTrue(self.is_colour(rgb[0], (255, 0, 0)) and self.is_colour(rgb[-1], (0, 0, 255)))
        self.assertIn('sizeX=1:sizeY=', assembly.whip_blur(tf.Cut('whip', 6, 'up'), 24, SMALL, 30))


if __name__ == '__main__':
    unittest.main()
