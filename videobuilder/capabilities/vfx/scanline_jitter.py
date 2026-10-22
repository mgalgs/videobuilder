"""Scanline jitter: every thin row of the picture slides a few pixels left or
right, each by its own amount, and the offsets keep twitching in an uneven
rhythm, so vertical edges go ragged and wavy like a picture with a shaky
horizontal sync."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def jitter_offsets(t, rows, amount=1.0, shift=18.0, seed=0, rate=24, wave=0.6, grain=0.4):
    """The sideways offset in px of each of `rows` rows at time `t` seconds,
    at strength `amount` (0 -> 1). Each offset mixes a slow wave running down
    the rows (`wave` of `shift`, which bends edges into curves) with per-row
    noise (`grain` of `shift`, which makes them ragged). Both re-roll `rate`
    times a second, and the same `seed` and `t` always give the same rows."""
    if amount <= 0 or rows <= 0:
        return [0.0] * max(rows, 0)
    step = int(t * rate)
    rng = random.Random(f'{seed}:{step}')
    waves = [(rng.uniform(1.0, 4.0), rng.uniform(0, 2 * math.pi), rng.uniform(0.4, 1.0)) for _ in range(3)]
    norm = sum(a for _, _, a in waves)
    out = []
    for i in range(rows):
        u = i / rows
        smooth = sum(a * math.sin(2 * math.pi * f * u + ph) for f, ph, a in waves) / norm
        out.append(shift * amount * (wave * smooth + grain * rng.uniform(-1, 1)))
    return out


def scanline_jitter(cv, draw, t, amount, x=0, y=0, w=None, h=None, line=6, base=True, **kw):
    """Draw `draw(cv)` with scanline jitter at time `t` seconds and strength
    `amount` (0 -> 1): the region (x, y, w, h) (default the whole frame) is
    cut into rows `line` px tall, each clipped and shifted sideways by its
    offset from `jitter_offsets` (`kw` goes there: `shift`, `seed`, `rate`,
    `wave`, `grain`). With `base`, an unshifted copy goes underneath so a
    row pulled aside uncovers picture rather than a gap; turn it off when
    `draw` doesn't fill the region (a title on its own), or it shows through
    as a ghost. At `amount` 0 it is `draw(cv)` untouched. Returns the
    offsets used, top row first."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    if amount <= 0:
        draw(cv)
        return []
    rows = max(1, math.ceil(h / line))
    offsets = jitter_offsets(t, rows, amount, **kw)
    if base:
        with cv.clip(x, y, w, h):
            draw(cv)
    for i, dx in enumerate(offsets):
        top = y + i * line
        with cv.clip(x, top, w, min(line, y + h - top)):
            with cv.layer(dx=dx):
                draw(cv)
    return offsets


def _unsteady(t, seed=5):
    """An irregular strength over time: a low hum that swells into uneven surges."""
    rng = random.Random(seed)
    surges = [(rng.uniform(0.5, 2.6), rng.uniform(0.15, 0.4), rng.uniform(0.5, 1.0)) for _ in range(5)]
    level = 0.25 + 0.1 * math.sin(t * 7.3)
    for at, length, peak in surges:
        d = abs(t - at) / length
        if d < 1:
            level = max(level, peak * (1 - d * d))
    return vb.clamp01(level)


def _scene(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    demo.card(cv, demo.W / 2, demo.H / 2, w=520, h=320, color=demo.TEAL)


def draw(n, cv):
    t = n / demo.FPS
    scanline_jitter(cv, _scene, t, _unsteady(t), line=6, shift=34, seed=11)


CAPABILITY = Capability(
    id='scanline-jitter',
    name='Scanline jitter',
    family='vfx',
    group='Glitch',
    aliases=('horizontal sync jitter', 'sync jitter', 'VHS jitter', 'line jitter'),
    definition='Each thin row of the picture keeps twitching a little to the left or right on its own, '
               'so straight upright edges turn ragged and wavy like a shaky old video signal.',
    phrasings=('make the picture wobble sideways line by line like a bad VHS tape',
               'give the footage that unstable sync look where the rows shiver left and right',
               'shaky horizontal lines, as if the TV can\'t hold the picture steady'),
    related=('scanline-tear', 'vhs-tracking-bar', 'tape-wobble', 'glitch-transition', 'speed-lines',
             'wiggle-path'),
    api=('videobuilder.capabilities.vfx.scanline_jitter.scanline_jitter',
         'videobuilder.capabilities.vfx.scanline_jitter.jitter_offsets'),
    demo=lambda: demo.film(draw),
)
