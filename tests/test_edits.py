"""Direct edits: the <film>.edits.toml overlay, its rules, and writing it."""
import hashlib
import os
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

from videobuilder import Grid, Segment, Timeline, edits, load, load_module

ROOT = Path(__file__).resolve().parent.parent

# 15 frames a beat. cuts is a group; close, a and b overlap the one before.
FILM = textwrap.dedent('''
    import videobuilder as vb
    GRID = vb.Grid(fps=30, bpm=120)
    SHARED = dict(title='Shared')
    T = vb.Timeline(GRID, [
        vb.Segment('intro', 0, 4, dict(title='Hello', n=3)),
        vb.Segment('body', 4, 8, SHARED),
        vb.Segment('cuts', 8, 12, children=vb.sequence(8, [('c1', 2), ('c2', 2, SHARED)])),
        vb.Segment('close', 12, 16, overlap=1),
        vb.Segment('a', 16, 18, overlap=1),
        vb.Segment('b', 18, 22, overlap=1.5),
    ], end=22)
    INTRO = T.span('intro')          # module-level values derived from the timeline
    TITLE = T.find('intro').data['title']
    COLOURS = {'intro': '#f00', 'body': '#0f0', 'c1': '#00f', 'c2': '#ff0', 'close': '#0ff', 'a': '#f0f', 'b': '#fff'}
    def draw(n, cv):
        cv.rect(0, 0, cv.width, cv.height, COLOURS[T.at(n)[0].name])
    FILM = vb.Film(draw=draw, timeline=T, formats='1x1')
''')


class FilmDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.film = self.dir / 'film.py'
        self.film.write_text(FILM)
        self.toml = self.dir / 'film.edits.toml'

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, toml=None):
        if toml is not None:
            self.toml.write_text(textwrap.dedent(toml))
        return load_module(str(self.film))

    def refused(self, toml, *pattern):
        with self.assertRaises(ValueError) as e:
            self.load(toml)
        for p in pattern:
            self.assertIn(p, str(e.exception))
        return str(e.exception)


