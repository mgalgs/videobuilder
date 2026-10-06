import unittest

from PIL import Image as PILImage, ImageDraw

from videobuilder import Box, Canvas, Image


def page(w=200, h=800):
    """A tall 'capture': a red navbar strip, then bands of grey."""
    im = PILImage.new('RGB', (w, h), (200, 200, 200))
    d = ImageDraw.Draw(im)
    for y in range(0, h, 40):
        d.rectangle((0, y, w - 1, y + 19), fill=(40, 40 + y % 200, 90))
    d.rectangle((0, 0, w - 1, 29), fill=(255, 0, 0))
    return Image.from_pil(im)


class ViewTests(unittest.TestCase):
    def test_matches_the_hand_written_camera(self):
        im, nav = page(), page(200, 120)
        box, (cx, cy, s), r = Box(30.5, 20, 150, 220), (100, 500, 0.75), 18
        a, b = Canvas(240, 300, '#ffffff'), Canvas(240, 300, '#ffffff')
        v = a.view(im, box, (cx, cy), s, radius=r, background='#123456')
        v.pin(Box(0, 0, nav.w, 30), img=nav, y=box.y)
        # by hand, as a film wrote it before `view`
        x, y, w, h = box
        with b.clip(x, y, w, h, r):
            b.rect(x, y, w, h, '#123456')
            left, top = x + w / 2 - cx * s, y + h / 2 - cy * s
            b.image(im, left, top, im.w * s, im.h * s)
            with b.clip(left, y, nav.w * s, 30 * s):
                b.image(nav, left, y, nav.w * s, nav.h * s)
        self.assertEqual(a.bgra(), b.bgra())
        self.assertEqual((v.left, v.top), (left, top))

    def test_camera_maths(self):
        im = page()
        cv = Canvas(400, 400)
        v = cv.view(im, Box(100, 100, 100, 50), (50, 400), 2)
        self.assertEqual(v.to_screen(50, 400), (150, 125))  # the centre point lands in the box's centre
        self.assertEqual(v.to_screen(0, 0), (150 - 100, 125 - 800))
        self.assertEqual(v.image_box(), Box(50, -675, 400, 1600))

    def test_defaults_cover_the_box_centred(self):
        im = page(200, 800)
        v = Canvas(400, 400).view(im, Box(0, 0, 100, 100))
        self.assertEqual((v.center, v.scale), ((100, 400), 0.5))
        self.assertEqual(v.image_box(), Box(0, -150, 100, 400))

    def test_clipped_to_the_window_and_pins_too(self):
        im = page()
        cv = Canvas(300, 300, '#000000')
        v = cv.view(im, Box(100, 100, 100, 100), (100, 400), 1)
        v.pin(Box(0, 0, 200, 30), y=100)  # the navbar strip of the same image, pinned to the top
        px = lambda x, y: tuple(cv.bgra()[(y * 300 + x) * 4:(y * 300 + x) * 4 + 3])  # noqa: E731
        self.assertEqual(px(50, 150), (0, 0, 0))  # outside the window: untouched
        self.assertEqual(px(150, 110), (0, 0, 255))  # the pinned red strip (BGRA)
        self.assertNotEqual(px(150, 150), (0, 0, 255))  # the page under it
        self.assertEqual(px(150, 250), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
