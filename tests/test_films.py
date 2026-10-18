"""Films made of clips: the timeline file, clip render keys, the assembly mix,
and an assembly that re-renders only what changed."""
import io
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
import urllib.error
from pathlib import Path

from videobuilder import assembly, timeline_file as tf
from videobuilder.clip_cache import ClipCache, FileTree, GitTree, clip_key, timeline_keys
from videobuilder.film import Sound

from tests import fixtures
from tests.test_project import TempProject, git, make_repo

QUIET = io.StringIO()
HAS_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def good():
    return {
        'version': 1, 'fps': 30, 'formats': ['1x1', '16x9'],
        'clips': [
            {'id': 'opening', 'dir': 'clips/01-opening'},
            {'id': 'boat', 'footage': 'sources/boat.mp4', 'in': 30, 'out': 120, 'head': 3, 'tail': 6,
             'cut': {'transition': 'dissolve', 'frames': 12},
             'sound': {'gain_db': -2, 'early': 6, 'dialogue': True}},
            {'id': 'credits', 'dir': 'clips/03-credits', 'film': 'credits.py',
             'cut': {'transition': 'wipe', 'frames': 10, 'direction': 'up'}},
        ],
        'acts': [{'title': 'The river', 'clips': ['opening', 'boat']}],
        'lanes': [
            {'duck': True, 'items': [{'sound': 'sources/theme.mp4', 'at': 0, 'frames': 240, 'gain_db': -3}]},
            {'items': []},
        ],
    }


def problems(data):
    with tf_raises() as caught:
        tf.parse(data)
    return caught.problems


class tf_raises:
    def __enter__(self):
        return self

    def __exit__(self, kind, exc, tb):
        if not isinstance(exc, tf.TimelineError):
            raise AssertionError(f'expected a TimelineError, got {exc!r}')
        self.problems = exc.problems
        return True


