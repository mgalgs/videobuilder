"""Ending: seamless loop-back. It opens and closes on the same calm frame: a
single small dot centred on the plain background, the quiet first frame a
video can loop back into. In between, the dot swells into a disc carrying a
loop arrow, the closing line unspools letter by letter around a ring that
turns, and a second line settles beside it. Then everything winds back into
the dot along the same path, so the last frame and the first are the same
picture.

Built from `examples/capabilities/seamless-loops.py` (one wrapping phase
drives the turn) and `staggered-reveals.py` (the letters).
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from . import _ending_util as u

DOT = 9  # radius of the calm dot, px
# Per format: text-ring radius, disc radius, ring type size, where the badge rests (x, y shares of the frame),
# and where the second line goes.
LAYOUT = {
    '16x9': dict(ring=160, disc=100, size=28, rest=(0.30, 0.5), side=True, sub=(52, 46, 40, 34, 30)),
    '9x16': dict(ring=212, disc=132, size=32, rest=(0.5, 0.39), side=False, sub=(52, 46, 40, 34)),
    '1x1': dict(ring=138, disc=84, size=23, rest=(0.5, 0.40), side=False, sub=(34, 30, 27, 24)),
}
SEP = '  •  '


def _phase(f, n):
    """0 at the calm dot, rising to 1 for the hold and back to 0 by the last frame."""
    t = f / max(1, n - 1)
    return u.smoother(t / 0.2) if t < 0.5 else u.smoother((1 - t) / 0.16)


def _ring_chars(copy, font, radius):
    """The closing line, repeated with separators as many whole times as fit
    around the ring, as (char, is_separator) pairs spread evenly over it."""
    unit = copy.upper() + SEP
    one = text.measure(unit, font)
    reps = max(1, int(2 * math.pi * radius / (one * 1.08)))
    out = []
    for _ in range(reps):
        out += [(c, False) for c in copy.upper()] + [(c, c != ' ') for c in SEP]
    return out


def _loop_arrow(cv, cx, cy, r, turn, color):
    ctx = cv.ctx
    a0, a1 = turn + 0.35, turn + 2 * math.pi - 0.35
    cv.arc(cx, cy, r, a0, a1, color, width=r * 0.2)
    hx, hy = cx + r * math.cos(a1), cy + r * math.sin(a1)
    tx, ty = -math.sin(a1), math.cos(a1)  # the direction of travel at the arrow's end
    nx, ny = math.cos(a1), math.sin(a1)
    s = r * 0.42
    u.fill_poly(cv, [(hx + tx * s, hy + ty * s), (hx + nx * s * 0.75, hy + ny * s * 0.75),
                     (hx - nx * s * 0.75, hy - ny * s * 0.75)], color)
    ctx.new_path()


def draw(cv, shot):
    cv.fill(kit.BG)
    data, f, n = shot.data, shot.f, shot.length
    name = cv.format.name if cv.format is not None and cv.format.name in LAYOUT else '16x9'
    L = LAYOUT[name]
    accent = data['accent']
    W, H = cv.width, cv.height
    s = vb.Box.of(cv).pad(48)
    ph = _phase(f, n)
    turn = 2 * math.pi * (f % n) / n  # one whole turn a shot: a true period

    # The badge travels from the frame's centre (the calm dot) to its resting place and back.
    rx, ry = W * L['rest'][0], H * L['rest'][1]
    bx, by = W / 2 + (rx - W / 2) * ph, H / 2 + (ry - H / 2) * ph

    ring, disc_r = L['ring'], L['disc']
    for size in range(L['size'], 15, -1):  # small enough that the line goes round at least twice
        ring_f = kit.font(size, 750, tracking=0.08)
        if len(_ring_chars(data['headline'], ring_f, ring)) >= 2 * (len(data['headline']) + len(SEP)):
            break
    lh = text.line_height(ring_f)

    # Guides: two hairline circles either side of the lettering.
    if ph > 0.01:
        for k, rr in enumerate((ring - lh * 0.75, ring + lh * 0.75)):
            cv.arc(bx, by, rr * ph, 0, 2 * math.pi, kit.LINE, width=2, alpha=min(1.0, ph * 1.5))

    # The disc: the calm dot, swollen.
    r = DOT + (disc_r - DOT) * ph
    cv.rect(bx - r, by - r, 2 * r, 2 * r, accent, radius=r)
    if ph > 0.3:
        with cv.layer(opacity=vb.clamp01((ph - 0.3) / 0.4)):
            _loop_arrow(cv, bx, by, r * 0.48, -turn * 2, kit.BG)
    cv.mark('disc', bx - r, by - r, 2 * r, 2 * r)

    # The ring of letters: unspool clockwise on the way in, wind back on the way out.
    chars = _ring_chars(data['headline'], ring_f, ring)
    count = len(chars)
    reveal = vb.clamp01((ph - 0.25) / 0.75)
    shown = reveal * count
    if shown > 0:
        ctx = cv.ctx
        widths = [text.measure(c, ring_f) for c, _ in chars]
        total = sum(widths)
        at = 0.0
        for i, ((c, sep), cw) in enumerate(zip(chars, widths)):
            mid = (at + cw / 2) / total
            at += cw
            k = vb.clamp01(shown - i)
            if k <= 0 or c == ' ':
                continue
            a = turn - math.pi / 2 + 2 * math.pi * mid
            gx, gy = bx + ring * ph * math.cos(a), by + ring * ph * math.sin(a)
            ctx.save()
            ctx.translate(gx, gy)
            ctx.rotate(a + math.pi / 2)
            ctx.scale(k * ph, k * ph)
            text.draw(cv, [c], ring_f, -cw / 2, -lh / 2, accent if sep else kit.INK)
            ctx.restore()
        outer = (ring + lh * 0.75) * ph
        cv.mark('ring', bx - outer, by - outer, 2 * outer, 2 * outer)

    # The second line: beside the badge in 16:9, under it otherwise.
    sub = data['subline']
    if sub:
        outer = ring + lh * 0.75
        if L['side']:
            x0 = rx + outer + 48
            sub_f, lines, sw, sh = u.fit(sub, L['sub'], 750, s.right - x0, 4, tracking=-0.02)
            sx, sy = x0, ry - sh / 2
            align = 'left'
        else:
            sub_f, lines, sw, sh = u.fit(sub, L['sub'], 750, s.w, 3, tracking=-0.02)
            sx, sy = s.cx - sw / 2, ry + outer + (56 if H > W else 26)
            align = 'center'
        t = f / max(1, n - 1)
        a = vb.clamp01((t - 0.16) / 0.08) * vb.clamp01((0.86 - t) / 0.06)
        if a > 0:
            with cv.layer(opacity=a, dy=(1 - a) * 18):
                text.draw(cv, lines, sub_f, sx, sy, kit.INK, align=align, width=sw)
                cv.line(sx if align == 'left' else s.cx - 24, sy - 18,
                        (sx if align == 'left' else s.cx - 24) + 48, sy - 18, accent, width=3)
            cv.mark('subline', sx, sy, sw, sh)


COMPONENT = Component(
    id='loop-back',
    kind='ending',
    description=('A seamless loop-back: starts and ends on one small dot on the plain background, so it loops cleanly '
                 'into a first frame; between, the dot swells into a disc with a loop arrow, the closing line '
                 'unspools around a turning ring and a second line settles beside it.'),
    tags=('ending', 'loop', 'seamless', 'outro', 'badge', 'circular text', 'replay'),
    formats=('16x9', '9x16', '1x1'),
    beats=(6, 12),
    slots=(
        Slot('headline', 'text', True, 'The closing line set around the ring, short, e.g. "See you at the top". '
             'It repeats around the circle.', max_length=22),
        Slot('subline', 'text', False, 'A second, plain line beside or under the ring, e.g. "One more time, from '
             'the start".', max_length=40),
        Slot('accent', 'color', False, 'Colour of the dot and disc, the separators and the rule.'),
    ),
    sample={'headline': 'See you at the top', 'subline': 'One more time, from the start', 'accent': kit.ACCENT},
    draw=draw,
    overlap_ok=(('disc', 'ring'),),
)
