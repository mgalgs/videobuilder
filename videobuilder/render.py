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

from .film import Audio, DEFAULT_LOUDNESS, Film, load  # noqa: F401  (Audio, Film: the old import path)


# Sample-peak ceiling for the limiter. True peak runs above sample peak, and the
# AAC encode lifts it further; -3 dBFS keeps the decoded MP4 under -1 dBTP.
PEAK_CEILING_DB = -3.0
# Most the limiter may take off the loudest peak. Past a dB or two it stops
# catching transients and compresses the mix, and its release audibly pumps;
# a track too peaky to reach the target this way stays quieter instead.
MAX_LIMITING_DB = 1.0
# More the limiter may take off a sound effect's peaks (`vb.sfx`) than off the
# music's or speech's: a click or a hit is a few ms to a few hundred, so the
# music under it dips for that long, as under a sidechain, rather than a film
# with sound effects coming out quieter by as much as they are peakier.
SFX_LIMITING_DB = 4.0


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


def _parse_summary(stderr):
    summary = stderr.rsplit('Summary:', 1)[-1]
    loud = float(re.search(r'I:\s*(-?inf|-?[\d.]+) LUFS', summary).group(1))
    peak = float(re.search(r'Peak:\s*(-?inf|-?[\d.]+) dBFS', summary).group(1))
    # ebur128 reports silence as -70 LUFS: never boost near-silence.
    if not math.isfinite(loud) or loud <= -69:
        return None
    return loud, peak


def measure(path, filters):
    """(integrated LUFS, sample peak dBFS) after `filters`; None for silence."""
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af',
                             f'{filters},ebur128=peak=sample', '-f', 'null', '-'],
                            capture_output=True, text=True, check=True)
    return _parse_summary(result.stderr)


def measure_graph(inputs, graph, label):
    """Like `measure`, over a filter_complex `graph` (ending in `[label]`) fed by
    `inputs`, for a mix of several files rather than one."""
    cmd = ['ffmpeg', '-hide_banner', '-nostats']
    for p in inputs:
        cmd += ['-i', p]
    cmd += ['-filter_complex', f'{graph};[{label}]ebur128=peak=sample[__measure]',
            '-map', '[__measure]', '-f', 'null', '-']
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return _parse_summary(result.stderr)


def limiter_suffix(gain):
    """`gain`, then a lookahead limiter that touches only the transients above the
    ceiling; the body of the mix keeps its dynamics. latency=1 removes the
    lookahead delay, which would put sound behind picture."""
    limit = 10 ** (PEAK_CEILING_DB / 20)
    return f'volume={gain:.2f}dB,alimiter=limit={limit:.4f}:attack=5:release=50:level=0:latency=1'


def normalise(filters, gain):
    """`filters`, then one gain to the loudness target through `limiter_suffix`."""
    return f'{filters},{limiter_suffix(gain)}'


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


def loudness_gain_graph(inputs, graph, label, target, bed=None):
    """Like `loudness_gain`, over a filter_complex `graph` fed by `inputs`.
    `bed`, (inputs, graph, label) of the same mix without its sound effects,
    lets the limiter take up to `SFX_LIMITING_DB` more off the sound effects'
    peaks, but no more than `MAX_LIMITING_DB` off the bed's."""
    m = measure_graph(inputs, graph, label)
    if m is None:
        return 0.0
    loud, peak = m
    cap = PEAK_CEILING_DB + MAX_LIMITING_DB - peak
    if bed is not None:
        b = measure_graph(*bed)
        cap += SFX_LIMITING_DB
        if b is not None:
            cap = min(cap, PEAK_CEILING_DB + MAX_LIMITING_DB - b[1])
    gain = target - loud
    if gain < cap:
        g2 = f'{graph};[{label}]{limiter_suffix(gain)}[__gained]'
        gain += target - measure_graph(inputs, g2, '__gained')[0]
    return min(gain, cap)


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


def ensure_has_audio(paths):
    """Raise a clear ValueError for any path with no audio stream, rather than
    letting ffmpeg mux in silence for it."""
    for p in dict.fromkeys(paths):  # unique, order-preserving
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                                 'stream=index', '-of', 'csv=p=0', p], capture_output=True, text=True)
        if not result.stdout.strip():
            raise ValueError(f'{p}: no audio stream')