class TimelineFile(unittest.TestCase):
    def test_a_good_file_loads_into_dataclasses(self):
        t = tf.parse(good())
        self.assertEqual((t.fps, t.formats), (30, ('1x1', '16x9')))
        opening, boat, credits = t.clips
        self.assertFalse(opening.is_footage)
        self.assertEqual(opening.film_path, 'clips/01-opening/film.py')
        self.assertEqual(credits.film_path, 'clips/03-credits/credits.py')
        self.assertEqual((boat.footage, boat.in_frame, boat.out_frame, boat.head, boat.tail),
                         ('sources/boat.mp4', 30, 120, 3, 6))
        self.assertEqual(boat.cut, tf.Cut('dissolve', 12))
        self.assertEqual(boat.sound, tf.ClipSound(-2.0, 6, 0, True))
        self.assertEqual(credits.cut, tf.Cut('wipe', 10, 'up'))
        self.assertEqual(opening.cut, tf.Cut())
        self.assertEqual(t.acts, (tf.Act('The river', ('opening', 'boat')),))
        self.assertEqual([lane.name for lane in t.lanes], ['Audio 1', 'Audio 2'])
        self.assertTrue(t.lanes[0].duck)
        self.assertEqual(t.lanes[0].duck_db, tf.DEFAULT_DUCK_DB)
        self.assertEqual(t.lanes[0].items[0], tf.LaneItem('sources/theme.mp4', 0, 240, 0, -3.0))
        self.assertIs(t.clip('boat'), boat)

    def test_the_least_a_file_needs(self):
        t = tf.loads('{"version": 1, "clips": [{"id": "a", "dir": "a"}]}')
        self.assertEqual((t.fps, t.formats, t.acts, t.lanes), (30, ('16x9',), (), ()))

    def test_every_problem_is_named_with_where_it_is(self):
        d = good()
        d['clips'][0]['trim'] = 4
        d['clips'][1]['cut'] = {'transition': 'whip', 'frames': 4}
        d['clips'][2]['cut'] = {'transition': 'dissolve'}
        d['lanes'][0]['items'][0].pop('at')
        found = problems(d)
        self.assertIn('clips[0] "opening": unknown key "trim" (trim with "head" and "tail", frames off each end)', found)
        self.assertIn('clips[1] "boat".cut: transition "whip" is not available yet; use one of cut, dissolve, wipe',
                      found)
        self.assertIn('clips[2] "credits".cut: a dissolve needs "frames", its length', found)
        self.assertIn('Audio 1, item 1: needs "at"', found)
        self.assertEqual(len(found), 4)

    def test_bad_files(self):
        cases = [
            ({'version': 2, 'clips': [{'id': 'a', 'dir': 'a'}]}, 'version: must be 1, not 2'),
            ({'version': 1, 'clips': []}, 'clips: must be a non-empty list'),
            ({'version': 1, 'formats': ['4x3'], 'clips': [{'id': 'a', 'dir': 'a'}]}, 'unknown format "4x3"'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'a', 'dir': 'b'}]}, 'ids must be unique'),
            ({'version': 1, 'clips': [{'id': 'Big Clip', 'dir': 'a'}]}, 'lowercase letters'),
            ({'version': 1, 'clips': [{'id': 'a'}]}, 'exactly one of "dir"'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a', 'footage': 'f.mp4'}]}, 'exactly one of "dir"'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': '../elsewhere'}]}, 'relative path inside the video'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': '/abs'}]}, 'relative path inside the video'),
            ({'version': 1, 'clips': [{'id': 'a', 'footage': 'f.mp4', 'in': 3}]}, 'needs "out"'),
            ({'version': 1, 'clips': [{'id': 'a', 'footage': 'f.mp4', 'in': 30, 'out': 10}]},
             'out (10) must be after in (30)'),
            ({'version': 1, 'clips': [{'id': 'a', 'footage': 'f.mp4', 'out': 10, 'head': 6, 'tail': 4}]},
             'trims away all 10 frames'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a', 'in': 3}]}, '"in" is for footage clips'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a', 'head': -1}]}, 'head must be at least 0'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a', 'head': 1.5}]}, 'head must be a whole number'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a', 'cut': {'transition': 'dissolve', 'frames': 5}}]},
             'the first clip has no clip before it'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b',
                                                               'cut': {'transition': 'cut', 'frames': 5}}]},
             'a cut has no length'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b',
                                                               'cut': {'transition': 'dissolve', 'frames': 5,
                                                                       'direction': 'up'}}]},
             'direction is for a wipe only'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b',
                                                               'cut': {'transition': 'spin', 'frames': 5}}]},
             'transition must be one of cut, dissolve, wipe, not "spin"'),
            ({'version': 1, 'clips': [{'id': 'a', 'footage': 'f.mp4', 'out': 10},
                                      {'id': 'b', 'dir': 'b', 'cut': {'transition': 'dissolve', 'frames': 20}}]},
             'longer than the 10 frames it shows'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b'}, {'id': 'c', 'dir': 'c'}],
              'acts': [{'title': 'One', 'clips': ['a', 'c']}]}, 'consecutive clips'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b'}],
              'acts': [{'title': 'One', 'clips': ['b']}, {'title': 'Two', 'clips': ['a']}]}, 'must not overlap'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}], 'acts': [{'title': 'One', 'clips': ['z']}]},
             'no clip with id "z"'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}], 'lanes': [{}, {'name': 'music'}]},
             'lanes[1] (Audio 2): unknown key "name"'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}], 'lanes': [{'duck_db': -6}]},
             'duck_db is set but duck is not true'),
            ({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}],
              'lanes': [{'items': [{'sound': 'x.wav', 'at': 0, 'frames': 0}]}]}, 'frames must be at least 1'),
        ]
        for data, expected in cases:
            with self.subTest(expected=expected):
                found = problems(data)
                self.assertTrue(any(expected in p for p in found), found)

    def test_not_json(self):
        with tf_raises() as caught:
            tf.loads('{"version": 1,', 'timeline.json')
        self.assertIn('not valid JSON', caught.problems[0])

    def test_placement_overlaps_transitions(self):
        t = tf.parse(good())
        # opening renders 60 frames; boat shows 120-30-3-6 = 81 from source frame 33; credits 40.
        placed, total = tf.place(t, {'opening': 60, 'credits': 40, 'boat': 150})
        self.assertEqual([(p.start, p.frames, p.source) for p in placed], [(0, 60, 0), (48, 81, 33), (119, 40, 0)])
        self.assertEqual(total, 159)
        self.assertEqual(placed[1].media_frames, 150)

    def test_placement_refuses_what_a_clip_is_too_short_for(self):
        t = tf.parse(good())
        with self.assertRaisesRegex(ValueError, 'transitions \\(10 in, 0 out\\) are longer than the 8 frames'):
            tf.place(t, {'opening': 60, 'credits': 8})
        with self.assertRaisesRegex(ValueError, 'is only 100 frames long'):
            tf.place(t, {'opening': 60, 'credits': 40, 'boat': 100})


