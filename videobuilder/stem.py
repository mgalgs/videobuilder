"""Many sounds mixed in-process into one WAV stem, for `render.sound_branches`.

ffmpeg gives every `-i` its own demuxer and decoder and every `amix` input
its own full-length stream, so a film with hundreds of sound effects (a
typed log's key clicks) is hundreds of inputs and branches, and ffmpeg runs
out of memory or time. A stem decodes each distinct file once and adds every
placement into one buffer, reproducing `render.sound_chain` to the sample:
its atrim, afade, volume, adelay, apad and atrim, each time read to the
microsecond and rescaled to samples the way ffmpeg rounds them.

A stem is cached by a hash of what went in (each file's path, size and
mtime, every placement, the range), so measuring the mix and rendering it
mix it once.
"""
import array
import hashlib
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

RATE = 48000
CHANNELS = 2
VERSION = 1
# Stems kept, newest first; older ones are removed when a new stem is written.
KEEP_BYTES = 1 << 30
ENV = 'VIDEOBUILDER_STEM_DIR'


def cache_dir():
    """$VIDEOBUILDER_STEM_DIR, else the user's cache, else the temp dir."""
    d = os.environ.get(ENV)
    if d:
        return Path(d).expanduser()
    return Path(os.environ.get('XDG_CACHE_HOME') or '~/.cache').expanduser() / 'videobuilder' / 'stems'


def samples(seconds):
    """`seconds` as ffmpeg reads it from a filter option written `:.6f`
    (whole microseconds), in samples, rounded half away from zero as
    `av_rescale` does."""
    us = int(round(float(f'{seconds:.6f}') * 1_000_000))
    q, r = divmod(abs(us) * RATE, 1_000_000)
    n = q + (1 if 2 * r >= 1_000_000 else 0)
    return n if us >= 0 else -n


_decoded = {}


def _decode(path):
    """`path` as interleaved stereo float samples at RATE, decoded once a process."""
    from .sfx import decode
    st = os.stat(path)
    k = (os.path.realpath(path), st.st_size, st.st_mtime_ns)
    if k not in _decoded:
        _decoded[k] = decode(path, channels=CHANNELS, rate=RATE)
    return _decoded[k]


def placement(sound, a, z, fps):
    """(source first sample, source end sample, delay samples, fade-in
    samples, fade-out start and samples), all per channel, of `sound` over
    frames a..z, as `render.sound_chain` writes them for ffmpeg; None when
    it plays nothing there."""
    ds, de = max(sound.at, a), min(sound.at + sound.frames, z)
    if de <= ds:
        return None
    src_start = sound.start + (ds - sound.at) / fps
    pad = max(0.0, -src_start)
    src_start += pad
    dur = (de - ds) / fps - pad
    if dur <= 0:
        return None
    delay = round(((ds - a) / fps + pad) * 1000) * RATE // 1000
    fade_in = samples(sound.fade_in_frames / fps) if ds == sound.at and sound.fade_in_frames else 0
    fade_out = None
    if de == sound.at + sound.frames and sound.fade_out_frames:
        st = max(dur - sound.fade_out_frames / fps, 0)
        fade_out = (samples(st), samples(sound.fade_out_frames / fps))
    return samples(src_start), samples(src_start + dur), delay, fade_in, fade_out


def _gains(n, fade_in, fade_out):
    """Per-sample gains of a placed sound's `n` samples: afade's linear ('tri')
    ramps, None where a sample keeps its level."""
    g = [None] * n
    if fade_in:
        for k in range(min(n, fade_in)):
            g[k] = k / fade_in
    if fade_out:
        st, d = fade_out
        for k in range(max(0, st), n):
            g[k] = (min(1.0, max(0.0, (d - (k - st)) / d)) if d else 0.0) * (1.0 if g[k] is None else g[k])
    return g


def mix(sounds, a, z, fps):
    """The placed `sounds` over frames a..z, summed: interleaved stereo float
    samples at RATE, as `amix` of their `render.sound_chain`s gives them."""
    total = samples((z - a) / fps)
    out = array.array('f', bytes(4 * CHANNELS * total))
    pieces = {}   # a key clicked a hundred times is cut and faded once
    for s in sounds:
        p = placement(s, a, z, fps)
        if p is None:
            continue
        first, end, delay, fade_in, fade_out = p
        src = _decode(s.path)
        n = min(min(end, len(src) // CHANNELS) - first, total - delay)
        if n <= 0:
            continue
        cut = (s.path, first, n, s.gain_db, fade_in, fade_out)
        if cut not in pieces:
            pieces[cut] = _piece(src, first, n, s.gain_db, fade_in, fade_out)
        lo, hi = delay * CHANNELS, (delay + n) * CHANNELS
        out[lo:hi] = array.array('f', map(float.__add__, out[lo:hi], pieces[cut]))
    return out


def _piece(src, first, n, gain_db, fade_in, fade_out):
    """`n` samples of `src` from `first`, faded, then at `gain_db`."""
    vol = 10 ** (gain_db / 20)
    piece = src[first * CHANNELS:(first + n) * CHANNELS]
    gains = _gains(n, fade_in, fade_out)
    if any(g is not None for g in gains):
        scale = [vol if g is None else g * vol for g in gains for _ in range(CHANNELS)]
        return array.array('f', map(float.__mul__, piece, scale))
    if vol != 1:
        return array.array('f', (x * vol for x in piece))
    return piece


def key(sounds, a, z, fps):
    """A hash of everything a stem's samples depend on."""
    def file(path):
        st = os.stat(path)
        return os.path.realpath(path), st.st_size, st.st_mtime_ns
    parts = [VERSION, a, z, fps] + [(file(s.path), s.at, s.start, s.frames, s.gain_db, s.fade_in_frames,
                                     s.fade_out_frames) for s in sounds]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:32]


def wav_bytes(pcm):
    """A 32-bit float WAV of interleaved stereo `pcm` at RATE."""
    data = pcm.tobytes() if sys.byteorder == 'little' else _swapped(pcm)
    fmt = struct.pack('<HHIIHH', 3, CHANNELS, RATE, RATE * CHANNELS * 4, CHANNELS * 4, 32)
    return (b'RIFF' + struct.pack('<I', 4 + 8 + len(fmt) + 8 + len(data)) + b'WAVE' +
            b'fmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(data)) + data)


def _swapped(pcm):
    c = array.array('f', pcm)
    c.byteswap()
    return c.tobytes()


def stem(sounds, a, z, fps):
    """The path of a WAV of `sounds` mixed over frames a..z (`mix`), written
    once and found again by `key`."""
    name = key(sounds, a, z, fps) + '.wav'
    data = None
    for d in (cache_dir(), Path(tempfile.gettempdir()) / 'videobuilder-stems'):
        path = d / name
        try:
            if path.exists():
                os.utime(path)
                return str(path)
            d.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f'{name}.{os.getpid()}.tmp')
            data = data or wav_bytes(mix(sounds, a, z, fps))
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError:
            continue
        _prune(d, keep=path)
        return str(path)
    raise OSError(f'nowhere to write a sound stem: {cache_dir()} and the temp dir are not writable')


def _prune(d, keep):
    """Removes the least recently used stems past KEEP_BYTES."""
    try:
        stems = sorted(((p.stat().st_mtime, p.stat().st_size, p) for p in d.glob('*.wav')), reverse=True)
    except OSError:
        return
    used = 0
    for _, size, p in stems:
        used += size
        if used > KEEP_BYTES and p != keep:
            try:
                p.unlink()
            except OSError:
                pass
