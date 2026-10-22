"""Radial Audio Visualizer: a ring of bars around a centre, each bar's length
following the loudness of one frequency band, so the circle throbs and
bristles with the music."""
import math
import random

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def band_levels(samples, rate, t, bands=32, window=1024, lo=50.0, hi=8000.0):
    """Loudness 0 -> 1 of `bands` log-spaced frequency bands from `lo` to `hi`
    Hz in the `window` mono `samples` centred on `t` seconds (a Goertzel
    filter per band, Hann-windowed; pure Python). Feed one call per frame to
    `radial_bars` or `radial_shape`; smooth across frames with `smooth`."""
    a = max(0, min(len(samples) - window, round(t * rate) - window // 2))
    chunk = samples[a:a + window]
    if len(chunk) < 2:
        return [0.0] * bands
    n = len(chunk)
    hann = [0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]
    out = []
    for b in range(bands):
        f = lo * (hi / lo) ** ((b + 0.5) / bands)
        k = 2 * math.cos(2 * math.pi * f / rate)
        s1 = s2 = 0.0
        for x, w in zip(chunk, hann):
            s1, s2 = x * w + k * s1 - s2, s1
        power = max(0.0, s1 * s1 + s2 * s2 - k * s1 * s2) / (n / 4) ** 2
        out.append(vb.clamp01(1 + 10 * math.log10(power + 1e-12) / 60))  # -60 dB -> 0, 0 dB -> 1
    return out


def smooth(previous, levels, attack=0.7, release=0.18):
    """`levels` eased from last frame's `previous`: rising fast (`attack`),
    falling slowly (`release`), so bars jump on a hit and sink back."""
    if previous is None:
        return list(levels)
    return [p + (v - p) * (attack if v > p else release) for p, v in zip(previous, levels)]


def mirrored(levels):
    """`levels` followed by themselves reversed, so a ring of them is
    symmetric left to right (bass at the top, treble at the bottom)."""
    return list(levels) + list(levels)[::-1]


def radial_bars(cv, cx, cy, levels, radius, length, color, width=None, start=-math.pi / 2,
                floor=0.04, alpha=1.0, round_ends=True):
    """A ring of bars around (cx, cy), one per entry of `levels` (each 0 -> 1),
    spaced evenly from angle `start` (radians, clockwise; default the top).
    Each bar starts at `radius` and reaches out `floor + level` of `length`.
    `width` defaults to most of the gap between bars."""
    count = len(levels)
    if not count:
        return
    width = width or 0.62 * 2 * math.pi * radius / count
    c = cv.ctx
    c.save()
    c.set_line_cap(1 if round_ends else 0)  # cairo: 1 round, 0 butt
    c.set_line_width(width)
    c.set_source_rgba(*rgba(color, alpha))
    for i, v in enumerate(levels):
        a = start + 2 * math.pi * i / count
        r1 = radius + length * (floor + (1 - floor) * vb.clamp01(v))
        c.move_to(cx + radius * math.cos(a), cy + radius * math.sin(a))
        c.line_to(cx + r1 * math.cos(a), cy + r1 * math.sin(a))
    c.stroke()
    c.restore()
    cv.mark('radial-bars', cx - radius - length, cy - radius - length, 2 * (radius + length),
            2 * (radius + length))


def radial_shape(cv, cx, cy, levels, radius, depth, color, start=-math.pi / 2, alpha=1.0, stroke=None):
    """A closed blob around (cx, cy) whose edge bulges out by `level * depth`
    at each entry of `levels`, joined with smooth curves: the filled
    variant of `radial_bars`. `stroke=(color, width)` outlines it instead of
    filling."""
    count = len(levels)
    if count < 3:
        return
    pts = []
    for i, v in enumerate(levels):
        a = start + 2 * math.pi * i / count
        r = radius + depth * vb.clamp01(v)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    c = cv.ctx
    c.save()
    c.new_path()
    c.move_to(*_mid(pts[-1], pts[0]))
    for i, p in enumerate(pts):  # a quadratic through each point's neighbours' midpoints
        q = _mid(p, pts[(i + 1) % count])
        x0, y0 = c.get_current_point()
        c.curve_to(x0 + 2 / 3 * (p[0] - x0), y0 + 2 / 3 * (p[1] - y0),
                   q[0] + 2 / 3 * (p[0] - q[0]), q[1] + 2 / 3 * (p[1] - q[1]), *q)
    c.close_path()
    if stroke:
        c.set_source_rgba(*rgba(stroke[0], alpha))
        c.set_line_width(stroke[1])
        c.stroke()
    else:
        c.set_source_rgba(*rgba(color, alpha))
        c.fill()
    c.restore()


def _mid(p, q):
    return (p[0] + q[0]) / 2, (p[1] + q[1]) / 2


# ---- the demo: a made-up beat, so it needs no sound file ----
BANDS = 32
BEAT = 0.5  # seconds between kicks


def _fake_levels(t):
    """A plausible spectrum at `t`: bass that punches on every beat, mids
    that wander, treble that flickers."""
    since = t % BEAT
    kick = math.exp(-since * 9)
    rng = random.Random(int(t * demo.FPS / 2))  # new jitter every other frame
    out = []
    for b in range(BANDS):
        x = b / (BANDS - 1)
        bass = kick * max(0.0, 1 - x * 2.2)
        mid = 0.35 * (0.5 + 0.5 * math.sin(t * 5 + b * 0.7)) * (1 - abs(x - 0.45) * 1.6)
        hiss = 0.25 * rng.random() * x
        out.append(vb.clamp01(0.08 + bass + max(0.0, mid) + hiss))
    return out


def _levels_at(n):
    lv = None
    for k in range(max(0, n - 12), n + 1):  # replay a few frames so `smooth` has history
        lv = smooth(lv, _fake_levels(k / demo.FPS))
    return lv


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    grow = vb.ease_out_back(demo.phase(n, 0.0, 0.5))
    lv = [v * grow for v in mirrored(_levels_at(n))]
    kick = math.exp(-((n / demo.FPS) % BEAT) * 9) * grow
    radial_shape(cv, cx, cy, lv, 70, 34, demo.TEAL, alpha=0.18)
    radial_bars(cv, cx, cy, lv, 92, 110, demo.ACCENT, width=6)
    demo.dot(cv, cx, cy, r=(54 + 9 * kick) * grow, color=demo.INK)
    demo.dot(cv, cx, cy, r=(20 + 5 * kick) * grow, color=demo.BG)


CAPABILITY = Capability(
    id='sound-reactive-radial-shape',
    name='Radial audio visualizer',
    family='shapes',
    group='Sound-reactive',
    aliases=('circular audio spectrum', 'radial equalizer', 'circular visualizer', 'audio spectrum ring'),
    definition='Bars fan out around a circle, each one stretching and shrinking with the loudness of '
               'its slice of the sound, so the ring pulses in time with the audio.',
    phrasings=('a circle of bars that bounces to the music',
               'a round equalizer around the logo that reacts to the beat',
               'a spectrum ring that pulses with the song',
               'the circle grows spikes when the bass hits'),
    related=('audio-reactive-particles', 'radial-stagger', 'radial-repeater', 'ripple-rings',
             'audio-waveform-bars', 'circle-pop'),
    api=('videobuilder.capabilities.shapes.sound_reactive_radial_shape.radial_bars',
         'videobuilder.capabilities.shapes.sound_reactive_radial_shape.radial_shape',
         'videobuilder.capabilities.shapes.sound_reactive_radial_shape.band_levels',
         'videobuilder.capabilities.shapes.sound_reactive_radial_shape.smooth',
         'videobuilder.capabilities.shapes.sound_reactive_radial_shape.mirrored'),
    demo=lambda: demo.film(draw),
)
