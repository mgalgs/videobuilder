"""Blinking Cursor: a caret after the last letter switches on and off on a
steady beat, held solid while letters are still arriving."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def cursor_on(t, since=0.0, period=1.0, duty=0.55, soft=0.0):
    """How visible a blinking cursor is at `t` seconds, 0 -> 1. Before
    `since` (the last keystroke) it holds solid; from there it is on for the
    first `duty` of every `period` and off for the rest. `soft` (seconds)
    fades each edge instead of snapping, for a gentler, OS-style blink."""
    if t < since:
        return 1.0
    u = (t - since) % period
    on = duty * period
    if soft <= 0:
        return 1.0 if u < on else 0.0
    if u < on:
        return vb.clamp01((on - u) / soft) if u > on - soft else 1.0
    return vb.clamp01((u - (period - soft)) / soft) if u > period - soft else 0.0


def draw_cursor(cv, x, y, h, t, color, shape='block', width=None, **kw):
    """Draw a blinking cursor whose left edge is at `x`, on a line whose top
    is `y` and height `h`, at `t` seconds. `shape`: 'block' (a cell wide),
    'bar' (a thin I-beam) or 'underline'. `width` overrides the cell width
    (default about half of `h`). `kw` goes to `cursor_on`. Returns its
    visibility, 0 -> 1."""
    a = cursor_on(t, **kw)
    w = width if width is not None else h * 0.5
    if a > 0:
        if shape == 'bar':
            cv.rect(x, y + h * 0.1, max(2.0, h * 0.07), h * 0.8, color, alpha=a)
        elif shape == 'underline':
            cv.rect(x, y + h * 0.82, w, max(2.0, h * 0.08), color, alpha=a)
        else:
            cv.rect(x, y + h * 0.12, w, h * 0.76, color, alpha=a)
    return a


def draw(n, cv):
    t = n / demo.FPS
    f = demo.mono(84, 600)
    prompt, text = '> ', 'ready'
    full = prompt + text
    w, h = vb.text.block_size([full + ' '], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    start, rate = 0.25, 0.09                     # one letter every 90 ms, then the cursor rests
    typed = max(0, min(len(text), int((t - start) / rate) + 1)) if t >= start else 0
    vb.text.draw(cv, [prompt], f, x, y, demo.ACCENT)
    if typed:
        vb.text.draw(cv, [text[:typed]], f, x + vb.text.measure(prompt, f), y, demo.INK)
    cx = x + vb.text.measure(prompt + text[:typed], f)
    draw_cursor(cv, cx + 4, y, h, t, demo.INK, width=vb.text.measure('M', f) * 0.8,
                since=start + len(text) * rate, period=0.8)
    cv.mark('text', x, y, w, h)


TECHNIQUE = Technique(
    id='blinking-cursor',
    name='Blinking cursor',
    family='typography',
    group='Typewriter and terminal',
    aliases=('blinking caret', 'text cursor blink', 'terminal cursor', 'insertion point'),
    definition='A thin bar or solid block sits just after the last character and flashes on and off '
               'at a steady rhythm, as if waiting for the next keystroke.',
    phrasings=('a cursor flashing at the end of the line like someone is about to type',
               'put a blinking block after the text, like a terminal prompt',
               'the caret keeps pulsing on and off once the typing stops'),
    related=('cursor-follower-dot-and-ring', 'cursor-state-change', 'spotlight-hover',
             'cursor-particle-trail', 'hover-lift', 'cursor-follow-auto-zoom'),
    api=('videobuilder.techniques.typography.blinking_cursor.draw_cursor',
         'videobuilder.techniques.typography.blinking_cursor.cursor_on'),
    demo=lambda: demo.film(draw),
)
