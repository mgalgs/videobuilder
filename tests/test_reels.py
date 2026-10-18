"""Reels: a film of clips cut to a song. Beat detection, the beat grid in the
timeline file, off-beat warnings and snapping, several clips from one source,
the whip and flash transitions, and the done-when reel: twelve dropped clips
and a click-track song cut so every cut lands on a beat."""
import io
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from videobuilder import assembly, beats, new_video, timeline_file as tf
from videobuilder.film import Format



HAS_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
ROOT = Path(__file__).resolve().parent.parent
SMALL = Format('small', 192, 108)
# Twelve colours far enough apart that a cut between any two is plain in the picture.
COLOURS = ['ff0000', '00ff00', '0000ff', 'ffff00', 'ff00ff', '00ffff',
           'ff8000', '8000ff', '00ff80', '804000', '008080', 'ffffff']


def click_track(path, bpm, first, seconds, rate=22050):
    """A WAV of a short 1 kHz click on every beat of `bpm`, the first at
    `first` seconds, and silence between."""
    n = int(rate * seconds)
    samples = [0] * n
    spb = 60 / bpm
    t = first
    while t < seconds:
        at = int(round(t * rate))
        for i in range(int(rate * 0.03)):
            if at + i < n:
                samples[at + i] = int(20000 * math.exp(-i / (rate * 0.006)) * math.sin(2 * math.pi * 1000 * i / rate))
        t += spb
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f'<{n}h', *samples))


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


def cuts_in(rgb, jump=60):
    """Frames where the picture changes colour at once: the first frame after each cut."""
    return [k for k in range(1, len(rgb)) if max(abs(a - b) for a, b in zip(rgb[k], rgb[k - 1])) > jump]


