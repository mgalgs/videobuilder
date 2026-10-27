"""videobuilder.speech: phrases, timing and joining, the sidecars, the mouth
flap, and `say` without the speech extra. A fake synthesizer stands in for
Kokoro: no test needs the model or kokoro-onnx."""
import array
import contextlib
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import videobuilder as vb
from videobuilder import cli, speech
from tests.fake_gemini import FakeGemini

ROOT = Path(__file__).resolve().parent.parent
RATE = speech.RATE


def tone(seconds, lead=0.0, tail=0.0, amp=0.5, hz=220):
    n = int(seconds * RATE)
    body = (int(amp * 32767 * math.sin(2 * math.pi * hz * i / RATE)) for i in range(n))
    return array.array('h', [0] * int(lead * RATE) + list(body) + [0] * int(tail * RATE))


class FakeEngine:
    """0.1 s of tone per phoneme character, with silence around it the way
    a real synthesizer leaves some."""
    model_id = 'fake'

    def __init__(self):
        self.calls = []

    def phonemize(self, text, lang):
        return text.lower()

    def synth(self, phonemes, voice, speed, lang):
        self.calls.append((phonemes, voice, speed, lang))
        return tone(0.1 * len(phonemes.replace(' ', '')) / speed, lead=0.2, tail=0.3)


class Script(unittest.TestCase):
    def test_lines_and_sentences_are_phrases(self):
        self.assertEqual(speech.phrases('Hello there. How are you?\n\n# a note\n  And   you!  \nLast one'),
                         ['Hello there.', 'How are you?', 'And you!', 'Last one'])

    def test_inline_phonemes_are_not_split_and_caption_as_the_word(self):
        ph = speech.phrases('Meet [Dr. Kokoro](/kəkˈɔːɹəʊ/). Bye.')
        self.assertEqual(ph, ['Meet [Dr. Kokoro](/kəkˈɔːɹəʊ/).', 'Bye.'])
        self.assertEqual(speech.caption_text(ph[0]), 'Meet Dr. Kokoro.')
        self.assertEqual(speech.spoken_parts(ph[0]), [('text', 'Meet '), ('phonemes', 'kəkˈɔːɹəʊ'), ('text', '.')])

    def test_lexicon_respells_whole_words_any_case(self):
        parts = speech.spoken_parts('galgs met Galgsby and GALGS.', {'Galgs': 'Gahlgz', 'met': '/mˈɛt/'})
        self.assertEqual(parts, [('text', 'Gahlgz '), ('phonemes', 'mˈɛt'), ('text', ' Galgsby and Gahlgz.')])

    def test_titles_initials_and_eg_do_not_end_a_sentence(self):
        got = speech.phrases('Dr. Smith met Mr. Jones. Bye. Ask J. R. R. Tolkien (e.g. on St. Kilda). Plan b. Ok')
        self.assertEqual(got, ['Dr. Smith met Mr. Jones.', 'Bye.', 'Ask J. R. R. Tolkien (e.g. on St. Kilda).', 'Plan b.', 'Ok'])

    def test_lexicon_keys_may_end_in_punctuation(self):
        self.assertEqual(speech.spoken_parts('I love C++, not C.', {'C++': 'see plus plus'}),
                         [('text', 'I love see plus plus, not C.')])

    def test_phonemes_join_without_a_space_before_punctuation(self):
        got = speech.phonemes_for(FakeEngine(), [('text', 'Hi '), ('phonemes', 'kˈo'), ('text', ', you.')], 'en-us')
        self.assertEqual(got, 'hi kˈo, you.')

    def test_years_are_read_as_years(self):
        self.assertEqual(speech.spoken_years('Caught in 1863, freed in 1900, born 1805; 1500 eels.'),
                         'Caught in eighteen sixty-three, freed in nineteen hundred, born eighteen oh five; '
                         'fifteen hundred eels.')

    def test_other_numbers_are_left_alone(self):
        for s in ('1,863 eels', '1863.5 m', 'the 1860s', '$1863', '2024', '1099', '18630', '50%', '1863%'):
            self.assertEqual(speech.spoken_years(s), s)

    def test_espeak_two_part_sounds_reach_the_voice_as_single_symbols(self):
        # FakeEngine hands text back as its "espeak output": `^` is espeak's tie.
        for two, one in [('eɪ', 'A'), ('aɪ', 'I'), ('aʊ', 'W'), ('ɔɪ', 'Y'), ('oʊ', 'O'), ('əʊ', 'Q'),
                         ('tʃ', 'ʧ'), ('dʒ', 'ʤ')]:
            with self.subTest(two=two):
                self.assertEqual(speech.phonemes_for(FakeEngine(), [('text', f'k{two[0]}^{two[1]}n')], 'en-us'),
                                 f'k{one}n')

    def test_espeak_untied_pairs_stay_two_sounds(self):
        # espeak-ng's "nutshell" and "sweatshirt": t + ʃ across the compound, untied, unlike "church".
        for ph in ('nˈʌtʃɛl', 'swˈɛtʃɜːt'):
            with self.subTest(ph=ph):
                self.assertEqual(speech.phonemes_for(FakeEngine(), [('text', ph)], 'en-us'), ph)
        self.assertEqual(speech.phonemes_for(FakeEngine(), [('text', 'nˈʌtʃɛl t^ʃˈɜːt^ʃ wˈɛ^ɹ')], 'en-us'),
                         'nˈʌtʃɛl ʧˈɜːʧ wˈɛɹ')

    def test_typed_phonemes_get_single_symbols_too(self):
        self.assertEqual(speech.phonemes_for(FakeEngine(), [('phonemes', 'fɹˈɔɪd')], 'en-us'), 'fɹˈYd')
        lexicon = speech.spoken_parts('Freud.', {'Freud': '/fɹˈɔɪd/'})
        self.assertEqual(speech.phonemes_for(FakeEngine(), lexicon, 'en-us'), 'fɹˈYd.')

    def test_single_symbols_and_plain_phonemes_are_left_alone(self):
        for ph in ('fɹˈYd', 'lˈuːmən', 'ðə vˈɔːɹtɛks'):
            with self.subTest(ph=ph):
                self.assertEqual(speech.phonemes_for(FakeEngine(), [('phonemes', ph)], 'en-us'), ph)

    def test_phonemes_mode_prints_what_the_voice_gets(self):
        out = io.StringIO()
        with mock.patch.object(speech, 'Kokoro', lambda *a: FakeEngine()), contextlib.redirect_stdout(out):
            cli.main(['say', '--text', '[Freud](/fɹˈɔɪd/) and boy.', '--phonemes'])
        self.assertEqual(out.getvalue(), '[Freud](/fɹˈɔɪd/) and boy.\n    /fɹˈYd and boy./\n')

    def test_years_only_in_english_text_not_phonemes(self):
        parts = [('text', 'In 1863 '), ('phonemes', '1863')]
        self.assertEqual(speech.phonemes_for(FakeEngine(), parts, 'en-gb'), 'in eighteen sixty-three 1863')
        self.assertEqual(speech.phonemes_for(FakeEngine(), [('text', 'En 1863')], 'fr-fr'), 'en 1863')


