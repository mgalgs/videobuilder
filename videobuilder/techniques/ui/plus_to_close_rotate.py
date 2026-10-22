"""Plus to close rotate: a plus icon turns an eighth of a turn and becomes an
x as the thing it controls opens, and turns back as it closes."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

PANEL = '#1d1f26'


def plus_angle(p, turn=math.pi / 4, overshoot=True):
    """The icon's rotation in radians at progress `p` (0 = plus, 1 = x):
    `turn` (45 degrees) at the end, overshooting a touch on the way there
    unless `overshoot` is False. To open then close, draw at
    `plus_angle(opening) - plus_angle(closing)`."""
    p = vb.clamp01(p)
    return turn * (vb.ease_out_back(p) if overshoot else vb.ease_in_out_quart(p))


def draw_plus_close(cv, cx, cy, size, angle, color, width=None, alpha=1.0):
    """A plus centred at (cx, cy), arms `size` px end to end, rotated by
    `angle` radians (from `plus_angle`): a plus at 0, a close x at 45
    degrees. Arms are `width` px thick (default `size` / 8) with round ends."""
    width = width or size / 8
    a, r = angle, size / 2
    for arm in (a, a + math.pi / 2):
        dx, dy = r * math.cos(arm), r * math.sin(arm)
        cv.line(cx - dx, cy - dy, cx + dx, cy + dy, color, width=width, alpha=alpha)
        for sx, sy in ((cx - dx, cy - dy), (cx + dx, cy + dy)):
            demo.dot(cv, sx, sy, r=width / 2, color=color, alpha=alpha)


def _mix(c0, c1, t):
    a, b = vb.canvas.rgba(c0, 1.0), vb.canvas.rgba(c1, 1.0)
    return tuple(255 * (x + (y - x) * t) for x, y in zip(a[:3], b[:3]))


def draw(n, cv):
    opening, closing = demo.phase(n, 0.6, 1.2), demo.phase(n, 2.0, 2.6)
    t = opening - closing                                           # opens, holds, closes
    press = max(1 - abs(n / demo.FPS - 0.6) / 0.12, 1 - abs(n / demo.FPS - 2.0) / 0.12, 0)
    w, head, body = 760, 150, 260
    h = head + body * vb.ease_in_out_quart(t)
    x, y = (demo.W - w) / 2, demo.H / 2 - (head + body) / 2
    cv.shadow(x, y, w, h, radius=24, dy=12, blur=32, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, PANEL, radius=24)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=24)
    cv.rect(x + 48, y + 52, 300, 18, demo.INK, radius=9, alpha=0.9)
    cv.rect(x + 48, y + 86, 200, 14, demo.MUTED, radius=7, alpha=0.7)
    with cv.clip(x, y + head, w, h - head):
        for i, bw in enumerate((560, 500, 420)):
            cv.rect(x + 48, y + head + 10 + i * 40, bw, 14, demo.MUTED, radius=7, alpha=0.55 * t)
        cv.rect(x + 48, y + head + 150, 150, 52, demo.TEAL, radius=14, alpha=t)
    bx, by, br = x + w - 48 - 44, y + head / 2, 44 * (1 - 0.1 * press)
    demo.dot(cv, bx, by, r=br, color=_mix(demo.LINE, demo.ACCENT, vb.clamp01(t)))
    draw_plus_close(cv, bx, by, 40, plus_angle(opening) - plus_angle(closing), demo.INK, width=6)
    cv.mark('icon', bx - br, by - br, 2 * br, 2 * br)


TECHNIQUE = Technique(
    id='plus-to-close-rotate',
    name='Plus to close rotate',
    family='ui',
    group='Toggles & controls',
    aliases=('expand toggle icon', 'plus rotate', 'plus to x'),
    definition='A plus sign turns an eighth of a turn to read as an x while the panel it '
               'belongs to expands, then spins back when the panel folds shut.',
    phrasings=('the plus button turns into an x when the section opens',
               'rotate the add icon 45 degrees so it becomes a close button',
               'an accordion toggle whose plus twists into a cross'),
    related=('word-flip-in', 'context-menu-origin-reveal', 'password-reveal-toggle', 'speed-dial-fan',
             'sidebar-collapse-width', 'hover-lift'),
    api=('videobuilder.techniques.ui.plus_to_close_rotate.draw_plus_close',
         'videobuilder.techniques.ui.plus_to_close_rotate.plus_angle'),
    demo=lambda: demo.film(draw),
)
