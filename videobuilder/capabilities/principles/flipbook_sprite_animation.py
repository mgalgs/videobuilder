"""Flipbook Sprite Animation: a handful of separately drawn frames swapped in
place at a fixed rate, so the motion comes from the drawings changing rather
than from anything being moved -- a sprite sheet played back as a loop."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def flipbook_index(t, count, fps=12, loop=True, pingpong=False):
    """Which of `count` frames shows at time `t` seconds when they play at
    `fps` drawings a second. Each frame holds for whole steps (no blending).
    `loop` wraps around, otherwise the last frame holds; `pingpong` plays
    forwards then backwards without repeating the end frames."""
    step = max(0, math.floor(t * fps + 1e-9))
    if count <= 1:
        return 0
    if pingpong:
        span = 2 * count - 2
        step = step % span if loop else min(step, count - 1)
        return step if step < count else span - step
    return step % count if loop else min(step, count - 1)


def sheet_frames(sheet, cols, rows, count=None):
    """The cells of a sprite sheet `sheet` (a `vb.Image` laid out in `cols` x
    `rows` equal cells, read left to right then top to bottom) as frames for
    `draw_flipbook`: each a `frame(cv, x, y, w, h)` drawing its one cell
    stretched to the box. `count` drops trailing empty cells."""
    count = cols * rows if count is None else count

    def cell(i):
        c, r = i % cols, i // cols

        def frame(cv, x, y, w, h):
            with cv.clip(x, y, w, h):
                cv.image(sheet, x - c * w, y - r * h, w * cols, h * rows)
        return frame
    return [cell(i) for i in range(count)]


def draw_flipbook(cv, frames, t, x, y, w, h, fps=12, loop=True, pingpong=False):
    """Draw the frame of `frames` that shows at time `t` into the box (x, y,
    w, h). A frame is a `vb.Image` (stretched to the box) or a callable
    `frame(cv, x, y, w, h)`, e.g. from `sheet_frames`. Returns its index."""
    i = flipbook_index(t, len(frames), fps, loop, pingpong)
    f = frames[i]
    if isinstance(f, vb.Image):
        cv.image(f, x, y, w, h)
    else:
        f(cv, x, y, w, h)
    return i


# The demo's drawings: a ball's bounce cycle as ten poses, each
# (height above the floor 0..1, horizontal stretch, vertical stretch, impact ticks).
POSES = ((0.00, 1.45, 0.62, True), (0.10, 0.78, 1.30, False), (0.42, 0.88, 1.14, False),
         (0.74, 0.97, 1.03, False), (0.94, 1.00, 1.00, False), (1.00, 1.00, 1.00, False),
         (0.94, 1.00, 1.00, False), (0.74, 0.97, 1.03, False), (0.42, 0.88, 1.14, False),
         (0.10, 0.78, 1.30, False))
FPS = 10


def _pose(lift, sx, sy, ticks):
    def frame(cv, x, y, w, h):
        k = w / 400
        r, ground = 46 * k, y + h * 0.86
        cy = ground - r * sy - lift * h * 0.48
        cv.line(x + w * 0.3, ground, x + w * 0.7, ground, demo.MUTED, width=max(1, 3 * k))
        cv.ctx.save()
        cv.ctx.translate(x + w / 2, cy)
        cv.ctx.scale(sx, sy)
        demo.dot(cv, 0, 0, r, color=demo.ACCENT)
        cv.ctx.restore()
        if ticks:
            for s in (-1, 1):
                ex = x + w / 2 + s * r * sx * 1.15
                cv.line(ex, ground - 6 * k, ex + s * 16 * k, ground - 20 * k, demo.INK, width=max(1, 3 * k))
    return frame


FRAMES = [_pose(*p) for p in POSES]


def draw(n, cv):
    t = n / demo.FPS
    bw, bh = 400, 300
    bx, by = (demo.W - bw) / 2, 50
    cv.rect(bx, by, bw, bh, demo.LINE, radius=14, alpha=0.5)
    i = draw_flipbook(cv, FRAMES, t, bx, by, bw, bh, fps=FPS)
    cv.mark('flipbook', bx, by, bw, bh)

    cw, ch, gap = 76, 57, 10   # the sheet itself, with the frame now showing outlined
    left = (demo.W - len(FRAMES) * cw - (len(FRAMES) - 1) * gap) / 2
    top = demo.H - ch - 70
    for j, f in enumerate(FRAMES):
        cx = left + j * (cw + gap)
        cv.rect(cx, top, cw, ch, demo.LINE, radius=6)
        f(cv, cx, top, cw, ch)
        if j == i:
            cv.outline(cx - 4, top - 4, cw + 8, ch + 8, demo.TEAL, width=3, radius=8)
    demo.word(cv, f'frame {i + 1} / {len(FRAMES)}', demo.W / 2, top + ch + 34, size=20,
              color=demo.MUTED, font=demo.mono(20, 600))


CAPABILITY = Capability(
    id='flipbook-sprite-animation',
    name='Flipbook Sprite Animation',
    family='principles',
    group='Cycles & loops',
    aliases=('sprite sheet animation', 'frame-sequence animation', 'frame sequence'),
    definition='A short series of separate drawings is swapped in one spot at a steady rate, '
               'so a subject moves the way pages do when a flipbook is thumbed.',
    phrasings=('play these drawings one after another like a flipbook',
               'animate it from a sprite sheet, frame by frame',
               'loop a few hand-drawn poses so the character looks alive'),
    related=('frame-by-frame-hand-drawn-animation', 'layout-animation-flip', 'flip', 'animated-sprite-particles',
             'tile-flip', 'scroll-scrubbed-frame-sequence'),
    api=('videobuilder.capabilities.principles.flipbook_sprite_animation.draw_flipbook',
         'videobuilder.capabilities.principles.flipbook_sprite_animation.flipbook_index',
         'videobuilder.capabilities.principles.flipbook_sprite_animation.sheet_frames'),
    demo=lambda: demo.film(draw),
)