class PhraseBreak(unittest.TestCase):
    SENTENCE = "California's tax revenue | rises and falls with the economy."

    def test_the_voice_gets_a_comma_where_the_mark_is_and_nowhere_else(self):
        ph = speech.phonemes_for(FakeEngine(), speech.spoken_parts(self.SENTENCE), 'en-us')
        self.assertEqual(ph, "california's tax revenue, rises and falls with the economy.")

    def test_captions_and_json_show_neither_the_mark_nor_a_comma(self):
        with tempfile.TemporaryDirectory() as d:
            eng = FakeEngine()
            doc = speech.say(self.SENTENCE, Path(d, 'n.wav'), eng)
            self.assertEqual(eng.calls[0][0], "california's tax revenue, rises and falls with the economy.")
            text = "California's tax revenue rises and falls with the economy."
            self.assertEqual([p['text'] for p in doc['phrases']], [text])
            self.assertEqual(json.loads(Path(d, 'n.json').read_text())['phrases'], doc['phrases'])
            self.assertIn(f'\n{text}\n', Path(d, 'n.vtt').read_text())

    def test_the_mark_does_not_split_a_phrase(self):
        self.assertEqual(speech.phrases('One | two. Three | four'), ['One | two.', 'Three | four'])

    def test_next_to_and_inside_typed_phonemes_and_respellings(self):
        eng = FakeEngine()
        for phrase, lexicon, want in [('tax [revenue](/ɹˈɛvənuː/) | rises.', None, 'tax ɹˈɛvənuː, rises.'),
                                      ('tax [revenue](/ɹˈɛvənuː/)|rises.', None, 'tax ɹˈɛvənuː, rises.'),
                                      ('[the tax](/ðə | tˈæks/) rises.', None, 'ðə, tˈæks rises.'),
                                      ('Kokoro rises.', {'Kokoro': 'ko | ko ro'}, 'ko, ko ro rises.'),
                                      ('tax Kokoro | rises.', {'Kokoro': '/kəkˈɔːɹəʊ/'}, 'tax kəkˈɔːɹQ, rises.')]:
            with self.subTest(phrase=phrase):
                self.assertEqual(speech.phonemes_for(eng, speech.spoken_parts(phrase, lexicon), 'en-us'), want)
                self.assertNotIn('|', speech.caption_text(phrase))
        self.assertEqual(speech.caption_text('[the tax](/ðə | tˈæks/) | rises.'), 'the tax rises.')

    def test_a_stray_mark_adds_at_most_one_break_and_never_an_empty_phrase(self):
        self.assertEqual(speech.phrases('| One || two |.\n|\n | \nThree. |\nFour. | Five |'),
                         ['| One || two |.', 'Three.', 'Four.', '| Five |'])
        eng = FakeEngine()
        for phrase, want in [('| One || two |.', 'one, two.'), ('| Five |', 'five'), ('x, | y', 'x, y'),
                             ('a | | b', 'a, b')]:
            with self.subTest(phrase=phrase):
                self.assertEqual(speech.phonemes_for(eng, speech.spoken_parts(phrase), 'en-us'), want)
        self.assertEqual(speech.caption_text('| One || two |.'), 'One two.')
        self.assertEqual(speech.caption_text('x, | y'), 'x, y')

    def test_a_mark_before_an_opening_quote_keeps_the_space(self):
        for phrase, want in [('The sign read | "Closed for the season."', 'The sign read "Closed for the season."'),
                             ("He said | 'no' twice", "He said 'no' twice"),
                             ('"Closed." | "Open."', '"Closed." "Open."'),
                             ('He said "no |" twice', 'He said "no" twice'),
                             ("He said 'no | |' twice", "He said 'no' twice")]:
            with self.subTest(phrase=phrase):
                self.assertEqual(speech.caption_text(phrase), want)
        self.assertEqual(speech.phonemes_for(FakeEngine(), speech.spoken_parts('He said | "no" twice'), 'en-us'),
                         'he said, "no" twice')
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError, 'no phrases'):
            speech.say('|\n | |\n', Path(d, 'n.wav'), FakeEngine())

    def test_phonemes_mode_echoes_the_phrase_without_the_mark(self):
        out = io.StringIO()
        with mock.patch.object(speech, 'Kokoro', lambda *a: FakeEngine()), contextlib.redirect_stdout(out):
            cli.main(['say', '--text', 'Tax revenue | rises.', '--phonemes'])
        self.assertEqual(out.getvalue(), 'Tax revenue rises.\n    /tax revenue, rises./\n')

    def test_without_the_mark_nothing_changes(self):
        phrase = "California's tax revenue rises, and [falls](/fˈɔːlz/) with C++. Ok"
        lexicon = {'C++': 'see plus plus'}
        self.assertEqual(speech.unmarked(phrase), phrase)
        self.assertEqual(speech.spoken_parts(phrase, lexicon),
                         [('text', "California's tax revenue rises, and "), ('phonemes', 'fˈɔːlz'),
                          ('text', ' with see plus plus. Ok')])
        self.assertEqual(speech.phonemes_for(FakeEngine(), speech.spoken_parts(phrase, lexicon), 'en-us'),
                         "california's tax revenue rises, and fˈɔːlz with see plus plus. ok")

class Assemble(unittest.TestCase):
    def test_trims_each_phrase_to_its_sound_and_gaps_them(self):
        chunks = [tone(1.0, lead=0.5, tail=0.5), tone(0.5, lead=0.2, tail=0.1)]
        out, spans = speech.assemble(chunks, RATE, gap=0.4, margin=0.03)
        (a0, z0), (a1, z1) = spans
        self.assertAlmostEqual(a0, 0.03, delta=0.011)
        self.assertAlmostEqual(z0 - a0, 1.0, delta=0.011)
        self.assertAlmostEqual(z1 - a1, 0.5, delta=0.011)
        self.assertAlmostEqual(a1 - z0, 0.03 + 0.4 + 0.03, delta=0.02)
        self.assertAlmostEqual(len(out) / RATE, z1 + 0.03, delta=0.011)

    def test_edges_fade_in_and_out(self):
        out, _ = speech.assemble([tone(0.2, amp=1.0, hz=50)], RATE, gap=0, margin=0)
        self.assertLess(abs(out[0]), 200)
        self.assertLess(abs(out[-1]), 200)

    def test_a_silent_phrase_is_an_error(self):
        with self.assertRaisesRegex(ValueError, 'phrase 2 came out silent'):
            speech.assemble([tone(0.2), array.array('h', [0] * 1000)], RATE)


