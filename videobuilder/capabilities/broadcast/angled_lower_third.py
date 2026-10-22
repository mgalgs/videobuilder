"""Angled lower third: a name strap in the bottom-left of the frame built from
slanted bars -- a thin accent blade, a wide name bar and a narrower title bar
under it -- that sweep open one after another along a shared slanted edge,
hold, then sweep shut again."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...looks.kit import clip_to, fill


def slanted_bar(x, y, w, h, lean):
    """The four corners of a bar `w` x `h` whose bottom-left corner is at
    (x, y + h) and whose ends lean right by `lean` px per px of height: a
    parallelogram, the building block of an angled strap."""
    t = lean * h
    return [(x, y + h), (x + t, y), (x + w + t, y), (x + w, y + h)]


def _span(p, start, end):
    return vb.clamp01((p - start) / (end - start))


def draw_angled_lower_third(cv, name, title, x, y, show, hide=0.0, angle=16.0, name_font=None,
                            title_font=None, bar=demo.INK, ink=demo.BG, title_bar=demo.ACCENT,
                            title_ink=demo.INK, accent=demo.TEAL, pad=22, gap=6):
    """Draw an angled lower third with its top-left at about (x, y).

    `show` (0 -> 1) builds it in: the accent blade sweeps up, then the name
    bar and title bar wipe open left to right along their slanted ends, each
    line of text sliding in behind its bar's leading edge. `hide` (0 -> 1)
    takes it away again, the bars sweeping shut towards the left in reverse
    order. `angle` is the lean of every edge, in degrees from vertical; all
    the bars share one slanted left edge. Returns the Box the finished strap
    covers."""
    nf = name_font or demo.font(40, 800)
    tf = title_font or demo.font(22, 600)
    lean = math.tan(math.radians(angle))
    nw, nh = vb.text.block_size([name], nf)
    tw, th = vb.text.block_size([title], tf)
    name_h, title_h = nh + 18, th + 12
    blade_w = 14
    # the slanted left edge passes through (x0, y + total height); every bar starts on it
    total = name_h + gap + title_h
    x0 = x

    rows = [  # (top, height, full width, text, font, text size, bar colour, ink, build-in window)
        (y, name_h, nw + 2 * pad, name, nf, (nw, nh), bar, ink, (0.15, 0.7)),
        (y + name_h + gap, title_h, tw + 2 * pad, title, tf, (tw, th), title_bar, title_ink, (0.35, 0.95)),
    ]
    # blade: a thin accent bar left of the strap, rising up the whole height
    b_in = vb.ease_out_expo(_span(show, 0.0, 0.4))
    b_out = vb.ease_in_expo(_span(hide, 0.55, 1.0))
    grow = b_in * (1 - b_out)
    if grow > 0:
        bh = total * grow
        bx = x0 - blade_w - gap
        fill(cv, slanted_bar(bx, y + total - bh, blade_w, bh, lean), accent)
    for i, (top, h, w, text, f, (txw, txh), colour, text_ink, (s0, s1)) in enumerate(rows):
        e_in = vb.ease_out_expo(_span(show, s0, s1))
        o0 = 0.3 * (len(rows) - 1 - i)  # hide in reverse order: the last bar in goes first
        e_out = vb.ease_in_expo(_span(hide, o0, o0 + 0.6))
        reach = w * e_in * (1 - e_out)
        if reach <= 0.5:
            continue
        bx = x0 + lean * (y + total - (top + h))
        pts = slanted_bar(bx, top, reach, h, lean)
        cv.shape_shadow(slanted_bar(bx, top, w, h, lean) if reach >= w else pts, dy=6, blur=14,
                        color=(0, 0, 0, 0.35))
        fill(cv, pts, colour)
        slide = (1 - vb.ease_out_expo(_span(show, s0 + 0.12, s1 + 0.05))) + e_out
        with clip_to(cv, pts):
            tx = bx + pad + lean * h - slide * (txw + pad)
            vb.text.draw(cv, [text], f, tx, top + (h - txh) / 2, text_ink)
    width = max(lean * (y + total - r[0] - r[1]) + r[2] + lean * r[1] for r in rows)
    return vb.Box(x0 - blade_w - gap, y, width + blade_w + gap, total)


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.rect(0, demo.H * 0.55, demo.W, demo.H * 0.45, '#000000', alpha=0.25)
    box = draw_angled_lower_third(cv, 'MAYA OKAFOR', 'Field correspondent  ·  Lagos', 92, 382,
                                  demo.phase(n, 0.2, 1.4), demo.phase(n, 2.3, 2.95))
    cv.mark('lower-third', *box)


CAPABILITY = Capability(
    id='angled-lower-third',
    name='Angled lower third',
    family='broadcast',
    group='Lower thirds',
    aliases=('slanted lower third', 'skewed name strap', 'angled name super', 'slash lower third'),
    definition='A name caption near the bottom of the frame made of bars with slanted ends, '
               'which sweep open one after another, hold for a read, then sweep away.',
    phrasings=('put the speaker\'s name on a slanted bar in the corner',
               'a news-style name tag with angled edges that slides in and out',
               'a sporty lower third where the bars are cut on a diagonal'),
    related=('slant-axis-swing', 'low-poly-faceting', 'isometric-view', 'bend-deformer', 'dutch-angle',
             'taper-deformer'),
    api=('videobuilder.capabilities.broadcast.angled_lower_third.draw_angled_lower_third',
         'videobuilder.capabilities.broadcast.angled_lower_third.slanted_bar'),
    demo=lambda: demo.film(draw),
)
