"""Impact Shake: videobuilder already has the jolt as `impact.shake` (the
decaying rattle `impact.Hit` uses on the whole frame), so this entry only
names it and demos it on a word: offset the text by `shake(n, hit)` and it
kicks on every hit, then settles."""
from videobuilder import impact

from .. import _demo as demo
from ..schema import Technique

HITS = (18, 40, 62)  # frames the word is struck on


def draw(n, cv):
    dx = dy = 0.0
    flash = 0.0
    for i, at in enumerate(HITS):
        sx, sy = impact.shake(n, at, frames=12, amount=34, seed=i)
        dx, dy = dx + sx, dy + sy
        if at <= n < at + 8:
            flash = max(flash, 1 - (n - at) / 8)
    x, y = demo.W / 2 + dx, demo.H / 2 + dy
    box = demo.word(cv, 'IMPACT', x, y, size=150, weight=900)
    if flash:  # the word blushes accent as it is struck
        demo.word(cv, 'IMPACT', x, y, size=150, weight=900, color=demo.ACCENT, alpha=flash)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='impact-shake',
    name='Impact shake',
    family='typography',
    group='Wave and motion',
    aliases=('hit shake text', 'kick jolt', 'text jolt'),
    definition='Text jerks sharply from side to side the moment something strikes it, '
               'the rattle dying away within a fraction of a second.',
    phrasings=('make the title jolt every time the beat hits',
               'the word rattles when it gets punched, then goes still',
               'give the headline a quick shake on impact'),
    related=('impact', 'impact-hit', 'shake', 'recoil', 'hitstop', 'error-shake'),
    api=('videobuilder.impact.shake',),
    demo=lambda: demo.film(draw),
)