class Say(unittest.TestCase):
    SCRIPT = 'Hello there.\nI am [Kokoro](/kko/), a fox.'

    def test_writes_wav_vtt_and_json_that_agree(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, 'voice', 'narration.wav')
            eng = FakeEngine()
            doc = speech.say(self.SCRIPT, out, eng, voice='bf_emma', gap=0.5)
            self.assertEqual([c[3] for c in eng.calls], ['en-gb', 'en-gb'])
            self.assertEqual(eng.calls[1][0], 'i am kko, a fox.')
            with wave.open(str(out)) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, RATE))
                self.assertAlmostEqual(w.getnframes() / RATE, doc['seconds'], places=3)
            texts = [p['text'] for p in doc['phrases']]
            self.assertEqual(texts, ['Hello there.', 'I am Kokoro, a fox.'])
            p0, p1 = doc['phrases']
            self.assertAlmostEqual(p0['end'] - p0['start'], 0.1 * len('hellothere.'), delta=0.011)
            self.assertAlmostEqual(p1['start'] - p0['end'], 0.56, delta=0.02)
            self.assertEqual(json.loads(Path(d, 'voice', 'narration.json').read_text())['phrases'], doc['phrases'])
            vtt = Path(d, 'voice', 'narration.vtt').read_text()
            self.assertIn(f"{speech._ts(p1['start'])} --> {speech._ts(p1['end'])}\nI am Kokoro, a fox.\n", vtt)
            track = vb.captions.load(Path(d, 'voice', 'narration.vtt'))
            self.assertEqual(track.text, 'Hello there. I am Kokoro, a fox.')
            self.assertAlmostEqual(track[0].start, p0['start'], places=3)
            self.assertAlmostEqual(track[-1].end, p1['end'], places=3)

    def test_rerun_with_the_same_inputs_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, 'n.wav')
            speech.say(self.SCRIPT, out, FakeEngine())
            os.utime(out, (1, 1))
            eng = FakeEngine()
            self.assertTrue(speech.say(self.SCRIPT, out, eng)['unchanged'])
            self.assertEqual(eng.calls, [])
            self.assertEqual(out.stat().st_mtime, 1)
            speech.say(self.SCRIPT, out, eng, speed=1.2)
            self.assertEqual(len(eng.calls), 2)
            speech.say(self.SCRIPT, out, eng, speed=1.2, force=True)
            self.assertEqual(len(eng.calls), 4)

    def test_a_speed_kokoro_refuses_is_an_error(self):
        engine = FakeEngine()
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError, '0.5 to 2.0'):
            speech.say('Hi.', Path(d, 'n.wav'), engine, speed=2.5)
        self.assertEqual(engine.calls, [])

    def test_an_empty_script_is_an_error(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError, 'no phrases'):
            speech.say('\n# only a note\n', Path(d, 'n.wav'), FakeEngine())


def write_wav(path, samples):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())


class Mouth(unittest.TestCase):
    def test_levels_are_per_frame_relative_to_the_loudest(self):
        s = tone(0.1, amp=0.5) + tone(0.1, amp=0.05) + array.array('h', [0] * int(0.1 * RATE))
        db = speech.levels(s, RATE, 30)
        self.assertEqual(len(db), 9)
        self.assertAlmostEqual(db[1], 0, delta=0.5)
        self.assertAlmostEqual(db[4], -20, delta=0.5)
        self.assertEqual(db[7], -120.0)

    def test_hold_stops_flicker(self):
        got = speech.flaps([0, -60] * 6, hold=2)
        runs = [len(r) for r in ''.join('#' if x else '.' for x in got).replace('#.', '#|.').replace('.#', '.|#').split('|')]
        self.assertTrue(all(n >= 2 for n in runs[:-1]), got)

    def test_hysteresis_keeps_it_open_between_the_thresholds(self):
        db = [-60, -20, -20, -27, -27, -27, -40, -40]
        self.assertEqual(speech.flaps(db, open_db=-24, close_db=-30, dip_db=10, max_open=99),
                         [False, True, True, True, True, True, False, False])
        self.assertEqual(speech.flaps([-60, -27, -27, -27], open_db=-24, close_db=-30), [False] * 4)

    def test_shuts_in_the_dip_between_syllables(self):
        db = [-60, -2, 0, -2, -12, -14, -12, -1, 0, -2, -60, -60]
        self.assertEqual(speech.flaps(db, dip_db=5), [False, True, True, True, False, False, True, True, True,
                                                       True, False, False])

    def test_opens_on_the_rise_not_at_the_peak(self):
        self.assertEqual(speech.flaps([-60, -60, -20, -8, 0, 0], max_open=99)[:3], [False, False, True])

    def test_a_long_vowel_still_flaps(self):
        got = speech.flaps([-60] + [0] * 20, max_open=6, hold=2)
        self.assertEqual(got[1:9], [True] * 6 + [False] * 2)
        self.assertTrue(got[9])

    def test_mouth_from_a_wav_on_the_film_clock_and_holds(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, 'v.wav')
            write_wav(path, array.array('h', [0] * int(0.2 * RATE)) + tone(0.15) + array.array('h', [0] * int(0.2 * RATE)))
            m = speech.mouth(path, 30, at=10, frames=40)
            self.assertEqual(len(m), 40)
            opened = [n for n, x in enumerate(m) if x]
            self.assertEqual((opened[0], opened[-1]), (16, 20))
            self.assertEqual(speech.holds(m), [(0, 'idle'), (16, 'talk'), (21, 'idle')])


class NarrationLoad(unittest.TestCase):
    def test_loads_the_sidecars_without_the_model(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, 'n.wav')
            doc = speech.say('One.\nTwo.', out, FakeEngine())
            n = vb.speech.load(out)
            self.assertEqual([p.text for p in n.phrases], ['One.', 'Two.'])
            self.assertEqual(n.frames(30), math.ceil(doc['seconds'] * 30))
            snd = n.sound(at=15)
            self.assertEqual((snd.path, snd.at, snd.frames), (str(out), 15, n.frames(30)))
            self.assertAlmostEqual(n.track_at(15)[0].start, doc['phrases'][0]['start'] + 0.5, places=6)
            self.assertIs(n.mouth(30, at=15), n.mouth(30, at=15))
            self.assertEqual(len(n.mouth(30, at=15)), 15 + n.frames(30))


class FakeVoicesEngine:
    model_id = 'fake-voices-v1'

    def voices(self):
        return ['af_heart', 'bm_george']