class Overlay(FilmDir):
    def test_no_file_is_a_no_op(self):
        mod = self.load()
        self.assertIsNone(mod.T.edits)
        self.assertEqual(mod.INTRO, (0, 60))
        self.assertEqual(mod.T.cut_frames(), [0, 60, 120, 150])

    def test_roll_moves_one_cut_and_keeps_the_rest(self):
        mod = self.load('[segments.intro]\nuntil = 6.5\n')
        tl = mod.T
        self.assertEqual((tl.find('intro').until, tl.find('body').at), (6.5, 6.5))
        self.assertEqual(mod.INTRO, (0, 98))  # derived at module level, after the edit: 97.5 -> 98
        self.assertEqual(tl.cut_frames(), [0, 98, 120, 150])
        self.assertEqual((tl.frames, mod.FILM.frames), (330, 330))
        self.assertEqual(tl.edits.path, str(self.toml))
        self.assertEqual(tl.edits.segments, {'intro': {'until': 6.5}})

    def test_roll_inside_a_group_and_integral_beats(self):
        tl = self.load('[segments.c1]\nuntil = 9\n').T
        self.assertEqual((tl.find('c1').until, tl.find('c2').at), (9, 9))
        self.assertEqual(tl.cut_frames(), [0, 60, 120, 135])

    def test_rolls_are_checked_together(self):
        # close past a's own end is fine when a's end moves too.
        tl = self.load('[segments.a]\nuntil = 19.5\n[segments.close]\nuntil = 18.5\n').T
        self.assertEqual([(s.name, s.at, s.until) for s in tl.segments[3:]],
                         [('close', 12, 18.5), ('a', 18.5, 19.5), ('b', 19.5, 22)])

    def test_roll_refusals(self):
        self.refused('[segments.intro]\nuntil = 6.25\n', 'intro', 'half-beat grid')
        self.refused('[segments.intro]\nuntil = 0\n', 'intro', 'strictly between 0 and 8')
        self.refused('[segments.intro]\nuntil = 8\n', 'intro', 'strictly between')
        self.refused('[segments.intro]\nuntil = -2\n', 'intro', 'strictly between')
        self.refused('[segments.c2]\nuntil = 11\n', 'c2', 'no next segment')
        self.refused('[segments.b]\nuntil = 21\n', 'segment b', 'no next segment')
        self.refused('[segments.body]\nuntil = 7\n', 'body', 'cuts is a group')
        self.refused('[segments.cuts]\nuntil = 13\n', 'cuts is a group')
        self.refused('[segments.a]\nuntil = 16.5\n', 'segment a', 'overlap of 1 beats')
        self.refused('[segments.a]\nuntil = 21\n', 'segment a', "b's overlap of 1.5 beats")
        self.refused('[segments.intro]\nuntil = "6"\n', 'intro', 'number of beats')
        self.refused('[segments.intro]\nuntil = true\n', 'intro', 'number of beats')
        self.refused('[segments.intro]\nuntil = inf\n', 'intro', 'number of beats')

    def test_unknown_names_and_keys(self):
        self.refused('[segments.nope]\nuntil = 2\n', "'nope'", str(self.toml))
        self.refused('[segments.intro]\nat = 2\n', "'at'", 'intro')
        self.refused('[other]\nx = 1\n', "'other'")
        self.refused('segments = 3\n', 'table')
        self.refused('[segments.intro\n', str(self.toml))  # not TOML at all

    def test_data_override(self):
        mod = self.load('[segments.body.data]\ntitle = "New body"\n[segments.intro.data]\ntitle = "Hi"\n')
        self.assertEqual(mod.TITLE, 'Hi')
        self.assertEqual(mod.T.find('intro').data, {'title': 'Hi', 'n': 3})
        self.assertEqual(mod.T.find('body').data, {'title': 'New body'})
        self.assertEqual(mod.T.find('c2').data, {'title': 'Shared'})  # the film's shared dict is untouched
        self.assertEqual(mod.SHARED, {'title': 'Shared'})

    def test_data_refusals(self):
        self.refused('[segments.intro.data]\nsubtitle = "x"\n', 'intro', "no key 'subtitle'")
        self.refused('[segments.intro.data]\nn = "4"\n', 'intro', 'data.n is int')
        self.refused('[segments.intro.data]\ntitle = 4\n', 'intro', 'must be a string')
        self.refused('[segments.intro]\ndata = 4\n', 'intro', 'data must be a table')

    def test_empty_file_and_empty_tables(self):
        self.assertIsNone(self.load('').T.find('intro').data.get('x'))
        self.assertEqual(self.load('[segments.intro]\n[segments.intro.data]\n').T.cut_frames()[1], 60)

    def test_the_edits_file_is_named_for_the_film(self):
        self.assertEqual(edits.path_for(str(self.film)), str(self.toml))
        self.assertEqual(edits.path_for('a/b/v2.final.py'), os.path.abspath('a/b/v2.final.edits.toml'))

    def test_a_plain_edits_toml_is_ignored(self):
        (self.dir / 'edits.toml').write_text('[segments.intro]\nuntil = 6\n')
        self.assertIsNone(self.load().T.edits)

    def test_two_films_in_one_directory_keep_their_own_edits(self):
        other = self.dir / 'other.py'
        other.write_text("import videobuilder as vb\n"
                         "T = vb.Timeline(vb.Grid(), [vb.Segment('x', 0, 2), vb.Segment('y', 2, 4)], end=4)\n"
                         "FILM = vb.Film(draw=lambda n, cv: None, timeline=T)\n")
        edits.roll(str(other), 'x', 1)
        edits.roll(str(self.film), 'intro', 6)  # would fail if it read other's edits: no segment x
        self.assertEqual(load_module(str(self.film)).T.find('intro').until, 6)
        self.assertEqual(load_module(str(other)).T.find('x').until, 1)
        self.assertEqual(sorted(p.name for p in self.dir.glob('*.toml')), ['film.edits.toml', 'other.edits.toml'])

    def test_timeline_outside_a_film_load_sees_no_edits(self):
        self.toml.write_text('[segments.x]\nuntil = 1\n')
        os.chdir(self.dir)
        try:
            tl = Timeline(Grid(), [Segment('x', 0, 2), Segment('y', 2, 4)], end=4)
        finally:
            os.chdir(ROOT)
        self.assertEqual((tl.find('x').until, tl.edits), (2, None))

    def test_only_the_first_timeline_takes_the_edits(self):
        self.film.write_text(FILM + 'OTHER = vb.Timeline(GRID, [vb.Segment("intro", 0, 4)], end=4)\n')
        mod = self.load('[segments.intro]\nuntil = 6\n')
        self.assertEqual((mod.T.find('intro').until, mod.OTHER.find('intro').until), (6, 4))
        self.assertIsNone(mod.OTHER.edits)

    def test_edits_with_no_timeline_to_apply_them(self):
        self.film.write_text("import videobuilder as vb\nFILM = vb.Film(draw=lambda n, cv: None, fps=30, frames=3)\n")
        self.refused('[segments.intro]\nuntil = 6\n', 'built no Timeline')
        self.assertEqual(self.load('').FILM.frames, 3)  # nothing to apply is fine

    def test_rollable(self):
        tl = self.load().T
        got = {s.name: edits.rollable(tl, s.name) for s, _ in tl.walk()}
        self.assertEqual(got, {'intro': True, 'body': False, 'cuts': False, 'c1': True, 'c2': False,
                               'close': True, 'a': True, 'b': False})
        # p is as short as its overlap allows, and q (last) has nothing to roll into
        tl = Timeline(Grid(), [Segment('o', 0, 1), Segment('p', 1, 2, overlap=1), Segment('q', 2, 2.5, overlap=0.5)],
                      end=2.5)
        self.assertEqual([edits.rollable(tl, n) for n in 'opq'], [True, False, False])


