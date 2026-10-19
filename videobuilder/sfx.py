"""Sound effects: a bank of ready-made sounds, each put on an exact frame.

    WHOOSH = vb.sfx.sound('whoosh_fast/tight', at=45, dur=0.5)      # its peak on frame 45
    TAP = vb.sfx.sound('fit/click/floss_lid', at=90, gain_db=-8)    # quieter than the music's hits
    DING = vb.sfx.sound('pro_notify/ding_2045', at=120, note='G5')  # a tuned sound, by note
    FILM = vb.Film(..., sounds=(WHOOSH, TAP, DING))

    vb.sfx.find('whoosh', near_dur=0.8)     # the bank's whooshes, the nearest length first
    vb.sfx.roles()                          # whoosh, hit, click, tap, pop, riser, ...

The sounds are earshot's bank (https://github.com/Leonxlnx/earshot, MIT, by
Leon Lin): sounds made in code and fitted from CC0 recordings, rendered once
to Opus files with every take's onset, peak and end measured on the file as
shipped. They come as one pack, `vb-sfx-1.tar`, kept outside the repo:

    python -m videobuilder sfx fetch             # download, check its sha256, unpack
    python -m videobuilder sfx list [--role R]   # what is in it
    python -m videobuilder sfx play-path ID[--VARIANT]

It is found in `$VIDEOBUILDER_SFX_DIR` (the editor's image sets
/opt/vb-sfx), else `~/.cache/videobuilder/vb-sfx-1`. The pack's pinned
sha256 is `PIN_FILE` (videobuilder/sfx-pack.sha256), read by `sfx fetch`
and by deploy/Dockerfile alike.

A sound lands by its **peak** (default: a whoosh peaks on the cut, a hit on
the impact frame) or its **onset**, `align='onset'`. A sound with several
lengths takes the one nearest `dur`, trimmed with a short fade when it is
longer; a tuned sound takes `note`. Every placed sound is a `Sfx`, a
`vb.Sound` that knows where it was asked to land, for `check.py --video`
(`sync`). Sound effects mix with the film's other sound and dip under its
speech as the music does (`Audio.duck_db`), unless `through=True`.
`at` is a frame of the film: a `Film` places its sounds again at its own
fps, so `fps=` matters only for a sound used outside one.
"""
import argparse
import array
import difflib
import hashlib
import json
import math
import operator
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .film import Sound

PACK = 'vb-sfx-1'
PACK_URL = 'https://github.com/mgalgs/videobuilder/releases/download/sfx-bank-1/vb-sfx-1.tar'
ENV = 'VIDEOBUILDER_SFX_DIR'
SCHEMA = 1
# `<sha256>  vb-sfx-1.tar`, as `sha256sum -c` reads it. All zeros until the pack is published.
PIN_FILE = Path(__file__).with_name('sfx-pack.sha256')
PLACEHOLDER = '0' * 64
RATE = 48000
ALIGNS = ('peak', 'onset')
TRIM_FADE_S = 0.15        # the longest fade on a sound cut shorter than its take
FETCH_TIMEOUT = 60


class SfxUnavailable(RuntimeError):
    """The pack isn't installed where videobuilder looks for it."""


def pack_dir():
    """Where the pack is (or goes): $VIDEOBUILDER_SFX_DIR, else the user's cache."""
    d = os.environ.get(ENV)
    if d:
        return Path(d).expanduser()
    return Path(os.environ.get('XDG_CACHE_HOME') or '~/.cache').expanduser() / 'videobuilder' / PACK


def missing_message(where):
    return (f'the sound-effects pack is not installed: no {where}/index.json. '
            f'Run `python -m videobuilder sfx fetch` (or set ${ENV} to an unpacked {PACK})')


def pinned_sha256():
    """The pack's sha256 from `PIN_FILE`; `PLACEHOLDER` until it is published."""
    return PIN_FILE.read_text().split()[0].lower()


