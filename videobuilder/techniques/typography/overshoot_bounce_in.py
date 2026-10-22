"""Overshoot Bounce-In: the letters arrive one after another, each riding an
under-damped spring (`vb.spring`) that carries it past its place on the line,
back, and to rest."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SPRING = vb.damped(0.3, hz=2.0)   # about a third past the line on the first swing, settled in about a second


def bounce_in(i, t, stagger=0.07, spring=SPRING):
    """Progress of letter `i` at `t` seconds after the first letter starts: 0
    before it starts, then a spring step that swings past 1 and settles on
    it. Letter `i` starts `i * stagger` seconds after the first."""
    return vb.spring(t - i * stagger, **spring)


def draw_bounce_in(cv, text, font, x, y, t, color, rise=140, stagger=0.07, spring=SPRING, fade=0.12):
    """Draw `text` bouncing in from its top-left (x, y), `t` seconds after the
    first letter starts. Each letter begins `rise` px below its place (negative
    `rise`: above, so it drops in), fades in over `fade` s and springs up past
    the line before settling on it. Spaces just hold their width. Returns the
    Box of the finished line."""
    left = x
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        local = t - i * stagger
        if not ch.isspace() and local > 0:
            p = bounce_in(i, t, stagger, spring)
            vb.text.draw(cv, [ch], font, left, y + rise * (1 - p), color, alpha=vb.clamp01(local / fade))
        left += adv
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'BOUNCE'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    demo.floor(cv, y + h * 0.86, demo.LINE)   # the line the letters come to rest on
    box = draw_bounce_in(cv, text, f, x, y, n / demo.FPS - 0.35, demo.INK, rise=180, stagger=0.09)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='overshoot-bounce-in',
    name='Overshoot bounce-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('overshoot bounce', 'spring letter bounce', 'elastic character entrance'),
    definition='Letters pop into a word one at a time, each shooting a little past its spot on the line, '
               'springing back and wobbling to a stop.',
    phrasings=('make each letter spring up into place with a bounce',
               'the title bounces in one character at a time',
               'letters jump up, overshoot and settle like they are on springs'),
    related=('underdamped-spring', 'bounce-ease-in', 'bounce-ease-out', 'ease-out-back', 'overdamped-spring',
             'ball-bounce'),
    api=('videobuilder.techniques.typography.overshoot_bounce_in.draw_bounce_in',
         'videobuilder.techniques.typography.overshoot_bounce_in.bounce_in',
         'videobuilder.spring', 'videobuilder.damped'),
    demo=lambda: demo.film(draw),
)
