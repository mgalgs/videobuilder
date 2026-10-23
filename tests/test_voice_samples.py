"""videobuilder.voice_samples.VoiceSamples, and the editor's
GET /api/narration/voice-sample route built on it. A fake Kokoro engine
stands in for the real one -- no test needs the model."""
import array
import math
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from videobuilder import speech
from videobuilder.voice_samples import UnknownVoice, VoiceSamples

from tests import fixtures


def tone(seconds, lead=0.0, tail=0.0, amp=0.5, hz=220):
    rate = speech.RATE
    n = int(seconds * rate)
    body = (int(amp * 32767 * math.sin(2 * math.pi * hz * i / rate)) for i in range(n))
    return array.array('h', [0] * int(lead * rate) + list(body) + [0] * int(tail * rate))


class FakeEngine:
    model_id = 'fake-engine-v1'

    def __init__(self):
        self.synth_calls = []

    def voices(self):
        return ['af_heart', 'bm_george']

    def phonemize(self, text, lang):
        return text.lower()

    def synth(self, phonemes, voice, speed, lang):
        self.synth_calls.append((phonemes, voice, speed, lang))
        return tone(0.4, lead=0.2, tail=0.2)


class SlowFakeEngine(FakeEngine):
    """Blocks inside `synth` until released, so a test can force two
    requests to genuinely overlap instead of just racing by luck."""

    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def synth(self, *a, **kw):
        self.started.set()
        self.release.wait(timeout=2)
        return super().synth(*a, **kw)


class Path_(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.state_dir = tmp.name
        self.engine = FakeEngine()
        self.samples = VoiceSamples(self.state_dir, engine_factory=lambda: self.engine)

    def test_first_call_renders_second_call_is_a_cache_hit(self):
        p1 = self.samples.path('af_heart', 1.0)
        self.assertTrue(Path(p1).is_file())
        rendered = len(self.engine.synth_calls)
        self.assertGreater(rendered, 0)
        p2 = self.samples.path('af_heart', 1.0)
        self.assertEqual(p1, p2)
        self.assertEqual(len(self.engine.synth_calls), rendered)

    def test_unknown_voice_raises(self):
        with self.assertRaises(UnknownVoice):
            self.samples.path('nope', 1.0)

    def test_different_speed_is_a_different_cache_entry(self):
        p1 = self.samples.path('af_heart', 1.0)
        p2 = self.samples.path('af_heart', 1.3)
        self.assertNotEqual(p1, p2)

    def test_different_voice_is_a_different_cache_entry(self):
        p1 = self.samples.path('af_heart', 1.0)
        p2 = self.samples.path('bm_george', 1.0)
        self.assertNotEqual(p1, p2)

    def test_concurrent_first_requests_for_the_same_voice_render_once(self):
        engine = SlowFakeEngine()
        samples = VoiceSamples(self.state_dir, engine_factory=lambda: engine)
        results = []

        def worker():
            results.append(samples.path('af_heart', 1.0))

        t1 = threading.Thread(target=worker)
        t1.start()
        self.assertTrue(engine.started.wait(timeout=2), 'the first render never started')
        t2 = threading.Thread(target=worker)
        t2.start()
        t2.join(timeout=0.2)
        self.assertTrue(t2.is_alive(), 'the second request must wait for the first, not render too')
        engine.release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertEqual(results, [results[0], results[0]])
        self.assertEqual(len(engine.synth_calls), 1)


class Route(fixtures.API):
    def _configure(self, engine=None):
        self.engine = engine or FakeEngine()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.start(voice_samples=VoiceSamples(tmp.name, engine_factory=lambda: self.engine))

    def test_first_request_renders_second_is_a_cache_hit(self):
        self._configure()
        with urllib.request.urlopen(self.base + '/api/narration/voice-sample?voice=af_heart') as r:
            self.assertEqual(r.headers.get_content_type(), 'audio/wav')
            first = r.read()
        self.assertGreater(len(first), 0)
        rendered = len(self.engine.synth_calls)
        self.assertGreater(rendered, 0)
        with urllib.request.urlopen(self.base + '/api/narration/voice-sample?voice=af_heart') as r:
            second = r.read()
        self.assertEqual(first, second)
        self.assertEqual(len(self.engine.synth_calls), rendered)

    def test_unknown_voice_is_404(self):
        self._configure()
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/api/narration/voice-sample?voice=nope')
        with e.exception:
            self.assertEqual(e.exception.code, 404)

    def test_missing_voice_is_400(self):
        self._configure()
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/api/narration/voice-sample')
        with e.exception:
            self.assertEqual(e.exception.code, 400)

    def test_speed_out_of_range_is_400(self):
        self._configure()
        for speed in ('0.1', '9', 'not-a-number'):
            with self.subTest(speed=speed), self.assertRaises(urllib.error.HTTPError) as e:
                self.get(f'/api/narration/voice-sample?voice=af_heart&speed={speed}')
            with e.exception:
                self.assertEqual(e.exception.code, 400)

    def test_speed_is_part_of_the_cache_key(self):
        # A different speed must not reuse speed=1.0's cached file: the fake engine ignores
        # speed (there's nothing to assert on the bytes), but it must still be asked to render
        # again rather than silently serving the wrong speed's sample.
        self._configure()
        with urllib.request.urlopen(self.base + '/api/narration/voice-sample?voice=af_heart&speed=0.5'):
            pass
        with urllib.request.urlopen(self.base + '/api/narration/voice-sample?voice=af_heart&speed=2.0'):
            pass
        self.assertEqual(len(self.engine.synth_calls), 2)


if __name__ == '__main__':
    unittest.main()
