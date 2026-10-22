"""Depth of field: everything at the focal distance stays crisp, and things
blur more the further they sit in front of or behind it, like a real lens
with a shallow focus band."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...type.kit import blurred


def defocus(z, focus, band=0.0, falloff=1.0, max_blur=40.0):
    """The blur radius (px) of something at depth `z` when the lens is focused
    at `focus` (both in any one unit, e.g. layer index or metres). Within
    `band` of the focus it is sharp; beyond that the blur grows by `max_blur`
    per `falloff` of distance, capped at `max_blur`."""
    off = max(0.0, abs(z - focus) - band)
    return max_blur * min(1.0, off / falloff) if falloff > 0 else (max_blur if off > 0 else 0.0)


def draw_at_depth(cv, box, z, focus, paint, alpha=1.0, **kw):
    """Draw `paint(c)` (which draws within `box`) blurred for depth `z`
    against the lens's `focus` (`kw` goes to `defocus`). Paint far things
    first so near, softer ones overlap them."""
    blurred(cv, box, defocus(z, focus, **kw), paint, alpha=alpha)


DEPTHS = (0, 1, 2, 3, 4, 5, 6)  # far -> near


def _sphere(c, x, y, r, color):
    demo.dot(c, x + r * 0.08, y + r * 1.05, r * 0.9, color='#000000', alpha=0.25)  # contact shadow
    demo.dot(c, x, y, r, color=color)
    demo.dot(c, x - r * 0.3, y - r * 0.32, r * 0.28, color='#ffffff', alpha=0.35)  # highlight


def draw(n, cv):
    # the focus plane glides from the middle sphere to a near one and back
    p = demo.phase(n, 0.5, 1.4) - demo.phase(n, 1.8, 2.7)
    focus = 3 + 2 * vb.ease_in_out_quart(p)
    for z in DEPTHS:
        t = z / (len(DEPTHS) - 1)
        x = demo.W * (0.84 - 0.66 * t)
        y = demo.H * (0.3 + 0.42 * t)
        r = 28 + 84 * t * t
        color = demo.ACCENT if z == 3 else demo.TEAL
        box = vb.Box(x - r, y - r, 2 * r, 2 * r * 2.0)
        draw_at_depth(cv, box, z, focus, lambda c, x=x, y=y, r=r, color=color: _sphere(c, x, y, r, color),
                      band=0.25, falloff=2.5, max_blur=36)
        cv.mark(f'z{z}', x - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='depth-of-field',
    name='Depth of field',
    family='camera',
    group='Depth',
    aliases=('DOF', 'shallow focus', 'bokeh blur', 'lens blur'),
    definition='Only things at one chosen distance from the camera stay crisp, while everything nearer '
               'or farther goes softer the further it is from that distance.',
    phrasings=('keep the middle object sharp and blur the ones in front and behind',
               'give it a shallow, cinematic focus so the background melts away',
               'make it look shot with a wide-open lens'),
    related=('focus-blur-out', 'bokeh-particles', 'gaussian-blur', 'focus-breathing', 'motion-blur',
             'character-blur-in'),
    api=('videobuilder.techniques.camera.depth_of_field.draw_at_depth',
         'videobuilder.techniques.camera.depth_of_field.defocus',
         'videobuilder.type.kit.blurred'),
    demo=lambda: demo.film(draw),
)
