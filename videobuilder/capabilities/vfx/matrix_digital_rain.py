"""Matrix digital rain: a screen of character columns, each with a white-hot
head glyph dropping at its own speed and a green tail of glyphs behind it
that dims away, the glyphs now and then flickering to other characters."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>{}[]=+*#%&/?:;$@'
GREEN = '#3dff7a'
HEAD = '#eaffef'


def digital_rain(t, cols, rows, seed=0, glyphs=GLYPHS, speed=(7.0, 18.0), trail=(6, 18), gap=(4, 30),
                 flicker=3.0):
    """The rain at `t` seconds on a grid of `cols` x `rows` cells, as
    `(col, row, glyph, level, head)` tuples: `level` 1 at a stream's head
    falling to near 0 at the end of its tail, `head` True for the leading
    glyph. Each column carries one stream that falls at a random rate in
    `speed` rows a second with a tail of `trail` glyphs, then waits `gap`
    rows' worth of time before it falls again, so the screen stays full
    with no column in step with another. Tail glyphs re-draw about
    `flicker` times a second; the head changes every row it falls. The same
    `seed` gives the same rain, frame for frame."""
    out = []
    for c in range(cols):
        rng = random.Random(f'{seed}:col:{c}')
        v = rng.uniform(*speed)
        length = rng.randint(*trail)
        cycle = rows + length + rng.randint(*gap)
        travelled = t * v + rng.uniform(0, cycle)
        lap = int(travelled // cycle)
        head = travelled - lap * cycle            # the head's row, fractional; may be below the screen
        top = int(head)
        for k in range(length + 1):
            r = top - k
            if r < 0:
                break
            if r >= rows:
                continue
            level = 1.0 if k == 0 else (1 - k / (length + 1)) ** 1.4
            tick = top if k == 0 else int(t * flicker + random.Random(f'{seed}:{c}:{r}').random() * 7)
            glyph = random.Random(f'{seed}:{c}:{r}:{lap}:{tick}').choice(glyphs)
            out.append((c, r, glyph, level, k == 0))
    return out


def draw_digital_rain(cv, t, x, y, w, h, font, color=GREEN, head=HEAD, seed=0, alpha=1.0, glow=True, **kw):
    """Fill the box (x, y, w, h) with digital rain at `t` seconds in `font`:
    one column per character width, tails in `color` fading out, heads in
    `head` with a soft halo when `glow`. `alpha` dims the whole layer (draw
    a smaller, dimmer layer first for depth). `kw` goes to `digital_rain`."""
    pitch = vb.text.measure('W', font) * 1.35
    lh = vb.text.line_height(font)
    cols, rows = max(1, int(w // pitch)), max(1, int(h // lh) + 1)
    x0 = x + (w - cols * pitch) / 2
    with cv.clip(x, y, w, h):
        for c, r, glyph, level, is_head in digital_rain(t, cols, rows, seed=seed, **kw):
            gx = x0 + c * pitch + (pitch - vb.text.measure(glyph, font)) / 2
            gy = y + r * lh
            if is_head:
                if glow:
                    demo.dot(cv, x0 + c * pitch + pitch / 2, gy + lh / 2, r=lh * 0.5, color=color,
                             alpha=0.08 * alpha)
                vb.text.draw(cv, [glyph], font, gx, gy, head, alpha=alpha)
            else:
                vb.text.draw(cv, [glyph], font, gx, gy, color, alpha=level * alpha)


def draw(n, cv):
    t = n / demo.FPS
    cv.fill('#020604')
    draw_digital_rain(cv, t, 0, 0, demo.W, demo.H, demo.mono(11, 600), seed=11, alpha=0.4, glow=False,
                      speed=(5.0, 10.0))
    draw_digital_rain(cv, t, 0, 0, demo.W, demo.H, demo.mono(17, 700), seed=5)
    cv.mark('rain', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='matrix-digital-rain',
    name='Matrix digital rain',
    family='vfx',
    group='Retro digital',
    aliases=('code rain', 'digital rain', 'falling glyphs', 'green code rain'),
    definition='Vertical streams of green computer characters slide down a dark screen at different '
               'speeds, each led by a glowing white glyph and trailing a tail that dims to nothing.',
    phrasings=('a screen full of falling green code like the hacker movie',
               'columns of glowing characters streaming down a black background',
               'that cascading green terminal text effect behind the title'),
    related=('falling-glyph-rain-reveal', 'falling-letter-rain', 'rainfall', 'dot-matrix-text',
             'rain-on-glass', 'character-drop'),
    api=('videobuilder.techniques.vfx.matrix_digital_rain.draw_digital_rain',
         'videobuilder.techniques.vfx.matrix_digital_rain.digital_rain'),
    demo=lambda: demo.film(draw),
)