class Detection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.song = Path(cls.tmp.name) / 'click.wav'
        click_track(cls.song, 128, 0.37, 20)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
    def test_a_click_track_gives_its_bpm_and_first_beat(self):
        found = beats.detect(self.song)
        self.assertAlmostEqual(found.bpm, 128, delta=0.5)
        self.assertAlmostEqual(found.first, 0.37, delta=0.01)
        self.assertEqual(found.first_frame(30), 11)
        self.assertGreater(found.strength, 2)
        known = beats.detect(self.song, bpm=128)
        self.assertEqual((known.bpm, known.candidates), (128.0, ()))
        self.assertAlmostEqual(known.first, 0.37, delta=0.01)

    @unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
    def test_the_cli_prints_the_timeline_key(self):
        out = subprocess.run([sys.executable, '-m', 'videobuilder', 'beats', str(self.song), '--bpm', '128'],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
        self.assertIn('"beats": {"lane": 1, "item": 1, "bpm": 128.0, "first": 11}', out)
        self.assertIn('14.062 frames a beat', out)
        out = subprocess.run([sys.executable, '-m', 'videobuilder', 'beats', str(self.song), '--fps', '24',
                              '--bpm', '128'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        self.assertIn('"first": 9}', out)

    @unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
    def test_a_file_with_no_sound_is_a_clear_error(self):
        pic = Path(self.tmp.name) / 'pic.mp4'
        solid(pic, 'ff0000', 1)
        with self.assertRaisesRegex(ValueError, 'cannot read its sound'):
            beats.detect(pic)


class Grid(unittest.TestCase):
    # 128 bpm at 30 fps: 14.0625 frames a beat, so beats don't sit a whole number of frames apart.
    grid = beats.BeatGrid(30, 128, zero=11, lo=0, hi=300)

    def test_beat_frames_round_half_up_like_vb_grid(self):
        from videobuilder.timeline import Grid as FilmGrid
        film = FilmGrid(fps=30, bpm=128)
        self.assertEqual([self.grid.frame(k) for k in range(9)], [11 + film.b(k) for k in range(9)])
        self.assertEqual(self.grid.frames()[:5], [11, 25, 39, 53, 67])
        self.assertEqual(self.grid.frames()[-1], 292)
        self.assertEqual(self.grid.frames(30, 60), [39, 53])

    def test_snap_and_off(self):
        g = self.grid
        # 18 is as near 11 as 25: the later wins.
        self.assertEqual([g.snap(f) for f in (0, 11, 17, 18, 19, 300)], [11, 11, 11, 25, 25, 292])
        self.assertEqual((g.off(27), g.off(23), g.off(25)), (2, -2, 0))
        self.assertTrue(g.on_beat(39))
        self.assertTrue(g.is_downbeat(67))      # beat 4: bar 2
        self.assertFalse(g.is_downbeat(53))
        self.assertEqual((g.describe(67), g.describe(53)), ('bar 2', 'beat 4'))

    def test_step_a_beat_at_a_time(self):
        g = self.grid
        self.assertEqual([g.step(25, n) for n in (1, 2, -1, -5)], [39, 53, 11, 11])
        # From between beats, the next beat is the first step.
        self.assertEqual((g.step(30, 1), g.step(30, -1), g.step(30, 2)), (39, 25, 53))
        self.assertEqual(g.step(292, 3), 292)    # the last beat on the grid

    def test_a_grid_that_starts_late(self):
        # The song placed at frame 100, 40 frames into its file: beats before the file's frame 40 are not on it.
        g = beats.BeatGrid(30, 120, zero=100 - 40 + 6, lo=100, hi=200)
        self.assertEqual(g.frames(), [111, 126, 141, 156, 171, 186])
        self.assertEqual((g.snap(0), g.snap(500)), (111, 186))
        self.assertIsNone(beats.BeatGrid(30, 120, zero=0, lo=1, hi=10).index(5))


def reel(n=4, out=60, **extra):
    """A footage reel: `n` clips of `out` frames from one file, a song on Audio 1."""
    return {'version': 1, 'fps': 30, 'formats': ['16x9'],
            'clips': [{'id': f'c{k}', 'footage': 'sources/a.mp4', 'in': 0, 'out': out} for k in range(n)],
            'lanes': [{'items': [{'sound': 'sources/song.wav', 'at': 0, 'offset': 0, 'frames': n * out}]}],
            'beats': {'lane': 1, 'item': 1, 'bpm': 120, 'first': 0}, **extra}


def problems(data):
    try:
        tf.parse(data)
    except tf.TimelineError as e:
        return e.problems
    raise AssertionError('expected a TimelineError')


class BeatsInTheTimelineFile(unittest.TestCase):
    def test_a_grid_loads(self):
        d = reel()
        d['beats'].update({'bpm': 128.5, 'first': 11, 'bar': 3})
        t = tf.parse(d)
        self.assertEqual(t.beats, tf.Beats(1, 1, 128.5, 11, 3))
        g = tf.beat_grid(t)
        self.assertEqual((g.zero, g.lo, g.hi, g.bar), (11, 0, 240, 3))

    def test_no_grid_is_as_before(self):
        d = reel()
        del d['beats']
        t = tf.parse(d)
        self.assertIsNone(t.beats)
        self.assertIsNone(tf.beat_grid(t))
        self.assertEqual(tf.offbeat(t, tf.place(t, {})[0]), [])

    def test_the_grid_follows_the_songs_item(self):
        d = reel()
        d['lanes'].insert(0, {'items': []})
        d['lanes'][1]['items'].insert(0, {'sound': 'sources/x.wav', 'at': 0, 'frames': 10})
        d['lanes'][1]['items'][1].update({'at': 30, 'offset': 45, 'frames': 150})
        d['beats'].update({'lane': 2, 'item': 2, 'first': 6})
        g = tf.beat_grid(tf.parse(d))
        # The file's first beat (its frame 6) would be at 30 - 45 + 6; the grid starts where the item does.
        self.assertEqual((g.zero, g.lo, g.hi, g.frames()[:2]), (-9, 30, 180, [36, 51]))

    def test_bad_grids(self):
        cases = [
            ({'lane': 2, 'item': 1, 'bpm': 120}, 'beats: lane 2: there is no Audio 2 (the timeline has 1 lane)'),
            ({'lane': 1, 'item': 3, 'bpm': 120}, 'beats: item 3: Audio 1 has 1 item'),
            ({'lane': 1, 'item': 1}, 'beats: needs "bpm"'),
            ({'lane': 1, 'item': 1, 'bpm': 900}, 'beats: bpm must be between 30 and 300, not 900'),
            ({'lane': 1, 'item': 1, 'bpm': 120, 'first': -2}, 'beats: first must be at least 0, not -2'),
            ({'lane': 1, 'item': 1, 'bpm': 120, 'first': 1.5}, 'beats: first must be a whole number of frames'),
            ({'lane': 0, 'item': 1, 'bpm': 120}, 'beats: lane must be at least 1, not 0'),
            ({'lane': 1, 'item': 1, 'bpm': 120, 'bar': 40}, 'beats: bar must be at most 16 beats, not 40'),
            ({'lane': 1, 'item': 1, 'bpm': 120, 'tempo': 3}, 'beats: unknown key "tempo"'),
            ('120', 'beats: must be an object, not a string'),
        ]
        for raw, expected in cases:
            with self.subTest(expected=expected):
                found = problems({**reel(), 'beats': raw})
                self.assertTrue(any(p.startswith(expected) for p in found), found)
        self.assertIn('beats: lane 1: there is no Audio 1 (the timeline has 0 lanes)',
                      problems({**reel(), 'lanes': []}))

    def test_whip_and_flash_load(self):
        d = reel()
        d['clips'][1]['cut'] = {'transition': 'whip', 'frames': 8, 'direction': 'right'}
        d['clips'][2]['cut'] = {'transition': 'flash', 'frames': 6}
        d['clips'][3]['cut'] = {'transition': 'whip', 'frames': 8}
        t = tf.parse(d)
        self.assertEqual([c.cut for c in t.clips[1:]], [tf.Cut('whip', 8, 'right'), tf.Cut('flash', 6),
                                                         tf.Cut('whip', 8, 'left')])
        d['clips'][2]['cut']['direction'] = 'up'
        self.assertIn('clips[2] "c2".cut: direction is for a wipe or a whip only', problems(d))
        d['clips'][2]['cut'] = {'transition': 'flash'}
        self.assertIn('clips[2] "c2".cut: a flash needs "frames", its length', problems(d))


class OffBeat(unittest.TestCase):
    def test_cuts_off_the_beat_are_warnings(self):
        d = reel(out=60)     # 120 bpm: a beat every 15 frames; cuts at 60, 120, 180
        d['clips'][1]['out'] = 62                          # the cut into c2 at 122
        d['clips'][3]['cut'] = {'transition': 'dissolve', 'frames': 10}  # its middle at 182 - 10 + 5
        t = tf.parse(d)
        placements, _ = tf.place(t, {})
        self.assertEqual([tf.cut_frame(p) for p in placements[1:]], [60, 122, 177])
        self.assertEqual(tf.offbeat(t, placements), [
            'clips[2] "c2": the cut into it is at frame 122, 2 frames after bar 3 (frame 120); put it on 120 or 135',
            'clips[3] "c3": the dissolve\'s middle into it is at frame 177, 3 frames before bar 4 (frame 180); '
            'put it on 180 or 165',
        ])
        # A cut past the end of the song is not the grid's to judge.
        d['lanes'][0]['items'][0]['frames'] = 100
        self.assertEqual(tf.offbeat(tf.parse(d), placements), [])

    def test_snapping_puts_every_cut_on_a_beat(self):
        d = reel(n=5, out=70)
        d['clips'][1]['tail'] = 4
        d['clips'][3]['cut'] = {'transition': 'flash', 'frames': 6}
        d['beats']['bpm'] = 128
        snapped, moves = tf.snap_cuts(d)
        t = tf.parse(snapped)
        self.assertEqual(tf.offbeat(t, tf.place(t, {})[0]), [])
        # 128 bpm: beats at 0, 14, 28, 42, 56, 70 (on it already), 84...
        self.assertEqual(moves, ['clips[2] "c2": cut moved from frame 136 to 141 (beat 11)',
                                 'clips[3] "c3": cut moved from frame 208 to 211 (beat 16)',
                                 'clips[4] "c4": cut moved from frame 278 to 281 (bar 6)'])
        self.assertEqual(d['clips'][1], {'id': 'c1', 'footage': 'sources/a.mp4', 'in': 0, 'out': 70, 'tail': 4},
                         'the original is left alone')
        # c1 grows by 5: its tail of 4 back first, then its out moves by 1.
        self.assertEqual(snapped['clips'][1], {'id': 'c1', 'footage': 'sources/a.mp4', 'in': 0, 'out': 71})
        # c3's cut is the flash's middle: 208 - 6 + 3.
        self.assertEqual(tf.cut_frame(tf.place(t, {})[0][3]), 211)
        self.assertEqual(tf.snap_cuts(snapped)[1], [])

    def test_snapping_respects_a_files_end_and_unknown_lengths(self):
        d = reel(n=3, out=58)
        d['clips'][1] = {'id': 'dir', 'dir': 'clips/x'}
        # The footage file is 58 frames long: c0 can't grow to 60, so its cut goes back to 45.
        snapped, moves = tf.snap_cuts(d, {'c0': 58, 'dir': 50, 'c2': 58})
        self.assertEqual(snapped['clips'][0]['out'], 45)
        self.assertEqual(snapped['clips'][1]['tail'], 5)     # 45 + 50 = 95: back to 90
        self.assertEqual(len(moves), 2)
        _, moves = tf.snap_cuts(d, {'c0': 58})
        self.assertEqual(moves[-1], 'stopped at clips[1]: its length is known once it renders')
        with self.assertRaisesRegex(ValueError, 'no beat grid'):
            tf.snap_cuts({k: v for k, v in d.items() if k != 'beats'})


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


@unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
class OneSourceManyClips(unittest.TestCase):
    def test_several_ranges_of_one_file_are_each_their_own_clip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'sources').mkdir()
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc=size=192x108:rate=30:duration=4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                            '-g', '1', str(root / 'sources' / 'a.mp4')], check=True)
            solid(root / 'sources' / 'b.mp4', '00ff00', 1, size='192x108')
            data = {'version': 1, 'fps': 30, 'clips': [
                {'id': 'a-late', 'footage': 'sources/a.mp4', 'in': 90, 'out': 100},
                {'id': 'b', 'footage': 'sources/b.mp4', 'out': 10},
                {'id': 'a-early', 'footage': 'sources/a.mp4', 'in': 5, 'out': 15},
                {'id': 'a-start', 'footage': 'sources/a.mp4', 'in': 0, 'out': 10, 'head': 2}]}
            out = root / 'out.mp4'
            frames, _ = assembly.assemble(tf.parse(data), SMALL, out, root, {}, log=io.StringIO())
            self.assertEqual(frames, 38)
            # Each range shows its own frames of the file, wherever it is in the order.
            whole = root / 'whole.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(root / 'sources' / 'a.mp4'), '-vf',
                            'format=yuv420p', '-c:v', 'libx264', '-crf', '18', '-g', '1', str(whole)], check=True)
            got, src = frames_rgb(out, 32, 18), frames_rgb(root / 'sources' / 'a.mp4', 32, 18)

            def near(a, b):
                return max(abs(x - y) for x, y in zip(a, b)) < 6
            self.assertTrue(all(near(got[k], src[90 + k]) for k in range(10)))
            self.assertTrue(all(near(got[20 + k], src[5 + k]) for k in range(10)))
            self.assertTrue(all(near(got[30 + k], src[2 + k]) for k in range(8)))


@unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
class DoneWhenReel(unittest.TestCase):
    """Twelve clips and a song dropped on New video come back as a reel with
    every cut on a beat: the builder's steps as films.md "Cutting a reel"
    gives them, on synthetic footage and a click track."""

    BPM, FIRST = 128, 0.37

    def test_twelve_clips_and_a_song_cut_on_the_beat(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'sources').mkdir()
            sources = {}
            for k, colour in enumerate(COLOURS):
                name = f'clip{k + 1:02d}'
                solid(root / 'sources' / f'{name}.mp4', colour, 4 + k % 3)
                sources[name] = {'name': name, 'ext': 'mp4', 'width': 96, 'duration': 4 + k % 3}
            click_track(root / 'sources' / 'song.wav', self.BPM, self.FIRST, 40)
            sources['song'] = {'name': 'song', 'ext': 'wav', 'width': None, 'duration': 40}
            # What New video writes for twelve clips and a song.
            start = new_video.Start(clips=[{'source': n, 'act': None} for n in sources if n != 'song'],
                                    lanes=[{'sound': 'song', 'act': None}])
            data = new_video.timeline(start, sources)
            self.assertIn('Cut these clips to the song on Audio 1 (sources/song.wav): a reel, every cut on a beat',
                          ' '.join(new_video.note_lines(start, sources)))
            self.assertEqual((len(data['clips']), 'beats' in data), (12, False))

            # The builder: the song's beats, into the timeline.
            found = beats.detect(root / 'sources' / 'song.wav')
            self.assertAlmostEqual(found.bpm, self.BPM, delta=0.5)
            data['beats'] = {'lane': 1, 'item': 1, 'bpm': found.bpm, 'first': found.first_frame(30)}
            fpb = 30 * 60 / found.bpm
            # Each clip's best moment (here: from its middle), cut to whole beats and bars; the
            # first clip runs over the song's intro to its second downbeat. One source gives two clips.
            lengths = [4, 4, 2, 2, 4, 8, 2, 2, 4, 4, 2, 2]
            clips = []
            for c, n in zip(data['clips'], lengths):
                media = c['out']
                c['in'] = media // 2 - round(n * fpb / 2)
                c['out'] = c['in'] + round(n * fpb)     # near enough: --snap puts the cuts on the beats
                clips.append(c)
            clips[0]['in'] = 0
            clips[0]['out'] = data['beats']['first'] + round(4 * fpb) + 3
            again = dict(clips[2], id='clip03-again', **{'in': 0, 'out': round(4 * fpb) - 2})
            clips.insert(7, again)
            clips[5]['cut'] = {'transition': 'cut'}
            data['clips'] = clips
            (root / 'timeline.json').write_text(json.dumps(data, indent=2))
            t = tf.load(root / 'timeline.json')
            self.assertTrue(assembly.beat_warnings(root, t), 'cut by eye, some cuts are off the beat')

            moves = assembly.snap_dir(root)
            self.assertTrue(moves)
            t = tf.load(root / 'timeline.json')
            self.assertEqual(assembly.beat_warnings(root, t), [])
            placements, total = tf.place(t, assembly.known_lengths(root, t))
            data = json.loads((root / 'timeline.json').read_text())
            data['lanes'][0]['items'][0]['frames'] = total
            (root / 'timeline.json').write_text(json.dumps(data, indent=2))
            check = subprocess.run([sys.executable, '-m', 'videobuilder', 'assemble', str(root), '--check'],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn('13 clips, a reel at 128 bpm, every cut on a beat', check.stdout)
            self.assertNotIn('off the beat', check.stderr)

            # The assembled MP4: its picture cuts where its sound has beats.
            t = tf.load(root / 'timeline.json')
            out = root / 'reel.mp4'
            log = io.StringIO()
            frames, _ = assembly.assemble(t, SMALL, out, root, {}, log=log)
            self.assertEqual(frames, total)
            self.assertNotIn('off the beat', log.getvalue())
            cuts = cuts_in(frames_rgb(out))
            grid = tf.beat_grid(t)
            self.assertEqual(cuts, [tf.cut_frame(p) for p in placements[1:]])
            self.assertEqual(len(cuts), 12)
            self.assertEqual([c for c in cuts if not grid.on_beat(c)], [])
            heard = beats.detect(out, bpm=found.bpm)
            by_ear = beats.BeatGrid(30, found.bpm, heard.first_frame(30))
            self.assertEqual([c for c in cuts if abs(by_ear.off(c)) > 1], [], (cuts, heard))


if __name__ == '__main__':
    unittest.main()
