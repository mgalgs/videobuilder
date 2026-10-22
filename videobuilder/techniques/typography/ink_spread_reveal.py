"""Ink Spread Reveal: the words show through a mask of ink blots that start
as specks at several points and soak outward with ragged, wobbling edges
until they merge and the whole line is visible."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

STEPS = 72  # points around each blot's edge


def _blots(box, p, seeds, seed, wobble):
    """The blots at progress `p` as `(cx, cy, radius, harmonics)`: `seeds`
    main blots scattered over `box`, each starting at its own moment, plus
    the small droplets that run ahead of their edges."""
    rnd = random.Random(f'ink:{seed}')
    diag = math.hypot(box.w, box.h)
    reach = max(box.w / seeds * 0.5, box.h * 0.3)  # a blot's own size before the final soak
    finish = vb.ease_in_out_quart(vb.clamp01((p - 0.6) / 0.4)) * diag * 0.6
    out = []
    for i in range(seeds):
        # spread the seeds along the line, jittered, so every part gets a source
        cx = box.x + box.w * (i + 0.5 + rnd.uniform(-0.35, 0.35)) / seeds
        cy = box.y + box.h * rnd.uniform(0.2, 0.8)
        start = rnd.uniform(0.0, 0.45)
        harm = [(k, rnd.uniform(0, 2 * math.pi), rnd.uniform(-2, 2), rnd.uniform(0.4, 1.0) / k)
                for k in range(2, 9)]
        drops = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(1.05, 1.5), rnd.uniform(0.06, 0.16))
                 for _ in range(rnd.randint(2, 4))]
        local = vb.clamp01((p - start) / 0.55)
        if local <= 0:
            continue
        r = (1 - (1 - local) ** 1.6) * reach + finish
        out.append((cx, cy, r, harm, p, wobble))
        for ang, dist, size in drops:
            # a droplet appears once the edge is near it, then is swallowed
            if r > 0 and local < 0.95:
                out.append((cx + math.cos(ang) * dist * r, cy + math.sin(ang) * dist * r * 0.8,
                            size * reach * min(1.0, local * 2), harm[:3], p, wobble))
    return out


def _blot_path(ctx, cx, cy, r, harm, p, wobble):
    for s in range(STEPS):
        th = 2 * math.pi * s / STEPS
        k_sum = sum(a * math.sin(k * th + ph + drift * p) for k, ph, drift, a in harm)
        rr = r * (1 + wobble * k_sum)
        x, y = cx + math.cos(th) * rr, cy + math.sin(th) * rr
        ctx.line_to(x, y) if s else ctx.move_to(x, y)
    ctx.close_path()


def ink_spread(cv, box, p, body, seeds=6, seed=0, wobble=0.22, bleed=0.12, bleed_alpha=0.35):
    """Draw `body(cv)` showing only through spreading ink blots over `box`
    (a `vb.Box`, or (x, y, w, h)) at progress `p` (0 -> 1). Nothing shows at 0;
    at 1 the whole of `body` does. `seeds` blots start at staggered moments;
    `wobble` is how ragged their edges are; a faint wet rim `bleed` (a
    fraction of each blot's size) wider than the blot shows `body` at
    `bleed_alpha`. The same `seed` gives the same blots, frame for frame."""
    box = vb.Box(*box)
    if p <= 0:
        return
    if p >= 1:
        body(cv)
        return
    ctx = cv.ctx
    blots = _blots(box, p, seeds, seed, wobble)
    for grow, alpha in ((1 + bleed, bleed_alpha), (1.0, 1.0)):
        ctx.save()
        ctx.new_path()
        for cx, cy, r, harm, pp, wob in blots:
            _blot_path(ctx, cx, cy, r * grow, harm, pp, wob)
        ctx.clip()  # non-zero winding: the union of the blots
        with cv.layer(opacity=alpha):
            body(cv)
        ctx.restore()


def draw_ink_spread(cv, text, font, x, y, p, color, **kw):
    """Draw `text` from its top-left (x, y) revealed by ink spreading
    through it at progress `p` (0 -> 1). `kw` goes to `ink_spread`. Returns
    the Box of the finished line."""
    w, h = vb.text.block_size([text], font)
    box = vb.Box(x, y, w, h)
    ink_spread(cv, box, p, lambda c: vb.text.draw(c, [text], font, x, y, color), **kw)
    return box


def draw(n, cv):
    f = demo.font(190, 900)
    text = 'INKWELL'
    w, h = vb.text.block_size([text], f)
    box = draw_ink_spread(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.5),
                          demo.INK, seeds=7, seed=3)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='ink-spread-reveal',
    name='Ink spread reveal',
    family='typography',
    group='Masking and clipping',
    aliases=('ink bleed text', 'spreading stain reveal', 'ink blot reveal'),
    definition='Blots start as specks at a few spots on the word and soak outward with ragged, '
               'shifting edges, uncovering the letters until they join and the word is whole.',
    phrasings=('make the title soak into view like spilled ink',
               'the words appear as blots spread out and merge',
               'reveal the text through growing ink stains'),
    related=('ink-bleed', 'ink-splash-spread', 'wipe-reveal', 'handwriting-reveal', 'text-mask-reveal',
             'ink-in-water'),
    api=('videobuilder.techniques.typography.ink_spread_reveal.draw_ink_spread',
         'videobuilder.techniques.typography.ink_spread_reveal.ink_spread'),
    demo=lambda: demo.film(draw),
)
