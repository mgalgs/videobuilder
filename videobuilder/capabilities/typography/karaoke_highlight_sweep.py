"""Karaoke highlight sweep: a line of lyrics changes colour from left to
right, the edge of the colour moving through each word as it is sung."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def sweep_width(text, font, p, spans=None):
    """How far into `text` (in px from its left edge) the highlight has
    reached at progress `p` (0 -> 1). With no `spans` the edge moves evenly
    across the whole line. `spans` gives each word (split on spaces) its own
    `(start, end)` in the same 0 -> 1 progress: the edge crosses that word
    between the two and waits in the gap before the next, the way a sung word
    takes its own time."""
    full = vb.text.measure(text, font)
    p = vb.clamp01(p)
    if not spans:
        return full * p
    words = text.split(' ')
    if len(spans) != len(words):
        raise ValueError(f'{len(words)} words but {len(spans)} spans')
    left = 0.0
    for i, (word, (a, b)) in enumerate(zip(words, spans)):
        w = vb.text.measure(word, font)
        if p < b:
            return left + w * vb.clamp01((p - a) / (b - a)) if b > a else left
        left += w
        if i + 1 < len(words):
            left += vb.text.measure(' ', font)
    return full


def draw_karaoke(cv, text, font, x, y, p, color, highlight, spans=None):
    """Draw `text` on one line from its top-left (x, y), sung up to progress
    `p`: the part left of the sweep edge in `highlight`, the rest in `color`.
    `spans` times the edge word by word (see `sweep_width`). Returns the Box
    of the line."""
    w, h = vb.text.block_size([text], font)
    edge = sweep_width(text, font, p, spans)
    with cv.clip(x + edge, y - h, w - edge + h, 3 * h):
        vb.text.draw(cv, [text], font, x, y, color)
    if edge > 0:
        with cv.clip(x - h, y - h, edge + h, 3 * h):
            vb.text.draw(cv, [text], font, x, y, highlight)
    return vb.Box(x, y, w, h)


LYRIC = 'SING IT LIKE YOU MEAN IT'
# Each word's share of the sweep, uneven like a sung line: a quick pick-up, a held note at the end.
SPANS = ((0.00, 0.10), (0.12, 0.20), (0.24, 0.40), (0.42, 0.50), (0.52, 0.68), (0.72, 1.00))


def draw(n, cv):
    f = demo.font(54, 800)
    w, h = vb.text.block_size([LYRIC], f)
    box = draw_karaoke(cv, LYRIC, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.6),
                       demo.MUTED, demo.ACCENT, spans=SPANS)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='karaoke-highlight-sweep',
    name='Karaoke highlight sweep',
    family='typography',
    group='Lyrics and captions',
    aliases=('karaoke fill', 'sung lyric fill', 'karaoke word highlight', 'word-by-word caption fill'),
    definition='A new colour runs through a line of lyrics from left to right, its edge passing each word '
               'as that word is sung.',
    phrasings=('colour the lyrics in as they are sung, like karaoke',
               'make the words fill up with colour left to right in time with the song',
               'a karaoke-style bar of colour moving through the caption'),
    related=('shape-fill-sweep', 'hue-cycle-fill', 'gradient-sweep-across-text', 'area-fill-sweep',
             'choropleth-fill', 'sheen-sweep'),
    api=('videobuilder.capabilities.typography.karaoke_highlight_sweep.draw_karaoke',
         'videobuilder.capabilities.typography.karaoke_highlight_sweep.sweep_width'),
    demo=lambda: demo.film(draw),
)
