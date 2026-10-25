"""videobuilder.speech: phrases, timing and joining, the sidecars, the mouth
flap, and `say` without the speech extra. A fake synthesizer stands in for
Kokoro: no test needs the model or kokoro-onnx."""
import array
import contextlib
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


if __name__ == '__main__':
    unittest.main()
