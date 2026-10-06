import unittest

from videobuilder import Film, Grid, Segment, Timeline
from videobuilder.cli import contact_sheet, default_sheet_frames, sheet_tiles

TL = Timeline(Grid(fps=30, bpm=120), [Segment('a', 0, 2), Segment('b', 2, 4)], end=4)


def draw(n, cv):
    cv.mark('box', 10, 10, 50, 50)


class Keyframes(unittest.TestCase):
    def test_normalised_and_checked(self):
        film = Film(draw=draw, timeline=TL, keyframes=(5, (40, 'b, settled')))
        self.assertEqual(film.keyframes, ((5, ''), (40, 'b, settled')))
        with self.assertRaises(ValueError):
            Film(draw=draw, timeline=TL, keyframes=((60, 'past the end'),))

    def test_sheet_defaults_to_keyframes(self):
        film = Film(draw=draw, timeline=TL, keyframes=((3, 'x'), 50))
        self.assertEqual(default_sheet_frames(film), [(3, 'x'), (50, '')])
        self.assertEqual(default_sheet_frames(film, every=20), [0, 20, 40])
        plain = Film(draw=draw, timeline=TL)
        self.assertEqual(default_sheet_frames(plain), [0, 15, 29, 30, 45, 59])

    def test_default_frames_and_labels_follow_groups_and_overlaps(self):
        tl = Timeline(Grid(fps=30, bpm=120), [
            Segment('cuts', 0, 2, children=[Segment('c1', 0, 1), Segment('c2', 1, 2)]),
            Segment('end', 2, 4, overlap=1),
        ], end=4)
        film = Film(draw=draw, timeline=tl)
        self.assertEqual(default_sheet_frames(film), [0, 7, 14, 15, 22, 29, 30, 45, 59])  # the children, not the group
        self.assertEqual(tl.label(7), 'cuts / c1')
        self.assertEqual(tl.label(35), 'cuts / c2 > end')


class Decorate(unittest.TestCase):
    def test_decorate_sees_marks_and_draws_in_film_px(self):
        film = Film(draw=draw, timeline=TL, background='#000000')
        seen = []

        def decorate(cv, n):
            seen.append((n, [tuple(b) for _, b in cv.marks]))
            cv.rect(0, 0, cv.width / 2, cv.height, '#ff0000')  # left half, in film px
            return 'ok'

        sheet = contact_sheet(film, [(0, 'first'), 31], film.format(), width=192, cols=2, decorate=decorate)
        self.assertEqual(seen, [(0, [(10, 10, 50, 50)]), (31, [(10, 10, 50, 50)])])
        self.assertEqual(sheet.getpixel((8 + 40, 8 + 50)), (255, 0, 0))  # left half of the first thumb
        self.assertEqual(sheet.getpixel((8 + 150, 8 + 50)), (0, 0, 0))  # right half untouched



class Tiles(unittest.TestCase):
    def test_per_format_defaults(self):
        film = Film(draw=draw, timeline=TL, formats=('9x16', '16x9', '1x1'))
        self.assertEqual([sheet_tiles(f) for f in film.formats], [(360, 6), (480, 4), (480, 4)])
        frames = [0, 10, 20]
        portrait = contact_sheet(film, frames, '9x16')
        wide = contact_sheet(film, frames, '16x9')
        self.assertEqual(portrait.size[0], 6 * (360 + 8) + 8)
        self.assertEqual(wide.size[0], 4 * (480 + 8) + 8)
        self.assertEqual(contact_sheet(film, frames, '16x9', width=100, cols=3).size[0], 3 * 108 + 8)


if __name__ == '__main__':
    unittest.main()
