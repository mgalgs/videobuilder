"""Spring-drag letters: each letter of a word hangs on its own spring. When a
pointer passes close it shoves the letters aside (or tugs them in), and they
lag, overshoot and wobble back to their places once it has gone."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def spring_drag(rest, pointer, t, fps=30, radius=120.0, push=50.0, hz=2.4, ratio=0.32, tilt=0.003, steps=4):
    """Offsets of letters on springs reacting to a moving pointer, at `t` seconds.

    `rest` lists each letter's resting centre (x, y); `pointer(t)` gives the
    pointer's (x, y) at time `t`, or None when it is away. Within `radius` a
    letter's goal is pushed `push` px straight away from the pointer (negative
    `push` pulls it toward the pointer), falling off smoothly to nothing at the
    edge; a spring (`hz`, damping `ratio`) drags the letter after that goal, so
    it lags, overshoots and settles home. Returns `(dx, dy, angle)` per letter,
    `angle` (radians) leaning with its sideways speed times `tilt`.

    Stepped from t = 0 each call, so any frame renders alone and the same `t`
    always gives the same answer."""
    k = (2 * math.pi * hz) ** 2
    c = 2 * ratio * math.sqrt(k)
    n = max(0, round(t * fps * steps))
    dt = 1 / (fps * steps)
    state = [[0.0, 0.0, 0.0, 0.0] for _ in rest]   # x, y, vx, vy
    for i in range(n):
        p = pointer(i * dt)
        for (rx, ry), s in zip(rest, state):
            gx = gy = 0.0
            if p is not None:
                ex, ey = rx + s[0] - p[0], ry + s[1] - p[1]
                d = math.hypot(ex, ey)
                if d < radius:
                    f = (1 - d / radius) ** 2 * push
                    ux, uy = (ex / d, ey / d) if d > 1e-6 else (0.0, -1.0)
                    gx, gy = ux * f, uy * f
            s[2] += (k * (gx - s[0]) - c * s[2]) * dt
            s[3] += (k * (gy - s[1]) - c * s[3]) * dt
            s[0] += s[2] * dt
            s[1] += s[3] * dt
    return [(x, y, max(-0.6, min(0.6, vx * tilt))) for x, y, vx, _ in state]


def draw_spring_letters(cv, text, font, x, y, pointer, t, color, alpha=1.0, **kw):
    """Draw `text` from its top-left (x, y) with every letter on a spring that
    the pointer (`pointer(t)` -> (x, y) or None) shoves aside as it passes;
    `kw` goes to `spring_drag`. Returns the Box of the line at rest."""
    w, h = vb.text.block_size([text], font)
    rest, left = [], x
    for ch in text:
        adv = vb.text.measure(ch, font)
        rest.append((left + adv / 2, y + h / 2))
        left += adv
    ctx = cv.ctx
    for ch, (cx, cy), (dx, dy, a) in zip(text, rest, spring_drag(rest, pointer, t, **kw)):
        if ch.isspace():
            continue
        adv = vb.text.measure(ch, font)
        ctx.save()
        ctx.translate(cx + dx, cy + dy)
        ctx.rotate(a)
        vb.text.draw(cv, [ch], font, -adv / 2, -h / 2, color, alpha=alpha)
        ctx.restore()
    return vb.Box(x, y, w, h)


REACH = 120


def _pointer(t):
    """The demo's pointer: up from below-left, sweeping along the word, then down and away to rest."""
    q = vb.ease_in_out_quart(vb.clamp01((t - 0.75) / 1.85)) * 0.4 + vb.clamp01((t - 0.75) / 1.85) * 0.6
    x = demo.W * (0.1 + 0.78 * q)
    y = demo.H / 2 + 8 + demo.H * 0.3 * (1 - math.sin(math.pi * q)) ** 1.5
    return x, y


def _arrow(cv, x, y, s=1.6):
    pts = [(0, 0), (0, 26), (6.5, 20), (11, 30), (15, 28), (10.5, 18.5), (19, 18.5)]
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(*pts[0])
    for px, py in pts[1:]:
        ctx.line_to(px, py)
    ctx.close_path()
    ctx.set_source_rgba(*vb.canvas.rgba(demo.INK))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.canvas.rgba(demo.BG))
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()


def draw(n, cv):
    t = n / demo.FPS
    f = demo.font(140, 900)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    p = _pointer(t)
    demo.dot(cv, *p, r=REACH, color=demo.ACCENT, alpha=0.12)   # the pointer's reach
    box = draw_spring_letters(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, _pointer, t, demo.INK,
                              fps=demo.FPS, radius=REACH, push=50, ratio=0.22)
    cv.mark('text', *box)
    _arrow(cv, *p, s=1.0)


CAPABILITY = Capability(
    id='spring-drag-letters',
    name='Spring-drag letters',
    family='typography',
    group='Physics and particles',
    aliases=('cursor-reactive letters', 'magnetic letter follow', 'springy hover text'),
    definition='Letters on springs get shoved aside as a pointer sweeps past, then wobble and '
               'overshoot their way back into the word once it moves on.',
    phrasings=('the letters scatter away from the mouse and bounce back into place',
               'when the cursor passes over the title the letters jiggle out of its way',
               'springy text that reacts to the pointer and settles again'),
    related=('hover-letter-displacement', 'magnetic-button', 'cursor-follower-dot-and-ring',
             'cursor-particle-trail', 'spring-return', 'particle-field-repel'),
    api=('videobuilder.capabilities.typography.spring_drag_letters.draw_spring_letters',
         'videobuilder.capabilities.typography.spring_drag_letters.spring_drag'),
    demo=lambda: demo.film(draw),
)
