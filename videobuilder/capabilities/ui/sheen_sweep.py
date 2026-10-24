"""Sheen sweep: the button-clipped version of Shine glint sweep
(`../typography/shine_glint_sweep.py`, which keeps the capability) -- a
slanted streak of light crossing a surface once, here clipped to a
button's rounded face instead of a word's glyphs; the two share four
aliases. This module's own code stays (a film may still import it), but it
is no longer a capability of its own."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'shine-glint-sweep'


def sheen(cv, x, y, w, h, p, radius=0, width=None, angle=20, color='#ffffff', strength=0.55):
    """Draw the sheen over the box (x, y, w, h) at progress `p` (0 -> 1): a band
    `width` px wide (default a third of `h` plus a tenth of `w`), leaning
    `angle` degrees from vertical, brightest along its middle and fading to
    nothing at its edges. It starts fully off the left edge and ends fully
    off the right, clipped to the box with corner `radius`, so p <= 0 or
    p >= 1 draws nothing. Draw it after the button's face and before or
    after its label (after makes the label catch the light too).

    In a film, call it on a hover or on a repeat, e.g.
    `sheen(cv, *button_box, radius=24, p=(t % 2.5) / 0.8)`."""
    if p <= 0 or p >= 1:
        return
    band = width if width is not None else h / 3 + w / 10
    lean = h * math.tan(math.radians(angle))
    travel = w + band + lean
    left = x - band - lean + travel * p  # the band's left edge, at the box's bottom
    c = cv.ctx
    with cv.clip(x, y, w, h, radius):
        c.new_path()
        c.move_to(left + lean, y)
        c.line_to(left + lean + band, y)
        c.line_to(left + band, y + h)
        c.line_to(left, y + h)
        c.close_path()
        mid = y + h / 2
        # Across the band, square to its slant, so both long edges fade out evenly.
        a = math.radians(angle)
        across = band * math.cos(a)
        x0 = left + lean / 2
        g = cairo.LinearGradient(x0, mid, x0 + across * math.cos(a), mid + across * math.sin(a))
        for stop, a in ((0.0, 0.0), (0.35, 0.6), (0.5, 1.0), (0.65, 0.6), (1.0, 0.0)):
            g.add_color_stop_rgba(stop, *vb.rgba(color, strength * a))
        c.set_source(g)
        c.fill()


def _button(cv, x, y, w, h, r):
    cv.shadow(x, y, w, h, radius=r, dy=10, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, demo.ACCENT, radius=r)


def draw(n, cv):
    w, h, r = 520, 150, 34
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    _button(cv, x, y, w, h, r)
    demo.word(cv, 'Continue', demo.W / 2, demo.H / 2, size=58, color=demo.BG)
    p = demo.phase(n, 1.3, 2.9)  # centred on the button at the poster frame (2.1 s)
    sheen(cv, x, y, w, h, p * p * (3 - 2 * p), radius=r, strength=0.65)
    cv.mark('button', x, y, w, h)
