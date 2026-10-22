"""Word flip-in: the words arrive one after another, each swinging up into
place about a horizontal hinge, in perspective, from edge-on to facing us."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def flip_word(cv, text, font, cx, cy, angle, color, pivot=0.5, focal=None, alpha=1.0, strips=None):
    """Draw `text` centred at (cx, cy), tipped `angle` degrees about a
    horizontal axis (0 faces the viewer, 90 is edge-on, positive tips the top
    away). The axis runs `pivot` of the way down the word (0 top, 1 bottom);
    `focal` (default three word-heights) sets how strong the perspective is.
    Cairo only does flat transforms, so the word is drawn once upright off
    the frame, then painted back as `strips` horizontal slices, each squashed
    and widened for its own depth. Returns
    the Box the word fills when upright."""
    w, h = vb.text.block_size([text], font)
    box = vb.Box(cx - w / 2, cy - h / 2, w, h)
    if alpha <= 0:
        return box
    a = math.radians(angle)
    cos, sin = math.cos(a), math.sin(a)
    f = focal or 3 * h
    top = -pivot * h                      # word rows relative to the axis
    axis_y = cy - h / 2 - top
    strips = strips or max(12, round(h / 4))

    def screen(y):                        # a word row -> (screen y, horizontal scale)
        s = f / max(f + y * sin, 1e-3)
        return axis_y + y * cos * s, s

    k, pad = cv.scale_factor() * 1.5, 4    # a little over-sampled: near slices are drawn wider
    word = vb.Canvas(w + 2 * pad, h + 2 * pad, scale=k)
    vb.text.draw(word, [text], font, pad, pad, color)
    c = cv.ctx
    with cv.layer(opacity=alpha):
        for i in range(strips):
            y0, y1 = top + h * i / strips, top + h * (i + 1) / strips
            (sy0, _), (sy1, _), (_, s) = screen(y0), screen(y1), screen((y0 + y1) / 2)
            if abs(sy1 - sy0) < 1e-3:
                continue
            c.save()
            lo, hi = min(sy0, sy1), max(sy0, sy1)
            c.rectangle(cx - 2 * w, lo - 0.5, 4 * w, hi - lo + 1)
            c.clip()
            c.translate(cx, sy0)
            c.scale(s, (sy1 - sy0) / (y1 - y0))
            c.translate(-w / 2 - pad, top - y0 - pad)
            c.scale(1 / k, 1 / k)
            c.set_source_surface(word.surface, 0, 0)
            c.paint()
            c.restore()
    return box


def draw_word_flip_in(cv, words, font, cx, cy, p, color, stacked=True, stagger=0.45, start=90.0,
                      pivot=0.5, gap=None):
    """Flip `words` in one by one at progress `p` (0 -> 1), as a block
    centred at (cx, cy): one per line when `stacked`, else side by side. Each
    word turns from `start` degrees to face the viewer with a slight
    overshoot, fading up over its first third; the next starts when `stagger`
    of the previous word's turn has run. `gap` is the space between words
    (default a line's leading, or a space). Returns the Box of the block."""
    words = list(words)
    n = len(words)
    sizes = [vb.text.block_size([t], font) for t in words]
    if stacked:
        gap = font.size * 0.08 if gap is None else gap
        bw, bh = max(w for w, _ in sizes), sum(h for _, h in sizes) + gap * (n - 1)
    else:
        gap = vb.text.measure(' ', font) if gap is None else gap
        bw, bh = sum(w for w, _ in sizes) + gap * (n - 1), max(h for _, h in sizes)
    x, y = cx - bw / 2, cy - bh / 2
    d = 1 / (1 + (n - 1) * stagger)       # each word's share of `p`
    for i, (t, (w, h)) in enumerate(zip(words, sizes)):
        q = vb.clamp01((p - i * stagger * d) / d)
        wx, wy = (cx, y + h / 2) if stacked else (x + w / 2, cy)
        if q > 0:
            flip_word(cv, t, font, wx, wy, start * (1 - vb.ease_out_back(q)), color, pivot=pivot,
                      alpha=vb.clamp01(q * 3))
        if stacked:
            y += h + gap
        else:
            x += w + gap
    return vb.Box(cx - bw / 2, cy - bh / 2, bw, bh)


def draw(n, cv):
    box = draw_word_flip_in(cv, ('EVERY', 'WORD', 'TURNS'), demo.font(104, 800), demo.W / 2, demo.H / 2,
                            demo.phase(n, 0.3, 2.4), demo.INK)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='word-flip-in',
    name='Word flip-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('word 3D flip reveal', 'rotateX word entrance', 'word flip reveal'),
    definition='Words appear one at a time, each tilting up from edge-on around a horizontal hinge '
               'until it faces the viewer.',
    phrasings=('make each word swing up into view one after the other',
               'the words tip forward into place in 3D, one by one',
               'flip the title in a word at a time'),
    related=('three-d-word-cube', 'flip', 'word-carousel-rotate', 'tile-flip', 'character-3d-flip', 'page-turn'),
    api=('videobuilder.techniques.typography.word_flip_in.draw_word_flip_in',
         'videobuilder.techniques.typography.word_flip_in.flip_word'),
    demo=lambda: demo.film(draw),
)
