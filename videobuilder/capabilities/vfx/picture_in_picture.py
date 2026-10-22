"""Picture-in-picture: a second, smaller shot plays in a framed window in one
corner of the main shot, with its own border and drop shadow."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def inset_box(cv, at='bottom-right', size=0.3, margin=48):
    """The inset window's Box: `size` of the frame's width, the frame's aspect,
    placed at anchor `at` ('top-left', 'bottom-right', ...) `margin` px in."""
    frame = vb.Box.of(cv)
    w = frame.w * size
    return frame.anchor(w, w * frame.h / frame.w, at, margin)


def picture_in_picture(cv, main, inset, p=1.0, at='bottom-right', size=0.3, margin=48,
                       border=6, border_color='#f4f1ea', radius=14):
    """Draw `main(cv)` full frame, then `inset(cv)` -- also drawn as if full
    frame -- shrunk into a bordered, shadowed window at corner `at`.

    `p` (0 -> 1) brings the window in: it grows from its corner with a small
    overshoot while fading up; leave it at 1 to just show it. Run `p` back
    from 1 to 0 to take it away. Returns the window's Box.

    In a film: `picture_in_picture(cv, lambda c: talk(c, shot), lambda c: screen(c, shot))`."""
    main(cv)
    p = vb.clamp01(p)
    if p <= 0:
        return None
    full = inset_box(cv, at, size, margin)
    box = full.scaled(0.55 + 0.45 * vb.ease_out_back(p), origin=at)
    k = box.w / cv.width
    alpha = vb.clamp01(p * 2.5)
    with cv.layer(opacity=alpha):
        cv.shadow(*box, radius=radius, dy=14, blur=36, color=(0, 0, 0, 0.55))
        cv.rect(*box.pad(-border), border_color, radius=radius + border)
        with cv.clip(*box, radius=radius):
            with cv.layer(dx=box.x, dy=box.y, scale=k):
                inset(cv)
    cv.mark('inset', *box)
    return box


def _main(n):
    def draw(cv):
        img = demo.photo()
        z = 1 + 0.06 * n / (demo.FPS * demo.SECONDS)  # a slow push so the main shot reads as footage
        cv.view(img, vb.Box.of(cv), scale=z * max(demo.W / img.w, demo.H / img.h))
        f = demo.font(30, 800)
        vb.text.draw(cv, ['Main shot'], f, 40, 32, demo.INK)
    return draw


def _inset(n):
    def draw(cv):
        cv.fill('#e9e6df')
        t = n / demo.FPS
        demo.card(cv, demo.W / 2 + 260 * math.sin(t * 2.2), demo.H / 2 + 40, w=420, h=260, color=demo.TEAL)
        f = demo.font(80, 800)
        vb.text.draw(cv, ['Inset'], f, 70, 60, demo.BG)
    return draw


def draw(n, cv):
    picture_in_picture(cv, _main(n), _inset(n), demo.phase(n, 0.5, 1.2), border_color=demo.ACCENT)


CAPABILITY = Capability(
    id='picture-in-picture',
    name='Picture-in-picture',
    family='vfx',
    group='Editing & frame',
    aliases=('PiP', 'inset window', 'floating inset'),
    definition='A second, smaller video sits in its own framed, shadowed box in a corner '
               'while the main shot keeps playing behind it.',
    phrasings=('put a small video box in the corner over the main footage',
               'show the webcam in a little window while the screen recording plays',
               'pop a mini player up in the bottom corner'),
    related=('film-edge-frame', 'angled-lower-third', 'pan', 'shutter-wipe', 'scroll-linked-clip-reveal',
             'corner-wipe'),
    api=('videobuilder.capabilities.vfx.picture_in_picture.picture_in_picture',
         'videobuilder.capabilities.vfx.picture_in_picture.inset_box'),
    demo=lambda: demo.film(draw),
)