CLIP = textwrap.dedent('''
    import videobuilder as vb
    from shared.palette import COLOUR
    def draw(n, cv):
        cv.rect(0, 0, cv.width, cv.height, COLOUR)
        cv.rect(10 * n, 300, 200, 200, '{mark}')
    FILM = vb.Film(draw=draw, fps=30, frames=30, formats=('1x1', '16x9'){audio})
''')


def write_clip(root, name, mark='#ffffff', audio=''):
    d = Path(root) / 'clips' / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'film.py').write_text(CLIP.format(mark=mark, audio=audio))


def write_film(root, timeline, pin=True):
    root = Path(root)
    (root / 'shared').mkdir(parents=True, exist_ok=True)
    (root / 'shared' / '__init__.py').write_text('')
    (root / 'shared' / 'palette.py').write_text("COLOUR = '#203040'\n")
    if pin:
        (root / 'requirements.txt').write_text('videobuilder\n')
    write_clip(root, 'a', mark='#ffffff')
    write_clip(root, 'c', mark='#ffff00')
    (root / 'timeline.json').write_text(json.dumps(timeline, indent=2))


def three_clips(transition='dissolve'):
    return {'version': 1, 'fps': 30, 'formats': ['1x1'], 'clips': [
        {'id': 'a', 'dir': 'clips/a', 'tail': 3},
        {'id': 'boat', 'footage': 'sources/boat.mp4', 'in': 15, 'out': 45,
         'cut': {'transition': transition, 'frames': 6} if transition != 'cut' else {'transition': 'cut'},
         'sound': {'dialogue': True, 'early': 6}},
        {'id': 'c', 'dir': 'clips/c', 'cut': {'transition': 'wipe', 'frames': 6}},
    ], 'lanes': [{'duck': True, 'items': [{'sound': 'sources/bed.wav', 'at': 0, 'frames': 75, 'gain_db': -6}]}]}


def make_media(root):
    src = Path(root) / 'sources'
    src.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=30:duration=2',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-shortest', str(src / 'boat.mp4')], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=3',
                    str(src / 'bed.wav')], check=True)


