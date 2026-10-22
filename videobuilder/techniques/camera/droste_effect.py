"""Droste effect: a picture holds a smaller framed copy of itself, which holds
a smaller copy again, nesting down to a point; the camera pushes in for ever,
each copy growing to fill the frame just as the next one takes its place."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def droste(cv, draw, p=0.0, ratio=0.42, cx=None, cy=None, border=8, border_color='#f4f1ea', min_px=3):
    """Paint whatever `draw(cv)` paints as a Droste picture: the frame-sized
    scene, with a copy of itself scaled by `ratio` about the point (cx, cy)
    (default the frame's centre) set into it, a copy of that inside, and so
    on until a copy is under `min_px` wide. Every level, the outermost too,
    gets a `border`-px frame (scaled with it) in `border_color`, and each
    copy a soft shadow, so the nesting reads as pictures within the picture
    and the loop has no seam.

    `p` is the zoom: 0 shows the scene as drawn, 1 has pushed in by
    1/`ratio` so the first copy fills the frame, which looks exactly like 0
    again. Run `p` linearly (or any amount past 1; only its fractional part
    counts) for an endless zoom loop. Marks `draw` makes are dropped: the
    picture is no longer where they say."""
    c = cv.ctx
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    marks = len(cv.marks)
    c.push_group()
    draw(cv)
    src = c.pop_group()
    del cv.marks[marks:]
    src.set_filter(cairo.FILTER_GOOD)
    s = ratio ** -(p % 1.0)      # the outermost copy's scale: 1 -> 1/ratio
    first = True
    while s * w >= min_px:
        c.save()
        c.translate(cx, cy)
        c.scale(s, s)
        c.translate(-cx, -cy)
        if not first:
            cv.shadow(0, 0, w, h, dy=6 / ratio, blur=40 / ratio, color=(0, 0, 0, 0.45))
        c.rectangle(0, 0, w, h)
        c.clip()
        c.set_source(src)
        c.paint()
        if border > 0:
            b = border / ratio   # in this copy's own units, so it looks `border` px when the copy is ratio-sized
            cv.outline(b / 2, b / 2, w - b, h - b, border_color, width=b)
        c.restore()
        first = False
        s *= ratio


def _scene(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    f = demo.font(30, 800)
    vb.text.draw(cv, ['Droste'], f, 48, 40, demo.INK)


FOCUS = (demo.W * 0.6, demo.H * 0.5)


def _draw(n, cv):
    # One and a half steady laps of the push-in over the demo: constant speed, so it reads as endless.
    droste(cv, _scene, p=1.5 * n / (demo.FPS * demo.SECONDS), cx=FOCUS[0], cy=FOCUS[1])


TECHNIQUE = Technique(
    id='droste-effect',
    name='Droste effect',
    family='camera',
    group='Shader looks',
    aliases=('recursive picture', 'picture-in-picture recursion', 'self-embedding image', 'infinite picture',
             'mise en abyme', 'infinite zoom'),
    definition='A frame shows a shrunken copy of itself set inside it, which holds a smaller copy again, '
               'and the view keeps pushing into that tunnel of pictures without end.',
    phrasings=('put the picture inside itself over and over, getting smaller each time',
               'an endless zoom into a picture within a picture within a picture',
               'make the shot recursive, like a frame holding a copy of the whole frame'),
    related=('multiples', 'pixelate-transition', 'blur-up-image-load', 'image-crossfade-slideshow',
             'ascii-art-render', 'pixelation'),
    api=('videobuilder.techniques.camera.droste_effect.droste',),
    demo=lambda: demo.film(_draw),
)
