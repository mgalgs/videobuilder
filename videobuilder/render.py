"""Render a film: frames in parallel chunks, each chunk piped to its own ffmpeg,
then the chunks concatenated (no re-encode) and the audio muxed in.

Every frame is drawn on its own (`draw(n, canvas)` is pure), so chunks render
in any order on any worker.
"""
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import time

from .film import Audio, Film, load  # noqa: F401  (Audio, Film: the old import path)


def check_chunk(chunk, fps):
    """The concat demuxer keeps time in microseconds; a chunk that isn't a whole
    number of them (20 frames at 30 fps) drifts the joins by a fraction of a ms each."""
    if chunk < 1:
        raise ValueError('chunk must be at least one frame')
    if chunk * 1_000_000 % fps:
        raise ValueError(f'chunk of {chunk} frames is not a whole number of microseconds at {fps} fps')


_job = None  # (film, format) for forked workers


def _encode_chunk(args):
    a, z, out, crf = args
    film, fmt = _job
    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra',
        '-s', f'{fmt.width}x{fmt.height}', '-r', str(film.fps), '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p',
        '-threads', '2', '-video_track_timescale', str(film.fps * 512), out], stdin=subprocess.PIPE)
    for n in range(a, z):
        enc.stdin.write(film.frame(n, fmt).bgra())
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError(f'ffmpeg failed on chunk {a}-{z}')
    return a, z


def render(film, out, format=None, jobs=None, chunk=15, crf=18, frames=None, log=sys.stderr):
    """Render `film` (a Film or a film file path) in `format` to the MP4 `out`."""
    if isinstance(film, (str, os.PathLike)):
        film = load(film)
    fmt = film.format(format)
    a, z = frames or (0, film.frames)
    if not 0 <= a < z <= film.frames:
        raise ValueError(f'frames {a}:{z} outside 0:{film.frames}')
    jobs = jobs or os.cpu_count()
    check_chunk(chunk, film.fps)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        tasks = [(s, min(s + chunk, z), os.path.join(tmp, f'c{s:06d}.mp4'), crf) for s in range(a, z, chunk)]
        # Warm the asset caches once (decoded images, mip levels, text metrics) by
        # drawing the first frame of each chunk here, then fork: workers share the
        # decoded pixels copy-on-write instead of each decoding every capture again.
        global _job
        _job = film, fmt
        for t in tasks:
            film.frame(t[0], fmt)
        t_warm = time.time() - t0
        ctx = mp.get_context('fork')
        with ctx.Pool(jobs) as pool:
            done = 0
            for _ in pool.imap_unordered(_encode_chunk, tasks):
                done += 1
                print(f'\r{fmt.name}: chunks {done}/{len(tasks)}', end='', file=log, flush=True)
        print(file=log)
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
    print(f'{out}: {z - a} frames {fmt.width}x{fmt.height}, {jobs} jobs: warm {t_warm:.1f}s, '
          f'frames+encode {t1 - t0:.1f}s, mux {t2 - t1:.1f}s, total {t2 - t0:.1f}s', file=log)
    return out
