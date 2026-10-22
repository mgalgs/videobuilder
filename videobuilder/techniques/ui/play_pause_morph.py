"""Play-pause morph: a media button's play triangle reshapes into the two
pause bars (and back) by sliding the corners of two four-point shapes, so
the icon never cuts or crossfades between states."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def play_pause_shapes(cx, cy, size, p, gap=0.22, bar=0.3):
    """The two filled quads of the icon at progress `p`: 0 is play, 1 is pause.
    `size` is the icon's height, centred at (cx, cy). Play is a right-pointing
    triangle split at its middle into a left trapezoid and a right sliver;
    pause is two bars `bar * size` wide with `gap * size` between them. Each
    corner moves in a straight line between the two. `p` above 1 (an
    overshooting ease) stretches the bars a touch past pause; below 0 it is
    held at play, since the arrow's tip would cross over itself."""
    p = max(0.0, p)
    h = size / 2
    top, bot = cy - h, cy + h
    # play: triangle with its centroid-ish weight shifted so it looks centred
    x0, x1 = cx - h * 0.8, cx + h * 1.0
    xm = (x0 + x1) / 2
    play = (((x0, top), (xm, cy - h / 2), (xm, cy + h / 2), (x0, bot)),
            ((xm, cy - h / 2), (x1, cy), (x1, cy), (xm, cy + h / 2)))
    b, g = bar * size, gap * size
    lx, rx = cx - g / 2 - b, cx + g / 2
    pause = (((lx, top), (lx + b, top), (lx + b, bot), (lx, bot)),
             ((rx, top), (rx + b, top), (rx + b, bot), (rx, bot)))
    return [[(ax + (bx - ax) * p, ay + (by - ay) * p) for (ax, ay), (bx, by) in zip(qa, qb)]
            for qa, qb in zip(play, pause)]


def draw_play_pause(cv, cx, cy, size, p, color, alpha=1.0, **kw):
    """Draw the play/pause icon at progress `p` (0 play -> 1 pause), filled in
    `color`. Feed `p` through an ease (e.g. `vb.ease_out_back`) for snap;
    `kw` goes to `play_pause_shapes`. Both quads fill as one path, so no
    seam shows where the triangle's halves meet."""
    c = cv.ctx
    c.new_path()
    for quad in play_pause_shapes(cx, cy, size, p, **kw):
        c.move_to(*quad[0])
        for pt in quad[1:]:
            c.line_to(*pt)
        c.close_path()
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()


def _toggle(t, at, dur=0.6):
    """Eased 0 -> 1 for a flip starting at `at` seconds, with a little overshoot."""
    return vb.ease_out_back(vb.clamp01((t - at) / dur))


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    flips = (0.7, 2.0)  # play -> pause, then pause -> play
    p = _toggle(t, flips[0]) - _toggle(t, flips[1])
    # a quick press: the button dips a touch at each flip
    press = max(math.exp(-((t - f - 0.05) / 0.09) ** 2) for f in flips)
    s = 1 - 0.06 * press
    r = 190 * s
    cv.shape_shadow([(cx + r * math.cos(a), cy + r * math.sin(a))
                     for a in (i * math.pi / 24 for i in range(48))], dy=10, blur=30, color=(0, 0, 0, 0.45))
    demo.dot(cv, cx, cy, r, color='#23262d')
    cv.arc(cx, cy, r, 0, 2 * math.pi, demo.LINE, width=2)
    draw_play_pause(cv, cx, cy, 150 * s, p, demo.INK)
    cv.mark('icon', cx - r, cy - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='play-pause-morph',
    name='Play-pause morph',
    family='ui',
    group='Toggles & controls',
    aliases=('media icon morph', 'triangle to bars', 'play/pause toggle'),
    definition='Pressing a media button bends its play arrow into the two pause bars, '
               'the corners sliding to their new spots instead of swapping icons.',
    phrasings=('the play button turns into a pause button smoothly',
               'animate the triangle reshaping into two bars when it starts playing',
               'a play/pause icon that morphs instead of switching'),
    related=('icon-state-morph', 'chart-type-morph', 'morph-cut', 'tape-wobble', 'morphing-shape-ident',
             'text-to-shape-morph'),
    api=('videobuilder.techniques.ui.play_pause_morph.draw_play_pause',
         'videobuilder.techniques.ui.play_pause_morph.play_pause_shapes'),
    demo=lambda: demo.film(draw),
)
