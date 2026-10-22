"""Pulse loader: a solid dot sits still while rings keep leaving it, each one
growing outward and fading to nothing, over and over -- "working on it"
without a progress amount."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pulse_rings(t, period=1.2, rings=2):
    """The rings alive at time `t` seconds as `(p, alpha)` pairs, oldest first:
    `p` 0 -> 1 is how far each has grown (eased out, so it bursts then
    slows), `alpha` fades from 1 to 0 as it goes. A new ring leaves every
    `period / rings` seconds and each lives one `period`, so the loop is seamless."""
    out = []
    for k in range(rings):
        age = ((t - k * period / rings) % period) / period
        out.append((1 - (1 - age) ** 2, 1 - age))
    return sorted(out, key=lambda r: -r[0])


def draw_pulse_loader(cv, cx, cy, t, r=22, color=demo.ACCENT, reach=3.2, width=4, period=1.2, rings=2,
                      breathe=0.08):
    """Draw a pulse loader centred at (cx, cy) at time `t` seconds: a dot of
    radius `r` that breathes by `breathe` of its size, with `rings` outlines
    growing from it to `reach` times its radius and fading, one leaving every
    `period / rings` seconds. Returns the Box the rings reach."""
    for p, alpha in pulse_rings(t, period, rings):
        rr = r * (1 + (reach - 1) * p)
        cv.arc(cx, cy, rr, 0, 2 * math.pi, color, width=width * (1 - 0.5 * p), alpha=alpha)
    s = 1 + breathe * math.cos(2 * math.pi * t / period)
    demo.dot(cv, cx, cy, r * s, color=color)
    edge = r * reach
    return vb.Box(cx - edge, cy - edge, 2 * edge, 2 * edge)


def draw(n, cv):
    t = n / demo.FPS
    box = draw_pulse_loader(cv, demo.W / 2, demo.H / 2 - 30, t, r=36, reach=4.2, width=6)
    demo.word(cv, 'Loading', demo.W / 2, demo.H / 2 + 190, size=34, color=demo.MUTED, weight=600)
    cv.mark('loader', *box)


CAPABILITY = Capability(
    id='pulse-loader',
    name='Pulse loader',
    family='ui',
    group='Loaders',
    aliases=('ring pulse', 'breathing dot', 'shockwave ring', 'expanding ring'),
    definition='A busy indicator where rings keep swelling out of a steady dot and fading away, '
               'signalling that something is in progress without saying how far along it is.',
    phrasings=('a dot with circles rippling out of it while it loads',
               'a pulsing ring spinner for a waiting state',
               'show that it is thinking with a beacon that keeps pinging'),
    related=('orbital-pulse', 'live-indicator-pulse', 'scale-pulse', 'location-ripple-pulse',
             'stroke-width-pulse', 'like-heart-burst'),
    api=('videobuilder.capabilities.ui.pulse_loader.draw_pulse_loader',
         'videobuilder.capabilities.ui.pulse_loader.pulse_rings'),
    demo=lambda: demo.film(draw),
)