# ---- notes ----
_NOTE = re.compile(r'^([A-Ga-g])(#|s|♯|b|♭)?(-?\d)$')
_SEMI = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_NAMES = ('C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B')


def note_name(note):
    """A note as the pack names it: 'C#5', 'Cs5' and 'Db5' are all 'Cs5'."""
    m = _NOTE.match(str(note).strip())
    if not m:
        raise ValueError(f'{note!r} is not a note; write it like C5, F#4, Fs4 or Eb6')
    letter, acc, octave = m.group(1).upper(), m.group(2), int(m.group(3))
    midi = 12 * (octave + 1) + _SEMI[letter] + {'#': 1, 's': 1, '♯': 1, 'b': -1, '♭': -1}.get(acc, 0)
    return f'{_NAMES[midi % 12]}{midi // 12 - 1}'


def _note_midi(name):
    m = _NOTE.match(name)
    return 12 * (int(m.group(3)) + 1) + _NAMES.index(m.group(1).upper() + ('s' if m.group(2) else ''))


# ---- the pack ----
@dataclass(frozen=True)
class Take:
    """One file of the pack: a sound's base take, or one of its variants (a
    length, `length_s`, or a note). Times are seconds into the file."""
    id: str
    variant: str | None
    path: str
    dur_s: float
    onset_s: float
    peak_s: float
    end_s: float
    peak_db: float
    lufs_m_max: float | None = None
    length_s: float | None = None
    note: str | None = None

    @property
    def name(self):
        """The id, with `--variant` when it is one: what `sfx play-path` takes."""
        return self.id + (f'--{self.variant}' if self.variant else '')

    def sync_s(self, align='peak'):
        if align not in ALIGNS:
            raise ValueError(f'align must be one of {", ".join(ALIGNS)}, not {align!r}')
        return self.peak_s if align == 'peak' else self.onset_s

    def sound(self, at, fps=30, align='peak', gain_db=0.0, dur=None, through=False):
        """This take as a `Sfx` with its peak (or onset) on film frame `at`,
        cut to `dur` seconds with a short fade when `dur` is shorter than it."""
        sync = self.sync_s(align)
        first, start = placement(sync, at, fps)
        play, fade = self.dur_s, 0
        if dur is not None and dur < self.dur_s:
            if dur <= sync:
                raise ValueError(f'{self.name}: dur {dur:g} s would cut it before its {align} at {sync:.3f} s')
            play = dur
        frames = max(1, math.ceil((play - start) * fps - 1e-9))
        if play < self.dur_s:
            fade = max(1, round(min(TRIM_FADE_S, play / 4) * fps))
            fade = max(1, min(fade, first + frames - at - 1))   # the fade starts after the sync point
        return Sfx(self.path, at=first, start=start, frames=frames, gain_db=gain_db, fade_in_frames=0,
                   fade_out_frames=fade, effect=self.id, variant=self.variant, align=align, mark=at,
                   sync_s=sync, through=through, fps=fps, take=self, dur=dur)


