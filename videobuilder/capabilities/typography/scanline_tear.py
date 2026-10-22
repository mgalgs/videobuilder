"""Scanline tear: the picture is cut into thin horizontal bands and some of
them jerk sideways, out of line with their neighbours, in short bursts, as if
the video signal lost sync for a moment."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def tear_bands(amount, y, h, seed=0, step=0, bands=24, shift=120, torn=0.4):
    """The tear at strength `amount` (0 -> 1) as `(top, height, dx)` bands
    covering `y` to `y + h`. Band heights vary around `h / bands`; about a
    `torn` fraction of them move, by up to `shift` px left or right, scaled by
    `amount`. The same `seed` and `step` give the same bands, so step it a few
    times a second (e.g. `frame // 2`) for a flicker rather than a blur."""
    rng = random.Random(f'{seed}:{step}')
    out, top, end = [], y, y + h
    while top < end:
        bh = min(end - top, h / bands * rng.uniform(0.35, 1.8))
        dx = 0.0
        if amount > 0 and rng.random() < torn * (0.5 + amount / 2):
            dx = rng.choice((-1, 1)) * shift * amount * rng.uniform(0.15, 1.0)
        out.append((top, bh, dx))
        top += bh
    return out


def scanline_tear(cv, draw, amount, y=0, h=None, x=0, w=None, ghost=None, seam=None, **kw):
    """Draw `draw(cv)` torn into horizontal bands at strength `amount`: each
    band clipped to its strip of (x, y, w, h) (default the whole frame) and
    shifted by its own offset from `tear_bands` (`kw` goes there). At
    `amount` 0 it is `draw(cv)` untouched. `ghost(cv)`, if given, draws a
    tinted copy under each torn band, trailing it by half its offset, for a
    colour fringe; `seam`, a colour, marks the top edge of each torn band with
    a hairline. Returns the bands drawn."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    if amount <= 0:
        draw(cv)
        return [(y, h, 0.0)]
    bands = tear_bands(amount, y, h, **kw)
    for top, bh, dx in bands:
        with cv.clip(x, top, w, bh):
            if dx and ghost:
                with cv.layer(dx=dx * 0.5):
                    ghost(cv)
            with cv.layer(dx=dx):
                draw(cv)
        if dx and seam:
            cv.rect(x, top, w, max(1.0, bh * 0.06), seam, alpha=0.5 * min(1.0, amount * 2))
    return bands


def _burst(t, start, length):
    """A spike: up fast at `start`, holding briefly, falling away over `length`."""
    p = (t - start) / length
    if p <= 0 or p >= 1:
        return 0.0
    return min(1.0, p * 6) * (1 - vb.clamp01((p - 0.35) / 0.65))


def draw(n, cv):
    t = n / demo.FPS
    amount = max(0.25 * _burst(t, 0.35, 0.35), 0.6 * _burst(t, 0.95, 0.4), 1.0 * _burst(t, 1.6, 0.8))
    f = demo.font(190, 900)
    text = 'SIGNAL'
    tw, th = vb.text.block_size([text], f)
    tx, ty = (demo.W - tw) / 2, (demo.H - th) / 2

    def title(c, color=demo.INK):
        vb.text.draw(c, [text], f, tx, ty, color)

    pad = 12
    scanline_tear(cv, title, amount, y=ty - pad, h=th + 2 * pad, ghost=lambda c: title(c, demo.ACCENT),
                  seam=demo.TEAL, seed=3, step=n // 2, bands=12, shift=220, torn=0.6)
    cv.mark('text', tx, ty, tw, th)


TECHNIQUE = Technique(
    id='scanline-tear',
    name='Scanline tear',
    family='typography',
    group='Glitch and distortion',
    aliases=('horizontal tear', 'line tear', 'sync tear', 'glitch slices', 'VHS tear'),
    definition='Thin horizontal strips of the text suddenly slide sideways out of step with each other, '
               'in quick bursts, as though the video signal briefly lost its lock.',
    phrasings=('make the title glitch by slicing it into strips that jump left and right',
               'a bad-signal effect where rows of the text tear sideways for a moment',
               'the logo breaks up into shifted horizontal lines and snaps back'),
    related=('scanline-jitter', 'screen-tearing', 'glitch-transition', 'crt-scanlines', 'scanline-wipe',
             'data-bending'),
    api=('videobuilder.techniques.typography.scanline_tear.scanline_tear',
         'videobuilder.techniques.typography.scanline_tear.tear_bands'),
    demo=lambda: demo.film(draw),
)
