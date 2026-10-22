"""Scale Zoom-Through: a word grows towards the viewer, faster and faster,
until the frame flies through a gap in it (the hole of an O), and the next
word rises out of the depth behind it to settle at its own size."""
import math
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@contextmanager
def scaled_about(cv, cx, cy, s, opacity=1.0):
    """A `cv.layer` that scales its drawing by `s` about the point (cx, cy),
    which stays put on screen."""
    with cv.layer(opacity=opacity, dx=cx * (1 - s), dy=cy * (1 - s), scale=s) as c:
        yield c


def scale_zoom_through(cv, a, b, p, focus=None, depth=60.0, start=0.5, cut=0.72,
                       ease=lambda t: t ** 2.5):
    """Draw the zoom-through at progress `p` (0 -> 1): `a(cv)` scales up about
    `focus` (default: the frame's centre) from 1 to `depth`, accelerating, and
    fades out over the last stretch before `cut`; from `start`, `b(cv)` grows
    behind it from small to full size, easing in to land. Aim `focus` at an
    opening in `a` (a letter's counter, a gap between words) so the frame
    passes through it and `b` shows through the hole.

    In a film, call it across the overlap of two shots, e.g.
    `scale_zoom_through(cv, lambda c: title(c, 'ZOOM'), lambda c: title(c, 'NEXT'), f / overlap, focus=o_hole)`."""
    fx, fy = focus if focus is not None else (cv.width / 2, cv.height / 2)
    if p >= start:
        q = vb.ease_out_quint(vb.clamp01((p - start) / (1 - start)))
        with scaled_about(cv, cv.width / 2, cv.height / 2, vb.log_lerp(0.05, 1.0, q),
                          opacity=vb.clamp01(q * 4)):
            b(cv)
    if p < cut:
        t = p / cut
        s = math.exp(math.log(depth) * ease(t))
        with scaled_about(cv, fx, fy, s, opacity=1 - vb.clamp01((t - 0.75) / 0.25)):
            a(cv)


# ---- demo ----

FIRST, SECOND = 'ZOOM', 'THROUGH'
SIZE = 220


def _font():
    return demo.font(SIZE, 900)


def _origin(text):
    w, h = vb.text.block_size([text], _font())
    return (demo.W - w) / 2, (demo.H - h) / 2


def _hole():
    """The middle of the first O's counter in FIRST, drawn centred."""
    f = _font()
    x, y = _origin(FIRST)
    lh = vb.text.line_height(f)
    content, baseline = vb.text._content(f)
    base = y + (lh - content) / 2 + baseline
    return x + vb.text.measure('Z', f) + vb.text.measure('O', f) / 2, base - 0.36 * SIZE


def _first(cv):
    box = demo.word(cv, FIRST, demo.W / 2, demo.H / 2, size=SIZE, weight=900)
    cv.mark('text', *box)


def _second(cv):
    box = demo.word(cv, SECOND, demo.W / 2, demo.H / 2, size=SIZE * 0.8, weight=900, color=demo.ACCENT)
    cv.mark('text', *box)


def draw(n, cv):
    p = demo.phase(n, 0.5, 2.5)
    if p <= 0:
        _first(cv)
    elif p >= 1:
        _second(cv)
    else:
        scale_zoom_through(cv, _first, _second, p, focus=_hole())


TECHNIQUE = Technique(
    id='scale-zoom-through',
    name='Scale zoom-through',
    family='typography',
    group='Stretch and squash',
    aliases=('zoom through text', 'fly through the letter', 'text zoom transition', 'scale through'),
    definition='A word swells towards the camera, picking up speed until the view passes right through '
               'an opening in its letters and the next word emerges from behind it.',
    phrasings=('zoom into the O of the title and come out on the next word',
               'the text grows so big we fly through it',
               'push the camera through the letters to reveal what is behind'),
    related=('zoom-through', 'zoom-through-shape', 'infinite-zoom-tunnel', 'punch-in', 'zoom-to-location-map',
             'ui-walkthrough-camera-zoom'),
    api=('videobuilder.techniques.typography.scale_zoom_through.scale_zoom_through',
         'videobuilder.techniques.typography.scale_zoom_through.scaled_about'),
    demo=lambda: demo.film(draw),
)
