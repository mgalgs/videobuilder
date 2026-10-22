"""Accordion height expand: a collapsed section opens by growing from zero
height to its content's full height, and everything below it is pushed down
in step."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def expand_height(p, full, ease=vb.ease_in_out_quart):
    """The open height of a section of content height `full` at progress `p`
    (0 closed -> 1 open), eased. Run `p` from 1 to 0 to collapse it."""
    return full * ease(vb.clamp01(p))


def accordion_section(cv, x, y, w, header_h, body_h, p, header, body, ease=vb.ease_in_out_quart):
    """Draw one accordion section at (x, y), `w` wide, opened to progress `p`.

    `header(cv, x, y, w, h)` draws the always-visible header row; `body(cv, x,
    y, w, h)` draws the body at its full height `body_h`, clipped to the part
    that is open, so the content is revealed rather than squashed. Returns the
    section's current total height: lay the next row at `y + returned + gap`
    and it is pushed down as the section opens."""
    open_h = expand_height(p, body_h, ease)
    header(cv, x, y, w, header_h)
    if open_h > 0.5:
        with cv.clip(x, y + header_h, w, open_h):
            body(cv, x, y + header_h, w, body_h)
    return header_h + open_h


def chevron(cv, cx, cy, p, size=9, color=demo.INK, width=3):
    """A disclosure chevron at (cx, cy) pointing down at `p` = 0 and turned to
    point up at `p` = 1, for the header of an accordion section."""
    a = math.pi * vb.ease_in_out_quart(vb.clamp01(p))
    pts = [(-size, -size / 2), (0, size / 2), (size, -size / 2)]
    rot = [(cx + px * math.cos(a) - py * math.sin(a), cy + px * math.sin(a) + py * math.cos(a)) for px, py in pts]
    cv.line(*rot[0], *rot[1], color, width=width)
    cv.line(*rot[1], *rot[2], color, width=width)


PANEL = '#1f2128'
BODY = '#191b21'
X, W = demo.W / 2 - 230, 460
ROW_H, BODY_H, GAP = 72, 150, 12


def _bar(cv, x, y, w, alpha=0.8, h=9):
    cv.rect(x, y, w, h, demo.MUTED, radius=h / 2, alpha=alpha)


def _header(p):
    def draw(cv, x, y, w, h):
        cv.rect(x, y, w, h, PANEL, radius=14)
        _bar(cv, x + 24, y + 22, 180, 0.95)
        _bar(cv, x + 24, y + 42, 120, 0.55)
        chevron(cv, x + w - 36, y + h / 2, p)
    return draw


def _body(cv, x, y, w, h):
    cv.rect(x, y - 14, w, h + 14, BODY, radius=14)
    _bar(cv, x + 24, y + 22, 260)
    _bar(cv, x + 24, y + 44, 220, 0.6)
    _bar(cv, x + 24, y + 66, 170, 0.6)
    cv.rect(x + 24, y + 94, 110, 36, demo.TEAL, radius=8)


def _row(cv, y, dot):
    cv.rect(X, y, W, ROW_H, PANEL, radius=14)
    _bar(cv, X + 24, y + 31, 200 if dot == demo.ACCENT else 150, 0.85)
    demo.dot(cv, X + W - 36, y + ROW_H / 2, r=9, color=dot)


def draw(n, cv):
    p = demo.phase(n, 0.7, 1.7)
    top = (demo.H - (3 * ROW_H + 2 * GAP + BODY_H)) / 2
    h = accordion_section(cv, X, top, W, ROW_H, BODY_H, p, _header(p), _body)
    cv.mark('section', X, top, W, h)
    y = top + h + GAP
    _row(cv, y, demo.ACCENT)
    _row(cv, y + ROW_H + GAP, demo.MUTED)


CAPABILITY = Capability(
    id='accordion-height-expand',
    name='Accordion height expand',
    family='ui',
    group='Overlays & menus',
    aliases=('collapsible panel', 'disclosure expand', 'expandable section'),
    definition='A closed panel opens by smoothly growing taller until its contents are fully shown, '
               'nudging the rows beneath it further down as it grows.',
    phrasings=('click the row and it slides open to show more, pushing the rest down',
               'a FAQ item that expands to reveal its answer',
               'the section unfolds downward and the list makes room for it'),
    related=('accordion-fold-text', 'accordion-fold', 'container-transform', 'row-collapse-removal',
             'scroll-linked-clip-reveal', 'paper-fold-reveal'),
    api=('videobuilder.capabilities.ui.accordion_height_expand.accordion_section',
         'videobuilder.capabilities.ui.accordion_height_expand.expand_height',
         'videobuilder.capabilities.ui.accordion_height_expand.chevron'),
    demo=lambda: demo.film(draw),
)
