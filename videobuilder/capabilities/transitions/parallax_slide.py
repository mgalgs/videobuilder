"""Parallax Slide: the incoming scene slides across the outgoing one, and
each scene's layers travel at their own speed -- backdrops lag behind the
seam, foreground pieces outrun it -- so the move reads as depth."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _layers(scene, back):
    """A scene as `((depth, draw), ...)`, far first; a plain draw is one layer at `back`."""
    return ((back, scene),) if callable(scene) else tuple(scene)


def parallax_slide(cv, a, b, p, back=0.5, ease=vb.ease_in_out_quart, edge='#000000'):
    """Draw the slide at progress `p` (0 -> 1): `b` enters from the right as
    `a` leaves to the left, the seam between them crossing the frame once.

    `a` and `b` are each a draw `scene(cv)` or a sequence of layers
    `(depth, draw)`, far first. A layer moves `depth` frame-widths over the
    whole slide: 1 keeps pace with the seam, under 1 lags (a backdrop, seen
    through its own scene's window), over 1 overtakes it (a foreground piece
    that leaves early or lands late). A plain draw is one layer at `back`.
    Each scene is clipped to its side of the seam; `edge` (None for none)
    shades the seam so the incoming scene reads as sliding over.

    In a film, call it inside an overlap, e.g. `parallax_slide(cv,
    [(0.4, sky_a), (1.6, title_a)], [(0.4, sky_b), (1.6, title_b)], f / overlap_frames)`."""
    e = ease(vb.clamp01(p))
    w, h = cv.width, cv.height
    seam = w * (1 - e)
    with cv.clip(0, 0, seam, h):
        for depth, draw in _layers(a, back):
            with cv.layer(dx=-w * e * depth):
                draw(cv)
    with cv.clip(seam, 0, w - seam, h):
        for depth, draw in _layers(b, back):
            with cv.layer(dx=w * (1 - e) * depth):
                draw(cv)
    if edge is not None and 0 < e < 1:
        for i in range(12):  # a soft shadow on the outgoing side, darkest at the seam
            cv.rect(seam - (i + 1) * 5, 0, 5, h, edge, alpha=0.05 * (12 - i) / 12)


# ---- the demo: each scene is a slow backdrop and a fast card ----

def _back_a(cv):
    demo.scene_a(cv)


def _front_a(cv):
    demo.card(cv, demo.W / 2, demo.H / 2, w=420, h=260)


def _back_b(cv):
    cv.fill('#e9e6df')
    for i in range(-4, 26):
        x = i * 90
        cv.line(x, demo.H, x + demo.H * 0.6, 0, '#d4cfc3', width=18)
    f = demo.font(28, 800)
    vb.text.draw(cv, ['Scene B'], f, 40, 32, demo.BG)


def _front_b(cv):
    demo.card(cv, demo.W / 2, demo.H / 2, w=420, h=260, color=demo.TEAL)


def _demo_slide(cv, a, b, p):
    parallax_slide(cv, [(0.35, _back_a), (1.7, _front_a)], [(0.35, _back_b), (1.7, _front_b)], p)


def _scene_a(cv):
    _back_a(cv)
    _front_a(cv)


def _scene_b(cv):
    _back_b(cv)
    _front_b(cv)


CAPABILITY = Capability(
    id='parallax-slide',
    name='Parallax slide',
    family='transitions',
    group='Slides and Pushes',
    aliases=('depth slide', 'layered slide', 'parallax push'),
    definition='The next scene slides in sideways over the last one while each scene\'s background '
               'drifts slowly and its foreground pieces race ahead, so the move feels deep.',
    phrasings=('slide to the next scene with a parallax effect',
               'push across to the next shot with the background moving slower than the foreground',
               'a sideways slide where the layers move at different speeds'),
    related=('scroll-parallax-layers', 'parallax-layers', 'pointer-parallax-layers', 'parallax-letter-layers',
             'two-point-five-d-photo-parallax', 'layered-fog-bands'),
    api=('videobuilder.capabilities.transitions.parallax_slide.parallax_slide',),
    demo=lambda: demo.two_scenes(_demo_slide, a=_scene_a, b=_scene_b, start=1.3, length=1.4),
)
