import math
import os
import shutil
import subprocess
import tempfile
import unittest

import struct
import wave

from videobuilder import Audio, Film, Grid, Segment, Sound, Timeline
from videobuilder.render import check_chunk, measure, render


def sine_wav(path, freq, duration, sr=48000, amplitude=10000):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
        n = int(duration * sr)
        w.writeframes(b''.join(struct.pack('<h', int(amplitude * math.sin(2 * math.pi * freq * i / sr)))
                               for i in range(n)))


def decode_pcm(path, sr=48000):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    return struct.unpack(f'<{len(raw) // 2}h', raw)


def peak_level(pcm, t0, t1, sr=48000):
    seg = pcm[int(t0 * sr):int(t1 * sr)]
    return max(abs(v) for v in seg) if seg else 0


class ChunkDriftGuard(unittest.TestCase):
    def test_whole_microsecond_chunks_pass(self):
        for chunk, fps in ((15, 30), (30, 30), (3, 30), (24, 24), (15, 24), (60, 60), (1, 25), (5, 50)):
            with self.subTest(chunk=chunk, fps=fps):
                check_chunk(chunk, fps)

    def test_drifting_chunks_rejected(self):
        # 20 frames at 30 fps is 666666.67 us: the concat joins would drift.
        for chunk, fps in ((20, 30), (1, 30), (7, 30), (10, 60), (1, 24)):
            with self.subTest(chunk=chunk, fps=fps):
                with self.assertRaises(ValueError):
                    check_chunk(chunk, fps)

    def test_empty_chunk_rejected(self):
        with self.assertRaises(ValueError):
            check_chunk(0, 30)

    def test_render_checks_before_drawing(self):
        drawn = []
        film = Film(draw=lambda n, cv: drawn.append(n), fps=30, frames=60)
        with self.assertRaises(ValueError):
            render(film, os.devnull, chunk=20)
        self.assertEqual(drawn, [])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg')
class RenderJoins(unittest.TestCase):
    def test_chunks_join_to_exact_length(self):
        def draw(n, cv):
            cv.rect(n, 0, 8, 8, '#ffffff')
        film = Film(draw=draw, fps=30, frames=50, formats=['1x1'])
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=2, chunk=15, log=quiet)  # 15 + 15 + 15 + 5
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-count_frames',
                                    '-show_entries', 'stream=nb_read_frames,width,height,duration',
                                    '-of', 'default=nw=1', out], capture_output=True, text=True, check=True).stdout
        facts = dict(line.split('=') for line in probe.split())
        self.assertEqual(int(facts['nb_read_frames']), 50)
        self.assertEqual((int(facts['width']), int(facts['height'])), (1080, 1080))
        self.assertAlmostEqual(float(facts['duration']), 50 / 30, places=3)


@unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg')
class ForkedWorkers(unittest.TestCase):
    def test_text_at_new_sizes_in_workers(self):
        # Pango loads fonts on a thread a forked worker doesn't inherit: text at a
        # size the parent never drew (a scaled layer) hung every worker.
        from videobuilder import Font, text

        def draw(n, cv):
            s = 0.3 + 0.7 * n / 30
            with cv.layer(dx=540 * (1 - s), dy=540 * (1 - s), scale=s):
                text.draw(cv, f'Scaled {n}', Font('Sans', 80, 700), 100, 500, '#ffffff')
        film = Film(draw=draw, fps=30, frames=30, formats=['1x1'])
        with tempfile.TemporaryDirectory() as tmp, open(os.devnull, 'w') as quiet:
            render(film, os.path.join(tmp, 'x.mp4'), jobs=2, chunk=15, log=quiet, stall=60)

    def test_progress_in_a_log_is_lines(self):
        import io
        film = Film(draw=lambda n, cv: None, fps=30, frames=300, formats=['1x1'])
        log = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            render(film, os.path.join(tmp, 'x.mp4'), jobs=4, chunk=15, log=log)
        lines = log.getvalue().splitlines()
        self.assertNotIn('\r', log.getvalue())
        self.assertEqual(lines[:-1], [f'1x1: chunks {k}/20' for k in range(2, 21, 2)])

    def test_a_stalled_worker_is_an_error(self):
        import time
        parent = os.getpid()

        def draw(n, cv):
            if os.getpid() != parent and n == 20:
                time.sleep(30)
        film = Film(draw=draw, fps=30, frames=30, formats=['1x1'])
        with tempfile.TemporaryDirectory() as tmp, open(os.devnull, 'w') as quiet:
            with self.assertRaisesRegex(RuntimeError, 'frames still pending: 15-29'):
                render(film, os.path.join(tmp, 'x.mp4'), jobs=2, chunk=15, log=quiet, stall=3)