class RenderKey(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        make_repo(self.root)
        write_film(self.root, three_clips())
        (self.root / 'README.md').write_text('a film\n')
        self.timeline = tf.load(self.root / 'timeline.json')
        self.a, self.c = self.timeline.clip('a'), self.timeline.clip('c')

    def commit(self, message):
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', message)
        return git(self.root, 'rev-parse', 'HEAD').strip()

    def keys(self, sha, fmt='1x1'):
        tree = GitTree(self.root, sha)
        return clip_key(tree, self.a, fmt), clip_key(tree, self.c, fmt)

    def test_a_key_follows_the_clip_and_what_it_shares(self):
        sha = self.commit('init')
        first = self.keys(sha)
        self.assertTrue(all(len(k) == 40 for k in first))
        self.assertNotEqual(first[0], first[1])
        self.assertTrue(set(self.keys(sha, '16x9')).isdisjoint(first))

        (self.root / 'README.md').write_text('an unrelated change\n')
        t = three_clips('cut')
        t['clips'][2]['head'] = 4
        (self.root / 'timeline.json').write_text(json.dumps(t))
        self.assertEqual(self.keys(self.commit('unrelated: readme, a trim, a transition')), first)

        write_clip(self.root, 'c', mark='#ff0000')
        after_c = self.keys(self.commit('edit clip c'))
        self.assertEqual(after_c[0], first[0])
        self.assertNotEqual(after_c[1], first[1])

        (self.root / 'shared' / 'palette.py').write_text("COLOUR = '#000000'\n")
        after_shared = self.keys(self.commit('edit shared'))
        self.assertNotEqual(after_shared[0], after_c[0])
        self.assertNotEqual(after_shared[1], after_c[1])

        (self.root / 'requirements.txt').write_text('videobuilder==9.9.9\n')
        after_pin = self.keys(self.commit('pin'))
        self.assertTrue(set(after_pin).isdisjoint(after_shared))

    def test_a_video_in_a_subdirectory(self):
        sub = self.root / 'promo'
        write_film(sub, three_clips())
        sha = self.commit('init')
        top, inner = GitTree(self.root, sha), GitTree(self.root, sha, 'promo')
        self.assertEqual(clip_key(top, self.a, '1x1'), clip_key(inner, self.a, '1x1'))
        (sub / 'shared' / 'palette.py').write_text("COLOUR = '#111111'\n")
        sha = self.commit('edit promo shared')
        self.assertNotEqual(clip_key(GitTree(self.root, sha), self.a, '1x1'),
                            clip_key(GitTree(self.root, sha, 'promo'), self.a, '1x1'))
        self.assertIsNotNone(GitTree(self.root, sha, 'promo').read('timeline.json'))

    def test_files_on_disk_key_the_same_way(self):
        tree = FileTree(self.root)
        first = clip_key(tree, self.a, '1x1'), clip_key(tree, self.c, '1x1')
        (self.root / 'clips' / 'a' / '__pycache__').mkdir()
        (self.root / 'clips' / 'a' / '__pycache__' / 'film.cpython.pyc').write_bytes(b'x')
        (self.root / 'timeline.json').write_text(json.dumps(three_clips('cut')))
        self.assertEqual((clip_key(tree, self.a, '1x1'), clip_key(tree, self.c, '1x1')), first)
        write_clip(self.root, 'a', mark='#00ff00')
        self.assertNotEqual(clip_key(tree, self.a, '1x1'), first[0])
        self.assertEqual(clip_key(tree, self.c, '1x1'), first[1])

    def test_a_missing_clip_is_an_error(self):
        sha = self.commit('init')
        gone = tf.Clip('gone', dir='clips/gone')
        with self.assertRaisesRegex(ValueError, 'clip "gone": no directory clips/gone'):
            clip_key(GitTree(self.root, sha), gone, '1x1')
        self.assertEqual(len(timeline_keys(self.timeline, GitTree(self.root, sha), ['1x1', '16x9'])), 4)

    def test_the_cache_writes_atomically_and_evicts(self):
        cache = ClipCache(self.root / 'cache')
        calls = []

        def render(out):
            calls.append(out.name)
            out.write_bytes(b'mp4')

        path, fresh = cache.get('a' * 40, '1x1', render)
        self.assertEqual((path.name, fresh, calls), ('a' * 40 + '-1x1.mp4', True, ['a' * 40 + '-1x1.partial.mp4']))
        self.assertEqual(cache.get('a' * 40, '1x1', render), (path, False))

        def broken(out):
            out.write_bytes(b'half')
            raise RuntimeError('died')

        with self.assertRaises(RuntimeError):
            cache.get('b' * 40, '1x1', broken)
        self.assertEqual(sorted(p.name for p in cache.root.iterdir()), [path.name])
        cache.get('b' * 40, '1x1', render)
        cache.evict({'b' * 40})
        self.assertEqual(sorted(p.name for p in cache.root.iterdir()), ['b' * 40 + '-1x1.mp4'])


class Mix(unittest.TestCase):
    """The assembly's sound: clip sound under its picture with J/L overlap, and
    lanes ducked under speech, built with the film mix code."""

    def setUp(self):
        self.t = tf.parse({'version': 1, 'fps': 30, 'clips': [
            {'id': 'a', 'dir': 'a', 'tail': 10, 'sound': {'late': 6}},
            {'id': 'b', 'footage': 'b.mp4', 'in': 30, 'out': 90, 'head': 4, 'sound': {'early': 12, 'gain_db': -3},
             'cut': {'transition': 'dissolve', 'frames': 8}},
            {'id': 'c', 'dir': 'c', 'sound': {'early': 6, 'late': 6}},
        ]})
        self.placed, self.total = tf.place(self.t, {'a': 60, 'b': 300, 'c': 30})
        self.media = {'a': ('a.mp4', True, False), 'b': ('b.mp4', True, True), 'c': ('c.mp4', True, False)}

    def test_clip_sound_follows_the_picture_and_its_j_l_overlap(self):
        (a, _), (b, b_speech), (c, _) = assembly.clip_sounds(self.t, self.placed, self.media)
        # a: shows 0..50 of 60; its L-cut runs 6 more frames from its trimmed tail.
        self.assertEqual((a.at, a.start, a.frames), (0, 0.0, 56))
        self.assertEqual(a.fade_out_frames, tf.DEFAULT_FADE)  # an L-cut: its own short ramp, not the dissolve
        # b: dissolves in at 42, shows source 34..90; its J-cut reaches 12 frames back into the source.
        self.assertEqual((b.at, b.start, b.frames, b.gain_db), (30, 22 / 30, 68, -3.0))
        self.assertTrue(b_speech)
        # c: nothing trimmed, so no sound before or after its picture to reveal.
        self.assertEqual((c.at, c.start, c.frames), (self.placed[2].start, 0.0, 30))

    def test_a_dissolve_crossfades_the_sound(self):
        t = tf.parse({'version': 1, 'clips': [
            {'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b', 'cut': {'transition': 'dissolve', 'frames': 8}}]})
        placed, _ = tf.place(t, {'a': 30, 'b': 30})
        (a, _), (b, _) = assembly.clip_sounds(t, placed, {'a': ('a.mp4', True, False), 'b': ('b.mp4', True, False)})
        self.assertEqual((a.fade_out_frames, b.fade_in_frames, b.at), (8, 8, 22))

    def test_clips_without_sound_add_nothing(self):
        media = {**self.media, 'a': ('a.mp4', False, False)}
        self.assertEqual(len(assembly.clip_sounds(self.t, self.placed, media)), 2)

    def test_a_ducked_lane_dips_under_speech_only(self):
        clips = assembly.clip_sounds(self.t, self.placed, self.media)
        bed = Sound('bed.wav', at=0, start=0.0, frames=self.total)
        ducked = tf.Lane('Audio 1', (), True, -10.0)
        plain = tf.Lane('Audio 2')
        inputs, graph, label = assembly.mix_graph(clips, [(ducked, [bed]), (plain, [bed])], self.total, 30)
        self.assertEqual(inputs, ['a.mp4', 'b.mp4', 'c.mp4', 'bed.wav', 'bed.wav'])
        chains = graph.split(';')
        self.assertEqual(label, 'mix')
        self.assertTrue(chains[-1].startswith('[s0][s1][s2][s3][s4]amix=inputs=5:normalize=0'))
        self.assertIn('volume=eval=frame', chains[3])
        self.assertIn('pow(10,(-10.0*', chains[3])
        # Only b is speech: one span in the envelope, from b's sound (1 s to its end).
        self.assertEqual(chains[3].count('clip((t-'), 1)
        self.assertIn(f'clip((t-{30 / 30:.6f})', chains[3])
        self.assertNotIn('volume=eval', chains[4])
        self.assertTrue(all('volume=eval' not in c for c in chains[:3]))

    def test_no_speech_no_ducking_and_input_numbering(self):
        media = {k: (p, True, False) for k, (p, _, _) in self.media.items()}
        clips = assembly.clip_sounds(self.t, self.placed, media)
        lane = tf.Lane('Audio 1', (), True)
        inputs, graph, _ = assembly.mix_graph(clips, [(lane, [Sound('bed.wav', 0, 0.0, 10)])], self.total, 30,
                                              start_idx=1)
        self.assertNotIn('volume=eval', graph)
        self.assertTrue(graph.startswith('[1:a]'))
        self.assertIn('[4:a]', graph)

    def test_nothing_at_all_is_silence(self):
        inputs, graph, label = assembly.mix_graph([], [], 60, 30)
        self.assertEqual(inputs, [])
        self.assertIn('anullsrc', graph)


def frame_count(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                          'stream=nb_read_frames', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip())


def framemd5(path):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v', '-f', 'framemd5', '-'],
                         capture_output=True, text=True, check=True).stdout
    return [line.split(',')[-1].strip() for line in out.splitlines() if not line.startswith('#')]


