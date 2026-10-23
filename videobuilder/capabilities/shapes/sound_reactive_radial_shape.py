"""Radial Audio Visualizer: a ring of bars around a centre, each bar's length
following the loudness of one frequency band, so the circle throbs and
bristles with the music."""
import math

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


def sounds_mix(sounds, frames, fps=30, rate=None):
    """The mono samples of `sounds` (`vb.Sound`s or `vb.sfx` hits, each
    placed on its film frame with its gain and fade-out) mixed over `frames`
    film frames at `rate` (default `vb.sfx.RATE`): the same hits the film
    plays, as a buffer `band_levels` can read the picture's levels from."""
    rate = rate or vb.sfx.RATE
    out = [0.0] * round(frames / fps * rate)
    for s in sounds:
        src = vb.sfx.decode_cached(s.path)
        gain = 10 ** (s.gain_db / 20)
        a = round(s.at / fps * rate)                       # the span's first sample
        lead = round(-s.start * rate)                      # file sample 0 plays this long after it
        span = round(s.frames / fps * rate)
        fade = max(1, round(s.fade_out_frames / fps * rate))
        for i in range(max(0, lead), min(span, lead + len(src))):
            j = a + i
            if 0 <= j < len(out):
                out[j] += gain * src[i - lead] * min(1.0, (span - i) / fade)
    return out


# ---- the demo: a beat of kicks, clicks and dings, heard and drawn from the same samples ----
BANDS = 32
BEAT = 15        # frames between kicks: 120 BPM
FIRST = 6        # the first kick's peak; the sub hit swells for 0.18 s before it
FRAMES = round(demo.SECONDS * demo.FPS)
DINGS = (None, 'G5', 'A5')


def _first(*ids):
    """The first of `ids` the sound pack has: the shipped pack and the test
    fixture pack name some sounds differently."""
    for i in ids[:-1]:
        try:
            return vb.sfx.get(i)
        except ValueError:
            pass
    return vb.sfx.get(ids[-1])


def _sounds():
    """A kick on every beat, a click on every off-beat with a tick just before
    it, and a ding stepping up on every other kick."""
    kick, click, ding = (vb.sfx.get(i) for i in ('pro_impact/short', 'fit/click/floss_lid', 'pro_notify/ding_2045'))
    tick = _first('pro_hover_tick/detent', 'hover_tick/detent')
    beats = range(FIRST, FRAMES, BEAT)
    return (tuple(kick.sound(at=f, dur=0.32, gain_db=-4) for f in beats)
            + tuple(click.sound(at=f + BEAT // 2, gain_db=-3) for f in beats if f + BEAT // 2 < FRAMES)
            + tuple(tick.sound(at=f + 4, gain_db=-8) for f in beats if f + 4 < FRAMES)
            + tuple(ding.sound(at=f, note=DINGS[i % len(DINGS)], gain_db=-10, align='onset')
                    for i, f in enumerate(beats[::2])))


def _levels(sounds):
    """Each frame's smoothed band levels, read off the mix of `sounds`."""
    mix, rate = sounds_mix(sounds, FRAMES, demo.FPS), vb.sfx.RATE
    out, lv = [], None
    for n in range(FRAMES):
        lv = smooth(lv, band_levels(mix, rate, n / demo.FPS, bands=BANDS))
        out.append(lv)
    return out


def _draw(levels):
    def draw(n, cv):
        cx, cy = demo.W / 2, demo.H / 2
        grow = vb.ease_out_back(demo.phase(n, 0.0, 0.5))
        lv = [v * grow for v in mirrored(levels[n])]
        bass = vb.clamp01(sum(levels[n][:4]) / 4 - 0.25) / 0.75 * grow
        radial_shape(cv, cx, cy, lv, 70, 34, demo.TEAL, alpha=0.18)
        radial_bars(cv, cx, cy, lv, 92, 110, demo.ACCENT, width=6)
        demo.dot(cv, cx, cy, r=(54 + 9 * bass) * grow, color=demo.INK)
        demo.dot(cv, cx, cy, r=(20 + 5 * bass) * grow, color=demo.BG)
    return draw


def demo_film():
    """The beat plays under the picture, and the ring is drawn from that
    same beat through `band_levels` and `smooth`, so every punch is heard."""
    sounds = _sounds()
    return demo.film(_draw(_levels(sounds)), sounds=sounds)


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
         'videobuilder.capabilities.shapes.sound_reactive_radial_shape.mirrored',
         'videobuilder.capabilities.shapes.sound_reactive_radial_shape.sounds_mix'),
    demo=demo_film,
)
