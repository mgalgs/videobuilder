import os
import tempfile
import textwrap
import unittest

from videobuilder import FORMATS, Audio, Film, Format, Grid, Segment, Sound, Timeline, load


def noop(n, cv):
    pass


class Formats(unittest.TestCase):
    def test_standard_sizes(self):
        self.assertEqual({k: (f.width, f.height) for k, f in FORMATS.items()},
                         {'9x16': (1080, 1920), '16x9': (1920, 1080), '1x1': (1080, 1080)})
        self.assertTrue(FORMATS['9x16'].portrait and FORMATS['16x9'].landscape and FORMATS['1x1'].square)

    def test_film_formats(self):
        film = Film(draw=noop, fps=30, frames=10, formats=('9x16', Format('4x5', 1080, 1350)))
        self.assertEqual(film.format().name, '9x16')
        self.assertEqual(film.format('4x5').height, 1350)
        with self.assertRaises(ValueError):
            film.format('16x9')  # known, but not one of this film's
        with self.assertRaises(ValueError):
            Film(draw=noop, fps=30, frames=10, formats=('3x2',))
        self.assertEqual(Film(draw=noop, fps=30, frames=1, formats='1x1').formats, (FORMATS['1x1'],))

    def test_frame_sees_its_format_and_scale(self):
        seen = []
        film = Film(draw=lambda n, cv: seen.append((n, cv.format.name, cv.width, cv.height)),
                    fps=30, frames=10, formats=('16x9', '9x16'))
        cv = film.frame(3, '9x16', scale=0.25)
        self.assertEqual(seen, [(3, '9x16', 1080, 1920)])
        self.assertEqual((cv.surface.get_width(), cv.surface.get_height()), (270, 480))


class Timing(unittest.TestCase):
    def test_from_timeline(self):
        tl = Timeline(Grid(fps=24, bpm=90), [Segment('a', 0, 4)], end=4)
        film = Film(draw=noop, timeline=tl)
        self.assertEqual((film.fps, film.frames), (24, 64))

    def test_mismatch_and_missing(self):
        tl = Timeline(Grid(fps=24), [Segment('a', 0, 4)], end=4)
        with self.assertRaises(ValueError):
            Film(draw=noop, fps=30, timeline=tl)
        with self.assertRaises(ValueError):
            Film(draw=noop, fps=30)


class Loading(unittest.TestCase):
    def test_load_and_neighbour_import(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'helper_vbtest.py'), 'w') as fh:
                fh.write('FRAMES = 12\n')
            with open(os.path.join(d, 'film.py'), 'w') as fh:
                fh.write(textwrap.dedent('''
                    import videobuilder as vb
                    from helper_vbtest import FRAMES
                    FILM = vb.Film(draw=lambda n, cv: None, fps=30, frames=FRAMES)
                '''))
            self.assertEqual(load(os.path.join(d, 'film.py')).frames, 12)

    def test_load_requires_film(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'film.py')
            with open(p, 'w') as fh:
                fh.write('FILM = 3\n')
            with self.assertRaises(TypeError):
                load(p)

    def test_reload_sees_same_size_edit(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'film.py')
            src = 'import videobuilder as vb\nFILM = vb.Film(draw=lambda n, cv: None, fps=30, frames={})\n'
            with open(p, 'w') as fh:
                fh.write(src.format(12))
            self.assertEqual(load(p).frames, 12)
            st = os.stat(p)
            with open(p, 'w') as fh:
                fh.write(src.format(13))
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))  # the edit lands within the same second
            self.assertEqual(load(p).frames, 13)


class Sounds(unittest.TestCase):
    def test_defaults(self):
        s = Sound('x.wav', at=10, start=1.5, frames=20)
        self.assertEqual((s.gain_db, s.fade_in_frames, s.fade_out_frames), (0, 3, 3))
        self.assertEqual(Audio('x.wav').duck_db, 0)

    def test_fully_inside_is_untouched(self):
        film = Film(draw=noop, fps=30, frames=100, sounds=(Sound('x.wav', at=10, start=2.0, frames=20),))
        self.assertEqual(film.sounds, (Sound('x.wav', at=10, start=2.0, frames=20),))

    def test_clipped_to_the_films_range(self):
        # Starts before frame 0: the head is cut, and the source start moves with it.
        film = Film(draw=noop, fps=30, frames=50, sounds=(Sound('x.wav', at=-10, start=2.0, frames=20),))
        self.assertEqual(film.sounds, (Sound('x.wav', at=0, start=2.0 + 10 / 30, frames=10),))
        # Runs past the last frame: the tail is cut, the source start is untouched.
        film = Film(draw=noop, fps=30, frames=15, sounds=(Sound('x.wav', at=10, start=2.0, frames=20),))
        self.assertEqual(film.sounds, (Sound('x.wav', at=10, start=2.0, frames=5),))

    def test_entirely_outside_is_dropped(self):
        film = Film(draw=noop, fps=30, frames=10, sounds=(Sound('x.wav', at=20, start=0, frames=5),))
        self.assertEqual(film.sounds, ())


if __name__ == '__main__':
    unittest.main()
