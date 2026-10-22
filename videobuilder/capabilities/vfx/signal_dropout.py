"""Signal dropout: for a frame or two, short horizontal streaks across the
picture flash pure white or pure black, as if the tape or the signal lost a
few lines of picture, then the image is clean again."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def dropout_streaks(amount, w, h, seed=0, step=0, count=14, length=(0.06, 0.45), thickness=(2, 9),
                    white=0.6):
    """The dropouts at strength `amount` (0 -> 1) as `(x, y, length, height,
    color)` streaks inside a `w` x `h` frame. Up to `count` streaks, fewer as
    `amount` falls; each is a `length` fraction of `w` long and `thickness`
    px tall, white with chance `white`, else black. The same `seed` and
    `step` give the same streaks, so step it every frame or two for a flicker."""
    rng = random.Random(f'{seed}:{step}')
    out = []
    if amount <= 0:
        return out
    for _ in range(count):
        if rng.random() > amount:
            continue
        sl = w * rng.uniform(*length)
        sh = rng.uniform(*thickness)
        x = rng.uniform(-0.1 * w, w - sl * 0.6)
        y = rng.uniform(0, h - sh)
        out.append((x, y, sl, sh, '#ffffff' if rng.random() < white else '#000000'))
    return out


def signal_dropout(cv, draw, amount, x=0, y=0, w=None, h=None, tail=0.35, **kw):
    """Draw `draw(cv)` with dropout streaks over (x, y, w, h) (default the
    whole frame) at strength `amount`; `kw` goes to `dropout_streaks`. Each
    streak is solid for most of its length and smears out over its last
    `tail` fraction, the way a player's dropout compensation trails off. At
    `amount` 0 it is `draw(cv)` untouched. Returns the streaks drawn."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    draw(cv)
    streaks = dropout_streaks(amount, w, h, **kw)
    with cv.clip(x, y, w, h):
        for sx, sy, sl, sh, color in streaks:
            solid = sl * (1 - tail)
            cv.rect(x + sx, y + sy, solid, sh, color)
            steps = 6
            for i in range(steps):
                seg = sl * tail / steps
                cv.rect(x + sx + solid + i * seg, y + sy, seg + 0.5, sh, color, alpha=1 - (i + 1) / (steps + 1))
    return streaks


def _envelope(t):
    """Two brief flickers, a heavier burst, then a clean hold."""
    bursts = ((0.45, 0.10, 0.35), (1.0, 0.13, 0.5), (1.4, 0.65, 1.0))
    return max((peak if start <= t < start + length else 0.0) for start, length, peak in bursts)


def draw(n, cv):
    img = demo.photo()

    def picture(c):
        c.image(img, *vb.Box.of(c).cover(img.w, img.h))

    signal_dropout(cv, picture, _envelope(n / demo.FPS), seed=7, step=n)


CAPABILITY = Capability(
    id='signal-dropout',
    name='Signal dropout',
    family='vfx',
    group='Glitch',
    aliases=('tape dropout', 'video dropout', 'signal loss', 'VHS dropout'),
    definition='Thin horizontal streaks of the picture flick to solid white or black for a frame or two, '
               'like a worn tape skipping a few lines, and then the image is whole again.',
    phrasings=('add little white and black line flashes like an old videotape',
               'make the footage look like it is losing signal for a split second',
               'sprinkle a few VHS dropout lines over the shot'),
    related=('scanline-tear', 'desaturation', 'dip-to-black', 'sub-drop', 'analog-ghosting', 'glitch-transition'),
    api=('videobuilder.capabilities.vfx.signal_dropout.signal_dropout',
         'videobuilder.capabilities.vfx.signal_dropout.dropout_streaks'),
    demo=lambda: demo.film(draw),
)
