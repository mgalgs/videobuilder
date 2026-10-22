"""Avatar Stack Spread: a row of overlapping profile circles (a facepile)
slides apart into evenly spaced, separate avatars when the pointer rests on
the group, and closes back up when it leaves."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def stack_centres(n, cx, r, p, overlap=0.4, gap=0.3):
    """The x centres of `n` avatars of radius `r` in a row centred on `cx`, at
    spread `p` (0 -> 1). At 0 neighbours overlap by `overlap` of a diameter;
    at 1 they stand apart with `gap` of a diameter between them. The row
    grows evenly from its middle, so the group stays centred."""
    step = 2 * r * ((1 - overlap) + (overlap + gap) * p)
    return [cx + (i - (n - 1) / 2) * step for i in range(n)]


def draw_avatar(cv, cx, cy, r, color, initials='', ring=demo.BG, ring_width=None):
    """One avatar: a filled circle with optional `initials`, inside a `ring`
    of the background colour that cuts it cleanly from the one beneath."""
    rw = r * 0.12 if ring_width is None else ring_width
    cv.sector(cx, cy, r + rw, 0, 2 * math.pi, ring)
    cv.sector(cx, cy, r, 0, 2 * math.pi, color)
    if initials:
        demo.word(cv, initials, cx, cy, size=round(r * 0.8), color=demo.INK, weight=800)


def draw_avatar_stack(cv, avatars, cx, cy, p, r=56, overlap=0.4, gap=0.3, ring=demo.BG):
    """A facepile at spread `p` (0 stacked, 1 spread; an overshooting ease
    such as `vb.ease_out_back` is fine). `avatars` is a list of
    `(color, initials)`; each later one sits over the one to its left. Drawn
    centred at (cx, cy). Returns the Box around the row."""
    xs = stack_centres(len(avatars), cx, r, p, overlap, gap)
    for x, (color, initials) in zip(xs, avatars):
        draw_avatar(cv, x, cy, r, color, initials, ring=ring)
    pad = r * 1.12
    box = vb.Box(xs[0] - pad, cy - pad, xs[-1] - xs[0] + 2 * pad, 2 * pad)
    cv.mark('avatars', *box)
    return box


def draw_pointer(cv, x, y, size=34, color=demo.INK, edge=demo.BG):
    """An arrow mouse pointer with its tip at (x, y)."""
    s = size / 34
    pts = [(0, 0), (0, 27), (7, 21), (12, 32), (17, 30), (12, 19), (21, 19)]
    c = cv.ctx
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.move_to if i == 0 else c.line_to)(x + px * s, y + py * s)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(edge))
    c.set_line_width(2 * s)
    c.stroke()


AVATARS = [(demo.ACCENT, 'AK'), (demo.TEAL, 'MJ'), ('#6c6fd8', 'RS'), ('#e0a43a', 'LP'), ('#8e5fc2', 'DT')]


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    # The pointer glides in and comes to rest over the group; the group opens up under it.
    m = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.0))
    px, py = demo.W * 0.78 + (cx + 30 - demo.W * 0.78) * m, demo.H * 0.82 + (cy + 10 - demo.H * 0.82) * m
    p = vb.ease_out_back(demo.phase(n, 1.0, 1.7))
    draw_avatar_stack(cv, AVATARS, cx, cy, p)
    draw_pointer(cv, px, py)


CAPABILITY = Capability(
    id='avatar-stack-spread',
    name='Avatar stack spread',
    family='ui',
    group='Cursor & hover',
    aliases=('facepile expand', 'overlap spread', 'avatar group hover'),
    definition='A row of overlapping profile pictures slides apart into separate, evenly spaced circles '
               'when the pointer hovers over the group.',
    phrasings=('the stacked user avatars fan out when you mouse over them',
               'overlapping profile bubbles spread apart on hover',
               'hovering the facepile pulls the faces apart so each is visible'),
    related=('circle-packing', 'cross-dissolve', 'shape-boolean-merge', 'scroll-linked-clip-reveal',
             'comment-pop-up-stack', 'center-out-stagger'),
    api=('videobuilder.capabilities.ui.avatar_stack_spread.draw_avatar_stack',
         'videobuilder.capabilities.ui.avatar_stack_spread.stack_centres',
         'videobuilder.capabilities.ui.avatar_stack_spread.draw_avatar',
         'videobuilder.capabilities.ui.avatar_stack_spread.draw_pointer'),
    demo=lambda: demo.film(draw),
)