class VoiceOptions(unittest.TestCase):
    def test_lists_the_engines_own_voices_not_a_hardcoded_set(self):
        options = speech.voice_options(FakeVoicesEngine())
        self.assertEqual([o.value for o in options], ['af_heart', 'bm_george'])
        self.assertIn('en-us', options[0].label)
        self.assertIn('en-gb', options[1].label)

    def test_each_option_has_a_preview_url_for_its_own_voice(self):
        options = speech.voice_options(FakeVoicesEngine())
        self.assertEqual(options[0].preview, 'api/narration/voice-sample?voice=af_heart')
        self.assertEqual(options[1].preview, 'api/narration/voice-sample?voice=bm_george')

    def test_falls_back_to_default_voice_without_an_engine(self):
        # The runtime gate image has the model, so take the engine away here.
        with mock.patch.dict(sys.modules, {'kokoro_onnx': None}):
            options = speech.voice_options()
        self.assertEqual([o.value for o in options], [speech.DEFAULT_VOICE])
        self.assertEqual(options[0].preview, f'api/narration/voice-sample?voice={speech.DEFAULT_VOICE}')

    def test_narration_settings_is_voice_then_speed_and_is_cached(self):
        self.assertIs(speech.narration_settings(), speech.narration_settings())
        voice, speed = speech.narration_settings()
        self.assertEqual(voice.id, 'voice')
        self.assertEqual((speed.id, speed.min, speed.max, speed.default), ('speed', 0.5, 2.0, 1.0))


class WithoutTheExtra(unittest.TestCase):
    def test_say_exits_with_what_to_install(self):
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {'kokoro_onnx': None}), contextlib.redirect_stderr(err), \
                self.assertRaises(SystemExit) as cm:
            cli.main(['say', '--text', 'Hello.', '--out', 'never.wav'])
        self.assertIn("pip install 'videobuilder[speech]'", str(cm.exception))
        self.assertTrue(str(cm.exception).startswith('say: '))
        self.assertFalse(Path('never.wav').exists())

    def test_an_empty_respelling_is_refused(self):
        with mock.patch.dict(sys.modules, {'kokoro_onnx': mock.MagicMock()}), \
                self.assertRaisesRegex(SystemExit, "no respelling for 'Galgs'"):
            cli.main(['say', '--text', 'Hi Galgs.', '--say', 'Galgs=', '--out', 'never.wav'])
        self.assertFalse(Path('never.wav').exists())

    def test_importing_videobuilder_never_imports_kokoro(self):
        code = 'import sys, videobuilder; print("kokoro_onnx" in sys.modules, "onnxruntime" in sys.modules)'
        env = {**os.environ, 'PYTHONPATH': str(ROOT)}
        out = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.split(), ['False', 'False'])



class KokoroUnchanged(unittest.TestCase):
    def test_kokoro_outputs_are_byte_for_byte_what_they_were(self):
        # Hashes from before `say` had a second engine: the default path must never move.
        want = {'.wav': 'f8efdab813f7937c9339cd58765f190ee15c0133b647dcb8e2637b86740025cd',
                '.vtt': 'cc638b0ced07384d130275eb807351d60bf98888ef2596c79d32bd1e93621085',
                '.json': 'a0ab9a72de396d69837483adf7f170bbff51a071834106d61ac163f4f3125156'}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, 'n.wav')
            speech.say('Hello there.\nI am [Kokoro](/kko/), a fox | today.', out, FakeEngine(),
                       lexicon={'fox': 'focks'})
            got = {p.suffix: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (out, out.with_suffix('.vtt'), out.with_suffix('.json'))}
        self.assertEqual(got, want)

    def test_chatterbox_flags_are_refused_for_kokoro(self):
        with self.assertRaisesRegex(SystemExit, '--seed is for --engine chatterbox'):
            cli.main(['say', '--text', 'Hi.', '--seed', '3', '--out', 'never.wav'])


class ChatterboxEngine(unittest.TestCase):
    """`say --engine chatterbox` against tests/fake_chatterbox.py standing in
    for Chatterbox's interpreter and its worker."""
    SCRIPT = 'Tax revenue | rises.\nI am [Kokoro](/kko/), a fox.'

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.dir)
        self.python = self.dir / 'python'
        self.python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT / "tests" / "fake_chatterbox.py"}" "$@"\n')
        self.python.chmod(0o755)
        self.log = self.dir / 'log.jsonl'
        env = {'VIDEOBUILDER_CHATTERBOX_PYTHON': str(self.python), 'FAKE_CHATTERBOX_LOG': str(self.log)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def logged(self):
        if not self.log.exists():
            return [], []
        lines = [json.loads(l) for l in self.log.read_text().splitlines()]
        return [l['argv'] for l in lines if 'argv' in l], [l['text'] for l in lines if 'text' in l]

    def say(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(['say', '--engine', 'chatterbox', '--text', self.SCRIPT, '--out', str(self.dir / 'n.wav'), *args])
        return out.getvalue(), err.getvalue()

    def test_writes_wav_vtt_and_json_with_phrase_cues(self):
        _, err = self.say()
        runs, texts = self.logged()
        self.assertEqual(len(runs), 1)   # one process for every phrase
        self.assertEqual(texts, ['Tax revenue rises.', 'I am Kokoro, a fox.'])
        self.assertIn('[word](/phonemes/) speaks the word as written', err)
        self.assertEqual(err.count('Chatterbox reads text'), 1)
        doc = json.loads((self.dir / 'n.json').read_text())
        self.assertEqual([p['text'] for p in doc['phrases']], texts)
        p0, p1 = doc['phrases']
        self.assertAlmostEqual(p0['end'] - p0['start'], 0.05 * len(texts[0]), delta=0.011)
        self.assertAlmostEqual(p1['start'] - p0['end'], 0.03 + 0.35 + 0.03, delta=0.02)
        self.assertEqual(doc['inputs'], {
            'phrases': texts, 'gap': 0.35, 'engine': 'chatterbox', 'model': speech.Chatterbox.model_id,
            'seed': 0, 'exaggeration': 0.4, 'cfg_weight': 0.5, 'voice': None, 'voice_sha256': None})
        self.assertIn(speech.CHATTERBOX_REVISION, doc['inputs']['model'])
        with wave.open(str(self.dir / 'n.wav')) as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, RATE))
            self.assertAlmostEqual(w.getnframes() / RATE, doc['seconds'], places=3)
        self.assertIn(f"{speech._ts(p1['start'])} --> {speech._ts(p1['end'])}\nI am Kokoro, a fox.\n",
                      (self.dir / 'n.vtt').read_text())
        argv = runs[0]
        self.assertEqual(argv[0], str(speech.CHATTERBOX_WORKER))
        for flag, v in (('--seed', '0'), ('--exaggeration', '0.4'), ('--cfg-weight', '0.5'),
                        ('--revision', speech.CHATTERBOX_REVISION)):
            self.assertEqual(argv[argv.index(flag) + 1], v)
        self.assertNotIn('--voice', argv)

    def test_a_break_never_reaches_the_worker(self):
        self.SCRIPT = '| Tax | revenue || rises |.\n"Yes |" | she said.'
        self.say()
        _, texts = self.logged()
        self.assertEqual(texts, ['Tax revenue rises.', '"Yes" she said.'])
        self.assertFalse(any('|' in t for t in texts))

    def test_reruns_only_when_seed_voice_contents_or_engine_change(self):
        out = self.dir / 'n.wav'
        self.say()
        before = out.read_bytes()
        printed, _ = self.say()
        self.assertIn('unchanged', printed)
        self.assertEqual(len(self.logged()[0]), 1)
        self.say('--seed', '1')
        self.assertEqual(len(self.logged()[0]), 2)
        self.assertNotEqual(out.read_bytes(), before)
        clip = self.dir / 'me.wav'
        clip.write_bytes(b'x' * 10)
        self.say('--seed', '1', '--voice', str(clip))
        argv = self.logged()[0][-1]
        self.assertEqual(argv[argv.index('--voice') + 1], str(clip.resolve()))
        inputs = json.loads((self.dir / 'n.json').read_text())['inputs']
        self.assertEqual(inputs['voice_sha256'], hashlib.sha256(b'x' * 10).hexdigest())
        self.say('--seed', '1', '--voice', str(clip))
        self.assertEqual(len(self.logged()[0]), 3)
        clip.write_bytes(b'y' * 10)   # same path, other voice
        self.say('--seed', '1', '--voice', str(clip))
        self.assertEqual(len(self.logged()[0]), 4)
        # Kokoro never reuses Chatterbox's audio, nor Chatterbox Kokoro's.
        kokoro = FakeEngine()
        speech.say(self.SCRIPT, out, kokoro)
        self.assertEqual(len(kokoro.calls), 2)
        self.say('--seed', '1', '--voice', str(clip))
        self.assertEqual(len(self.logged()[0]), 5)

    def test_a_kokoro_voice_name_says_what_voice_means_here(self):
        with self.assertRaisesRegex(SystemExit, r"no voice clip 'af_heart'.*--voice is a \.wav"):
            self.say('--voice', 'af_heart')
        self.assertEqual(self.logged(), ([], []))

    def test_kokoro_only_options_are_refused(self):
        for flags in (['--lang', 'en-gb'], ['--phonemes'], ['--speed', '1.2']):
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                self.say(*flags)
        self.assertFalse((self.dir / 'n.wav').exists())

    def test_a_missing_interpreter_says_how_to_install_it(self):
        os.environ['VIDEOBUILDER_CHATTERBOX_PYTHON'] = str(self.dir / 'nope' / 'python')
        with self.assertRaises(SystemExit) as cm:
            self.say()
        msg = str(cm.exception)
        self.assertTrue(msg.startswith('say: no Chatterbox interpreter at '))
        for want in ('$VIDEOBUILDER_CHATTERBOX_PYTHON', 'uv pip install', 'chatterbox-tts==',
                     'download.pytorch.org/whl/cpu'):
            self.assertIn(want, msg)
        self.assertFalse((self.dir / 'n.wav').exists())

    def test_a_worker_failure_is_a_clear_error_and_writes_nothing(self):
        os.environ['FAKE_CHATTERBOX_FAIL'] = 'ModuleNotFoundError: No module named chatterbox'
        with self.assertRaises(SystemExit) as cm:
            self.say()
        self.assertIn('Chatterbox: ModuleNotFoundError', str(cm.exception))
        self.assertIn('$VIDEOBUILDER_CHATTERBOX_PYTHON', str(cm.exception))
        self.assertFalse((self.dir / 'n.wav').exists())


