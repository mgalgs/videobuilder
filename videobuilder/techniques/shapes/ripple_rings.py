"""Ripple Rings: thin circles are born one after another at a point, grow
outward and thin out to nothing, like rings spreading on a pond."""
import math

from .. import _demo as demo
from ..schema import Technique


def ripple_rings(cv, cx, cy, t, radius=420, every=0.5, life=1.6, color=demo.ACCENT, width=4,
                 start_radius=0.0, count=None, ease=None):
    """Draw the rings at `t` seconds after the first is emitted from (cx, cy).

    A new ring is born every `every` seconds and lives `life` seconds, growing
    from `start_radius` to `radius` along `ease` while its alpha and stroke
    `width` fall to zero; `ease` defaults to a gentle ease-out, which keeps
    the rings evenly spaced. `count` stops emitting after that many rings (None
    keeps going); a negative `t` draws nothing. Call it once per frame with the
    shot's own clock, e.g. `ripple_rings(cv, x, y, shot.f / fps - 0.4)`."""
    if t < 0:
        return
    born = int(t // every)
    if count is not None:
        born = min(born, count - 1)
    for k in range(born, -1, -1):
        q = (t - k * every) / life
        if q >= 1:
            break  # older rings are gone too
        g = ease(q) if ease else 1 - (1 - q) ** 1.6
        r = start_radius + (radius - start_radius) * g
        fade = (1 - q) ** 1.5
        if r > 0 and fade > 0:
            cv.arc(cx, cy, r, 0, math.tau, color, width=max(0.5, width * (0.4 + 0.6 * fade)),
                   alpha=fade)


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    t = n / demo.FPS
    ripple_rings(cv, cx, cy, t - 0.2, radius=400, every=0.45, life=1.8, width=5, start_radius=14)
    pulse = 1 + 0.25 * max(0.0, 1 - ((t - 0.2) % 0.45) / 0.15)  # the source dot kicks as each ring leaves
    demo.dot(cv, cx, cy, 12 * pulse, color=demo.INK)
    cv.mark('source', cx - 12, cy - 12, 24, 24)


TECHNIQUE = Technique(
    id='ripple-rings',
    name='Ripple rings',
    family='shapes',
    group='Waves & ripples',
    aliases=('concentric pulse', 'sonar ring', 'shockwave ring', 'radar ping'),
    definition='Thin circles keep spawning at one spot and swell outward, each one growing fainter '
               'until it vanishes, the way rings spread after a stone drops into still water.',
    phrasings=('send rings rippling out from that point',
               'a sonar-style ping pulsing out in circles',
               'circles that spread out and fade like a drop in a pond'),
    related=('refraction-ripple', 'ripple', 'height-field-ripples', 'location-ripple-pulse',
             'rotating-rings', 'ripple-displacement'),
    api=('videobuilder.techniques.shapes.ripple_rings.ripple_rings',),
    demo=lambda: demo.film(draw),
)