@dataclass(frozen=True)
class Effect:
    """A sound in the bank, with its takes (`takes`: the base take and its
    length or note variants)."""
    id: str
    category: str
    role: str
    family: str
    about: str
    takes: tuple
    credit: dict | None = None

    @property
    def lengths(self):
        """The takes chosen by length: the base and the length variants."""
        return tuple(t for t in self.takes if t.note is None)

    @property
    def notes(self):
        return tuple(t.note for t in self.takes if t.note)

    @property
    def tuned(self):
        return bool(self.notes)

    def nearest_length(self, dur):
        """The take whose length is nearest `dur` seconds (the longer of two as near)."""
        if not self.lengths:
            raise ValueError(f'{self.id} has only notes: pick one with note= ({", ".join(self.notes)})')
        return min(self.lengths, key=lambda t: (abs((t.length_s or t.dur_s) - dur), -(t.length_s or t.dur_s)))

    def take(self, variant=None, dur=None, note=None):
        """The take for `variant` (its name: '0.8s', 'C5'), else for `note`,
        else the length nearest `dur`, else the base take."""
        if variant is not None:
            for t in self.takes:
                if t.variant == variant or (t.note and t.note == _try_note(variant)):
                    return t
            have = ', '.join(t.variant for t in self.takes if t.variant) or 'none'
            raise ValueError(f'{self.id} has no variant {variant!r}; it has {have}')
        if note is not None:
            name = note_name(note)
            for t in self.takes:
                if t.note == name:
                    return t
            if not self.notes:
                raise ValueError(f'{self.id} is not tuned: it has no notes')
            near = min(self.notes, key=lambda n: abs(_note_midi(n) - _note_midi(name)))
            raise ValueError(f'{self.id} has no {name} (nearest: {near}); its notes: {", ".join(self.notes)}')
        if dur is not None:
            return self.nearest_length(dur)
        base = [t for t in self.takes if t.variant is None]
        return base[0] if base else (self.lengths or self.takes)[0]

    def sound(self, at, fps=30, align='peak', gain_db=0.0, variant=None, dur=None, note=None, through=False):
        """This sound as a `Sfx` with its peak (or onset) on film frame `at`; see `Take.sound`."""
        return self.take(variant, dur, note).sound(at, fps, align, gain_db, dur, through)


def _try_note(s):
    try:
        return note_name(s)
    except ValueError:
        return None


def role_key(role):
    return ' '.join(str(role).lower().replace('_', ' ').replace('-', ' ').split())


class Bank:
    """An unpacked pack: its `index.json` and audio files."""

    def __init__(self, root):
        self.root = Path(root)
        index = self.root / 'index.json'
        if not index.is_file():
            raise SfxUnavailable(missing_message(self.root))
        doc = json.loads(index.read_text(encoding='utf-8'))
        if doc.get('schema') != SCHEMA:
            raise SfxUnavailable(f'{index}: pack schema {doc.get("schema")!r}, this videobuilder reads {SCHEMA}; '
                                 f'fetch the pack again: python -m videobuilder sfx fetch')
        self.pack = doc.get('pack')
        self.left_out = tuple(doc.get('left_out', ()))
        self.effects = {}
        for s in doc['sounds']:
            takes = tuple(Take(s['id'], v['variant'], str(self.root / v['file']), v['dur_s'], v['onset_s'],
                               v['peak_s'], v['end_s'], v['peak_db'], v.get('lufs_m_max'), v.get('length_s'),
                               v.get('note')) for v in s['variants'])
            self.effects[s['id']] = Effect(s['id'], s['category'], s['role'], s['family'], s.get('about', ''),
                                           takes, s.get('credit'))

    def get(self, id):
        """The `Effect` called `id` (an `id--variant` name gives its effect)."""
        e = self.effects.get(str(id).split('--')[0])
        if e is None:
            near = difflib.get_close_matches(str(id), list(self.effects), n=3)
            raise ValueError(f'no sound {id!r} in the pack' + (f'; did you mean {", ".join(near)}?' if near else
                                                                '; `python -m videobuilder sfx list` lists them'))
        return e

    def roles(self):
        return sorted({e.role for e in self.effects.values()})

    def find(self, role=None, near_dur=None, category=None, family=None):
        """The effects whose role (or category) is `role`, the nearest length
        to `near_dur` first when it is given, else by id."""
        found = list(self.effects.values())
        if role is not None:
            key = role_key(role)
            found = [e for e in found if e.role == key or role_key(e.category) == key]
            if not found:
                raise ValueError(f'no sounds with the role {role!r}; roles: {", ".join(self.roles())}')
        if category is not None:
            found = [e for e in found if e.category == category]
        if family is not None:
            found = [e for e in found if e.family == family]
        if near_dur is not None:
            def gap(e):
                return min((abs((t.length_s or t.dur_s) - near_dur) for t in e.lengths), default=math.inf)
            return sorted(found, key=lambda e: (gap(e), e.id))
        return sorted(found, key=lambda e: e.id)

    def take(self, name):
        """The take an `id--variant` name (`sfx play-path`'s) names."""
        id, _, variant = str(name).partition('--')
        return self.get(id).take(variant or None)


