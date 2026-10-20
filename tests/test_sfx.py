"""Sound effects: building the pack, its index, placing a sound on a frame,
the mix (a single film's and an assembly's), the timeline key, the missing
pack, fetching it, and the sync check. Every test reads the fixture pack
(tests/fixtures/sfx-pack, set in tests/__init__.py)."""
import array
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import videobuilder as vb
from videobuilder import assembly, sfx, timeline_file as tf
from videobuilder.film import Audio, Film, Sound
from videobuilder.render import ducking, render

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'tests' / 'fixtures' / 'sfx-pack'
BANK_INDEX = ROOT / 'tests' / 'fixtures' / 'sfx-bank-index.json'
CHECK = ROOT / 'skill' / 'make-a-video' / 'scripts' / 'check.py'
QUIET = io.StringIO()


def builder():
    spec = importlib.util.spec_from_file_location('build_sfx_pack', ROOT / 'scripts' / 'build_sfx_pack.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def index():
    return json.loads((FIXTURE / 'index.json').read_text())


def write_wav(path, samples, rate=48000):
    """A 16-bit mono WAV of float `samples`."""
    data = array.array('h', (max(-32767, min(32767, round(x * 32767))) for x in samples))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def blank(n, cv):
    cv.fill('#000')


def mix_envelope(path):
    """The rendered MP4's mono sound, as 1 ms power."""
    return sfx.envelope(sfx.decode(path, channels=1))


class Pack(unittest.TestCase):
    """scripts/build_sfx_pack.py on a bank made from the fixture pack's own takes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        bank = Path(cls.tmp.name) / 'bank'
        (bank / 'wav').mkdir(parents=True)
        shutil.copy(BANK_INDEX, bank / 'index.json')
        rows = json.loads(BANK_INDEX.read_text())['files']
        for r in rows:
            ogg = FIXTURE / 'audio' / (Path(r['file']).stem + '.ogg')
            wav = bank / 'wav' / r['file']
            if ogg.exists():
                subprocess.run(['ffmpeg', '-v', 'error', '-i', str(ogg), '-c:a', 'pcm_f32le', str(wav)], check=True)
            else:   # a take the fixture left out: any sound will do
                write_wav(wav, [math.sin(i / 7) * math.exp(-i / 2000) for i in range(9600)])
        b = builder()
        cls.tar = Path(cls.tmp.name) / 'pack.tar'
        cls.dir = Path(cls.tmp.name) / 'pack'
        cls.doc, cls.problems = b.build(bank, FIXTURE / 'LICENSE-earshot', cls.tar, cls.dir, jobs=1, log=QUIET)
        cls.again = Path(cls.tmp.name) / 'again.tar'
        b.build(bank, FIXTURE / 'LICENSE-earshot', cls.again, jobs=1, log=QUIET)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_takes_and_what_was_left_out(self):
        self.assertEqual(self.problems, [])
        takes = {(s['id'], v['variant']) for s in self.doc['sounds'] for v in s['variants']}
        want = {(s['id'], v['variant']) for s in index()['sounds'] for v in s['variants']}
        self.assertEqual(takes, want)
        # ding_2045 Fs5 failed earshot's audit and goes; detent failed it too, but is its category's only take.
        self.assertEqual([(x['id'], x['variant']) for x in self.doc['left_out']], [('pro_notify/ding_2045', 'Fs5')])
        self.assertIn('comb ring', self.doc['left_out'][0]['why'])
        self.assertIn(('hover_tick/detent', None), takes)

    def test_times_are_measured_on_the_encoded_files(self):
        shipped = {(s['id'], v['variant']): v for s in index()['sounds'] for v in s['variants']}
        for s in self.doc['sounds']:
            for v in s['variants']:
                with self.subTest(id=s['id'], variant=v['variant']):
                    measured = sfx.measure(sfx.decode(self.dir / v['file']))
                    self.assertAlmostEqual(v['peak_s'], measured['peak_s'], delta=0.002)
                    self.assertEqual(v['onset_s'], measured['onset_s'])
                    # A second encode of the fixture's takes keeps their peaks.
                    self.assertAlmostEqual(v['peak_s'], shipped[(s['id'], v['variant'])]['peak_s'], delta=0.002)

    def test_the_tar_is_plain_and_the_same_each_time(self):
        self.assertEqual(self.tar.read_bytes(), self.again.read_bytes())
        with tarfile.open(self.tar, 'r:') as tf_:   # no compression on top of the audio
            names = tf_.getnames()
            self.assertTrue({'index.json', 'LICENSE-earshot', 'CREDITS.md', 'README.md'} <= set(names))
            self.assertTrue(all(n.startswith('audio/') and n.endswith('.ogg') for n in names if '/' in n))
            self.assertEqual({m.mtime for m in tf_.getmembers()}, {0})
        self.assertIn('MIT', (self.dir / 'LICENSE-earshot').read_text())
        credits = (self.dir / 'CREDITS.md').read_text()
        self.assertIn('Leon Lin', credits)
        self.assertIn('qubodup', credits)   # fit/click/floss_lid's recordist

    def test_settle_keeps_a_flat_peak_and_refuses_a_shifted_take(self):
        b = builder()
        src = array.array('f', [0.0] * 9600 * 2)
        for i in range(2000, 8000):   # a flat swell: any 5 ms of it is as loud
            src[2 * i] = src[2 * i + 1] = 0.5 * math.sin(i / 3)
        m_wav = sfx.measure(src)
        m = dict(m_wav, peak_s=m_wav['peak_s'] + 0.03)
        self.assertIsNone(b.settle('swell', m, m_wav, src, src))
        self.assertEqual(m['peak_s'], m_wav['peak_s'])
        late = array.array('f', [0.0] * 2 * 480) + src[:-2 * 480]   # 10 ms late: pre-skip left in
        self.assertIn('+10 ms off', b.settle('late', dict(m_wav), m_wav, src, late))


class Index(unittest.TestCase):
    """The pack's index.json, as the fixture ships it."""

    def test_schema(self):
        doc = index()
        self.assertEqual((doc['pack'], doc['schema']), (sfx.PACK, sfx.SCHEMA))
        self.assertEqual(doc['audio']['codec'], 'opus')
        for s in doc['sounds']:
            with self.subTest(id=s['id']):
                self.assertTrue({'id', 'category', 'role', 'family', 'about', 'credit', 'variants'} <= set(s))
                self.assertIn(s['family'], ('classic', 'designed', 'fitted'))
                self.assertEqual(s['credit'] is not None, s['family'] == 'fitted')
                self.assertEqual(s['variants'][0]['variant'] is None, any(v['variant'] is None for v in s['variants']))
                for v in s['variants']:
                    self.assertTrue((FIXTURE / v['file']).is_file(), v['file'])
                    self.assertLessEqual(v['onset_s'], v['peak_s'])
                    self.assertLessEqual(v['peak_s'], v['end_s'])
                    self.assertLessEqual(v['end_s'], v['dur_s'] + 1e-9)
                    self.assertLess(v['peak_db'], 0)
                    self.assertTrue((v['length_s'] is None) != (v['note'] is None) or v['variant'] is None)
        fit = sfx.bank().get('fit/click/floss_lid')
        self.assertEqual(fit.credit['license'], 'CC0 1.0')

    def test_roles_are_plain_words(self):
        self.assertEqual(vb.sfx.roles(), ['click', 'ding', 'hit', 'tick', 'whoosh'])
        self.assertEqual([e.id for e in vb.sfx.find('hit')], ['pro_impact/short'])
        self.assertEqual([e.id for e in vb.sfx.find('pro_impact')], ['pro_impact/short'])   # a category works too
        with self.assertRaisesRegex(ValueError, 'roles: click, ding'):
            vb.sfx.find('sub-drop')
        self.assertEqual(sfx.role_key('Sub_Drop'), 'sub drop')


class Placement(unittest.TestCase):
    def test_a_sound_lands_its_peak_or_onset_on_its_frame(self):
        for fps in (24, 30, 60):
            for sync in (0.0, 0.004, 0.0333, 0.129, 1.0):
                first, start = sfx.placement(sync, 100, fps)
                self.assertLessEqual(start, 0)
                self.assertGreater(start, -1 / fps)
                # The file begins -start s after frame `first`; its sync point plays on frame 100.
                self.assertAlmostEqual(first / fps - start + sync, 100 / fps)
        whoosh = vb.sfx.sound('whoosh_fast/tight', at=45, variant='0.5s')
        self.assertIsInstance(whoosh, Sound)
        self.assertAlmostEqual(whoosh.at / 30 - whoosh.start + 0.1287, 45 / 30)
        tap = vb.sfx.sound('fit/click/floss_lid', at=45, align='onset', gain_db=-6)
        self.assertAlmostEqual(tap.at / 30 - tap.start + 0.004, 45 / 30)
        self.assertEqual((tap.mark, tap.align, tap.gain_db, tap.ducks, tap.fade_in_frames), (45, 'onset', -6, False, 0))

    def test_a_film_places_its_sounds_at_its_own_fps(self):
        whoosh = vb.sfx.sound('whoosh_fast/tight', at=120, variant='0.5s')   # placed at the default 30 fps
        for fps in (24, 25, 60):
            s = Film(draw=blank, fps=fps, frames=300, formats=('1x1',), sounds=(whoosh,)).sounds[0]
            self.assertEqual((s.fps, s.mark), (fps, 120))
            self.assertAlmostEqual(s.at / fps - s.start + s.sync_s, 120 / fps)
            self.assertGreaterEqual((s.at + s.frames) / fps - s.start, s.take.dur_s)   # the whole take plays
            self.assertEqual(s, vb.sfx.sound('whoosh_fast/tight', at=120, fps=fps, variant='0.5s'))
        trimmed = Film(draw=blank, fps=60, frames=300, formats=('1x1',),
                       sounds=(vb.sfx.sound('whoosh_fast/tight', at=120, dur=0.45),)).sounds[0]
        self.assertEqual(trimmed, vb.sfx.sound('whoosh_fast/tight', at=120, fps=60, dur=0.45))
        self.assertGreater(trimmed.fade_out_frames, 0)

    def test_the_length_nearest_dur(self):
        e = vb.sfx.get('whoosh_fast/tight')
        self.assertEqual(e.take(dur=0.3).variant, '0.25s')
        self.assertEqual(e.take(dur=0.375).variant, '0.5s')   # as near as 0.25 s: the longer, to cut
        self.assertEqual(e.take(dur=2).variant, '0.5s')
        short = e.sound(at=30, dur=0.3)   # 0.25 s is shorter than asked: played whole, no fade
        self.assertEqual((short.variant, short.fade_out_frames), ('0.25s', 0))
        cut = e.sound(at=30, dur=0.4)     # the 0.5 s take, cut to 0.4 s with a short fade
        self.assertEqual(cut.variant, '0.5s')
        self.assertEqual(cut.fade_out_frames, 3)
        self.assertEqual(cut.frames, math.ceil((0.4 - cut.start) * 30))
        self.assertGreater(cut.at + cut.frames - cut.fade_out_frames, cut.mark)   # fades after its peak
        with self.assertRaisesRegex(ValueError, 'before its peak'):
            e.sound(at=30, variant='0.5s', dur=0.1)
        whole = vb.sfx.sound('pro_impact/short', at=30)
        self.assertEqual(whole.fade_out_frames, 0)

    def test_the_note(self):
        self.assertEqual([sfx.note_name(n) for n in ('C#5', 'Cs5', 'Db5', 'c#5', 'Bb4', 'E#4', 'Cb5', 'G5')],
                         ['Cs5', 'Cs5', 'Cs5', 'Cs5', 'As4', 'F4', 'B4', 'G5'])
        ding = vb.sfx.get('pro_notify/ding_2045')
        self.assertEqual(ding.take(note='G5').variant, 'G5')
        self.assertEqual(ding.take(variant='A5').note, 'A5')
        self.assertIsNone(ding.take().variant)
        with self.assertRaisesRegex(ValueError, r'no Gs5 \(nearest: G5\); its notes: G5, A5'):
            ding.take(note='Ab5')
        with self.assertRaisesRegex(ValueError, 'not tuned'):
            vb.sfx.get('pro_impact/short').take(note='C5')
        with self.assertRaisesRegex(ValueError, 'not a note'):
            sfx.note_name('H2')

    def test_an_unknown_sound_suggests_a_near_one(self):
        with self.assertRaisesRegex(ValueError, 'did you mean whoosh_fast/tight'):
            vb.sfx.get('whoosh_fast/tigth')
        with self.assertRaisesRegex(ValueError, "has no variant '0.8s'; it has 0.25s, 0.5s"):
            vb.sfx.sound('whoosh_fast/tight', at=3, variant='0.8s')

    def test_find_by_role_nearest_length_first(self):
        self.assertEqual([e.id for e in vb.sfx.find('whoosh', near_dur=0.8)], ['whoosh_fast/tight'])
        self.assertEqual(sfx.bank().take('whoosh_fast/tight--0.25s').length_s, 0.25)


class Mix(unittest.TestCase):
    """Sound effects in a rendered film's sound."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def render(self, film, name='film.mp4'):
        out = str(self.dir / name)
        render(film, out, jobs=2, log=QUIET)
        return out

    def test_a_sound_lands_on_its_frame(self):
        sounds = (vb.sfx.sound('fit/click/floss_lid', at=20), vb.sfx.sound('whoosh_fast/tight', at=47, dur=0.5),
                  vb.sfx.sound('pro_notify/ding_2045', at=70, note='G5', align='onset'))
        out = self.render(Film(draw=blank, fps=30, frames=90, formats=('1x1',), sounds=sounds, loudness=None))
        mix = sfx.decode(out, channels=1)
        # With nothing else playing, each sound measures in the mix as in the pack: its peak (onset) on its frame.
        for s, key in zip(sounds, ('peak_s', 'peak_s', 'onset_s')):
            begins = s.at / 30 - s.start
            heard = sfx.measure(mix[round(begins * 48000):round((s.at + s.frames) / 30 * 48000)], channels=1)
            self.assertAlmostEqual(begins + heard[key], s.mark / 30, delta=0.003)
        self.assertEqual([r['offset_ms'] for r in sfx.sync(out, sounds, 30, 90)], [0, 0, 0])

    def test_sounds_stacked_on_one_frame_each_land(self):
        music = self.dir / 'music.wav'
        write_wav(music, [0.05 * math.sin(i * 2 * math.pi * 110 / 48000) for i in range(48000 * 3)])
        sounds = (vb.sfx.sound('whoosh_fast/tight', at=40, dur=0.5), vb.sfx.sound('pro_impact/short', at=40),
                  vb.sfx.sound('fit/click/floss_lid', at=40, align='onset'))
        out = self.render(Film(draw=blank, fps=30, frames=75, formats=('1x1',), sounds=sounds,
                               audio=Audio(str(music))))
        rows = sfx.sync(out, sounds, 30, 75)
        self.assertEqual([r['landed'] for r in rows], [True, True, True], rows)

    def test_sound_effects_may_be_limited_more_than_the_bed(self):
        from videobuilder import render as mixer
        music = self.dir / 'music.wav'
        write_wav(music, [0.05 * math.sin(i * 2 * math.pi * 110 / 48000) for i in range(48000 * 2)])
        film = Film(draw=blank, fps=30, frames=60, sounds=(vb.sfx.sound('pro_impact/short', at=30),),
                    audio=Audio(str(music)))
        whole, bed = mixer.mix_graph(film, 0, 60), mixer.mix_graph(film, 0, 60, effects=False)
        self.assertEqual(len(bed[0]), 1)   # the music alone
        plain = mixer.loudness_gain_graph(*whole, -14)
        more = mixer.loudness_gain_graph(*whole, -14, bed)
        self.assertAlmostEqual(more - plain, mixer.SFX_LIMITING_DB, delta=0.01)   # the hit's peak set the cap

    def test_sound_effects_dip_under_speech_with_the_music_unless_through(self):
        speech = self.dir / 'speech.wav'
        write_wav(speech, [0.003 * math.sin(i * 2 * math.pi * 300 / 48000) for i in range(48000)])
        music = self.dir / 'music.wav'
        write_wav(music, [0.0] * 48000 * 2)
        levels = {}
        for through in (False, True):
            hit = vb.sfx.sound('pro_impact/short', at=30, through=through)
            film = Film(draw=blank, fps=30, frames=60, formats=('1x1',),
                        audio=Audio(str(music), duck_db=-12, loudness=None),
                        sounds=(Sound(str(speech), at=15, start=0.0, frames=30, fade_in_frames=1, fade_out_frames=1),
                                hit))
            env = mix_envelope(self.render(film, f'{through}.mp4'))
            # The hit's peak, 0.18 s into it, plays at 1 s, while the speech plays.
            levels[through] = 10 * math.log10(max(env[995:1006]))
        self.assertAlmostEqual(levels[True] - levels[False], 12, delta=1.5)

    def test_sound_effects_dont_duck_the_music(self):
        hit = vb.sfx.sound('pro_impact/short', at=30)
        voice = Sound('v.wav', at=10, start=0.0, frames=10)
        self.assertEqual(ducking([hit, voice]), [voice])
        spans = self.dir / 'spans.json'
        assembly.write_spans(Film(draw=blank, fps=30, frames=60, sounds=(hit, voice)), spans)
        self.assertEqual([s['at'] for s in json.loads(spans.read_text())], [10])   # lanes don't dip under a hit

    def test_a_sound_cut_off_at_the_films_start_or_end(self):
        early = vb.sfx.sound('pro_impact/short', at=2)   # starts before frame 0
        self.assertLess(early.at, 0)
        film = Film(draw=blank, fps=30, frames=12, formats=('1x1',), sounds=(early,), loudness=None)
        self.assertEqual(film.sounds[0].at, 0)
        self.assertIsInstance(film.sounds[0], sfx.Sfx)
        out = self.render(film)
        self.assertTrue(sfx.sync(out, film.sounds, 30, 12)[0]['cut'])


class TimelineKey(unittest.TestCase):
    def doc(self, item=None, cut=None):
        d = {'version': 1, 'fps': 30, 'clips': [{'id': 'a', 'dir': 'a'}, {'id': 'b', 'dir': 'b'}],
             'lanes': [{'duck': True, 'items': [item]}] if item else []}
        if cut:
            d['clips'][1]['cut'] = cut
        return d

    def problems(self, **kw):
        try:
            tf.parse(self.doc(**kw))
        except tf.TimelineError as e:
            return e.problems
        return []

    def test_a_sound_effect_on_a_lane(self):
        t = tf.parse(self.doc({'sfx': 'whoosh_fast/tight', 'at': 47, 'frames': 15, 'align': 'onset',
                               'gain_db': -6, 'through': True}))
        item = t.lanes[0].items[0]
        self.assertIsNone(item.sound)
        self.assertEqual(item.cue, tf.SfxCue('whoosh_fast/tight', None, None, 15, 'onset', -6.0, True))
        self.assertEqual(tf.parse(self.doc({'sfx': 'pluck/kalimba', 'note': 'Db5', 'at': 3})).lanes[0].items[0].cue.note,
                         'Cs5')

    def test_bad_sound_effects(self):
        cases = [
            ({'sfx': 'whoosh', 'at': 3}, 'must be a sound effect\'s id'),
            ({'sfx': 'a/b', 'at': 3, 'offset': 2}, 'unknown key "offset"'),
            ({'sfx': 'a/b'}, 'needs "at"'),
            ({'sfx': 'a/b', 'sound': 'x.wav', 'at': 3, 'frames': 3}, 'not both'),
            ({'sfx': 'a/b', 'at': 3, 'align': 'end'}, 'align must be "peak" or "onset"'),
            ({'sfx': 'a/b', 'at': 3, 'note': 'H5'}, 'not a note'),
            ({'sfx': 'a/b', 'at': 3, 'note': 'C5', 'variant': '0.5s'}, 'a variant or a note, not both'),
            ({'sfx': 'auto', 'at': 3}, 'for a cut'),
            ({'sfx': 'a/b', 'at': 3, 'through': 'yes'}, 'through must be true or false'),
        ]
        for item, msg in cases:
            with self.subTest(item=item):
                self.assertTrue(any(msg in p for p in self.problems(item=item)), self.problems(item=item))

    def test_a_cuts_sound(self):
        t = tf.parse(self.doc(cut={'transition': 'whip', 'frames': 8, 'sound': 'auto'}))
        self.assertEqual(t.clips[1].cut.sound.sfx, 'auto')
        t = tf.parse(self.doc(cut={'transition': 'cut', 'sound': {'sfx': 'pro_impact/short', 'gain_db': -3}}))
        self.assertEqual(t.clips[1].cut.sound.gain_db, -3)
        self.assertIn('name the sound effect for a dissolve',
                      self.problems(cut={'transition': 'dissolve', 'frames': 8, 'sound': 'auto'})[0])
        self.assertIn('unknown key "at"',
                      self.problems(cut={'transition': 'whip', 'frames': 8, 'sound': {'sfx': 'a/b', 'at': 1}})[0])

    def test_the_beats_are_a_songs(self):
        d = self.doc({'sfx': 'a/b', 'at': 3})
        d['beats'] = {'lane': 1, 'item': 1, 'bpm': 120}
        with self.assertRaises(tf.TimelineError) as e:
            tf.parse(d)
        self.assertIn('is a sound effect', str(e.exception))

    def test_the_check_knows_the_pack(self):
        t = tf.parse(self.doc({'sfx': 'whoosh_fast/tigth', 'at': 3},
                              cut={'transition': 'cut', 'sound': {'sfx': 'pro_notify/ding_2045', 'note': 'C5'}}))
        found = assembly.cue_problems(t)
        self.assertIn('did you mean whoosh_fast/tight', found[0])
        self.assertIn('has no C5', found[1])


@unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg')
class AssemblyMix(unittest.TestCase):
    """A film of two footage clips with a whip between them: the whip's
    "auto" whoosh and a lane's hit land on their frames in the assembly."""

    def test_lane_and_cut_sounds_land_on_their_frames(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / 'sources').mkdir()
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=30:duration=2',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(root / 'sources' / 'a.mp4')], check=True)
        doc = {'version': 1, 'fps': 30, 'formats': ['1x1'], 'clips': [
            {'id': 'a', 'footage': 'sources/a.mp4', 'in': 0, 'out': 30},
            {'id': 'b', 'footage': 'sources/a.mp4', 'in': 20, 'out': 50,
             'cut': {'transition': 'whip', 'frames': 8, 'sound': 'auto'}}],
            'lanes': [{'items': [{'sfx': 'pro_impact/short', 'at': 40, 'gain_db': -3},
                                 {'sfx': 'fit/click/floss_lid', 'at': 10, 'align': 'onset'}]}]}
        (root / 'timeline.json').write_text(json.dumps(doc))
        log = io.StringIO()
        result = assembly.assemble_dir(root, out=root / 'out.mp4', log=log)
        self.assertIn('sound effects: 3 of 3 sound effects within a frame of their frames', log.getvalue())
        t = tf.load(root / 'timeline.json')
        placements, total = tf.place(t, {})
        cuts = assembly.cut_sounds(t, placements)
        self.assertEqual([(c.effect, c.mark, c.gain_db) for c in cuts], [('whoosh_fast/tight', 26, -6.0)])
        self.assertEqual(cuts[0].variant, '0.5s')   # the length nearest two whips
        lanes = [s for _, sounds in assembly.lane_sounds(t, root) for s in sounds]
        rows = sfx.sync(result.out, cuts + lanes, 30, total)
        self.assertEqual([(r['name'], r['mark'], r['offset_ms']) for r in rows],
                         [('whoosh_fast/tight--0.5s', 26, 0), ('pro_impact/short', 40, 0),
                          ('fit/click/floss_lid', 10, 0)])
        _, problems, missing = assembly.check_dir(root)
        self.assertEqual((problems, missing), ([], []))


class MissingPack(unittest.TestCase):
    def test_one_clear_error_with_the_fetch_command(self):
        with tempfile.TemporaryDirectory() as empty, patch.dict(os.environ, {'VIDEOBUILDER_SFX_DIR': empty}):
            for call in (lambda: vb.sfx.find('whoosh'), lambda: vb.sfx.sound('a/b', at=3)):
                with self.assertRaises(sfx.SfxUnavailable) as e:
                    call()
                self.assertIn('python -m videobuilder sfx fetch', str(e.exception))
                self.assertIn(empty, str(e.exception))
            t = tf.parse({'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}],
                          'lanes': [{'items': [{'sfx': 'a/b', 'at': 3}]}]})
            self.assertIn('sfx fetch', assembly.cue_problems(t)[0])
            with self.assertRaisesRegex(ValueError, 'sfx fetch'):
                assembly.lane_sounds(t, empty)
            result = subprocess.run([sys.executable, '-m', 'videobuilder', 'sfx', 'list'], capture_output=True,
                                    text=True, cwd=ROOT, env={**os.environ, 'VIDEOBUILDER_SFX_DIR': empty})
            self.assertEqual(result.returncode, 1)
            self.assertIn('sfx fetch', result.stderr)

    def test_the_default_place(self):
        env = {k: v for k, v in os.environ.items() if k != 'VIDEOBUILDER_SFX_DIR'}
        with patch.dict(os.environ, {**env, 'XDG_CACHE_HOME': '/c'}, clear=True):
            self.assertEqual(sfx.pack_dir(), Path('/c/videobuilder/vb-sfx-1'))


class Fetch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tar = Path(self.tmp.name) / 'vb-sfx-1.tar'
        builder().write_tar(self.tar, {str(p.relative_to(FIXTURE)): p.read_bytes()
                                       for p in FIXTURE.rglob('*') if p.is_file()})
        import hashlib
        self.sha = hashlib.sha256(self.tar.read_bytes()).hexdigest()
        self.dest = Path(self.tmp.name) / 'cache' / 'vb-sfx-1'

    def test_fetch_checks_the_sha256_and_unpacks(self):
        sfx.fetch(self.dest, self.tar.as_uri(), self.sha, log=QUIET)
        self.assertEqual(sfx.bank(self.dest).get('pro_impact/short').role, 'hit')
        # Again, over the old one: replaced whole.
        (self.dest / 'stale').write_text('x')
        opened = []

        def opener(url):
            opened.append(url)
            return open(self.tar, 'rb')
        sfx.fetch(self.dest, 'https://example.invalid/vb-sfx-1.tar', self.sha, opener=opener, log=QUIET)
        self.assertEqual(opened, ['https://example.invalid/vb-sfx-1.tar'])
        self.assertFalse((self.dest / 'stale').exists())
        self.assertEqual(sorted(p.name for p in self.dest.parent.iterdir()), ['vb-sfx-1'])   # no temp left

    def test_a_wrong_sha256_unpacks_nothing(self):
        with self.assertRaisesRegex(ValueError, 'nothing unpacked'):
            sfx.fetch(self.dest, self.tar.as_uri(), 'f' * 64, log=QUIET)
        self.assertFalse(self.dest.exists())

    def test_the_pin(self):
        line = sfx.PIN_FILE.read_text().split()
        self.assertEqual(line[1], 'vb-sfx-1.tar')
        self.assertRegex(line[0], r'^[0-9a-f]{64}$')
        with patch.object(sfx, 'pinned_sha256', return_value=sfx.PLACEHOLDER):
            with self.assertRaisesRegex(ValueError, 'not pinned yet'):
                sfx.fetch(self.dest, self.tar.as_uri(), log=QUIET)
        dockerfile = (ROOT / 'deploy' / 'Dockerfile').read_text()
        self.assertIn('videobuilder/sfx-pack.sha256', dockerfile)
        self.assertIn(sfx.PACK_URL.rsplit('/', 1)[0], dockerfile)
        self.assertIn('VIDEOBUILDER_SFX_DIR=/opt/vb-sfx', dockerfile)


class SyncCheck(unittest.TestCase):
    """check.py --video: each sound effect within a frame of its frame."""

    def test_check_passes_on_the_frame_and_fails_off_it(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        music = d / 'music.wav'
        write_wav(music, [0.2 * math.sin(i * 2 * math.pi * 110 / 48000) for i in range(48000 * 3)])
        film = textwrap_film(music)
        (d / 'film.py').write_text(film)
        (d / 'late.py').write_text(film.replace('SOUNDS = SHIFT(0)', 'SOUNDS = SHIFT(2)'))
        env = {**os.environ, 'PYTHONPATH': str(ROOT)}
        for name in ('film', 'late'):
            subprocess.run([sys.executable, '-m', 'videobuilder', 'render', str(d / f'{name}.py'), '--out',
                            str(d / f'{name}.mp4'), '--jobs', '2'], check=True, capture_output=True, env=env)
        ok = subprocess.run([sys.executable, str(CHECK), str(d / 'film.py'), '--video', str(d / 'film.mp4')],
                            capture_output=True, text=True, env=env)
        self.assertIn('3 of 3 sound effects within a frame of their frames', ok.stdout, ok.stdout)
        self.assertNotIn('FAIL', ok.stdout)
        # late.mp4 has every sound 2 frames late; checked against where they were asked for.
        late = subprocess.run([sys.executable, str(CHECK), str(d / 'film.py'), '--video', str(d / 'late.mp4')],
                              capture_output=True, text=True, env=env)
        self.assertEqual(late.stdout.count('ms from its frame (one frame is 33 ms)'), 3, late.stdout)
        self.assertEqual(late.returncode, 1)

    def test_a_clipped_or_buried_sound(self):
        mix = array.array('f', [0.0] * 48000)
        hit = vb.sfx.sound('pro_impact/short', at=10)
        src = sfx.decode_cached(hit.path)
        t0 = round((hit.at / 30 - hit.start) * 48000)
        for i, x in enumerate(src[:48000 - t0]):
            mix[t0 + i] = min(1.0, max(-1.0, x * 4))   # 12 dB too hot: flat tops at full scale
        row = sfx.sync('unused.mp4', [hit], 30, 30, mix=mix)[0]
        self.assertEqual(row['offset_ms'], 0)
        self.assertGreater(row['clipped'], 0)
        # A centred hit at -3 dBFS in both channels: ffmpeg's mono downmix (0.707 a side) takes
        # it to full scale, but no channel is, so it is not called clipped.
        quiet = [min(1.0, max(-1.0, x * 0.71 / max(map(abs, src)))) for x in src[:48000 - t0]]
        stereo = array.array('f', [0.0] * 96000)
        for i, x in enumerate(quiet):
            stereo[2 * (t0 + i)] = stereo[2 * (t0 + i) + 1] = x
        downmix = array.array('f', (min(1.0, max(-1.0, 0.7071 * (stereo[2 * k] + stereo[2 * k + 1])))
                                    for k in range(48000)))
        self.assertGreater(sum(1 for x in downmix if abs(x) >= 0.999), 0)
        row = sfx.sync('unused.mp4', [hit], 30, 30, mix=downmix, stereo=stereo)[0]
        self.assertEqual(row['clipped'], 0)
        import random
        rng = random.Random(1)
        noise = array.array('f', (rng.uniform(-0.9, 0.9) for _ in range(48000)))
        self.assertLess(sfx.sync('unused.mp4', [hit], 30, 30, mix=noise)[0]['r'], sfx.BURIED_R)


def textwrap_film(music):
    return f'''import videobuilder as vb
from dataclasses import replace


def SHIFT(k):
    return tuple(replace(s, at=s.at + k) for s in (
        vb.sfx.sound('fit/click/floss_lid', at=20, gain_db=-3),
        vb.sfx.sound('whoosh_fast/tight', at=40, dur=0.5),
        vb.sfx.sound('pro_impact/short', at=60, gain_db=-6)))


SOUNDS = SHIFT(0)


def draw(n, cv):
    cv.fill('#000')
    cv.mark('frame', 100, 100, 100, 100)


FILM = vb.Film(draw=draw, fps=30, frames=90, formats=('1x1',), sounds=SOUNDS,
               audio=vb.Audio({str(music)!r}, gain_db=-12, loudness=None))
'''


if __name__ == '__main__':
    unittest.main()
