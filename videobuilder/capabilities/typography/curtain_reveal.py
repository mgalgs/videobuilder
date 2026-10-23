"""Curtain Reveal: two panels cover a line of text, meet in the middle, and
slide apart to the sides, uncovering the words from the centre outward."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def draw_curtain(cv, x, y, w, h, p, color, edge=None, edge_width=4, ease=vb.ease_in_out_quart):
    """Draw the two curtain panels over the box (x, y, w, h) at progress `p`
    (0 = closed, meeting in the middle; 1 = fully open). Draw whatever is
    being revealed first, then call this on top. Each panel slides outward
    within the box, clipped to it, so nothing spills past the frame of the
    reveal. `edge` (a colour, or a pair of colours for left and right) draws
    a thin line on each panel's inner, leading edge."""
    half = w / 2
    off = half * ease(vb.clamp01(p))
    if off >= half:
        return
    edges = (edge, edge) if edge is None or isinstance(edge, str) else tuple(edge)
    with cv.clip(x, y, w, h):
        lx, rx = x - off, x + half + off          # left panel's left, right panel's left
        cv.rect(lx, y, half, h, color)
        cv.rect(rx, y, half, h, color)
        if edges[0]:
            cv.rect(lx + half - edge_width, y, edge_width, h, edges[0])
        if edges[1]:
            cv.rect(rx, y, edge_width, h, edges[1])


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'CURTAIN'
    w, h = vb.text.block_size([text], f)
    bw, bh = w + 160, h + 120
    bx, by = (demo.W - bw) / 2, (demo.H - bh) / 2
    box = demo.word(cv, text, demo.W / 2, demo.H / 2, size=150)
    cv.mark('text', *box)
    draw_curtain(cv, bx, by, bw, bh, demo.phase(n, 1.1, 2.85), '#3a3f4b',
                 edge=(demo.ACCENT, demo.TEAL), edge_width=5)


CAPABILITY = Capability(
    id='curtain-reveal',
    name='Curtain reveal',
    family='typography',
    group='Per-unit reveals',
    aliases=('split curtain text', 'two-panel reveal', 'barn door text reveal'),
    definition='Two solid panels sitting edge to edge over a line of type slide apart sideways, '
               'uncovering the words from the middle out to the ends.',
    phrasings=('have the title appear as two blocks pull apart like stage curtains',
               'two panels part in the middle to show the text underneath',
               'open the headline like a pair of sliding doors'),
    related=('split-screen-comparison', 'shutter-slat-reveal', 'text-mask-reveal', 'split-screen-transition',
             'zoom-out-reveal', 'accordion-fold-text'),
    api=('videobuilder.capabilities.typography.curtain_reveal.draw_curtain',),
    demo=lambda: demo.film(draw),
)
