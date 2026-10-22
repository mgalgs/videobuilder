"""Pop-on Captions: each caption is a whole block of one or two lines that
cuts on at its cue and cuts off at its end, with nothing animating in
between -- the classic subtitle, as opposed to captions that roll up or
light up word by word (`vb.captions.draw`)."""
import bisect

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def cue_at(cues, t):
    """The `(start, end, text)` cue on screen at `t` seconds, or None in a
    gap. `cues` are sorted by start and don't overlap; a cue that runs past
    the next one's start gives way to it."""
    i = bisect.bisect_right([c[0] for c in cues], t) - 1
    if i >= 0 and t < cues[i][1]:
        return cues[i]
    return None


def draw_pop_on(cv, cues, t, font, color='#ffffff', box='#000000', box_alpha=0.72, safe=None,
                position='bottom', max_width=None, mark='caption'):
    """Draw the caption whose cue covers `t` (seconds) as one block, all at
    once: its text wrapped into balanced lines no wider than `max_width`
    (default two thirds of `safe`), centred, in a rounded `box` (None: no
    box) at the bottom ('top', 'middle') of `safe` (default
    `vb.captions.safe_area(cv)`). A newline in the text forces a break.
    Returns the block's Box, or None between cues, when it draws nothing."""
    cue = cue_at(cues, t)
    if cue is None:
        return None
    safe = safe or vb.captions.safe_area(cv)
    max_width = max_width if max_width is not None else safe.w * 2 / 3
    lines = [ln for part in cue[2].split('\n') for ln in vb.text.wrap(part, font, max_width, balance=True)]
    tw, th = vb.text.block_size(lines, font)
    pad_v, pad_h = font.size * 0.35, font.size * 0.55
    bw, bh = tw + 2 * pad_h, th + 2 * pad_v
    by = {'bottom': safe.bottom - bh, 'top': safe.y, 'middle': safe.cy - bh / 2}[position]
    b = vb.Box(safe.cx - bw / 2, by, bw, bh)
    if box is not None:
        cv.rect(*b, box, radius=font.size * 0.22, alpha=box_alpha)
    vb.text.draw(cv, lines, font, b.x + pad_h, b.y + pad_v, color, align='center', width=tw)
    if mark:
        cv.mark(mark, *b)
    return b


CUES = ((0.2, 1.3, 'We move together,\none step at a time.'),
        (1.7, 2.9, 'And find our rhythm\nin the motion.'))


def draw(n, cv):
    t = n / demo.FPS
    safe = vb.Box(0, 0, demo.W, demo.H).pad(demo.H * 0.1, demo.W * 0.0625, demo.H * 0.22, demo.W * 0.0625)
    draw_pop_on(cv, CUES, t, demo.font(54, 700), color=demo.INK, box=demo.LINE, box_alpha=0.9, safe=safe)
    # a cue timeline under the frame: the blocks are on exactly while the playhead is in a cue
    x0, x1, y = 160, demo.W - 160, demo.H - 70
    cv.line(x0, y, x1, y, demo.MUTED, width=2, alpha=0.4)
    for start, end, _ in CUES:
        a, b = x0 + (x1 - x0) * start / demo.SECONDS, x0 + (x1 - x0) * end / demo.SECONDS
        cv.rect(a, y - 7, b - a, 14, demo.ACCENT, radius=7, alpha=0.9 if start <= t < end else 0.35)
    px = x0 + (x1 - x0) * min(t / demo.SECONDS, 1)
    cv.line(px, y - 20, px, y + 20, demo.INK, width=3)


TECHNIQUE = Technique(
    id='pop-on-captions',
    name='Pop-on captions',
    family='typography',
    group='Lyrics and captions',
    aliases=('pop-on subtitles', 'caption block pop', 'subtitle pop-on', 'block captions'),
    definition='A whole caption of a line or two cuts onto the screen at once when its cue starts '
               'and cuts away when it ends, with no motion on the words themselves.',
    phrasings=('show the dialogue as plain subtitles, one full caption at a time',
               'captions that just appear and vanish in blocks, no word-by-word animation',
               'swap in each subtitle as a complete two-line chunk on its timing'),
    related=('callout-highlight', 'slide-over-cover', 'jump-cut', 'comment-pop-up-stack', 'voiceover',
             'play-pause-morph'),
    api=('videobuilder.techniques.typography.pop_on_captions.draw_pop_on',
         'videobuilder.techniques.typography.pop_on_captions.cue_at'),
    demo=lambda: demo.film(draw),
)
