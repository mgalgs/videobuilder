"""The make-a-video skill's template film and scripts work against this checkout."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skill' / 'make-a-video'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def script(name, *args, cwd, check=True):
    return subprocess.run([sys.executable, str(SKILL / 'scripts' / name), *map(str, args)], cwd=cwd, env=ENV,
                          capture_output=True, text=True, check=check)


# Four seconds at 120 bpm, a hard cut from black to white on beat 4, with music.
SHORT = """\
from pathlib import Path
import videobuilder as vb
from videobuilder import Box
HERE = Path(__file__).resolve().parent
GRID = vb.Grid(fps=30, bpm=120, head_trim=HEAD)
TIMELINE = vb.Timeline(GRID, [vb.Segment('a', 0, 4, dict(copy='Hi')), vb.Segment('b', 4, 8, dict(copy='Bye'))], end=8)
LAYOUTS = {'1x1': dict(safe=Box(100, 100, 880, 880))}
def draw(n, cv):
    seg, f = TIMELINE.at(n)
    if seg.name == 'b':
        cv.fill('#fff')
    cv.mark(seg.name, *BOX)
FILM = vb.Film(draw=draw, timeline=TIMELINE, formats='1x1', audio=vb.Audio(str(HERE / 'music.wav')))
"""


class Skill(unittest.TestCase):
    def test_template_runs_and_passes_its_checks(self):
        with tempfile.TemporaryDirectory() as d:
            film = Path(d, 'film.py')
            film.write_text((SKILL / 'template' / 'film.py').read_text())
            from videobuilder import load
            f = load(str(film))
            self.assertEqual([x.name for x in f.formats], ['9x16', '16x9'])
            for fmt in f.formats:
                f.frame(f.frames // 2, fmt, scale=0.1)
            out = script('check.py', film, cwd=d)
            self.assertIn('0 failed', out.stdout)

    def test_sandbox_checkout_with_placeholder_track(self):
        with tempfile.TemporaryDirectory() as d:
            film = Path(d, 'film.py')
            film.write_text((SKILL / 'template' / 'film.py').read_text().replace(
                '# audio=vb.Audio', 'audio=vb.Audio'))
            Path(d, 'assets').mkdir()
            script('make_track.py', '--bpm', 120, '--beats', 40,
                   '--out', 'assets/music.wav', cwd=d)
            result = subprocess.run(
                [sys.executable, '-c',
                 "import videobuilder as vb; f=vb.load('film.py'); "
                 "assert f.timeline.grid.head_trim == 0; "
                 "assert f.audio.path; f.frame(0, scale=0.05)"],
                cwd=d, env={**os.environ, 'PYTHONPATH': str(ROOT)},
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('0 failed', script('check.py', film, cwd=d).stdout)

    def test_template_registers_nested_fonts(self):
        from unittest.mock import patch
        from videobuilder import load
        with tempfile.TemporaryDirectory() as d:
            film = Path(d, 'film.py')
            film.write_text((SKILL / 'template' / 'film.py').read_text())
            fonts = Path(d, 'assets', 'fonts')
            fonts.mkdir(parents=True)
            for name in ('A.otf', 'B.ttf', 'OFL.txt'):
                (fonts / name).touch()
            with patch('videobuilder.text.register') as register:
                load(film)
            self.assertEqual([c.args[0].name for c in register.call_args_list], ['A.otf', 'B.ttf'])

    def test_copy_lists_warnings_and_entrance_times(self):
        cases = [
            ("copy=['one two three', 'four five six']", 1, '6 words'),
            ("copy='Hi', pro='Other words'", 0, 'uncounted string keys beside copy: pro'),
            ("copy=['Hi'], copy_at=0.5", 0, '1.73 s'),
            ("copy=['Hi'], copy_at=2.5", 1, '0.73 s'),
            ("copy='Hi', copy_at=10", 1, '0.00 s'),
            ("copy=['Hi', 2]", 1, 'copy must be a string or a list'),
            ("copy='Hi', copy_at=-1", 1, 'copy_at must be finite'),
            ("copy='Hi', copy_at=float('nan')", 1, 'copy_at must be finite'),
            ("title='Hi', subtitle='There'", 0, '2 words'),
        ]
        with tempfile.TemporaryDirectory() as d:
            for data, code, message in cases:
                with self.subTest(data=data):
                    Path(d, 'short.py').write_text(
                        SHORT.replace('HEAD', '0').replace('BOX', '(200, 200, 300, 100)')
                        .replace("copy='Hi'", data))
                    out = script('check.py', 'short.py', cwd=d, check=False)
                    self.assertEqual(out.returncode, code, out.stdout + out.stderr)
                    self.assertIn(message, out.stdout)

    def test_short_film_render_checks_clean(self):
        with tempfile.TemporaryDirectory() as d:
            script('make_track.py', '--bpm', 120, '--beats', 8, '--out', 'music.wav', cwd=d)
            Path(d, 'short.py').write_text(SHORT.replace('HEAD', '0').replace('BOX', '(200, 200, 300, 100)'))
            subprocess.run([sys.executable, '-m', 'videobuilder', 'render', 'short.py'], cwd=d, env=ENV,
                           capture_output=True, check=True)
            out = script('check.py', 'short.py', '--video', cwd=d).stdout
        self.assertIn('0 failed, 0 warnings', out)
        self.assertIn('1 hard picture changes, 1 on the 1 cuts', out)
        self.assertIn('within half a frame', out)

    def test_check_fails_marks_outside_safe_and_short_read_times(self):
        with tempfile.TemporaryDirectory() as d:
            script('make_track.py', '--bpm', 120, '--beats', 8, '--out', 'music.wav', cwd=d)
            Path(d, 'short.py').write_text(
                SHORT.replace('HEAD', '0').replace('BOX', '(0, 0, 300, 100)')
                .replace("copy='Hi'", "copy='far too many words to read in only two seconds flat'"))
            out = script('check.py', 'short.py', '--wps', 3, cwd=d, check=False)
        self.assertEqual(out.returncode, 1)
        self.assertIn("FAIL  read time 'a'", out.stdout)
        self.assertIn("mark 'a' (0,0 300x100) leaves the safe area", out.stdout)

    def test_tempo_finds_the_bpm_and_first_beat(self):
        with tempfile.TemporaryDirectory() as d:
            script('make_track.py', '--bpm', 112, '--beats', 24, '--lead', 0.4, '--out', 't.wav', cwd=d)
            out = script('tempo.py', 't.wav', '--fps', 30, cwd=d).stdout
        self.assertIn('Grid(fps=30, bpm=112, head_trim=12)', out)

    def test_check_warns_on_a_cut_onto_an_empty_frame(self):
        with tempfile.TemporaryDirectory() as d:
            script('make_track.py', '--bpm', 120, '--beats', 8, '--out', 'music.wav', cwd=d)
            Path(d, 'short.py').write_text(
                SHORT.replace('HEAD', '0').replace('BOX', '(200, 200, 300, 100)')
                .replace("    cv.mark(seg.name", "    if f > 3: cv.mark(seg.name"))
            out = script('check.py', 'short.py', cwd=d).stdout
        self.assertIn('WARN  1x1 f60 (b): the cut lands on a frame with no visible marked content', out)

    def test_fontinfo_reads_the_font_itself(self):
        out = script('fontinfo.py', ROOT / 'examples' / 'assets' / 'Cantarell-VF.otf', '--ofl', cwd=ROOT).stdout
        self.assertIn("Font('Cantarell', ...)", out)
        self.assertIn('variable: wght 100-800', out)
        self.assertIn('SIL Open Font License', out)

    def test_fontinfo_resolves_and_writes_the_ofl(self):
        font = ROOT / 'examples' / 'assets' / 'Inter-Variable.ttf'
        out = script('fontinfo.py', '--resolve', 'Inter', 700, font, cwd=ROOT).stdout
        self.assertIn('-> Inter', out)
        self.assertNotIn('fallback', out)
        out = script('fontinfo.py', '--resolve', 'No Such Family', 400, cwd=ROOT).stdout
        self.assertIn('fallback', out)
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d, 'Inter.ttf')
            copy.write_bytes(font.read_bytes())
            script('fontinfo.py', '--write-ofl', copy, cwd=d)
            ofl = Path(d, 'Inter-OFL.txt').read_text()
        self.assertTrue(ofl.startswith('Copyright 2016 The Inter Project Authors'))
        self.assertIn('SIL OPEN FONT LICENSE Version 1.1', ofl)
        self.assertNotIn('Cantarell', ofl)
        self.assertNotIn('glyphsLib', ofl)
        self.assertEqual(ofl.count('Inter Project Authors'), 1)

    def test_benchmark_example_passes_its_checks(self):
        out = script('check.py', ROOT / 'examples' / 'benchmark.py', cwd=ROOT).stdout
        self.assertIn('0 failed, 0 warnings', out)

    def test_doctor_passes_here(self):
        out = script('doctor.py', cwd=ROOT)
        self.assertIn('all good', out.stdout)


if __name__ == '__main__':
    unittest.main()