class Writing(FilmDir):
    def text(self):
        return self.toml.read_text() if self.toml.exists() else None

    def test_roll_writes_and_rolling_back_removes(self):
        edits.roll(str(self.film), 'intro', 6.5)
        self.assertEqual(self.text(), '[segments.intro]\nuntil = 6.5\n')
        self.assertEqual(load(str(self.film)).timeline.find('body').at, 6.5)
        edits.roll(str(self.film), 'intro', 5.0)
        self.assertEqual(self.text(), '[segments.intro]\nuntil = 5\n')  # whole beats are written as ints
        edits.roll(str(self.film), 'intro', 4)  # the film's own value
        self.assertIsNone(self.text())  # nothing left: no file

    def test_copy_round_trips_awkward_strings(self):
        nasty = 'He said "hi" \\ C:\\path\nline two\ttab \x01 \x7f é ✓ \'single\' """'
        edits.set_copy(str(self.film), 'intro', 'title', nasty)
        with open(self.toml, 'rb') as fh:
            self.assertEqual(tomllib.load(fh), {'segments': {'intro': {'data': {'title': nasty}}}})
        self.assertEqual(load_module(str(self.film)).TITLE, nasty)
        self.assertEqual(self.text().count('\n'), 2)  # newlines are escaped, one line per entry

    def test_keys_that_need_quoting(self):
        segs = {'quick cuts': {'until': 2}, 'a.b': {'data': {'sub title': 'x', 'ok_key-1': 'y'}}}
        text = edits.dumps(segs)
        self.assertEqual(text, '[segments."a.b".data]\nok_key-1 = "y"\n"sub title" = "x"\n\n'
                               '[segments."quick cuts"]\nuntil = 2\n')
        self.assertEqual(tomllib.loads(text)['segments'], segs)

    def test_writes_are_deterministic_and_sorted(self):
        f = str(self.film)
        edits.set_copy(f, 'intro', 'title', 'One')
        edits.roll(f, 'c1', 9)
        edits.roll(f, 'intro', 6)
        first = self.text()
        self.toml.unlink()
        edits.roll(f, 'intro', 6)
        edits.roll(f, 'c1', 9)
        edits.set_copy(f, 'intro', 'title', 'One')
        self.assertEqual(self.text(), first)
        self.assertEqual(first, '[segments.c1]\nuntil = 9\n\n[segments.intro]\nuntil = 6\n\n'
                                '[segments.intro.data]\ntitle = "One"\n')

    def test_copy_back_to_the_original_drops_empty_tables(self):
        f = str(self.film)
        edits.roll(f, 'intro', 6)
        edits.set_copy(f, 'intro', 'title', 'Changed')
        edits.set_copy(f, 'intro', 'title', 'Hello')
        self.assertEqual(self.text(), '[segments.intro]\nuntil = 6\n')
        edits.set_copy(f, 'body', 'title', 'B')
        edits.roll(f, 'intro', 4)
        self.assertEqual(self.text(), '[segments.body.data]\ntitle = "B"\n')

    def test_refusals_leave_the_file_alone(self):
        f = str(self.film)
        edits.roll(f, 'intro', 6)
        before = self.toml.read_bytes()
        for call in (lambda: edits.roll(f, 'intro', 6.25), lambda: edits.roll(f, 'cuts', 10),
                     lambda: edits.roll(f, 'nope', 2), lambda: edits.roll(f, 'intro', 'six'),
                     lambda: edits.set_copy(f, 'intro', 'n', '4'), lambda: edits.set_copy(f, 'intro', 'title', 4),
                     lambda: edits.set_copy(f, 'intro', 'missing', 'x'), lambda: edits.roll(f, 'body', 7)):
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()
            self.assertEqual(self.toml.read_bytes(), before)
        self.assertFalse(Path(str(self.toml) + '.tmp').exists())

    def test_segments_from_a_helper_module(self):
        # Rolls edit Segments in place; a helper holding them must be re-imported
        # for set_copy and roll to see the film's own values.
        name = f'storyboard_{id(self)}'
        (self.dir / f'{name}.py').write_text(
            "import videobuilder as vb\nSEGS = [vb.Segment('x', 0, 2, dict(t='A')), vb.Segment('y', 2, 4)]\n")
        self.film.write_text(f"import videobuilder as vb\nfrom {name} import SEGS\n"
                             "T = vb.Timeline(vb.Grid(), SEGS, end=4)\n"
                             "FILM = vb.Film(draw=lambda n, cv: None, timeline=T)\n")
        f = str(self.film)
        edits.roll(f, 'x', 1)
        edits.set_copy(f, 'x', 't', 'B')
        edits.roll(f, 'x', 2)  # the film's own end: removed, not written
        edits.set_copy(f, 'x', 't', 'A')
        self.assertIsNone(self.text())

    def test_refused_with_no_file_writes_none(self):
        with self.assertRaises(ValueError):
            edits.roll(str(self.film), 'intro', 9)
        self.assertFalse(self.toml.exists())


