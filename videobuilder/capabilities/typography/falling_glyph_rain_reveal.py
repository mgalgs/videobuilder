"""Falling Glyph Rain Reveal: one column of random characters per letter
pours down from above, and each column's leading glyph lands on its line and
turns into the real letter while the trail behind it fades away."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>{}[]=+*#%&/?'


def glyph_rain(text, p, seed=0, glyphs=GLYPHS, drop=6, trail=6, stagger=0.4, fade=0.18, changes=40):
    """`text` at progress `p` (0 -> 1) as one column per character: a list of
    `[(glyph, row, alpha, landed), ...]`, head first. `row` is in line heights
    relative to the text's own line (0 on it, negative above). Columns start
    in a shuffled order spread over the first `stagger` of the reveal; each
    head falls `drop` rows, slowing as it lands, then shows the real letter
    while its `trail` glyphs fade over `fade`. Spaces give empty columns.
    Glyphs are re-drawn `changes` times across the reveal; the same `seed`
    gives the same rain, frame for frame."""
    p = vb.clamp01(p)
    rng = random.Random(f'{seed}:order')
    order = list(range(len(text)))
    rng.shuffle(order)
    rank = {i: r for r, i in enumerate(order)}
    span = 1 - stagger - fade
    step = int(p * changes)
    out = []
    for i, ch in enumerate(text):
        if ch.isspace():
            out.append([])
            continue
        start = stagger * rank[i] / max(1, len(text) - 1)
        q = vb.clamp01((p - start) / span) if p > start else -1
        if q < 0:
            out.append([])
            continue
        head = -drop * (1 - q) ** 2                  # ease-out: the fall slows into its line
        gone = vb.clamp01((p - start - span) / fade)  # 0 while falling, 1 once the trail has faded
        landed = q >= 1
        col = [(ch if landed else random.Random(f'{seed}:{i}:0:{step}').choice(glyphs), head, 1.0, landed)]
        for k in range(1, trail + 1):
            alpha = (1 - k / (trail + 1)) * (1 - gone)
            if alpha > 0:
                col.append((random.Random(f'{seed}:{i}:{k}:{step}').choice(glyphs), head - k, alpha, False))
        out.append(col)
    return out


def draw_glyph_rain(cv, text, font, x, y, p, color, rain=None, head=None, seed=0, **kw):
    """Draw `text` raining in at progress `p`, its line's top-left at (x, y).
    Each column falls on its letter's place, every glyph centred on that
    letter's advance so the settled line never shifts. Trail glyphs use
    `rain` (default: `color`); a falling head uses `head` (default: `color`),
    a landed one `color`. `kw` goes to `glyph_rain`. Returns the Box of the
    finished line."""
    lh = vb.text.line_height(font)
    left = x
    for col, ch in zip(glyph_rain(text, p, seed=seed, **kw), text):
        adv = vb.text.measure(ch, font)
        for k, (glyph, row, alpha, landed) in reversed(list(enumerate(col))):  # the head last, on top
            ink = color if landed else (head or color) if k == 0 else (rain or color)
            gx = left + (adv - vb.text.measure(glyph, font)) / 2
            vb.text.draw(cv, [glyph], font, gx, y + row * lh, ink, alpha=alpha)
        left += adv
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(120, 800)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    box = draw_glyph_rain(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2 + 120, demo.phase(n, 0.0, 2.5),
                          demo.INK, rain=demo.TEAL, head=demo.ACCENT, seed=3)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='falling-glyph-rain-reveal',
    name='Falling glyph rain reveal',
    family='typography',
    group='Scramble and decode',
    aliases=('matrix rain text', 'code rain reveal', 'digital rain title'),
    definition='A stream of random characters drops down above every letter, and as each stream '
               'reaches the line its front character becomes the real letter while the rest fade.',
    phrasings=('the title rains down out of falling computer code',
               'streams of random symbols pour down and land as the word',
               'each letter drops in at the bottom of a column of flickering characters'),
    related=('matrix-digital-rain', 'falling-letter-rain', 'character-rise', 'dot-matrix-text', 'rainfall',
             'text-mask-reveal'),
    api=('videobuilder.techniques.typography.falling_glyph_rain_reveal.draw_glyph_rain',
         'videobuilder.techniques.typography.falling_glyph_rain_reveal.glyph_rain'),
    demo=lambda: demo.film(draw),
)
