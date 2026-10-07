import os
import shutil
import subprocess
import tempfile
import unittest

import struct
import wave

from videobuilder import Audio, Film, Grid, Segment, Timeline
from videobuilder.render import check_chunk, render


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
                        audio=Audio(wav, fade_out_frames=k))
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
