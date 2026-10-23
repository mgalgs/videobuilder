"""Gradient Sweep Across Text: a band of colour slides through a line of
type from left to right, recolouring each letter as it passes and leaving it
in its plain colour behind."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

STOPS = ('#f2c14e', '#ef5b4c', '#8b7cf6', '#4fc3b0')


def draw_gradient_sweep(cv, text, font, x, y, p, color, stops=STOPS, band=0.6, alpha=1.0):
    """Draw `text` from its top-left (x, y) in `color`, with a gradient band
    of `stops` (left to right) crossing it at progress `p` (0 -> 1): at 0 the
    band sits just off the left edge, at 1 just off the right, so the line
    starts and ends plain. `band` is the band's width as a fraction of the
    line's. Returns the Box of the line."""
    w, h = vb.text.block_size([text], font)
    bw = max(1.0, band * w)
    left = x - bw + vb.clamp01(p) * (w + bw)
    grad = cairo.LinearGradient(left, 0, left + bw, 0)  # pads with the end stops: plain colour either side
    grad.add_color_stop_rgba(0, *vb.rgba(color, alpha))
    for i, c in enumerate(stops):
        grad.add_color_stop_rgba(0.15 + 0.7 * i / max(1, len(stops) - 1), *vb.rgba(c, alpha))
    grad.add_color_stop_rgba(1, *vb.rgba(color, alpha))
    ctx = cv.ctx
    ctx.push_group()
    box = vb.text.draw(cv, [text], font, x, y, '#ffffff')  # the letters' shape, used as the mask
    mask = ctx.pop_group()
    ctx.set_source(grad)
    ctx.mask(mask)
    return box


def draw(n, cv):
    f = demo.font(132, 900)
    text = 'SPECTRUM'
    w, h = vb.text.block_size([text], f)
    # a gentle ease-in over nearly the whole clip: colour is on the letters from
    # ~0.7s to ~2.8s and the band sits mid-word (p ~ 0.55) at the 70% poster frame
    p = demo.phase(n, 0.2, 2.9) ** 1.7
    box = draw_gradient_sweep(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, p, demo.INK)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='gradient-sweep-across-text',
    name='Gradient sweep across text',
    family='typography',
    group='Surface and light',
    aliases=('gradient text sweep', 'color band sweep', 'gradient wipe text', 'shimmering gradient text'),
    definition='A stripe of blended colours travels through a word from one side to the other, '
               'tinting the letters while it covers them and letting them return to plain afterwards.',
    phrasings=('a rainbow of colour runs through the title from left to right',
               'the headline lights up with a moving gradient that passes across it',
               'colour washes over the letters one after another and fades back to white'),
    related=('animated-gradient-sweep', 'gradient-wipe', 'sheen-sweep', 'gradient-mesh-drift',
             'gradient-border-spin', 'twirl-warp-text'),
    api=('videobuilder.capabilities.typography.gradient_sweep_across_text.draw_gradient_sweep',),
    demo=lambda: demo.film(draw),
)
