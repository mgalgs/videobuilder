"""Word-by-word emphasis: the same idea as Word-timed captions
(`word_timed_captions.py`), which keeps the capability -- both call
`vb.captions.draw` to light up the word being said in a caption line. This
module's own code stays (a film may still import it), but it is no longer
a capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'word-timed-captions'

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
