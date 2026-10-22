"""Word-by-word emphasis: videobuilder already does it as `vb.captions.draw`,
which colours the word being spoken in a line of timed words, so this entry
only names it and demos it with a hand-timed `Track`."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

LINE = 'every word takes its turn to shine'
START, STEP = 0.35, 0.36  # the first word lights at START s, each next one STEP s later

TRACK = vb.captions.Track(vb.captions.Word(w, START + i * STEP, START + (i + 1) * STEP)
                          for i, w in enumerate(LINE.split()))


def draw(n, cv):
    t = n / demo.FPS
    lit = demo.ACCENT if t >= START else demo.MUTED  # before the first word: the whole line, unlit
    t = min(max(t, START), TRACK[-1].end - 0.01)     # and after the last, hold it lit
    vb.captions.draw(cv, TRACK, t, font=demo.font(44, 800), safe=vb.Box.of(cv), position='middle',
                     color=demo.MUTED, spoken=lit, box='#000000', box_alpha=0.35, linger=STEP, mark='text')


CAPABILITY = Capability(
    id='word-by-word-emphasis',
    name='Word-by-word emphasis',
    family='typography',
    group='Lyrics and captions',
    aliases=('karaoke text', 'karaoke captions', 'active word highlight', 'word highlight captions'),
    definition='A whole line stays on screen while a highlight colour moves along it one word at a time, '
               'marking the word being said.',
    phrasings=('light up each word of the caption as it is spoken',
               'karaoke-style text where the current word changes colour',
               'highlight the words one after another along the sentence'),
    related=('per-word-fade-in', 'callout-highlight', 'gradient-sweep-across-text', 'shine-glint-sweep',
             'scroll-driven-text-reveal', 'stamp-impression'),
    api=('videobuilder.captions.draw', 'videobuilder.captions.Track', 'videobuilder.captions.Word'),
    demo=lambda: demo.film(draw),
)
