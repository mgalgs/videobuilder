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

    def test_benchmark_example_passes_its_checks(self):
        out = script('check.py', ROOT / 'examples' / 'benchmark.py', cwd=ROOT).stdout
        self.assertIn('0 failed, 0 warnings', out)

    def test_doctor_passes_here(self):
        out = script('doctor.py', cwd=ROOT)
        self.assertIn('all good', out.stdout)


if __name__ == '__main__':
    unittest.main()
