"""Title Card Reveal: a thin rule draws out across the frame, then the title's
letters rise up out of it one after another, hidden below the rule until they
clear it, and settle into place."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def draw_title_card(cv, text, font, cx, rule_y, p, color, rule_color, rule_split=0.35, stagger=0.5,
                    gap=14, overhang=60, rule_width=4):
    """Draw `text` revealing at progress `p` (0 -> 1), centred on `cx`, its
    baseline area resting `gap` above a rule at `rule_y`. Up to `rule_split`
    the rule grows out from `cx` to `overhang` past both ends of the line; the
    rest of `p` raises the letters from below the rule, each starting a little
    after the one before it (`stagger` is the share of that span spent
    staggering), clipped so nothing shows beneath the rule. Returns the Box of
    the finished title."""
    w, h = vb.text.block_size([text], font)
    x, y = cx - w / 2, rule_y - gap - h
    half = (w / 2 + overhang) * vb.ease_in_out_quart(vb.clamp01(p / rule_split))
    if half > 0:
        cv.line(cx - half, rule_y, cx + half, rule_y, rule_color, width=rule_width)
    q = vb.clamp01((p - rule_split) / (1 - rule_split))
    if q > 0:
        with cv.clip(x - overhang, 0, w + 2 * overhang, rule_y - rule_width / 2):
            left = x
            for i, ch in enumerate(text):
                start = stagger * i / max(1, len(text) - 1)
                t = vb.ease_out_expo(vb.clamp01((q - start) / (1 - stagger)))
                if t > 0:
                    vb.text.draw(cv, [ch], font, left, y + (h + gap) * (1 - t), color)
                left += vb.text.measure(ch, font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 900)
    box = draw_title_card(cv, 'MOTION', f, demo.W / 2, demo.H / 2 + 70, demo.phase(n, 0.3, 2.3),
                          demo.INK, demo.ACCENT)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='title-card-reveal',
    name='Title card reveal',
    family='typography',
    group='Titles and captions',
    aliases=('title sequence card', 'opening title'),
    definition='A line sweeps out across the screen and the title climbs up out of it letter by letter, '
               'opening the piece.',
    phrasings=('an opening title where a line draws across and the name rises up from it',
               'start the video with a title card that animates in over a plain background',
               'letters pop up from behind an underline to introduce the film'),
    related=('tile-grid-title-reveal', 'broadcast-title-card-stinger', 'stacked-card-reveal',
             'text-mask-reveal', 'quote-card-reveal', 'curtain-reveal'),
    api=('videobuilder.techniques.typography.title_card_reveal.draw_title_card',),
    demo=lambda: demo.film(draw),
)