_banks = {}


def bank(root=None):
    """The pack at `root` (default `pack_dir()`), read once."""
    root = Path(root) if root is not None else pack_dir()
    index = root / 'index.json'
    try:
        key = (str(root.resolve()), index.stat().st_mtime_ns)
    except OSError:
        raise SfxUnavailable(missing_message(root)) from None
    if key not in _banks:
        _banks[key] = Bank(root)
    return _banks[key]


def get(id):
    return bank().get(id)


def find(role=None, near_dur=None, category=None, family=None):
    """`vb.sfx.find('whoosh', near_dur=0.8)`: see `Bank.find`."""
    return bank().find(role, near_dur, category, family)


def roles():
    return bank().roles()


def sound(id, at, fps=30, align='peak', gain_db=0.0, variant=None, dur=None, note=None, through=False):
    """The bank's sound `id` as a `Sfx` with its peak (or `align='onset'`)
    on film frame `at`, `gain_db` from its take's level (each take peaks at
    -1 dBFS). `variant` names a take ('0.8s', 'C5'); `dur` picks the nearest
    length and cuts it to `dur` s with a short fade if longer; `note` picks a
    tuned sound's note. `through=True` keeps it at its level under speech."""
    return bank().get(id).sound(at, fps, align, gain_db, variant, dur, note, through)


# ---- placing a sound on a frame ----
def placement(sync_s, at, fps):
    """(first frame, start): the film frame a sound's span starts on, and the
    seconds into its file playing then, so the point `sync_s` seconds into
    the file plays at frame `at`. `start` is never positive: the file starts
    `-start` seconds after the first frame (less than a frame), so nothing
    before the sync point is cut."""
    lead = math.ceil(sync_s * fps - 1e-9)
    return at - lead, sync_s - lead / fps


@dataclass
class Sfx(Sound):
    """A bank sound placed on the film: a `vb.Sound` (a negative `start`
    delays the file by that much past frame `at`) that remembers what it is
    and where its `align` point was asked to land (`mark`, a film frame;
    `sync_s`, seconds into the file). It doesn't duck the music; it dips with
    it under speech unless `through`."""
    ducks: bool = False
    effect: str = ''
    variant: str | None = None
    align: str = 'peak'
    mark: int = 0
    sync_s: float = 0.0
    through: bool = False
    fps: int | None = None
    take: Take | None = field(default=None, repr=False)
    dur: float | None = None

    def at_fps(self, fps):
        """This sound placed again for a film at `fps`, its `align` point on
        the same frame `mark` (`Film` does this, so `fps=` may be left out)."""
        if self.take is None or self.fps in (None, fps):
            return self
        return self.take.sound(self.mark, fps, self.align, self.gain_db, self.dur, self.through)