def audio_seconds(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=duration',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


@unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
class Assembly(unittest.TestCase):
    """A 3-clip film (two clip directories and a footage clip) assembles; an
    edit to one clip re-renders only it; a transition or trim, none."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "Tom's film"  # a quote: the concat list must escape it
        write_film(self.root, three_clips())
        make_media(self.root)
        self.rendered = []

    def render_clip(self, clip, fmt, out):
        self.rendered.append(clip.id)
        assembly.render_clip_local(self.root, clip, fmt, out, jobs=2, log=QUIET)

    def assemble(self):
        return assembly.assemble_dir(self.root, out=self.root / 'out.mp4', render_clip=self.render_clip,
                                     log=io.StringIO())

    def test_only_what_changed_renders(self):
        first = self.assemble()
        # a shows 27 of 30; boat 30, dissolving in over 6; c 30, wiping in over 6.
        self.assertEqual((self.rendered, first.frames), (['a', 'c'], 27 + 30 + 30 - 6 - 6))
        self.assertEqual(frame_count(first.out), 75)
        self.assertAlmostEqual(audio_seconds(first.out), 75 / 30, delta=0.05)
        self.assertFalse(first.copied)

        self.rendered.clear()
        write_clip(self.root, 'c', mark='#ff0000')
        second = self.assemble()
        self.assertEqual((self.rendered, second.reused), (['c'], ['a']))

        self.rendered.clear()
        t = three_clips('cut')
        t['clips'][0]['tail'] = 0
        (self.root / 'timeline.json').write_text(json.dumps(t))
        third = self.assemble()
        self.assertEqual((self.rendered, third.reused), ([], ['a', 'c']))
        self.assertEqual(frame_count(third.out), 30 + 30 + 30 - 6)

    def test_plain_hard_cuts_join_without_re_encoding(self):
        t = {'version': 1, 'fps': 30, 'formats': ['1x1'],
             'clips': [{'id': 'a', 'dir': 'clips/a'}, {'id': 'c', 'dir': 'clips/c'}]}
        (self.root / 'timeline.json').write_text(json.dumps(t))
        result = self.assemble()
        self.assertTrue(result.copied)
        self.assertEqual(frame_count(result.out), 60)

    def test_footage_seeked_near_its_cut_shows_the_same_frames(self):
        t = three_clips('cut')
        t['clips'][1].update({'in': 40, 'out': 55})
        (self.root / 'timeline.json').write_text(json.dumps(t))
        self.assertEqual(assembly.footage_seek(40, 30), 10)
        seeked = self.assemble()
        sums = framemd5(seeked.out)
        orig = assembly.footage_seek
        assembly.footage_seek = lambda source, fps: 0
        self.addCleanup(setattr, assembly, 'footage_seek', orig)
        self.assertEqual(framemd5(self.assemble().out), sums)

    def test_an_ffmpeg_failure_says_why(self):
        with self.assertRaisesRegex(ValueError, '(?s)encoding the picture failed:.*No such file'):
            assembly._run(['ffmpeg', '-v', 'error', '-i', str(self.root / 'missing.mp4'), '-f', 'null', '-'],
                          'encoding the picture')

    def test_a_clip_at_another_frame_rate_is_refused(self):
        film = self.root / 'clips' / 'a' / 'film.py'
        film.write_text(film.read_text().replace('fps=30', 'fps=25'))
        with self.assertRaisesRegex(ValueError, 'clip "a" renders at 25 fps; the timeline is 30 fps'):
            self.assemble()

    def test_footage_outside_the_video_is_refused(self):
        os.symlink('/etc/hostname', self.root / 'sources' / 'escape.mp4')
        t = three_clips()
        t['clips'][1]['footage'] = 'sources/escape.mp4'
        (self.root / 'timeline.json').write_text(json.dumps(t))
        with self.assertRaisesRegex(ValueError, 'resolves outside the video'):
            self.assemble()


@unittest.skipUnless(HAS_FFMPEG, 'needs ffmpeg')
class EditorAssembly(TempProject):
    """The editor serves a film of clips' assembly from /api/video, and one
    clip's render from /api/clip, through the render queue."""
    start = fixtures.API.start
    get = fixtures.API.get

    def setUp(self):
        super().setUp()
        self.start()
        git(self.root, 'branch', '-M', 'main')
        promo = self.root / 'promo'
        write_film(promo, three_clips(), pin=False)  # no pin: the editor's own videobuilder renders it
        make_media(promo)
        # The editor links uploaded sources into a render's worktree; committing
        # the tiny fixtures stands in for that here.
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'a film of clips')
        self.sha = git(self.root, 'rev-parse', 'main').strip()
        self.rendered = []

        def render_clip(video, work, root, clip, fmt, out):
            self.rendered.append(clip.id)
            assembly.render_clip_local(root, clip, fmt, out, jobs=2, log=QUIET)
        self.editor.renders.clip_renderer = render_clip

    def wait(self, path):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            body = self.get(path)
            if isinstance(body, bytes):
                return body
            self.assertIn(body['state'], ('queued', 'rendering'), body)
            time.sleep(0.2)
        self.fail('render did not finish')

    def test_video_and_clip(self):
        data = self.wait(f'/api/video?video=promo/film&commit={self.sha}')
        self.assertTrue(data[4:8] == b'ftyp')
        self.assertEqual(sorted(self.rendered), ['a', 'c'])
        self.assertEqual(self.editor.renders.states('promo/film', self.sha), {'1x1': 'ready'})

        self.rendered.clear()
        clip = self.wait(f'/api/clip?video=promo/film&clip=c&commit={self.sha}')
        self.assertEqual(self.rendered, [])  # the assembly cached it
        self.assertEqual(clip, self.editor.renders.clip_path('promo/film', self.sha, '1x1', 'c').read_bytes())

        for path, code in ((f'/api/clip?video=promo/film&clip=boat&commit={self.sha}', 404),
                           (f'/api/video?video=promo/film&commit={self.sha}&format=16x9', 400)):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.get(path)
            with caught.exception as e:
                self.assertEqual(e.code, code)

        t = three_clips('cut')
        (self.root / 'promo' / 'timeline.json').write_text(json.dumps(t))
        git(self.root, 'commit', '-qam', 'a hard cut')
        sha = git(self.root, 'rev-parse', 'main').strip()
        self.wait(f'/api/video?video=promo/film&commit={sha}')
        self.assertEqual(self.rendered, [])

        self.editor.renders.keep = 1
        self.editor.renders.evict('promo/film')
        self.assertTrue(self.editor.renders.clip_path('promo/film', sha, '1x1', 'c').is_file())
        write_clip(self.root / 'promo', 'c', mark='#00ff00')
        git(self.root, 'commit', '-qam', 'edit c')
        old_c = self.editor.renders.clip_path('promo/film', sha, '1x1', 'c')
        self.editor.renders.evict('promo/film')
        self.assertFalse(old_c.exists())
        self.assertTrue(self.editor.renders.clip_path('promo/film', sha, '1x1', 'a').is_file())


if __name__ == '__main__':
    unittest.main()
