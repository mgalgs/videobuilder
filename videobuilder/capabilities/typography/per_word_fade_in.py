"""Per-word fade-in: a line of text comes up one word at a time, each word
going from invisible to solid a beat after the one before it. Nothing moves;
only opacity changes."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def word_alphas(count, p, fade=0.35, ease=vb.ease_in_out_quart):
    """Opacity 0 -> 1 of each of `count` words at progress `p` (0 -> 1). Each
    word's fade lasts `fade` of the whole reveal; the starts are spread evenly
    so the first begins at 0 and the last finishes at 1."""
    if count <= 0:
        return []
    fade = min(max(fade, 1e-6), 1.0)
    gap = (1 - fade) / (count - 1) if count > 1 else 0.0
    return [ease(vb.clamp01((p - i * gap) / fade)) for i in range(count)]


def draw_word_fade(cv, text, font, x, y, p, color, width=None, align='left', balance=True, **kw):
    """Draw `text` from its top-left (x, y), fading in word by word at progress
    `p`. It wraps within `width` (default: one line), each line placed by
    `align` across that width, so every word sits where the finished text puts
    it. `kw` goes to `word_alphas`. Returns the Box of the finished text."""
    lines = vb.text.wrap(text, font, width, balance) if width else (text,)
    width = width or vb.text.block_size(lines, font)[0]
    lh, space = vb.text.line_height(font), vb.text.measure(' ', font)
    words = []
    for i, line in enumerate(lines):
        lw = vb.text.measure(line, font)
        left = x + {'left': 0, 'center': (width - lw) / 2, 'right': width - lw}[align]
        for w in line.split():
            words.append((w, left, y + i * lh))
            left += vb.text.measure(w, font) + space
    for (w, wx, wy), a in zip(words, word_alphas(len(words), p, **kw)):
        if a > 0:
            vb.text.draw(cv, [w], font, wx, wy, color, alpha=a)
    lw = max(vb.text.measure(ln, font) for ln in lines)
    return vb.Box(x + {'left': 0, 'center': (width - lw) / 2, 'right': width - lw}[align], y, lw, lh * len(lines))


def draw(n, cv):
    f = demo.font(84, 800)
    width = 1100
    lines = vb.text.wrap('Every word arrives on its own beat.', f, width, True)
    h = vb.text.line_height(f) * len(lines)
    box = draw_word_fade(cv, 'Every word arrives on its own beat.', f, (demo.W - width) / 2, (demo.H - h) / 2,
                         demo.phase(n, 0.3, 2.4), demo.INK, width=width, align='center')
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='per-word-fade-in',
    name='Per-word fade-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('word stagger reveal', 'word-by-word fade', 'staggered word fade'),
    definition='Text shows up in reading order one word at a time, each word fading up from nothing '
               'shortly after the word before it starts.',
    phrasings=('have the sentence fade in word by word',
               'bring the words up one after another instead of all at once',
               'each word gently appears in turn until the line is complete'),
    related=('text-mask-reveal', 'linear-stagger', 'word-by-word-emphasis', 'center-out-stagger',
             'proximity-stagger', 'scroll-driven-text-reveal'),
    api=('videobuilder.techniques.typography.per_word_fade_in.draw_word_fade',
         'videobuilder.techniques.typography.per_word_fade_in.word_alphas'),
    demo=lambda: demo.film(draw),
)