# ---- measuring a sound ----
def decode(path, channels=2, rate=RATE):
    """`path`'s first sound stream as float samples (interleaved `channels`)."""
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-ac', str(channels),
                             '-ar', str(rate), '-f', 'f32le', '-'], capture_output=True)
    if result.returncode:
        raise ValueError(f'{path}: ffmpeg cannot read its sound: {result.stderr.decode(errors="replace")[-300:]}')
    out = array.array('f')
    out.frombytes(result.stdout[:len(result.stdout) // 4 * 4])
    if sys.byteorder != 'little':
        out.byteswap()
    return out


def envelope(samples, channels=1, rate=RATE, ms=1):
    """Mean power of every `ms` milliseconds of `samples`, over all channels."""
    step = rate * ms // 1000 * channels
    mul = operator.mul
    return [sum(map(mul, b, b)) / len(b) for b in
            (samples[i:i + step] for i in range(0, len(samples) - step + 1, step))]


PEAK_DB = 1.0   # the stretch around a sound's loudest 5 ms that its peak is the middle of


def measure(samples, channels=2, rate=RATE):
    """{dur_s, onset_s, peak_s, end_s, peak_db} of a sound: the onset is the
    start of the first 1 ms within 30 dB of its loudest 1 ms; the end, the
    end of its last 5 ms within 50 dB of its loudest 5 ms; the peak, the
    middle of its loudest 5 ms (1 ms steps), or of the stretch around it
    within `PEAK_DB` of it, weighted by how far over that each 5 ms is: a
    sharp hit's loudest moment, a broad swell's middle, which a re-encode
    can't move far (a sub drop's loudest 5 ms can jump 50 ms on a 0.1 dB
    ripple). Pure Python."""
    p1 = envelope(samples, channels, rate)
    if not p1 or max(p1) <= 0:
        raise ValueError('silent: nothing to measure')
    p5 = [sum(p1[i:i + 5]) / 5 for i in range(max(1, len(p1) - 4))]
    top1, top5 = max(p1), max(p5)
    onset = next(i for i, p in enumerate(p1) if p >= top1 * 1e-3)
    i = p5.index(top5)
    floor = top5 * 10 ** (-PEAK_DB / 10)
    lo, hi = i, i
    while lo > 0 and p5[lo - 1] >= floor:
        lo -= 1
    while hi + 1 < len(p5) and p5[hi + 1] >= floor:
        hi += 1
    weights = [(k, p5[k] - floor) for k in range(lo, hi + 1)]
    total = sum(w for _, w in weights)
    peak = sum(k * w for k, w in weights) / total if total > 0 else i
    end = max(k for k, p in enumerate(p5) if p >= top5 * 1e-5)
    amp = max(max(samples), -min(samples))
    return {'dur_s': round(len(samples) / channels / rate, 4), 'onset_s': onset / 1000,
            'peak_s': round((peak + 2.5) / 1000, 4), 'end_s': min(len(p1), end + 5) / 1000,
            'peak_db': round(20 * math.log10(amp), 2) if amp > 0 else -math.inf}


# ---- the sync check: is each sound effect where it was asked to be? ----
SEARCH_FRAMES = 4         # how far either side of its mark a sound is looked for
# A sound whose fit on its mark is this good next to its best fit (`r`) is as likely there: a smooth
# envelope (a sub drop's bloom) fits several frames about as well. A sound 2 frames off fits its mark
# at 0-0.2 of its best.
SAME_FIT = 0.6
BURIED_R = 0.3            # under this, the mix buries a sound too far to say where it is
REF_BEFORE, REF_AFTER = 0.2, 0.3  # seconds of a sound around its peak that are matched


def _correlate(ref, mix, max_lag):
    """(lag, r): the shift of `ref` into `mix` (both 1 ms envelopes, `mix`
    with `max_lag` extra points either side) with the highest Pearson r."""
    n = len(ref)
    mr = sum(ref) / n
    dr = [x - mr for x in ref]
    sr = math.sqrt(sum(x * x for x in dr)) or 1e-30
    best = (0, -2.0)
    for lag in range(-max_lag, max_lag + 1):
        seg = mix[max_lag + lag:max_lag + lag + n]
        if len(seg) < n:
            continue
        ms = sum(seg) / n
        ds = [x - ms for x in seg]
        ss = math.sqrt(sum(x * x for x in ds))
        if not ss:
            continue
        r = sum(map(operator.mul, dr, ds)) / (sr * ss)
        if r > best[1] or (r == best[1] and abs(lag) < abs(best[0])):
            best = (lag, r)
    return best


def _placed(s, fps):
    """(first ms, 1 ms power envelope) of a placed sound on the film's clock, at its gain."""
    src = decode_cached(s.path)
    lo = max(0.0, s.start)
    hi = min(s.start + s.frames / fps, len(src) / RATE)
    g = 10 ** (s.gain_db / 10)
    return round((s.at / fps - s.start + lo) * 1000), [p * g for p in envelope(src[int(lo * RATE):int(hi * RATE)])]


def _fit(y, x1, x2):
    """(R^2 of y on x1, x2 and a constant; R^2 on x2 alone), x1's weight kept positive."""
    n = len(y)
    my, m1, m2 = sum(y) / n, sum(x1) / n, sum(x2) / n
    dy = [v - my for v in y]
    d1 = [v - m1 for v in x1]
    d2 = [v - m2 for v in x2]
    mul = operator.mul
    syy = sum(map(mul, dy, dy)) or 1e-30
    s11, s22, s12 = sum(map(mul, d1, d1)), sum(map(mul, d2, d2)), sum(map(mul, d1, d2))
    s1y, s2y = sum(map(mul, d1, dy)), sum(map(mul, d2, dy))
    r2_others = (s2y * s2y / s22 / syy) if s22 > 0 else 0.0
    det = s11 * s22 - s12 * s12
    if s22 <= 0 or det <= 1e-30 * s11 * s22:
        a, b = (s1y / s11 if s11 > 0 else 0.0), 0.0
    else:
        a, b = (s1y * s22 - s2y * s12) / det, (s2y * s11 - s1y * s12) / det
    if a <= 0:
        return r2_others, r2_others
    return (a * s1y + b * s2y) / syy, r2_others


def sync(mp4, sounds, fps, frames, mix=None):
    """For each `Sfx` among `sounds` (as placed in a film of `frames` frames
    at `fps`), where its sync point is in `mp4`'s sound: a dict with
    `name`, `mark` (the frame asked for), `offset_ms` (how far from it the
    sound fits best), `r` (0-1, how much of the mix's loudness around it the
    sound explains there: low when the mix buries it), `r_at_mark` (the
    same, on its mark), `landed` (within a frame of its mark, or fitting
    its mark about as well: `SAME_FIT`), `clipped` (samples at full scale in
    its span) and `cut` (its tail runs past the film's end).

    Model-free: the mix's 1 ms loudness envelope around the sound's mark is
    fitted, by least squares, as the sound's own envelope shifted by up to
    `SEARCH_FRAMES` frames, plus the other sound effects as placed, plus a
    constant (the music, speech); the shift that fits best is where it is.
    `mix` is the MP4's mono samples, if decoded already."""
    out = []
    placed = [s for s in sounds if isinstance(s, Sfx)]
    if not placed:
        return out
    mix = mix if mix is not None else decode(mp4, channels=1)
    envs = {id(s): _placed(s, fps) for s in placed}
    lag = round(SEARCH_FRAMES * 1000 / fps)
    for s in placed:
        name = s.effect + (f'--{s.variant}' if s.variant else '')
        row = {'name': name, 'align': s.align, 'mark': s.mark, 'offset_ms': None, 'r': None, 'clipped': 0,
               'cut': (s.at + s.frames >= frames and s.sync_s + 0.05 < measure_cached(s.path)['end_s'])}
        if not 0 <= s.mark < frames:
            row['skip'] = 'its mark is outside the film'
            out.append(row)
            continue
        first, env = envs[id(s)]
        # Matched around its loudest moment, where the sound says most about where it is.
        loud_ms = round((s.mark / fps + measure_cached(s.path)['peak_s'] - s.sync_s) * 1000)
        a0 = max(first, loud_ms - round(REF_BEFORE * 1000))
        a1 = min(first + len(env), loud_ms + round(REF_AFTER * 1000), len(mix) * 1000 // RATE - lag)
        ref = env[a0 - first:a1 - first]
        w0, n = a0 - lag, len(ref) + 2 * lag
        y = envelope(mix[w0 * RATE // 1000:(w0 + n) * RATE // 1000]) if w0 >= 0 else []
        if w0 < 0 or len(ref) < 5 or len(y) < n:
            row['skip'] = 'too near the film\'s start to match' if w0 < 0 else 'too short to match'
            out.append(row)
            continue
        others = [0.0] * n
        for o in placed:
            if o is s:
                continue
            f0, e = envs[id(o)]
            for k in range(max(0, f0 - w0), min(n, f0 + len(e) - w0)):
                others[k] += e[k + w0 - f0]
        best, at_mark = (0, -1.0), 0.0
        for d in range(-lag, lag + 1):
            x1 = [0.0] * (lag + d) + ref + [0.0] * (lag - d)
            r2, r2_others = _fit(y, x1, others)
            partial = (r2 - r2_others) / (1 - r2_others) if r2_others < 1 else 0.0
            if d == 0:
                at_mark = partial
            if partial > best[1] + 1e-12 or (abs(partial - best[1]) <= 1e-12 and abs(d) < abs(best[0])):
                best = (d, partial)
        span = mix[max(0, round((s.at / fps) * RATE)):round(((s.at + s.frames) / fps) * RATE)]
        r, r_mark = math.sqrt(max(0.0, best[1])), math.sqrt(max(0.0, at_mark))
        row.update(offset_ms=best[0], r=round(r, 3), r_at_mark=round(r_mark, 3),
                   landed=abs(best[0]) <= 1000 / fps or r_mark >= SAME_FIT * r,
                   clipped=sum(1 for x in span if x >= 0.999 or x <= -0.999))
        out.append(row)
    return out


def report(rows, fps):
    """`sync`'s rows in words: [(level, message)], level 'ok', 'note',
    'warn' or 'fail' (what `check.py --video` and `assemble` print)."""
    out, good = [], 0
    for row in rows:
        where = f"{row['name']} ({row['align']} on f{row['mark']})"
        if 'skip' in row:
            out.append(('note', f'{where}: not checked, {row["skip"]}'))
            continue
        if row['r'] < BURIED_R:
            out.append(('warn', f'{where}: not clearly heard in the mix (match {row["r"]:.2f}); it is buried '
                                f'under the music or speech: raise its gain_db, or check it by ear'))
        elif not row['landed']:
            out.append(('fail', f'{where} lands {row["offset_ms"]:+d} ms from its frame '
                                f'(one frame is {1000 / fps:.0f} ms)'))
        else:
            good += 1
        if row['clipped']:
            out.append(('fail', f'{where}: {row["clipped"]} samples at full scale in its span: lower its gain_db'))
        if row['cut']:
            out.append(('warn', f'{where}: the film ends before its tail does'))
    if good:
        out.append(('ok', f'{good} of {len(rows)} sound effects within a frame of their frames'))
    return out


_decoded, _measured = {}, {}


def decode_cached(path):
    if path not in _decoded:
        _decoded[path] = decode(path, channels=1)
    return _decoded[path]


def measure_cached(path):
    if path not in _measured:
        _measured[path] = measure(decode_cached(path), channels=1)
    return _measured[path]


# ---- fetching the pack ----
def fetch(dest=None, url=PACK_URL, sha256=None, opener=None, log=sys.stderr):
    """Download the pack from `url`, check its sha256 (default: the pinned
    one) and unpack it to `dest` (default `pack_dir()`), replacing what was
    there. `opener(url)` returns a readable response (default urllib's
    urlopen, which reads file:// URLs too). Returns `dest`."""
    dest = Path(dest) if dest is not None else pack_dir()
    want = (sha256 or pinned_sha256()).lower()
    if want == PLACEHOLDER:
        raise ValueError(f'the pack\'s sha256 is not pinned yet ({PIN_FILE} holds a placeholder): '
                         f'pass --sha256, or pin the published {PACK}.tar\'s sha256 there')
    opener = opener or (lambda u: urllib.request.urlopen(u, timeout=FETCH_TIMEOUT))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=f'.{PACK}-') as tmp:
        tar_path = Path(tmp) / f'{PACK}.tar'
        digest = hashlib.sha256()
        print(f'fetching {url}', file=log)
        with opener(url) as response, open(tar_path, 'wb') as fh:
            for chunk in iter(lambda: response.read(1 << 20), b''):
                digest.update(chunk)
                fh.write(chunk)
        got = digest.hexdigest()
        if got != want:
            raise ValueError(f'{url}: sha256 {got}, expected {want}: not the pinned {PACK}, nothing unpacked')
        unpacked = Path(tmp) / 'pack'
        with tarfile.open(tar_path) as tf:
            if hasattr(tarfile, 'data_filter'):
                tf.extractall(unpacked, filter='data')
            else:   # Python 3.11 before 3.11.4: only plain files and directories, inside the pack
                for m in tf.getmembers():
                    if not (m.isfile() or m.isdir()) or m.name.startswith('/') or '..' in Path(m.name).parts:
                        raise ValueError(f'{url}: {m.name}: not a plain file in the pack')
                tf.extractall(unpacked)
        if not (unpacked / 'index.json').is_file():
            raise ValueError(f'{url}: no index.json in the pack')
        old = Path(tmp) / 'old'
        if dest.exists():
            dest.rename(old)
        unpacked.rename(dest)
    print(f'{PACK}: unpacked to {dest}', file=log)
    return dest


# ---- the command line ----
def _fmt_take(t):
    what = f'{t.length_s:g} s' if t.variant and t.length_s else (t.note or '')
    return (f'    {t.name:44} {what:>7}  {t.dur_s:6.3f} s long, peak at {t.peak_s:.3f} s, '
            f'onset {t.onset_s:.3f} s')


def main(argv=None):
    p = argparse.ArgumentParser(prog='videobuilder sfx', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    ls = sub.add_parser('list', help='the sounds in the pack, by role')
    ls.add_argument('--role', help='only this role (whoosh, hit, click, ...)')
    ls.add_argument('--category', help='only this category (whoosh_fast, pro_impact, ...)')
    ls.add_argument('--takes', action='store_true', help='every take, with its length and peak')
    pp = sub.add_parser('play-path', help="print a sound's file: ID, or ID--VARIANT (whoosh_fast/tight--0.5s)")
    pp.add_argument('name')
    ft = sub.add_parser('fetch', help=f'download {PACK}.tar, check its sha256 and unpack it')
    ft.add_argument('--dir', help=f'where to unpack it (default ${ENV}, else ~/.cache/videobuilder/{PACK})')
    ft.add_argument('--url', default=PACK_URL)
    ft.add_argument('--sha256', help='the sha256 to check (default: the pinned one)')
    a = p.parse_args(argv)
    try:
        if a.cmd == 'fetch':
            fetch(a.dir, a.url, a.sha256)
            return 0
        b = bank()
        if a.cmd == 'play-path':
            print(b.take(a.name).path)
            return 0
        effects = b.find(a.role, category=a.category)
        by_role = {}
        for e in effects:
            by_role.setdefault(e.role, []).append(e)
        for role in sorted(by_role):
            print(f'{role}:')
            for e in by_role[role]:
                lengths = [t.length_s for t in e.lengths if t.variant]
                extra = (f'lengths {", ".join(f"{x:g}" for x in lengths)} s' if lengths else '') + \
                        (f'{"; " if lengths else ""}notes {e.notes[0]}-{e.notes[-1]}' if e.notes else '')
                print(f'  {e.id:34} {e.family:8} {e.about[:60]}' + (f'  [{extra}]' if extra else ''))
                if a.takes:
                    for t in e.takes:
                        print(_fmt_take(t))
        print(f'{len(effects)} sounds', file=sys.stderr)
        return 0
    except (SfxUnavailable, ValueError) as e:
        raise SystemExit(str(e)) from None


if __name__ == '__main__':
    sys.exit(main())
