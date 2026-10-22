"""Swipe Action Row: a list row is dragged sideways and the coloured action
buttons hidden under it are uncovered, sharing the gap it leaves."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ROW = '#22242b'
CURSOR = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def swipe_row(cv, x, y, w, h, offset, actions, content=None, color=ROW, radius=18, font=None):
    """A list row at (x, y, w, h) slid left by `offset` px, uncovering
    `actions` -- `(label, color)` pairs, left to right -- in the strip it
    leaves on the right. The buttons split the uncovered width evenly, so
    they grow as the row moves; each label fades in once its button is wide
    enough to hold it. `content(cv, x, y, w, h)` draws the row's face (at its
    shifted place); `color` is the face. Everything stays inside the row's
    rounded outline. Returns the face's Box."""
    offset = max(0.0, offset)
    f = font or demo.font(max(14, round(h * 0.2)), 700)
    with cv.clip(x, y, w, h, radius):
        if offset > 0 and actions:
            bw = offset / len(actions)
            for i, (label, c) in enumerate(actions):
                bx = x + w - offset + i * bw
                cv.rect(bx, y, bw + 1, h, c)  # +1 hides the seam between buttons
                lw, lh = vb.text.block_size([label], f)
                a = vb.clamp01((bw - lw) / (lw * 0.6 + 1))
                if a > 0:
                    with cv.clip(bx, y, bw, h):
                        vb.text.draw(cv, [label], f, bx + (bw - lw) / 2, y + (h - lh) / 2, demo.INK, alpha=a)
        fx = x - offset
        cv.rect(fx, y, w, h, color, radius=radius)
        if content:
            content(cv, fx, y, w, h)
    cv.mark('row', fx, y, w, h)
    return vb.Box(fx, y, w, h)


def _face(dot):
    def draw(cv, x, y, w, h):
        demo.dot(cv, x + h * 0.5, y + h / 2, r=h * 0.2, color=dot)
        bar = h * 0.11
        cv.rect(x + h, y + h * 0.33, w * 0.36, bar, demo.INK, radius=bar / 2, alpha=0.85)
        cv.rect(x + h, y + h * 0.33 + bar * 2.2, w * 0.56, bar, demo.MUTED, radius=bar / 2, alpha=0.6)
    return draw


def _cursor(cv, x, y, k=1.6):
    pts = [(x + px * k, y + py * k) for px, py in CURSOR]
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(2)
    c.stroke()


ACTIONS = (('Archive', demo.TEAL), ('Delete', demo.ACCENT))
REACH = 360            # the open width: two 180 px buttons


def draw(n, cv):
    w, h, gap = 900, 120, 26
    x = (demo.W - w) / 2
    top = (demo.H - 3 * h - 2 * gap) / 2
    t = n / demo.FPS
    # Drag a little past the open width, let go, and spring back onto it.
    over = REACH * 1.15
    drag = vb.ease_in_out_quart(demo.phase(n, 0.6, 1.6)) * over
    settle = vb.spring(t - 1.6, **vb.damped(0.5, hz=2.2))
    offset = drag if t < 1.6 else over + (REACH - over) * settle
    for i in range(3):
        y = top + i * (h + gap)
        if i == 1:
            swipe_row(cv, x, y, w, h, offset, ACTIONS, content=_face(demo.ACCENT))
        else:
            cv.rect(x, y, w, h, ROW, radius=18)
            _face(demo.LINE)(cv, x, y, w, h)
    # The pointer grabs the row near its right end, pulls, then lets go and drifts off.
    gx, gy = x + w - 140, top + h + gap + h * 0.55
    away = demo.phase(n, 1.6, 2.2)
    cx = gx - drag + 40 * vb.ease_out_quint(away)
    cy = gy + 90 * vb.ease_out_quint(away) + 50 * (1 - vb.ease_out_quint(demo.phase(n, 0.0, 0.6)))
    _cursor(cv, cx, cy)


CAPABILITY = Capability(
    id='swipe-action-row',
    name='Swipe action row',
    family='ui',
    group='Gestures & drag',
    aliases=('row swipe actions', 'revealed row buttons', 'swipe to delete', 'swipe actions'),
    definition='A list item is pulled sideways by a finger or pointer, and coloured buttons such as '
               'archive or delete appear in the space it slides away from.',
    phrasings=('drag the list row left so the delete and archive buttons show underneath',
               'swipe a message aside to reveal its actions',
               'the row slides over and colourful action buttons peek out behind it'),
    related=('hover-reveal-actions', 'stacked-card-reveal', 'magnetic-button', 'hover-lift',
             'highlighter-swipe', 'spring-drag-letters'),
    api=('videobuilder.capabilities.ui.swipe_action_row.swipe_row', 'videobuilder.spring', 'videobuilder.damped'),
    demo=lambda: demo.film(draw),
)