def duck_envelope_expr(sounds, fps, offset):
    """An ffmpeg eval expression, 0..1, that is 1 while any sound plays (ramping
    over its fade frames) and 0 elsewhere: a deterministic function of the
    sounds' spans, evaluated at `t` seconds from film frame `offset`."""
    terms = []
    for s in sounds:
        t0 = (s.at - offset) / fps
        t1 = (s.at + s.frames - offset) / fps
        fade_in = max(s.fade_in_frames / fps, 1e-6)
        fade_out = max(s.fade_out_frames / fps, 1e-6)
        rise = f'clip((t-{t0:.6f})/{fade_in:.6f},0,1)'
        fall = f'clip(({t1:.6f}-t)/{fade_out:.6f},0,1)'
        terms.append(f'min({rise},{fall})')
    expr = terms[0]
    for t in terms[1:]:
        expr = f'max({expr},{t})'
    return expr


def music_chain(film, a, z, idx):
    """The filter_complex statement for the film's music over frames a..z, input
    `idx`, ducked under any sound when `Audio.duck_db` is set."""
    au = film.audio
    filt = audio_filters(film, a, z)
    speech = ducking(film.sounds)
    if au.duck_db and speech:
        filt += duck_filter(au.duck_db, speech, film.fps, a)
    return f'[{idx}:a]{filt}[music]', 'music'


def ducking(sounds):
    """The sounds the music ducks under: every one but the sound effects."""
    return [s for s in sounds if s.ducks]


def dips(sound, duck_db, speech, fps, offset):
    """The `duck_filter` a sound that doesn't duck the music (a sound
    effect) gets: it dips with the music under `speech`, unless `through`."""
    if sound.ducks or getattr(sound, 'through', False) or not duck_db or not speech:
        return ''
    return duck_filter(duck_db, speech, fps, offset)


def duck_filter(duck_db, sounds, fps, offset):
    """`,volume=...`: a gain that drops by `duck_db` while any of `sounds` plays,
    from `duck_envelope_expr`. Appended to a chain whose `t` is seconds from
    film frame `offset`."""
    envelope = duck_envelope_expr(sounds, fps, offset)
    gain_expr = f'pow(10,({duck_db}*({envelope}))/20)'
    return f",volume=eval=frame:volume='{gain_expr}'"


def sound_chain(sound, a, z, fps, idx, after=''):
    """The filter_complex statement placing `sound` at its frame in a..z, input
    `idx`; None when its span doesn't reach into a..z at all. `after` is more
    filters for the placed sound, where `t` is seconds from frame `a` (a
    `duck_filter`, say)."""
    ds, de = max(sound.at, a), min(sound.at + sound.frames, z)
    if de <= ds:
        return None
    src_start = sound.start + (ds - sound.at) / fps
    # A negative start: the file begins that long after frame ds.
    pad = max(0.0, -src_start)
    src_start += pad
    dur = (de - ds) / fps - pad
    if dur <= 0:
        return None
    delay_ms = round(((ds - a) / fps + pad) * 1000)
    fades = []
    if ds == sound.at and sound.fade_in_frames:
        fades.append(f'afade=t=in:st=0:d={sound.fade_in_frames / fps:.6f}')
    if de == sound.at + sound.frames and sound.fade_out_frames:
        st = max(dur - sound.fade_out_frames / fps, 0)
        fades.append(f'afade=t=out:st={st:.6f}:d={sound.fade_out_frames / fps:.6f}')
    fade = (',' + ','.join(fades)) if fades else ''
    label = f's{idx}'
    # asetpts after adelay: given a first frame atrim cut short (any `start` off
    # a frame boundary), adelay emits frames with no timestamps, and the apad and
    # atrim after it then end the sound early (or amix stretches the mix).
    chain = (f'[{idx}:a]atrim=start={src_start:.6f}:end={src_start + dur:.6f},asetpts=PTS-STARTPTS'
             f'{fade},volume={sound.gain_db}dB,adelay={delay_ms}:all=1,asetpts=N/SR/TB,'
             f'apad,atrim=end={(z - a) / fps:.6f}{after}[{label}]')
    return chain, label


# More non-ducking placements than this with the same `after` filters (none,
# or one dip) are mixed in-process into one stem (`stem.stem`) instead of a
# branch apiece.
PREMIX_OVER = 16