def digest(film, n, fmt):
    cv = film.frame(n, fmt, scale=0.25)
    cv.surface.flush()
    return hashlib.sha256(bytes(cv.surface.get_data())).hexdigest()


class ExampleFilms(unittest.TestCase):
    """The examples load with no edits, and an edit to one moves its cut on screen."""

    def test_examples_have_no_edits(self):
        self.assertEqual(list((ROOT / 'examples').glob('*.toml')), [])
        for name in ('tour.py', 'benchmark.py'):
            with self.subTest(film=name):
                self.assertIsNone(load(str(ROOT / 'examples' / name)).timeline.edits)

    def test_a_roll_moves_the_tours_first_cut(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d, 'tour.py')
            copy.write_text((ROOT / 'examples' / 'tour.py').read_text())
            os.symlink(ROOT / 'examples' / 'assets', Path(d, 'assets'))
            Path(d, 'tour.edits.toml').write_text('[segments.title]\nuntil = 4\n')
            edited = load(str(copy))
        film = load(str(ROOT / 'examples' / 'tour.py'))
        self.assertEqual(film.timeline.cut_frames(), [0, 90, 195, 300])
        self.assertEqual(edited.timeline.cut_frames(), [0, 60, 195, 300])  # picture starts 2 beats early
        self.assertEqual(edited.frames, film.frames)
        self.assertEqual((film.timeline.label(75), edited.timeline.label(75)), ('title', 'picture'))
        self.assertNotEqual(digest(edited, 75, '16x9'), digest(film, 75, '16x9'))
        for n in (30, 200, 330):  # before the moved cut, and after the next one: untouched
            self.assertEqual(digest(edited, n, '16x9'), digest(film, n, '16x9'), n)


if __name__ == '__main__':
    unittest.main()
