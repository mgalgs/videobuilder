"""Solarization: every tone brighter than a threshold is flipped to its
negative while darker tones are left alone, so highlights fold back into
darks and the picture turns half positive, half negative. The tone curve
rises to the threshold and then falls; lowering the threshold folds more of
the picture over."""
from PIL import Image

from .. import _demo as demo
from ..schema import Capability
from ...looks import fx


def solarize_curve(threshold=128, amount=1.0):
    """The solarization tone curve as a 256-entry lookup table: a level at or
    below `threshold` (0-255) is kept, one above it moves toward its negative
    `255 - v` by `amount` (0 leaves the picture alone, 1 is full solarization)."""
    th = max(0.0, min(255.0, threshold))
    k = max(0.0, min(1.0, amount))
    return [round(v if v <= th else v + (255 - 2 * v) * k) for v in range(256)]


def solarize_image(im, threshold=128, amount=1.0):
    """A PIL image solarized per channel with `solarize_curve`."""
    lut = solarize_curve(threshold, amount)
    im = im.convert('RGB')
    return im.point(lut * 3)


def _treat(im, t, age, u, threshold=128, amount=1.0):
    return solarize_image(im, threshold, amount)


_FILTER = fx.Filter('solarization', 'Solarization', 'tones past a threshold flip to their negative', _treat)


def solarize(cv, threshold=128, amount=1.0, box=None):
    """A context manager: everything already on `cv` and everything drawn
    inside the block is solarized when the block ends (only `box`, (x, y, w, h)
    in frame px, if given). Animate `threshold` down to fold more tones over,
    or `amount` 0 -> 1 to bring the effect in.

        with solarize(cv, threshold=140, amount=p):
            draw_the_shot(n, cv)
    """
    return fx.apply(cv, _FILTER, 0.0, box=box, opts={'threshold': threshold, 'amount': amount})


# ---- demo ----

def _curve_inset(cv, threshold, amount):
    """A small tone-curve plot in the corner: input level across, output up."""
    s, x0, y0 = 170, demo.W - 230, demo.H - 230
    cv.rect(x0 - 20, y0 - 20, s + 40, s + 40, demo.BG, radius=14, alpha=0.85)
    cv.rect(x0, y0, s, s, demo.LINE, radius=2, alpha=0.5)
    pts = [(x0 + s * v / 255, y0 + s - s * o / 255)
           for v, o in enumerate(solarize_curve(threshold, amount)) if v % 5 == 0 or v == 255]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.ACCENT, width=4)
    f = demo.mono(18)
    demo.vb.text.draw(cv, ['tone curve'], f, x0, y0 + s + 2, demo.MUTED)


def _draw(n, cv):
    up = demo.phase(n, 0.4, 1.1)
    down = demo.phase(n, 2.2, 2.7)
    amount = demo.vb.ease_in_out_quart(up) * (1 - demo.vb.ease_in_out_quart(down))
    sweep = demo.phase(n, 1.0, 2.2)
    threshold = 200 - 110 * demo.vb.ease_in_out_quart(sweep)  # fold more tones over while it holds
    img = demo.photo()
    with solarize(cv, threshold, amount):
        cv.image(img, *demo.vb.Box.of(cv).cover(img.w, img.h))
    _curve_inset(cv, threshold, amount)


CAPABILITY = Capability(
    id='solarization',
    name='Solarization',
    family='vfx',
    group='Color & grading',
    aliases=('Sabattier effect', 'tonal reversal', 'solarize'),
    definition='The brightest parts of the picture flip to their photographic negative while the darker '
               'parts stay as they are, giving a strange half-positive, half-negative image.',
    phrasings=('make the highlights go negative like an old darkroom accident',
               'invert just the bright parts of the shot',
               'a trippy partly-inverted photo look'),
    related=('halation', 'posterization', 'gooch-shading', 'theme-swap-crossfade', 'heat-haze', 'vignette'),
    api=('videobuilder.capabilities.vfx.solarization.solarize',
         'videobuilder.capabilities.vfx.solarization.solarize_image',
         'videobuilder.capabilities.vfx.solarization.solarize_curve'),
    demo=lambda: demo.film(_draw),
)