class ChatterboxWorker(unittest.TestCase):
    """The real chatterbox_worker.py, which runs in another interpreter."""
    WORKER = ROOT / 'videobuilder' / 'chatterbox_worker.py'

    def test_it_imports_nothing_from_videobuilder(self):
        import ast
        tree = ast.parse(self.WORKER.read_text(encoding='utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0, 'a relative import')
                names.add(node.module.split('.')[0])
            elif isinstance(node, ast.Import):
                names.update(n.name.split('.')[0] for n in node.names)
        self.assertNotIn('videobuilder', names)
        allowed = set(sys.stdlib_module_names) | {'torch', 'torchaudio', 'chatterbox', 'perth', 'numpy',
                                                   'huggingface_hub', 'faster_whisper'}
        self.assertEqual(names - allowed, set())

    def run_worker(self, modules):
        with tempfile.TemporaryDirectory() as d:
            for name, src in modules.items():
                Path(d, *name.split('.')[:-1]).mkdir(parents=True, exist_ok=True)
                Path(d, *name.split('.')).with_suffix('.py').write_text(src)
            env = {**os.environ, 'PYTHONPATH': d}
            return subprocess.run([sys.executable, str(self.WORKER), '--repo', 'r', '--revision', 'v'], env=env,
                                  input='', capture_output=True, text=True)

    def test_a_watermarker_that_did_not_load_is_an_error_naming_why(self):
        # resemble-perth hides its own ImportError (pkg_resources, gone from setuptools 81 on) as None.
        out = self.run_worker({
            'perth.__init__': 'PerthImplicitWatermarker = None\nprint("noise on stdout")\n',
            'perth.perth_net.__init__': '', 'perth.perth_net.perth_net_implicit.__init__': '',
            'perth.perth_net.perth_net_implicit.perth_watermarker': 'from pkg_resources_gone import x\n',
            'torch': '', 'chatterbox.__init__': '', 'chatterbox.tts': 'ChatterboxTTS = None\n',
            'huggingface_hub': 'snapshot_download = None\n'})
        self.assertEqual(out.returncode, 1)
        msg = json.loads(out.stdout)   # one line: the library's print went to stderr
        self.assertTrue(msg['install'])
        self.assertIn("No module named 'pkg_resources_gone'", msg['error'])
        self.assertIn("'setuptools<81'", msg['error'])
        self.assertIn('noise on stdout', out.stderr)

    def test_without_chatterbox_it_says_so(self):
        out = self.run_worker({'perth': 'PerthImplicitWatermarker = object\n', 'torch': ''})
        msg = json.loads(out.stdout)
        self.assertEqual(out.returncode, 1)
        self.assertTrue(msg['install'])
        self.assertIn("No module named 'chatterbox'", msg['error'])


class ChatterboxOpsTest(unittest.TestCase):
    """speech.ChatterboxOps (voice conversion and the transcript check, for
    `say --engine gemini`) against tests/fake_chatterbox.py."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.dir)
        self.python = self.dir / 'python'
        self.python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT / "tests" / "fake_chatterbox.py"}" "$@"\n')
        self.python.chmod(0o755)
        self.log = self.dir / 'log.jsonl'
        self.clip = self.dir / 'target.wav'
        self.clip.write_bytes(b'x' * 37)
        env = {'VIDEOBUILDER_CHATTERBOX_PYTHON': str(self.python), 'FAKE_CHATTERBOX_LOG': str(self.log)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def logged(self):
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def runs(self):
        return [l for l in self.logged() if 'argv' in l]

    def test_convert_starts_one_process_and_carries_the_target_clip(self):
        ops = speech.ChatterboxOps(convert_to=str(self.clip))
        self.addCleanup(ops.close)
        out = ops.convert(tone(0.05))
        self.assertIsInstance(out, array.array)
        self.assertEqual(len(self.runs()), 1)
        argv = self.runs()[0]['argv']
        self.assertEqual(argv[argv.index('--ops') + 1], 'convert')
        self.assertEqual(argv[argv.index('--convert-to') + 1], str(self.clip.resolve()))
        ops.convert(tone(0.05))
        self.assertEqual(len(self.runs()), 1)   # the second call reuses the same process

    def test_transcribe_gets_the_canned_words(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['hello there'])
        ops = speech.ChatterboxOps(transcribe=True)
        self.addCleanup(ops.close)
        self.assertEqual(ops.transcribe(tone(0.1)), 'hello there')
        argv = self.runs()[0]['argv']
        self.assertEqual(argv[argv.index('--ops') + 1], 'transcribe')
        self.assertNotIn('--convert-to', argv)

    def test_convert_and_transcribe_share_one_process(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['ok'])
        ops = speech.ChatterboxOps(convert_to=str(self.clip), transcribe=True)
        self.addCleanup(ops.close)
        ops.convert(tone(0.05))
        ops.transcribe(tone(0.05))
        self.assertEqual(len(self.runs()), 1)
        self.assertEqual(sorted(self.runs()[0]['argv'][self.runs()[0]['argv'].index('--ops') + 1].split(',')),
                         ['convert', 'transcribe'])

    def test_no_worker_without_convert_or_transcribe(self):
        os.environ['VIDEOBUILDER_CHATTERBOX_PYTHON'] = str(self.dir / 'does' / 'not' / 'exist')
        ops = speech.ChatterboxOps()
        self.addCleanup(ops.close)
        self.assertEqual(self.logged(), [])

    def test_a_missing_interpreter_says_how_to_install_it(self):
        os.environ['VIDEOBUILDER_CHATTERBOX_PYTHON'] = str(self.dir / 'does' / 'not' / 'exist')
        ops = speech.ChatterboxOps(transcribe=True)
        with self.assertRaises(speech.SpeechUnavailable) as cm:
            ops.transcribe(tone(0.05))
        self.assertIn('$VIDEOBUILDER_CHATTERBOX_PYTHON', str(cm.exception))
        self.assertIn('faster-whisper==', str(cm.exception))   # the transcript check needs it too

    def test_transcribe_gets_the_cache_dir(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['ok'])
        os.environ['VIDEOBUILDER_CHATTERBOX_CACHE'] = str(self.dir / 'hf')
        ops = speech.ChatterboxOps(transcribe=True)
        self.addCleanup(ops.close)
        ops.transcribe(tone(0.05))
        argv = self.runs()[0]['argv']
        self.assertEqual(argv[argv.index('--cache-dir') + 1], str(self.dir / 'hf'))


class GeminiStyle(unittest.TestCase):
    """The pure style/context helpers, no HTTP needed."""

    def test_first_phrase_gets_the_style_alone(self):
        self.assertEqual(speech._gemini_style('warm and playful', None), 'warm and playful')
        self.assertEqual(speech._gemini_style('', None), '')

    def test_later_phrases_get_the_previous_phrase_as_context(self):
        got = speech._gemini_style('warm and playful', 'Meet Lumen.')
        self.assertEqual(got, 'warm and playful This continues straight on from the narrator\'s '
                               'previous sentence: "Meet Lumen."')

    def test_no_style_still_gets_context_alone(self):
        self.assertEqual(speech._gemini_style('', 'Meet Lumen.'),
                         'This continues straight on from the narrator\'s previous sentence: "Meet Lumen."')


class TranscriptNormalize(unittest.TestCase):
    """normalize_for_check: say's transcript-check comparison, no model needed."""

    def test_case_and_punctuation_are_ignored(self):
        self.assertEqual(speech.normalize_for_check('Hello, World!'), speech.normalize_for_check('hello world'))

    def test_a_number_matches_however_it_is_spelled(self):
        for text in ('1,500', 'fifteen hundred', 'one thousand five hundred'):
            with self.subTest(text=text):
                self.assertEqual(speech.normalize_for_check(text), speech.normalize_for_check('1,500'))

    def test_percent_matches_the_written_word(self):
        self.assertEqual(speech.normalize_for_check('20%'), speech.normalize_for_check('twenty percent'))

    def test_a_joined_compound_matches_the_two_words(self):
        self.assertEqual(speech.normalize_for_check('healthcare'), speech.normalize_for_check('health care'))

    def test_a_real_mismatch_still_differs(self):
        self.assertNotEqual(speech.normalize_for_check('the cat sat'), speech.normalize_for_check('the cat ran'))
        self.assertNotEqual(speech.normalize_for_check('1,500'), speech.normalize_for_check('1,600'))

    def test_place_value_ends_a_number(self):
        n = speech.normalize_for_check
        self.assertEqual(n('one hundred and twenty people'), n('120 people'))
        self.assertEqual(n('in twenty twenty-four'), n('in 2024'))
        self.assertEqual(n('nineteen eighty-four'), n('1984'))
        self.assertEqual(n('one, two, three'), n('1, 2, 3'))
        self.assertNotEqual(n('one, two, three'), n('six'))
        self.assertNotEqual(n('in twenty twenty-four'), n('in forty-four'))
        self.assertEqual(n('salt and pepper'), 'saltandpepper')

    def test_a_whole_sentence_with_a_number_and_a_compound(self):
        a = speech.normalize_for_check('Our healthcare costs rose by 20% to $1,500 this year.')
        b = speech.normalize_for_check('our health care costs rose by twenty percent to $one thousand five '
                                       'hundred this year')
        self.assertEqual(a, b)


class GeminiEngine(unittest.TestCase):
    """`say --engine gemini` against tests/fake_gemini.py standing in for Gemini's REST endpoint."""
    SCRIPT = 'Hello there.\nHow are you today?\nGoodbye now.'

    def setUp(self):
        self.fake = FakeGemini()
        self.addCleanup(self.fake.close)
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.dir)
        env = {'GEMINI_API_KEY': 'test-key-xyz', 'VIDEOBUILDER_GEMINI_URL': self.fake.url}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = mock.patch.object(speech.time, 'sleep')
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    def say(self, *args, script=None):
        # --no-check: this class is about style, caching and HTTP errors, not the transcript check
        # (see GeminiCheck), and it has no Chatterbox worker to run that check with.
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(['say', '--engine', 'gemini', '--no-check', '--text',
                     script if script is not None else self.SCRIPT, '--out', str(self.dir / 'n.wav'), *args])
        return out.getvalue(), err.getvalue()

    def test_style_and_context_go_in_speech_metadata_not_the_text(self):
        self.say('--style', 'warm and playful')
        reqs = self.fake.requests
        self.assertEqual(len(reqs), 3)
        p0, p1, p2 = (r['contents'][0]['parts'][0] for r in reqs)
        self.assertEqual(p0['text'], 'Hello there.')
        self.assertEqual(p0['speech_metadata'], {'style': 'warm and playful'})
        self.assertEqual(p1['text'], 'How are you today?')
        self.assertEqual(p1['speech_metadata'], {'style': 'warm and playful This continues straight on '
                                                           'from the narrator\'s previous sentence: '
                                                           '"Hello there."'})
        self.assertNotIn('Hello there', p1['text'])
        self.assertEqual(p2['text'], 'Goodbye now.')
        self.assertIn('How are you today?', p2['speech_metadata']['style'])
        for r in reqs:
            self.assertEqual(r['generationConfig']['speechConfig']['voiceConfig']['prebuiltVoiceConfig']
                             ['voiceName'], speech.GEMINI_VOICE)

    def test_without_style_the_first_phrase_has_no_metadata_key(self):
        self.say()
        p0 = self.fake.requests[0]['contents'][0]['parts'][0]
        self.assertNotIn('speech_metadata', p0)
        p1 = self.fake.requests[1]['contents'][0]['parts'][0]
        self.assertIn('speech_metadata', p1)

    def test_a_lexicon_or_say_prints_a_notice_and_does_not_apply(self):
        _, err = self.say('--say', 'there=thair')
        self.assertIn('Gemini reads text, not phonemes', err)
        self.assertIn('--say/--lexicon respellings do not apply', err)
        self.assertEqual(self.fake.requests[0]['contents'][0]['parts'][0]['text'], 'Hello there.')

    def test_a_custom_voice_and_model_reach_the_request(self):
        self.say('--voice', 'Puck', '--model', 'gemini-9000-tts')
        self.assertEqual(self.fake.requests[0]['generationConfig']['speechConfig']['voiceConfig']
                         ['prebuiltVoiceConfig']['voiceName'], 'Puck')

    def test_unchanged_input_makes_no_network_call(self):
        self.say()
        self.assertEqual(len(self.fake.requests), 3)
        printed, _ = self.say()
        self.assertIn('unchanged', printed)
        self.assertEqual(len(self.fake.requests), 3)

    def test_editing_one_phrase_redoes_it_and_the_next_only(self):
        self.say()
        self.assertEqual(len(self.fake.requests), 3)
        before = (self.dir / 'n.wav').read_bytes()
        before_doc = json.loads((self.dir / 'n.json').read_text())
        self.say(script='Hello there.\nHow are you this evening?\nGoodbye now.')
        self.assertEqual(len(self.fake.requests), 5)   # phrase 2 and phrase 3 only
        after = (self.dir / 'n.wav').read_bytes()
        self.assertNotEqual(before, after)
        after_doc = json.loads((self.dir / 'n.json').read_text())
        p0_before, p0_after = before_doc['phrases'][0], after_doc['phrases'][0]
        self.assertEqual(p0_before['text'], p0_after['text'])

        def slice_bytes(wav_bytes, cue):
            a = round(cue['start'] * RATE) * 2 + 44   # 44-byte canonical WAV header
            z = round(cue['end'] * RATE) * 2 + 44
            return wav_bytes[a:z]
        self.assertEqual(slice_bytes(before, p0_before), slice_bytes(after, p0_after))

    def phrase_audio(self):
        """{text: its samples' bytes} from the committed n.wav and n.json."""
        wav = (self.dir / 'n.wav').read_bytes()
        doc = json.loads((self.dir / 'n.json').read_text())
        return {p['text']: wav[round(p['start'] * RATE) * 2 + 44:round(p['end'] * RATE) * 2 + 44]
                for p in doc['phrases']}

    def test_removing_a_line_redoes_only_the_phrase_after_it(self):
        self.say(script='One.\nTwo.\nThree.\nFour.\nFive.')
        before = self.phrase_audio()
        self.say(script='One.\nThree.\nFour.\nFive.')
        self.assertEqual([r['contents'][0]['parts'][0]['text'] for r in self.fake.requests[5:]], ['Three.'])
        after = self.phrase_audio()
        for t in ('One.', 'Four.', 'Five.'):
            self.assertEqual(before[t], after[t])

    def test_inserting_a_line_redoes_it_and_the_phrase_after_it_only(self):
        self.say(script='One.\nTwo.\nThree.')
        before = self.phrase_audio()
        self.say(script='Zero.\nOne.\nTwo.\nThree.')
        self.assertEqual([r['contents'][0]['parts'][0]['text'] for r in self.fake.requests[3:]], ['Zero.', 'One.'])
        after = self.phrase_audio()
        for t in ('Two.', 'Three.'):
            self.assertEqual(before[t], after[t])

    def test_changing_style_voice_or_model_redoes_every_phrase(self):
        self.say()
        self.assertEqual(len(self.fake.requests), 3)
        self.say('--style', 'cheerful')
        self.assertEqual(len(self.fake.requests), 6)
        self.say('--style', 'cheerful', '--voice', 'Puck')
        self.assertEqual(len(self.fake.requests), 9)
        self.say('--style', 'cheerful', '--voice', 'Puck', '--model', 'gemini-9000-tts')
        self.assertEqual(len(self.fake.requests), 12)

    def test_missing_api_key_is_a_clear_error(self):
        del os.environ['GEMINI_API_KEY']
        with self.assertRaises(SystemExit) as cm:
            self.say()
        self.assertIn('GEMINI_API_KEY', str(cm.exception))
        self.assertTrue(str(cm.exception).startswith('say: '))

    def test_the_key_never_appears_in_output(self):
        self.fake.queue(400, {'error': {'message': 'nope'}})
        with self.assertRaises(SystemExit) as cm:
            self.say()
        self.assertNotIn('test-key-xyz', str(cm.exception))
        self.assertFalse((self.dir / 'n.json').exists())

    def test_a_rate_other_than_24k_is_a_clear_error(self):
        self.fake.queue(200, {'candidates': [{'content': {'parts': [
            {'inlineData': {'mimeType': 'audio/L16;rate=16000', 'data': 'AAAA'}}]}}]})
        with self.assertRaises(SystemExit) as cm:
            self.say()
        self.assertIn('16000', str(cm.exception))
        self.assertIn('24000', str(cm.exception))

    def test_unsupported_style_names_the_model_not_a_raw_dump(self):
        self.fake.queue(400, {'error': {'message': 'Unknown name "speech_metadata": Cannot find field.'}})
        with self.assertRaises(SystemExit) as cm:
            self.say('--style', 'warm')
        msg = str(cm.exception)
        self.assertIn(speech.GEMINI_MODEL, msg)
        self.assertIn('style', msg)
        self.assertNotIn('Traceback', msg)

    def test_429_then_503_then_success_retries_with_backoff(self):
        self.fake.queue(429, {'error': {'message': 'rate limited'}})
        self.fake.queue(503, {'error': {'message': 'overloaded'}})
        self.say(script='Hello there.')
        self.assertEqual(len(self.fake.requests), 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_exhausted_retries_is_a_clear_error(self):
        for _ in range(speech.GEMINI_HTTP_RETRIES):
            self.fake.queue(500, {'error': {'message': 'down for maintenance'}})
        with self.assertRaises(SystemExit) as cm:
            self.say(script='Hello there.')
        self.assertIn('down for maintenance', str(cm.exception))

    def test_style_is_refused_for_other_engines(self):
        with self.assertRaisesRegex(SystemExit, '--style is for --engine gemini'):
            cli.main(['say', '--text', 'Hi.', '--style', 'warm', '--out', str(self.dir / 'never.wav')])
        self.assertFalse((self.dir / 'never.wav').exists())

    def test_kokoro_only_options_are_refused(self):
        for flags in (['--lang', 'en-gb'], ['--phonemes'], ['--list-voices']):
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                self.say(*flags)
        self.assertFalse((self.dir / 'n.wav').exists())

    def test_gemini_only_flags_are_refused_for_other_engines(self):
        for flags in (['--convert-to', 'x.wav'], ['--retries', '1'], ['--no-check']):
            with self.subTest(flags=flags), self.assertRaisesRegex(SystemExit, 'is for --engine gemini'):
                cli.main(['say', '--text', 'Hi.', '--out', str(self.dir / 'never.wav'), *flags])
            self.assertFalse((self.dir / 'never.wav').exists())


class GeminiCheck(unittest.TestCase):
    """`say --engine gemini`'s `--convert-to` and transcript check, against
    both tests/fake_gemini.py and tests/fake_chatterbox.py."""

    def setUp(self):
        self.fake = FakeGemini()
        self.addCleanup(self.fake.close)
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.dir)
        self.python = self.dir / 'python'
        self.python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT / "tests" / "fake_chatterbox.py"}" "$@"\n')
        self.python.chmod(0o755)
        self.log = self.dir / 'log.jsonl'
        self.clip = self.dir / 'target.wav'
        self.clip.write_bytes(b'x' * 37)
        env = {'GEMINI_API_KEY': 'test-key', 'VIDEOBUILDER_GEMINI_URL': self.fake.url,
               'VIDEOBUILDER_CHATTERBOX_PYTHON': str(self.python), 'FAKE_CHATTERBOX_LOG': str(self.log)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = mock.patch.object(speech.time, 'sleep')
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def logged(self):
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def say(self, *args, script='Hello there.'):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(['say', '--engine', 'gemini', '--text', script, '--out', str(self.dir / 'n.wav'), *args])
        return out.getvalue(), err.getvalue()

    def test_check_passes_when_the_transcript_matches(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['Hello there.'])
        self.say()
        self.assertTrue((self.dir / 'n.wav').exists())
        self.assertEqual(len([l for l in self.logged() if 'transcribe' in l]), 1)

    def test_a_mismatch_retries_then_succeeds(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['wrong words', 'Hello there.'])
        _, err = self.say()
        self.assertIn('mismatch', err)
        self.assertIn('wrong words', err)
        self.assertIn('Hello there.', err)
        self.assertEqual(len(self.fake.requests), 2)   # redone once
        self.assertEqual(len([l for l in self.logged() if 'transcribe' in l]), 2)

    def test_persistent_mismatch_fails_without_writing_partial_output(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['nope'])
        with self.assertRaises(SystemExit) as cm:
            self.say('--retries', '1')
        msg = str(cm.exception)
        self.assertIn('Hello there.', msg)
        self.assertIn('nope', msg)
        self.assertFalse((self.dir / 'n.wav').exists())
        self.assertFalse((self.dir / 'n.json').exists())
        self.assertEqual(len(self.fake.requests), 2)   # the initial try plus 1 retry

    def test_no_check_skips_the_transcript_worker_entirely(self):
        self.say('--no-check')
        self.assertTrue((self.dir / 'n.wav').exists())
        self.assertEqual(self.logged(), [])

    def test_convert_to_sends_each_phrase_through_one_shared_worker(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['Hello there.', 'How are you?'])
        self.say('--convert-to', str(self.clip), script='Hello there.\nHow are you?')
        converts = [l for l in self.logged() if 'convert' in l]
        transcribes = [l for l in self.logged() if 'transcribe' in l]
        self.assertEqual(len(converts), 2)
        self.assertEqual(len(transcribes), 2)
        # the check ran on the converted audio, not the pre-conversion Gemini audio: each
        # transcribe request's bytes are exactly some convert reply's bytes, in order.
        self.assertEqual([t['transcribe_sha256'] for t in transcribes],
                         [c['convert_out_sha256'] for c in converts])
        runs = [l for l in self.logged() if 'argv' in l]
        self.assertEqual(len(runs), 1)   # convert and transcribe share one worker process
        argv = runs[0]['argv']
        self.assertEqual(sorted(argv[argv.index('--ops') + 1].split(',')), ['convert', 'transcribe'])
        self.assertEqual(argv[argv.index('--convert-to') + 1], str(self.clip.resolve()))

    def test_unchanged_reuse_starts_no_worker_either(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['Hello there.'])
        self.say()
        self.assertEqual(len(self.fake.requests), 1)
        runs_before = len([l for l in self.logged() if 'argv' in l])
        printed, _ = self.say()
        self.assertIn('unchanged', printed)
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual(len([l for l in self.logged() if 'argv' in l]), runs_before)

    def test_the_same_clip_by_another_path_redoes_nothing(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['Hello there.'])
        self.say('--convert-to', str(self.clip))
        other = self.dir / 'elsewhere' / 'same.wav'
        other.parent.mkdir()
        other.write_bytes(self.clip.read_bytes())
        self.say('--convert-to', str(other))
        self.assertEqual(len(self.fake.requests), 1)

    def test_retries_without_the_check_redoes_nothing(self):
        self.say('--no-check')
        self.say('--no-check', '--retries', '5')
        self.assertEqual(len(self.fake.requests), 1)

    def test_negative_retries_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            self.say('--retries', '-1')
        self.assertIn('--retries', str(cm.exception))
        self.assertEqual(self.fake.requests, [])

    def test_a_broken_worker_fails_before_any_gemini_call(self):
        os.environ['VIDEOBUILDER_CHATTERBOX_PYTHON'] = str(self.dir / 'does' / 'not' / 'exist')
        with self.assertRaises(SystemExit):
            self.say()
        self.assertEqual(self.fake.requests, [])

    def test_changing_convert_to_bytes_redoes_the_phrase(self):
        os.environ['FAKE_CHATTERBOX_TRANSCRIPTS'] = json.dumps(['Hello there.'])
        self.say('--convert-to', str(self.clip))
        self.assertEqual(len(self.fake.requests), 1)
        self.clip.write_bytes(b'y' * 37)   # same path, different bytes
        self.say('--convert-to', str(self.clip))
        self.assertEqual(len(self.fake.requests), 2)


if __name__ == '__main__':
    unittest.main()