def sound_branches(branches, a, z, fps, idx):
    """(inputs, chains, labels) placing every (sound, after) of `branches` in
    a..z (see `sound_chain`), from ffmpeg input `idx`. More than
    `PREMIX_OVER` sounds that don't duck and share an `after` are summed
    in-process into one WAV (`stem`), the same samples as their branches,
    with `after` applied once to the sum: hundreds of sound effects are one
    input, not hundreds."""
    from . import stem
    # Ducking sounds (speech, footage) keep a branch: a stem decodes from the
    # first sample, where atrim honours an mp4's audio start time, and a
    # branch streams only the span it plays.
    groups = {}
    for s, after in branches:
        if not s.ducks:
            groups.setdefault(after, []).append(s)
    inputs, chains, labels, mixed = [], [], [], set()
    for s, after in branches:
        sounds = groups.get(after, ()) if not s.ducks else ()
        if len(sounds) > PREMIX_OVER:
            if after in mixed:
                continue
            mixed.add(after)
            label = f's{idx}'
            inputs.append(stem.stem(sounds, a, z, fps))
            # A WAV is read in frames of thousands of samples, and a dip's gain is
            # evaluated once a frame: 10 ms frames ramp it about as finely as a branch.
            chains.append(f'[{idx}:a]asetnsamples=n=480:p=0{after}[{label}]' if after else f'[{idx}:a]anull[{label}]')
            labels.append(label)
            idx += 1
            continue
        branch = sound_chain(s, a, z, fps, idx, after)
        if branch is None:
            continue
        inputs.append(s.path), chains.append(branch[0]), labels.append(branch[1])
        idx += 1
    return inputs, chains, labels


def mix_graph(film, a, z, start_idx=0, effects=True):
    """(inputs, filter_complex graph, output label) mixing the film's music and
    sounds over frames a..z, before any final gain and limiting. `start_idx` is
    the ffmpeg input index of the first file this graph refers to (1 when a
    video is `-i`'d first, as in the final render; 0 for a standalone measure).
    `effects=False` leaves the sound effects out (`vb.sfx`: the sounds that
    don't duck the music)."""
    au = film.audio
    inputs, chains, labels = [], [], []
    idx = start_idx
    if au:
        chain, label = music_chain(film, a, z, idx)
        inputs.append(au.path), chains.append(chain), labels.append(label)
        idx += 1
    speech = ducking(film.sounds)
    branches = [(s, dips(s, au.duck_db if au else 0, speech, film.fps, a)) for s in (film.sounds if effects else speech)]
    more = sound_branches(branches, a, z, film.fps, idx)
    inputs += more[0]
    graph, mix_label = join_mix(chains + more[1], labels + more[2], (z - a) / film.fps)
    return inputs, graph, mix_label


def join_mix(chains, labels, seconds):
    """(graph, output label): the filter_complex `chains` with their outputs
    `labels` summed by `amix` (no normalising: each branch keeps its gain), or
    `seconds` of silence when there are none."""
    chains, labels = list(chains), list(labels)
    if not labels:
        chains.append(f'anullsrc=channel_layout=stereo:sample_rate=48000,atrim=end={seconds:.6f}[mix0]')
        labels = ['mix0']
    if len(labels) > 1:
        joined = ''.join(f'[{l}]' for l in labels)
        chains.append(f'{joined}amix=inputs={len(labels)}:normalize=0:dropout_transition=0[mix]')
        mix_label = 'mix'
    else:
        mix_label = labels[0]
    return ';'.join(chains), mix_label


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
    if film.sounds:
        ensure_has_audio(s.path for s in film.sounds)
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
        if film.sounds:
            graph_inputs, graph, label = mix_graph(film, a, z, start_idx=1)
            target = au.loudness if au else film.loudness
            if target is not None:
                # Measured over the whole film, so a partial render gets the same gain.
                whole_inputs, whole_graph, whole_label = mix_graph(film, 0, film.frames)
                bed = mix_graph(film, 0, film.frames, effects=False) if any(not s.ducks for s in film.sounds) else None
                gain = loudness_gain_graph(whole_inputs, whole_graph, whole_label, target, bed)
                suffix = limiter_suffix(gain)
            else:
                suffix = 'anull'
            cmd += [f for p in graph_inputs for f in ('-i', p)]
            cmd += ['-filter_complex', f'{graph};[{label}]{suffix}[a]',
                    '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000']
        elif au:
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
