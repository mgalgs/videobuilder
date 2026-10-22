"""Hamburger to X: a three-bar menu icon turns into a close icon -- the outer
bars slide together onto the middle one, which fades away, then they turn
about the centre into a cross. Run backwards, the X turns back into a menu."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _bar(cv, cx, cy, length, thickness, angle, color, alpha=1.0):
    """A rounded bar centred at (cx, cy), turned `angle` radians."""
    cv.ctx.save()
    cv.ctx.translate(cx, cy)
    cv.ctx.rotate(angle)
    cv.rect(-length / 2, -thickness / 2, length, thickness, color, radius=thickness / 2, alpha=alpha)
    cv.ctx.restore()


def hamburger_to_x(cv, cx, cy, p, size=120, color=demo.INK, thickness=None, gap=None, split=0.5):
    """Draw the menu icon centred at (cx, cy) at progress `p`: 0 is three
    stacked bars (a hamburger), 1 is an X. For the first `split` of the move
    the top and bottom bars slide in onto the middle bar as it fades and
    shrinks; for the rest they rotate +45 and -45 degrees into a cross. The
    bars are `size` long and `thickness` thick (default `size` / 8), `gap`
    apart (default `size` / 3). Pass `1 - p` to morph X back to a hamburger.
    Returns the icon's Box."""
    thickness = thickness or size / 8
    gap = gap if gap is not None else size / 3
    p = vb.clamp01(p)
    slide = vb.ease_in_out_quart(vb.clamp01(p / split)) if split > 0 else 1.0
    turn = vb.ease_out_back(vb.clamp01((p - split) / (1 - split))) if split < 1 else float(p >= 1)
    offset = gap * (1 - slide)
    angle = math.pi / 4 * turn
    _bar(cv, cx, cy, size * (1 - 0.6 * slide), thickness, 0, color, alpha=1 - slide)
    _bar(cv, cx, cy - offset, size, thickness, angle, color)
    _bar(cv, cx, cy + offset, size, thickness, -angle, color)
    half = size / 2 + thickness / 2
    return vb.Box(cx - half, cy - half, 2 * half, 2 * half)


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    p = demo.phase(n, 0.5, 1.2) - demo.phase(n, 2.0, 2.7)  # to the X, hold, and back to the menu
    pressed = max(0.0, 1 - abs(n / demo.FPS - 0.5) / 0.12, 1 - abs(n / demo.FPS - 2.0) / 0.12)
    s = 300 * (1 - 0.06 * pressed)
    x, y = cx - s / 2, cy - s / 2
    cv.shadow(x, y, s, s, radius=60, dy=14, blur=36, color=(0, 0, 0, 0.45))
    cv.rect(x, y, s, s, demo.ACCENT, radius=60)
    box = hamburger_to_x(cv, cx, cy, p, size=150 * (1 - 0.06 * pressed), color=demo.INK)
    cv.mark('icon', *box)


TECHNIQUE = Technique(
    id='hamburger-to-x',
    name='Hamburger to X',
    family='ui',
    group='Toggles & controls',
    aliases=('menu to close', 'hamburger menu animation', 'menu icon morph', 'burger to cross'),
    definition='A three-line menu icon folds into a close cross: the outer lines slide onto the middle one, '
               'which disappears, then swing round into an X.',
    phrasings=('the menu button turns into an X when you tap it',
               'animate the three-line icon into a close button',
               'the burger icon morphs into a cross and back'),
    related=('context-menu-origin-reveal', 'radial-menu-fan-out', 'sidebar-collapse-width',
             'dropdown-stagger-reveal', 'icon-state-morph', 'text-to-shape-morph'),
    api=('videobuilder.techniques.ui.hamburger_to_x.hamburger_to_x',),
    demo=lambda: demo.film(draw),
)