class AudioTrim(unittest.TestCase):
    def test_trim_defaults_to_the_grid(self):
        tl = Timeline(Grid(fps=30, bpm=120, head_trim=8), [Segment('a', 0, 2)], end=2)
        film = Film(draw=lambda n, cv: None, timeline=tl, audio=Audio('x.wav'))
        self.assertEqual(film.audio.trim_frames, 8)
        film = Film(draw=lambda n, cv: None, timeline=tl, audio=Audio('x.wav', trim_frames=3))
        self.assertEqual(film.audio.trim_frames, 3)  # given: kept
        film = Film(draw=lambda n, cv: None, fps=30, frames=10, audio=Audio('x.wav'))
        self.assertEqual(film.audio.trim_frames, 0)  # no grid, no trim

    def test_audio_object_not_mutated(self):
        au = Audio('x.wav')
        tl = Timeline(Grid(head_trim=4), [Segment('a', 0, 1)], end=1)
        Film(draw=lambda n, cv: None, timeline=tl, audio=au)
        self.assertIsNone(au.trim_frames)


@unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg')
class AudioFade(unittest.TestCase):
    def test_fade_ends_silent_at_the_last_frame(self):
        sr, fps, frames, k = 48000, 30, 30, 10
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, 'dc.wav')
            with wave.open(wav, 'wb') as w:  # a 2 s square wave at 1 kHz, half scale
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
                w.writeframes(b''.join(struct.pack('<h', 16000 if (i // 24) % 2 else -16000) for i in range(2 * sr)))
            film = Film(draw=lambda n, cv: None, fps=fps, frames=frames, formats=['1x1'],
                        audio=Audio(wav, fade_out_frames=k, loudness=None))
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=1, chunk=15, log=quiet)
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', out, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'],
                                 capture_output=True, check=True).stdout
        pcm = struct.unpack(f'<{len(raw) // 2}h', raw)

        def level(frame):  # peak over the middle of a frame
            a = int((frame + 0.25) * sr / fps)
            return max(abs(v) for v in pcm[a:a + sr // fps // 2]) / 16000

        start = frames - 1 - k  # gain 1 here, falling to 0 at the start of the last frame
        self.assertGreater(level(start - 2), 0.9)
        self.assertAlmostEqual(level(start + k // 2), 0.5, delta=0.12)
        self.assertLess(level(frames - 1), 0.08)


if __name__ == '__main__':
    unittest.main()


@unittest.skipUnless(shutil.which('ffmpeg'), 'needs ffmpeg')
class Loudness(unittest.TestCase):
    sr, fps, frames = 48000, 30, 30

    def render_pcm(self, samples):
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, 'in.wav')
            with wave.open(wav, 'wb') as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(self.sr)
                w.writeframes(struct.pack(f'<{len(samples)}h', *samples))
            film = Film(draw=lambda n, cv: None, fps=self.fps, frames=self.frames, formats=['1x1'], audio=Audio(wav))
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=1, chunk=15, log=quiet)
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', out, '-ac', '1', '-ar', str(self.sr),
                                  '-f', 's16le', '-'], capture_output=True, check=True).stdout
        return struct.unpack(f'<{len(raw) // 2}h', raw)

    def test_silence_is_not_boosted(self):
        pcm = self.render_pcm([0] * self.sr)
        self.assertEqual(max(abs(v) for v in pcm), 0)

    def test_limiter_keeps_hits_on_time(self):
        # Quiet 440 Hz bed with a loud click at 0.5 s: the click is limited, not moved.
        hit = self.sr // 2
        bed = [int(300 * math.sin(2 * math.pi * 440 * i / self.sr)) for i in range(self.sr)]
        for i in range(hit, hit + 48):
            bed[i] = 30000 if (i - hit) % 2 == 0 else -30000
        pcm = self.render_pcm(bed)
        peak = max(range(len(pcm)), key=lambda i: abs(pcm[i]))
        self.assertLess(abs(peak - hit), self.sr // 1000)  # within 1 ms
        self.assertLess(max(abs(v) for v in pcm) / 32768, 10 ** (-1 / 20))  # under -1 dBFS

    def test_peaks_cap_the_gain(self):
        # The click needs only a little limiting at its cap, so the bed is not
        # boosted toward -14 LUFS: it comes out about where it went in.
        hit = self.sr // 2
        bed = [int(300 * math.sin(2 * math.pi * 440 * i / self.sr)) for i in range(self.sr)]
        for i in range(hit, hit + 48):
            bed[i] = 30000 if (i - hit) % 2 == 0 else -30000
        pcm = self.render_pcm(bed)
        cap = -3 + 1 - 20 * math.log10(30000 / 32768)
        quiet = max(abs(v) for v in pcm[self.sr // 10:hit - self.sr // 10])
        self.assertAlmostEqual(quiet / (300 * 10 ** (cap / 20)), 1, delta=0.15)

    def test_clean_track_reaches_target(self):
        tone = [int(1000 * math.sin(2 * math.pi * 440 * i / self.sr)) for i in range(self.sr)]
        pcm = self.render_pcm(tone)
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, 'out.wav')
            with wave.open(wav, 'wb') as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(self.sr)
                w.writeframes(struct.pack(f'<{len(pcm)}h', *pcm))
            loud, _ = measure(wav, 'anull')
        self.assertAlmostEqual(loud, -14, delta=1)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg')
class UnchangedDefaultPath(unittest.TestCase):
    """Decision 5: a film with no sounds must build exactly the same ffmpeg mux
    command as before this round, whether or not it has music."""

    def captured_cmd(self, film, out):
        from unittest import mock
        import videobuilder.render as render_mod
        calls = []
        real_run = subprocess.run

        def spy(cmd, *a, **k):
            calls.append(cmd)
            return real_run(cmd, *a, **k)
        with open(os.devnull, 'w') as quiet, mock.patch.object(render_mod.subprocess, 'run', side_effect=spy):
            render(film, out, jobs=1, chunk=15, log=quiet)
        return calls[-1]

    def test_no_audio_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            film = Film(draw=lambda n, cv: None, fps=30, frames=20, formats=['1x1'])
            out = os.path.join(tmp, 'x.mp4')
            cmd = self.captured_cmd(film, out)
        self.assertNotIn('-filter_complex', cmd)
        self.assertEqual(cmd.count('-i'), 1)  # only the concat listing
        self.assertEqual(cmd[-5:], ['-c:v', 'copy', '-movflags', '+faststart', out])

    def test_music_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, 'music.wav')
            sine_wav(wav, 220, 1.0)
            film = Film(draw=lambda n, cv: None, fps=30, frames=20, formats=['1x1'], audio=Audio(wav))
            out = os.path.join(tmp, 'x.mp4')
            cmd = self.captured_cmd(film, out)
        self.assertEqual(cmd.count('-i'), 2)  # the concat listing, then the music file
        fc = cmd[cmd.index('-filter_complex') + 1]
        self.assertTrue(fc.startswith('[1:a]') and fc.endswith('[a]'))
        self.assertNotIn('amix', fc)
        self.assertNotIn('adelay', fc)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg')
class SoundMix(unittest.TestCase):
    fps = 30

    def test_length_matches_and_sound_is_audible_only_in_its_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            music, voice = os.path.join(tmp, 'music.wav'), os.path.join(tmp, 'voice.wav')
            sine_wav(music, 220, 3.0, amplitude=3000)
            sine_wav(voice, 1000, 1.0, amplitude=16000)
            frames = 90  # 3 s at 30 fps
            film = Film(draw=lambda n, cv: None, fps=self.fps, frames=frames, formats=['1x1'],
                        audio=Audio(music, loudness=None),
                        sounds=(Sound(voice, at=30, start=0.0, frames=30, fade_in_frames=0, fade_out_frames=0),))
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=1, chunk=15, log=quiet)
            duration = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries',
                                       'stream=duration', '-of', 'default=nw=1:nk=1', out],
                                      capture_output=True, text=True, check=True).stdout
            self.assertAlmostEqual(float(duration), frames / self.fps, delta=0.05)
            pcm = decode_pcm(out)
        self.assertLess(peak_level(pcm, 0.1, 0.9), 6000)       # before: music bed only
        self.assertGreater(peak_level(pcm, 1.1, 1.9), 10000)   # during: the voice
        self.assertLess(peak_level(pcm, 2.1, 2.9), 6000)       # after: music bed only

    def test_sounds_with_no_music_render_with_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            voice = os.path.join(tmp, 'voice.wav')
            sine_wav(voice, 1000, 1.0)
            film = Film(draw=lambda n, cv: None, fps=self.fps, frames=60, formats=['1x1'],
                        sounds=(Sound(voice, at=10, start=0.0, frames=30),))
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=1, chunk=15, log=quiet)
            pcm = decode_pcm(out)
        self.assertGreater(peak_level(pcm, 10 / self.fps + 0.1, 10 / self.fps + 0.5), 1000)

    def test_a_sound_with_no_audio_stream_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            silent = os.path.join(tmp, 'novideo.mp4')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=red:s=16x16:d=1', silent],
                           check=True)
            film = Film(draw=lambda n, cv: None, fps=self.fps, frames=30, formats=['1x1'],
                        sounds=(Sound(silent, at=0, start=0.0, frames=10),))
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet, self.assertRaisesRegex(ValueError, 'no audio stream'):
                render(film, out, jobs=1, chunk=15, log=quiet)

    def test_partial_render_gets_the_same_gain_as_the_full_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            music, voice = os.path.join(tmp, 'music.wav'), os.path.join(tmp, 'voice.wav')
            sine_wav(music, 220, 3.0, amplitude=3000)
            sine_wav(voice, 1000, 1.0, amplitude=16000)
            frames = 90
            film = Film(draw=lambda n, cv: None, fps=self.fps, frames=frames, formats=['1x1'],
                        audio=Audio(music), sounds=(Sound(voice, at=30, start=0.0, frames=20),))
            full, partial = os.path.join(tmp, 'full.mp4'), os.path.join(tmp, 'partial.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, full, jobs=1, chunk=15, log=quiet)
                render(film, partial, jobs=1, chunk=15, frames=(45, 75), log=quiet)
            pcm_full, pcm_partial = decode_pcm(full), decode_pcm(partial)
        a, b = 60 / self.fps, 70 / self.fps  # music-only window, well clear of the sound's span
        full_level = peak_level(pcm_full, a, b)
        partial_level = peak_level(pcm_partial, a - 45 / self.fps, b - 45 / self.fps)
        self.assertGreater(full_level, 0)
        self.assertAlmostEqual(full_level / partial_level, 1, delta=0.05)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg')
class Ducking(unittest.TestCase):
    fps = 30

    def test_duck_db_quiets_the_music_during_a_sounds_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            music = os.path.join(tmp, 'music.wav')
            sine_wav(music, 220, 2.0, amplitude=10000)
            frames = 60
            # Same file as the "sound", but all but silent: it only triggers ducking,
            # so the mix during its span is still (ducked) music, directly comparable.
            film = Film(draw=lambda n, cv: None, fps=self.fps, frames=frames, formats=['1x1'],
                        audio=Audio(music, loudness=None, duck_db=-12),
                        sounds=(Sound(music, at=20, start=0.0, frames=20, gain_db=-90),))
            out = os.path.join(tmp, 'x.mp4')
            with open(os.devnull, 'w') as quiet:
                render(film, out, jobs=1, chunk=15, log=quiet)
            pcm = decode_pcm(out)
        before = peak_level(pcm, 0.1, 0.5)
        during = peak_level(pcm, 0.9, 1.1)  # inside the span, clear of its fade ramps
        after = peak_level(pcm, 1.5, 1.9)
        self.assertAlmostEqual(before / during, 10 ** (12 / 20), delta=0.4)
        self.assertAlmostEqual(after / during, 10 ** (12 / 20), delta=0.4)
