"""Frame-by-frame hand-drawn animation: motion made of separate drawings, each
held for a couple of frames (on twos) and each traced afresh, so the ink line
shimmers ("boils") and the movement steps rather than glides."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def held(n, on=2):
    """The frame whose pose frame `n` shows when every drawing is held for
    `on` frames (2: on twos, 12 drawings a second at 24-30 fps). Sample the
    motion at `held(n)` instead of `n` and it steps from drawing to drawing."""
    return n - n % on


def drawing(n, on=2):
    """Which drawing (0, 1, 2 ...) frame `n` shows when each is held `on` frames."""
    return n // on


def sketch(points, which, seed=0, amount=2.5, wander=0.35):
    """`points` as drawing number `which` traces them: a seeded hand wobble of
    about `amount` px that is the same for every frame of one drawing and
    different for the next, so a line that holds still still boils."""
    return vb.paths.jitter(points, f'{seed}:{which}', amount=amount, wander=wander)


def draw_sketch(cv, points, which, color, width=4, seed=0, amount=2.5, passes=2, closed=False, alpha=1.0):
    """Ink `points` as drawing number `which`: `passes` overlapping wobbly
    strokes, the way a pencil line is gone over twice. A `closed` outline is
    traced a little past its start, so the seam overlaps like a real stroke."""
    pts = list(points)
    if closed and len(pts) > 2:
        pts = pts + pts[:max(2, len(pts) // 12)]
    for k in range(passes):
        w = width if k == 0 else width * 0.55
        vb.paths.draw(cv, sketch(pts, which, f'{seed}/{k}', amount), color, width=w,
                      alpha=alpha * (1 if k == 0 else 0.7))


def _ellipse(cx, cy, rx, ry, tilt=0.0, steps=40):
    c, s = math.cos(tilt), math.sin(tilt)
    out = []
    for i in range(steps):
        a = 2 * math.pi * i / steps
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


R, GROUND = 34, demo.H - 70
HOPS = (1.0, 0.55, 0.3)  # each bounce's height, as a share of the first


def _ball(f):
    """The ball's centre and squash/stretch at frame `f` of the demo."""
    t = vb.clamp01(f / (demo.FPS * demo.SECONDS))
    x = 140 + (demo.W - 280) * t
    k = min(int(t * len(HOPS)), len(HOPS) - 1)
    u = t * len(HOPS) - k  # 0 -> 1 across this hop
    lift = 4 * u * (1 - u) * HOPS[k] * 300
    speed = abs(1 - 2 * u)  # fastest at the ground
    if lift < 10:  # touching down: squash flat and wide
        sy = 0.68 + 0.32 * lift / 10
    else:  # in the air: stretch along the fall
        sy = 1 + 0.28 * speed * HOPS[k]
    return x, GROUND - R * sy - lift, R / math.sqrt(sy), R * sy


def _pose(cv, f, which, ink, fill, alpha=1.0):
    x, y, rx, ry = _ball(f)
    outline = _ellipse(x, y, rx, ry)
    if fill:
        # the colour is painted under the line a touch off-register, like a cel
        vb.paths.draw(cv, sketch(_ellipse(x + 2, y + 2, rx - 2, ry - 2), which, 'paint', 1.0), fill,
                      fill=True, alpha=alpha)
    draw_sketch(cv, outline, which, ink, width=3.5, seed='ball', amount=3.0, closed=True, alpha=alpha)
    # a curved highlight stroke, re-drawn with each drawing too
    shine = [(x - rx * 0.55 * math.cos(a), y - ry * 0.55 * math.sin(a)) for a in (0.35, 0.6, 0.85, 1.1, 1.35)]
    draw_sketch(cv, shine, which, ink, width=2, seed='shine', amount=1.0, passes=1, alpha=alpha)
    return x, y, rx, ry


def draw(n, cv):
    on = 2
    which, f = drawing(n, on), held(n, on)
    # onion skins: the last few drawings, faint, as on a light table
    for back in (3, 2, 1):
        if which - back >= 0:
            _pose(cv, f - back * on * 2, which - back * 2, demo.TEAL, None, alpha=0.12 + 0.06 * (3 - back))
    floor = [(50 + i * (demo.W - 100) / 24, GROUND) for i in range(25)]
    draw_sketch(cv, floor, which, demo.MUTED, width=3, seed='floor', amount=3.0)
    x, y, rx, ry = _pose(cv, f, which, demo.INK, demo.ACCENT)
    cv.mark('ball', x - rx, y - ry, 2 * rx, 2 * ry)
    demo.word(cv, f'{which + 1:03d}', demo.W - 70, 40, size=24, color=demo.MUTED, font=demo.mono(24, 700))


TECHNIQUE = Technique(
    id='frame-by-frame-hand-drawn-animation',
    name='Frame-by-frame hand-drawn animation',
    family='shapes',
    group='Hand-drawn & traditional',
    aliases=('traditional animation', 'cel animation', 'hand-drawn animation', 'animating on twos',
             'line boil'),
    definition='Movement built from a run of separately drawn pictures, each held for a frame or two '
               'and re-inked every time, so the lines wobble and the motion steps like a cartoon.',
    phrasings=('make it look like an old hand-drawn cartoon, drawn frame by frame',
               'animate it on twos with that wobbly pencil line',
               'give it a traditional 2D animation feel instead of smooth computer motion'),
    related=('flipbook-sprite-animation', 'layout-animation-flip', 'flip', 'interruptible-motion',
             'scroll-scrubbed-frame-sequence', 'seamless-loop'),
    api=('videobuilder.techniques.shapes.frame_by_frame_hand_drawn_animation.draw_sketch',
         'videobuilder.techniques.shapes.frame_by_frame_hand_drawn_animation.sketch',
         'videobuilder.techniques.shapes.frame_by_frame_hand_drawn_animation.held',
         'videobuilder.techniques.shapes.frame_by_frame_hand_drawn_animation.drawing',
         'videobuilder.paths.jitter'),
    demo=lambda: demo.film(draw),
)
