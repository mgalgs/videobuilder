"""Rubber: bouncy letters on springs. Each letter drops onto its line, and
its spring (`vb.spring`, under-damped) carries it on: where the spring
overshoots, the letter squashes flat and wide against the line instead of
sinking through it; where it swings back, it stretches up tall and thin;
then it settles. Through the hold a hop runs along each line now and then,
every letter jumping and squashing in turn, and the letters keep a slow
jelly wobble between hops. On the exit they squash down and pop away.

Heavy rounded-feeling sans set as big as the frame allows, centred line by
line, with a soft shadow in the accent under each letter that spreads as
it squashes.
"""
import math
from functools import lru_cache

from .. import text
from ..ease import damped, spring
from ..layout import Box
from ..text import Font
from . import kit
from .style import Style

BOUNCE = damped(0.28, hz=2.2)
HOP_EVERY = 1.7         # s between hops along a line, through the hold
HOP = 0.32              # s a hop is in the air


@lru_cache(maxsize=64)
def _layout(lines, box, family):
    inner, w, h, k = kit.room(box, tall=(0.9, 0.5), wide=(0.8, 0.62), square=(0.86, 0.6))
    font = kit.fit(lines, lambda s: Font(family, s, weight=900, line_height=1.18), w, h)
    lh = text.line_height(font)
    top = inner.cy - lh * len(lines) / 2
    out = []
    for i, line in enumerate(lines):
        xs, width = kit.advances(line, font)
        x0 = inner.cx - width / 2
        out.append((x0, top + i * lh, xs, width))
    return font, lh, tuple(out)


def _land(lines, hold):
    """When each letter first touches its line: {(line, index): seconds}."""
    rnd = kit.rng('rubber', '|'.join(lines))
    raw = {}
    for i, line in enumerate(lines):
        for j, ch in enumerate(line):
            if ch != ' ':
                raw[(i, j)] = 0.35 + 0.07 * j + 0.3 * i + rnd.uniform(0, 0.06)
    latest = max(raw.values(), default=1)
    k = min(1.0, max(0.1, hold - 0.9) / latest)
    return {key: v * k for key, v in raw.items()}


def _pose(t, land, drop):
    """(lift px, squash): squash > 0 is flat and wide, < 0 tall and thin."""
    fall = 0.28
    if t < land - fall:
        return None
    if t < land:                          # falling: gravity, stretched by the speed
        q = (t - (land - fall)) / fall
        return drop * (1 - q * q), -0.18 * q
    s = spring(t - land, **BOUNCE)        # 0 at contact -> 1 at rest, bouncing about it
    v = 1 - s                             # > 0 above rest, < 0 overshoot
    if v < 0:
        return 0.0, min(0.45, -v * 1.3)   # the overshoot goes into the squash, not through the floor
    return v * drop * 0.22, -min(0.3, v * 0.5)


def draw(cv, p, t, box, clock):
    lines = p.lines
    font, lh, rows = _layout(lines, Box(*box), STYLE.font_family(p))
    lands = _land(lines, clock.hold)
    drop = lh * 1.6
    content, _ = text._content(font)
    ctx = cv.ctx
    out_t = clock.exit
    out_len = p.length - clock.exit
    with cv.layer(**kit.camera(t, clock.hold, box.cx, box.cy, box, k=0.05)):
        for i, (x0, y, xs, width) in enumerate(rows):
            base = y + lh / 2 + content / 2 - font.size * 0.12     # about where the letters stand
            settled = True
            n = len(lines[i])
            for j, ch in enumerate(lines[i]):
                if ch == ' ':
                    continue
                pose = _pose(t, lands[(i, j)], drop)
                if pose is None:
                    settled = False
                    continue
                lift, squash = pose
                if t - lands[(i, j)] < 1.6:
                    settled = False
                # The hold: a hop along the line now and then, and a jelly wobble between.
                if clock.hold < t < out_t:
                    h_t = (t - clock.hold - 0.06 * j - 0.25 * i) % HOP_EVERY
                    if h_t < HOP:
                        q = h_t / HOP
                        lift += math.sin(math.pi * q) * font.size * 0.22
                        squash -= 0.12 * math.sin(math.pi * q)
                    elif h_t < HOP + 0.4:
                        squash += 0.2 * math.exp(-(h_t - HOP) * 9) * math.cos((h_t - HOP) * 28)
                    squash += 0.035 * math.sin(t * 5.1 + j * 0.8 + i)
                scale = 1.0
                if t >= out_t:                    # the exit: squash flat, then pop away
                    # staggered along the lines, the last letter popped by the last frame
                    lag = out_len * 0.4 * (j / max(1, n) + 0.1 * i) / (1 + 0.1 * (len(lines) - 1))
                    q = min(1.0, max(0.0, (t - out_t - lag) / (out_len * 0.5)))
                    squash += 0.5 * min(1.0, q * 2.5)
                    scale = 1.0 if q < 0.4 else max(0.0, 1 - (q - 0.4) / 0.6) * (1 + 0.25 * math.sin(math.pi * q))
                    settled = False
                    if scale <= 0.01:
                        continue
                sx, sy = (1 + squash * 0.8) * scale, (1 - squash) * scale
                gw = text.measure(ch, font)
                gx = x0 + xs[j] + gw / 2
                shadow_w = gw * 0.55 * (1 + squash) * max(0.2, 1 - lift / drop) * scale
                cv.ctx.save()
                cv.ctx.translate(gx, base + font.size * 0.05)
                cv.ctx.scale(max(1.0, shadow_w), max(1.0, shadow_w * 0.16))
                cv.ctx.arc(0, 0, 1, 0, 2 * math.pi)
                cv.ctx.restore()
                ctx.set_source_rgba(*kit.rgba(p.accent, 0.45 * max(0.15, 1 - lift / drop)))
                ctx.fill()
                ctx.save()
                ctx.translate(gx, base - lift)
                ctx.scale(sx, sy)
                kit.glyphs(cv, ch, font, -gw / 2, -(lh / 2 + content / 2 - font.size * 0.12), p.ink)
                ctx.restore()
            if settled or (clock.hold <= t < out_t):
                cv.mark(f'line-{i}', x0, y, width, lh)


def events(p, clock):
    """A soft pop as each letter first lands, and one as each pops away;
    no closer than 1/20 s apart."""
    out_len = p.length - clock.exit
    pops = [clock.exit + (j / max(1, len(p.lines[i]))) * out_len * 0.45 + i * 0.05 + 0.2 * out_len
            for i, j in _land(p.lines, clock.hold)]
    lands = sorted(list(_land(p.lines, clock.hold).values()) + pops)
    out, last = [], -1.0
    for t in lands:
        if t - last >= 0.05:
            out.append((t, 'pop'))
            last = t
    return out


STYLE = Style('rubber', 'Rubber letters', 'letters drop, squash, stretch and settle on springs, then hop in turn',
              draw, aliases=('bouncy', 'bouncy letters', 'jelly', 'springy', 'bounce'), events=events,
              sound={'pop': (('pro_pop/boop', 'pop/0', 'fit/pop/mouth_plop'), ('pop', 'tap', 'click'), -12.0)})
