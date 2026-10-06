"""Render a film: frames in parallel chunks, each chunk piped to its own ffmpeg,
then the chunks concatenated (no re-encode) and the music muxed in.

    python3 -m videobuilder film.py out.mp4 [--jobs N]
    python3 -m videobuilder film.py --still 300 f300.png

A film file defines `FILM = Film(...)`. Its `draw(n, canvas)` must be a pure
function of `n`, so any frame (or chunk) renders alone and in any order.
"""
import argparse
import importlib.util
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Callable

from .canvas import Canvas


@dataclass
class Audio:
    path: str
    trim_frames: int = 0  # skipped at the head of the file
    gain_db: float = 0.0
    fade_out_frames: int = 0  # linear fade reaching silence on the last frame


@dataclass
class Film:
    width: int
    height: int
    fps: int
    frames: int
    draw: Callable[[int, Canvas], None]
    background: str = '#000000'
    audio: Audio | None = None

    def frame(self, n):
        cv = Canvas(self.width, self.height, self.background)
        self.draw(n, cv)
        return cv


def load(path):
    path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location('film', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.FILM


_film = None


def _encode_chunk(args):
    a, z, out, crf = args
    f = _film
    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra',
        '-s', f'{f.width}x{f.height}', '-r', str(f.fps), '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p',
        '-threads', '2', '-video_track_timescale', str(f.fps * 512), out], stdin=subprocess.PIPE)
    for n in range(a, z):
        enc.stdin.write(f.frame(n).bgra())
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError(f'ffmpeg failed on chunk {a}-{z}')
    return a, z


def render(film_path, out, jobs=None, chunk=15, crf=18, frames=None):
    film = load(film_path)
    a, z = frames or (0, film.frames)
    jobs = jobs or os.cpu_count()
    # The concat demuxer keeps time in microseconds; a chunk that isn't a whole
    # number of them (20 frames at 30 fps) drifts the joins by a fraction of a ms each.
    if chunk * 1_000_000 % film.fps:
        raise ValueError(f'chunk of {chunk} frames is not a whole number of microseconds at {film.fps} fps')
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        tasks = [(s, min(s + chunk, z), os.path.join(tmp, f'c{s:06d}.mp4'), crf) for s in range(a, z, chunk)]
        # Warm the asset caches once (decoded images, mip levels, text metrics) by
        # drawing the first frame of each chunk here, then fork: workers share the
        # decoded pixels copy-on-write instead of each decoding every capture again.
        global _film
        _film = film
        for t in tasks:
            film.frame(t[0])
        t_warm = time.time() - t0
        ctx = mp.get_context('fork')
        with ctx.Pool(jobs) as pool:
            done = 0
            for _ in pool.imap_unordered(_encode_chunk, tasks):
                done += 1
                print(f'\rchunks {done}/{len(tasks)}', end='', file=sys.stderr, flush=True)
        print(file=sys.stderr)
        t1 = time.time()
        listing = os.path.join(tmp, 'list.txt')
        with open(listing, 'w') as fh:
            fh.writelines(f"file '{t[2]}'\n" for t in tasks)
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', listing]
        au = film.audio
        if au:
            dur = (z - a) / film.fps
            trim = (au.trim_frames + a) / film.fps
            fade = ''
            if au.fade_out_frames:
                st = (film.frames - 1 - au.fade_out_frames - a) / film.fps
                fade = f',afade=t=out:st={st:.6f}:d={au.fade_out_frames / film.fps:.6f}'
            cmd += ['-i', au.path, '-filter_complex',
                    f'[1:a]atrim=start={trim:.6f},asetpts=PTS-STARTPTS,volume={au.gain_db}dB{fade},apad,atrim=end={dur:.6f}[a]',
                    '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
        cmd += ['-c:v', 'copy', '-movflags', '+faststart', out]
        subprocess.run(cmd, check=True)
    t2 = time.time()
    print(f'{z - a} frames, {jobs} jobs: warm {t_warm:.1f}s, frames+encode {t1 - t0:.1f}s, mux {t2 - t1:.1f}s, total {t2 - t0:.1f}s', file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('film')
    p.add_argument('out', nargs='?')
    p.add_argument('--jobs', type=int)
    p.add_argument('--frames', help='a:b, half-open')
    p.add_argument('--chunk', type=int, default=15, help='frames per encoded chunk')
    p.add_argument('--still', type=int, nargs='+', help='frame number(s); out is a PNG path or a dir')
    a = p.parse_args()
    if a.still:
        film = load(a.film)
        for n in a.still:
            path = os.path.join(a.out, f'f{n:04d}.png') if len(a.still) > 1 else a.out
            film.frame(n).save_png(path)
        return
    frames = tuple(int(x) for x in a.frames.split(':')) if a.frames else None
    render(a.film, a.out, a.jobs, chunk=a.chunk, frames=frames)


if __name__ == '__main__':
    main()
