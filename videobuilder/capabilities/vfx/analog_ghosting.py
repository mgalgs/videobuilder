"""Analog ghosting: faint copies of the picture sit a little to the right of
it, as a reflected signal arrives late on an old aerial or cable, so every
hard edge carries a pale double."""
import math

import cairo

from .. import _demo as demo
from ..schema import Capability


def analog_ghosting(cv, scene, strength=0.35, offset=0.03, echoes=2, decay=0.5, dy=0.0, background=None):
    """Draw `scene(cv)` with `echoes` ghosts of it: the first shifted right
    by `offset` of the frame width at `strength` opacity, each further one
    shifted by another `offset` and `decay` times as strong. `dy` (also a
    fraction of the frame width) tilts the ghosts off the horizontal.
    `strength` 0 is the clean picture.

    The clean picture always stays at full strength; only the trailing
    doubles are pale. With `background` (a colour, or a callable taking the
    canvas) it is drawn once, the ghosts go on it, and `scene` -- then only
    the foreground -- is drawn clean on top, so a ghost shows only where
    nothing covers it. Without it, `scene` may paint its own full-frame fill,
    and each ghost is laid over the clean picture with a lighten blend, so
    its copy of that fill never veils what is beneath.

    In a film, wrap a shot's drawing: `analog_ghosting(cv, lambda c: shot(c, n), strength=s)`;
    animate `strength` and `offset` for a signal that drifts in and out."""
    ghosts = []
    alpha = strength
    for i in range(1, echoes + 1):
        if alpha <= 0.004:
            break
        ghosts.append((min(1.0, alpha), offset * cv.width * i, dy * cv.width * i))
        alpha *= decay
    if background is not None:
        if callable(background):
            background(cv)
        else:
            cv.fill(background)
        # Faintest first, so the stronger, nearer ghost sits over the further one.
        for a, gx, gy in reversed(ghosts):
            with cv.layer(opacity=a, dx=gx, dy=gy):
                scene(cv)
        scene(cv)
        return
    scene(cv)
    c = cv.ctx
    for a, gx, gy in ghosts:
        c.save()
        c.push_group()
        c.translate(gx, gy)
        scene(cv)
        c.pop_group_to_source()
        c.set_operator(cairo.OPERATOR_LIGHTEN)
        c.paint_with_alpha(a)
        c.restore()


def _broadcast(cv):
    """The demo picture: a high-contrast still with hard edges for the ghost to double."""
    cv.fill(demo.BG)
    demo.dot(cv, demo.W * 0.74, demo.H * 0.34, r=120, color=demo.ACCENT)
    demo.word(cv, 'CHANNEL 3', demo.W * 0.46, demo.H * 0.42, size=120, weight=900)
    demo.card(cv, demo.W * 0.4, demo.H * 0.72, w=420, h=200, color=demo.TEAL)


def _draw(n, cv):
    # The signal is clean, then the reflection creeps in and settles, wavering like a loose aerial.
    p = demo.phase(n, 0.3, 1.4)
    t = n / demo.FPS
    wobble = 1 + 0.12 * math.sin(t * 7.0) * p
    analog_ghosting(cv, _broadcast, strength=0.38 * p, offset=0.03 * p * wobble)


CAPABILITY = Capability(
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
    api=('videobuilder.capabilities.vfx.analog_ghosting.analog_ghosting',),
    demo=lambda: demo.film(_draw),
)
