"""Analog ghosting: faint copies of the picture sit a little to the right of
it, as a reflected signal arrives late on an old aerial or cable, so every
hard edge carries a pale double."""
import math

from .. import _demo as demo
from ..schema import Technique


def analog_ghosting(cv, scene, strength=0.35, offset=0.03, echoes=2, decay=0.5, dy=0.0):
    """Draw `scene(cv)`, then redraw it `echoes` times on top as ghosts: the
    first shifted right by `offset` of the frame width at `strength` opacity,
    each further one shifted by another `offset` and `decay` times as strong.
    `dy` (also a fraction of the frame width) tilts the ghosts off the
    horizontal. `strength` 0 is the clean picture.

    In a film, wrap a shot's drawing: `analog_ghosting(cv, lambda c: shot(c, n), strength=s)`;
    animate `strength` and `offset` for a signal that drifts in and out."""
    scene(cv)
    alpha = strength
    for i in range(1, echoes + 1):
        if alpha <= 0.004:
            break
        with cv.layer(opacity=min(1.0, alpha), dx=offset * cv.width * i, dy=dy * cv.width * i):
            scene(cv)
        alpha *= decay


def _broadcast(cv):
    """The demo picture: a high-contrast still with hard edges for the ghost to double."""
    cv.fill(demo.BG)
    demo.dot(cv, demo.W * 0.74, demo.H * 0.34, r=120, color=demo.ACCENT)
    demo.word(cv, 'CHANNEL 3', demo.W * 0.4, demo.H * 0.42, size=150, weight=900)
    demo.card(cv, demo.W * 0.4, demo.H * 0.72, w=420, h=200, color=demo.TEAL)


def _draw(n, cv):
    # The signal is clean, then the reflection creeps in and settles, wavering like a loose aerial.
    p = demo.phase(n, 0.3, 1.4)
    t = n / demo.FPS
    wobble = 1 + 0.12 * math.sin(t * 7.0) * p
    analog_ghosting(cv, _broadcast, strength=0.38 * p, offset=0.03 * p * wobble)


TECHNIQUE = Technique(
    id='analog-ghosting',
    name='Analog ghosting',
    family='vfx',
    group='VHS & tape',
    aliases=('video ghosting', 'double image', 'echo ghost', 'multipath ghosting'),
    definition='Pale, slightly shifted duplicates of the picture trail just beside every edge, '
               'like a weak TV signal bouncing off something before it reaches the set.',
    phrasings=('give it that doubled, ghosty look of bad TV reception',
               'add a faint offset copy of the image like an old aerial picking up an echo',
               'make the edges smear into a see-through double like a worn VHS'),
    related=('double-exposure', 'static-noise', 'frame-delay-echo', 'linear-repeater-stagger', 'pixelation',
             'glitch-transition'),
    api=('videobuilder.techniques.vfx.analog_ghosting.analog_ghosting',),
    demo=lambda: demo.film(_draw),
)
