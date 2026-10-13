"""Render a film: frames in parallel chunks, each chunk piped to its own ffmpeg,
then the chunks concatenated (no re-encode) and the audio muxed in.

Every frame is drawn on its own (`draw(n, canvas)` is pure), so chunks render
in any order on any worker.
"""
import multiprocessing as mp
import math
import os
import re
import subprocess
import sys
import tempfile
import time

from .film import Audio, Film, load  # noqa: F401  (Audio, Film: the old import path)


# Sample-peak ceiling for the limiter. True peak runs above sample peak, and the
# AAC encode lifts it further; -3 dBFS keeps the decoded MP4 under -1 dBTP.
PEAK_CEILING_DB = -3.0
# Most the limiter may take off the loudest peak. Past a dB or two it stops
# catching transients and compresses the mix, and its release audibly pumps;
# a track too peaky to reach the target this way stays quieter instead.
MAX_LIMITING_DB = 1.0


def default_jobs(cpu_max='/sys/fs/cgroup/cpu.max'):
    """Worker processes for this machine or container. Not os.cpu_count(): that
    is the host's count and ignores a cgroup CPU quota."""
    jobs = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count() or 1
    try:
        with open(cpu_max) as fh:
            quota, period = fh.read().split()[:2]
        if quota != 'max':
            jobs = min(jobs, max(1, math.ceil(int(quota) / int(period))))
    except (OSError, ValueError):
        pass
    return jobs


def measure(path, filters):
    """(integrated LUFS, sample peak dBFS) after `filters`; None for silence."""
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af',
                             f'{filters},ebur128=peak=sample', '-f', 'null', '-'],
                            capture_output=True, text=True, check=True)
    summary = result.stderr.rsplit('Summary:', 1)[-1]
    loud = float(re.search(r'I:\s*(-?inf|-?[\d.]+) LUFS', summary).group(1))
    peak = float(re.search(r'Peak:\s*(-?inf|-?[\d.]+) dBFS', summary).group(1))
    # ebur128 reports silence as -70 LUFS: never boost near-silence.
    if not math.isfinite(loud) or loud <= -69:
        return None
    return loud, peak


def loudness_gain(path, filters, target):
    """dB to add after `filters` toward `target` integrated LUFS, capped so the
    limiter takes at most MAX_LIMITING_DB off the loudest peak; 0 for silence."""
    m = measure(path, filters)
    if m is None:
        return 0.0
    loud, peak = m
    cap = PEAK_CEILING_DB + MAX_LIMITING_DB - peak
    gain = target - loud
    if gain < cap:  # the limiter shaves a little loudness off; measure again through it
        gain += target - measure(path, normalise(filters, gain))[0]
    return min(gain, cap)


def normalise(filters, gain):
    """One gain to the loudness target, then a lookahead limiter that touches only
    the transients above the ceiling; the body of the mix keeps its dynamics.
    latency=1 removes the lookahead delay, which would put sound behind picture."""
    limit = 10 ** (PEAK_CEILING_DB / 20)
    return (f'{filters},volume={gain:.2f}dB,'
            f'alimiter=limit={limit:.4f}:attack=5:release=50:level=0:latency=1')


def audio_filters(film, a, z):
    """The ffmpeg filter chain that cuts the film's audio to frames a..z."""
    au = film.audio
    trim = (au.trim_frames + a) / film.fps
    fade = ''
    if au.fade_out_frames:
        st = (film.frames - 1 - au.fade_out_frames - a) / film.fps
        fade = f',afade=t=out:st={st:.6f}:d={au.fade_out_frames / film.fps:.6f}'
    return (f'atrim=start={trim:.6f},asetpts=PTS-STARTPTS,volume={au.gain_db}dB{fade},'
            f'apad,atrim=end={(z - a) / film.fps:.6f}')


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


def render(film, out, format=None, jobs=None, chunk=15, crf=18, frames=None, log=sys.stderr, stall=600):
    """Render `film` (a Film or a film file path) in `format` to the MP4 `out`.
    `stall`: seconds to wait for the next chunk before giving up with an error
    that names the chunks still pending (a worker stuck in `draw`, say)."""
    if isinstance(film, (str, os.PathLike)):
        film = load(film)
    fmt = film.format(format)
    a, z = frames or (0, film.frames)
    if not 0 <= a < z <= film.frames:
        raise ValueError(f'frames {a}:{z} outside 0:{film.frames}')
    jobs = jobs or default_jobs()
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
        tty = getattr(log, 'isatty', lambda: False)()
        step = max(1, len(tasks) // 10)
        ctx = mp.get_context('fork')
        with ctx.Pool(jobs) as pool:
            done, pending = 0, {t[0]: t[1] for t in tasks}
            results = pool.imap_unordered(_encode_chunk, tasks)
            for _ in tasks:
                try:
                    first, _ = results.next(timeout=stall)
                except mp.TimeoutError:
                    stuck = ', '.join(f'{p}-{e - 1}' for p, e in sorted(pending.items()))
                    raise RuntimeError(f'render stalled: no chunk finished in {stall:g} s; frames still pending: '
                                       f'{stuck}. Try `still` on one of them to see where draw hangs.') from None
                del pending[first]
                done += 1
                if tty:
                    print(f'\r{fmt.name}: chunks {done}/{len(tasks)}', end='', file=log, flush=True)
                elif done % step == 0 or done == len(tasks):  # a log file: a line every tenth
                    print(f'{fmt.name}: chunks {done}/{len(tasks)}', file=log, flush=True)
        if tty:
            print(file=log)
        t1 = time.time()
        listing = os.path.join(tmp, 'list.txt')
        with open(listing, 'w') as fh:
            fh.writelines(f"file '{t[2]}'\n" for t in tasks)
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', listing]
        au = film.audio
        if au:
            filters = audio_filters(film, a, z)
            if au.loudness is not None:
                # Measured over the whole film, so a partial render gets the same gain.
                whole = audio_filters(film, 0, film.frames)
                filters = normalise(filters, loudness_gain(au.path, whole, au.loudness))
            cmd += ['-i', au.path, '-filter_complex', f'[1:a]{filters}[a]',
                    '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
        cmd += ['-c:v', 'copy', '-movflags', '+faststart', out]
        subprocess.run(cmd, check=True)
    t2 = time.time()
    print(f'{out}: {z - a} frames {fmt.width}x{fmt.height}, {jobs} jobs: warm {t_warm:.1f}s, '
          f'frames+encode {t1 - t0:.1f}s, mux {t2 - t1:.1f}s, total {t2 - t0:.1f}s', file=log)
    return out
