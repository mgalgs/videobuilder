"""Type explosion: a word holds, then blows apart -- every letter flung out
from the word's centre, spinning, slowed by drag, pulled down by gravity and
fading as it goes."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def explode(text, font, x, y, t, seed=0, speed=6, drag=1.8, gravity=4, spin=540, grow=0.6, life=1.8):
    """Where each letter of `text` (laid out on one line from top-left (x, y))
    is `t` seconds after it detonates, as `(char, cx, cy, angle, scale, alpha)`
    per non-space character: the letter's centre, its turn in radians, its
    size against the original and its opacity. Before `t` = 0 every letter
    sits in place. Each letter flies away from the word's centre at about
    `speed` line heights a second, slowed by `drag` (per second), falls with
    `gravity` line heights per second squared,
    turns up to `spin` degrees/s, grows by up to `grow` and fades out over
    `life` seconds. The same `seed` gives the same blast."""
    w, h = vb.text.block_size([text], font)
    mx, my = x + w / 2, y + h / 2
    rnd = random.Random(seed)
    lh = vb.text.line_height(font)
    speed, gravity = speed * lh, gravity * lh
    t = max(0.0, t)
    reach = (1 - math.exp(-drag * t)) / drag if drag else t   # distance per unit velocity under drag
    out, left = [], x
    for ch in text:
        adv = vb.text.measure(ch, font)
        cx, cy = left + adv / 2, my
        left += adv
        if ch.isspace():
            continue
        # Away from the centre, with some scatter, biased a little upward.
        dx, dy = cx - mx, (cy - my) - h * 0.3
        a = math.atan2(dy, dx if abs(dx) > 1 else rnd.choice((-1, 1))) + rnd.uniform(-0.6, 0.6)
        v = speed * rnd.uniform(0.6, 1.2)
        turn = math.radians(spin) * rnd.uniform(-1, 1)
        k = rnd.uniform(0.6, 1.2)
        out.append((ch, cx + math.cos(a) * v * reach, cy + math.sin(a) * v * reach + gravity * t * t / 2,
                    turn * t, 1 + grow * k * vb.clamp01(t / life), vb.clamp01(1 - t / life) ** 1.5))
    return out


def draw_type_explosion(cv, text, font, x, y, t, color, alpha=1.0, **kw):
    """Draw `text` from its top-left (x, y) exploding, `t` seconds after the
    blast (at or before 0 it reads normally). `kw` goes to `explode`.
    Returns the Box of the intact line."""
    w, h = vb.text.block_size([text], font)
    lh = vb.text.line_height(font)
    for ch, cx, cy, angle, scale, a in explode(text, font, x, y, t, **kw):
        if a * alpha <= 0:
            continue
        cw = vb.text.measure(ch, font)
        c = cv.ctx
        c.save()
        c.translate(cx, cy)
        c.rotate(angle)
        c.scale(scale, scale)
        vb.text.draw(cv, [ch], font, -cw / 2, -lh / 2, color, alpha=a * alpha)
        c.restore()
    return vb.Box(x, y, w, h)


BLAST = 1.0  # seconds into the demo


def draw(n, cv):
    t = n / demo.FPS - BLAST
    f = demo.font(110, 900)
    text = 'KABOOM'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    if t < 0:  # pressure building: a growing tremble before it goes
        k = demo.phase(n, 0.3, BLAST) ** 2 * 4
        x += math.sin(n * 2.7) * k
        y += math.cos(n * 3.9) * k
    else:      # a shock ring at the moment it goes
        ring = vb.clamp01(t / 0.6)
        if ring < 1:
            r = 20 + 420 * vb.ease_out_quint(ring)
            cv.arc(demo.W / 2, demo.H / 2, r, 0, 2 * math.pi, demo.ACCENT, width=24 * (1 - ring) + 1,
                   alpha=1 - ring)
    box = draw_type_explosion(cv, text, f, x, y, t, demo.INK, seed=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='type-explosion',
    name='Type explosion',
    family='typography',
    group='Physics and particles',
    aliases=('text explosion', 'exploding text', 'letter explosion', 'shatter text'),
    definition='A word sits still for a beat, then bursts apart, its letters flying outward, '
               'spinning and falling as they fade away.',
    phrasings=('make the title blow up into flying letters',
               'the word explodes and the letters scatter everywhere',
               'letters burst out from the middle like something went off'),
    related=('shape-burst', 'twirl-warp-text', 'outline-pulse-glow', 'typewriter-reveal', 'liquid-melt',
             'impact-shake'),
    api=('videobuilder.capabilities.typography.type_explosion.draw_type_explosion',
         'videobuilder.capabilities.typography.type_explosion.explode'),
    demo=lambda: demo.film(draw),
)
