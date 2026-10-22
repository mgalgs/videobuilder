"""Quote card reveal: a card settles in, a big opening quote mark draws itself
stroke by stroke, the quotation rises up line by line beneath it, and the
speaker's name slides in last behind a short rule."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _bezier(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def draw_quote_mark(cv, x, y, size, p, color, gap=0.95):
    """Draw an opening quote mark (two "6"-shaped commas) whose top-left is
    roughly (x, y) and whose height is `size`, at progress `p` (0 -> 1). Each
    comma's tail draws on from its tip down into the bowl, then the round bowl
    swells in; the second comma follows the first by a beat. Returns its Box."""
    r = size * 0.24
    width = 2 * (r * 2.4) + gap * r
    for k in range(2):
        q = vb.clamp01((p - 0.25 * k) / 0.75)
        if q <= 0:
            continue
        cx, cy = x + r * 1.0 + k * (r * 2.4 + gap * r), y + size - r
        tail = _bezier((cx + r * 1.15, cy - r * 2.75), (cx - r * 1.35, cy - r * 2.2), (cx - r * 0.55, cy))
        vb.paths.draw(cv, vb.paths.reveal(tail, vb.ease_in_out_quart(vb.clamp01(q / 0.6))), color,
                      width=r * 0.85)
        bowl = vb.ease_out_back(vb.clamp01((q - 0.45) / 0.55))
        if bowl > 0:
            demo.dot(cv, cx, cy, r * bowl, color=color)
    return vb.Box(x, y, width, size)


def draw_quote_card(cv, box, lines, name, p, font, small, ink, accent, card='#1d1f26', role=None,
                    pad=56, mark=150):
    """Draw a quote card filling `box` (a `vb.Box`) at progress `p` (0 -> 1).

    0 -> 0.15 the card fades up and lifts into place; 0.1 -> 0.45 the quote
    mark draws in (`draw_quote_mark`, `mark` px tall, in `accent`); 0.35 ->
    0.8 each of `lines` rises into its own slot from just below, staggered,
    clipped so it emerges from nothing; 0.75 -> 1 a short `accent` rule grows
    and `name` (and `role` under it, muted) slides in beside it. Fonts:
    `font` for the quote, `small` for the attribution. Nothing reflows as
    parts arrive. Returns the Box of the finished quote text."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    c = vb.ease_out_quint(vb.clamp01(p / 0.15))
    if c <= 0:
        return vb.Box(box.x + pad, box.y + pad, 0, 0)
    lift = 24 * (1 - c)
    with cv.layer(opacity=c, dy=lift):
        cv.shadow(box.x, box.y, box.w, box.h, radius=22, dy=12, blur=36, color=(0, 0, 0, 0.5))
        cv.rect(box.x, box.y, box.w, box.h, card, radius=22)
        cv.outline(box.x, box.y, box.w, box.h, '#ffffff', width=1, radius=22, alpha=0.06)
    x, y = box.x + pad, box.y + pad + lift
    draw_quote_mark(cv, x, y, mark * 0.6, vb.clamp01((p - 0.1) / 0.35), accent)

    lh = vb.text.line_height(font)
    ty = y + mark * 0.6 + pad * 0.6
    q = vb.clamp01((p - 0.35) / 0.45)
    for i, line in enumerate(lines):
        t = vb.ease_out_quint(vb.clamp01((q - 0.3 * i / max(1, len(lines) - 1)) / 0.7))
        if t > 0:
            ly = ty + i * lh
            with cv.clip(x - 4, ly, box.w, lh):
                vb.text.draw(cv, [line], font, x, ly + lh * 0.8 * (1 - t), ink, alpha=t)
    w, h = vb.text.block_size(lines, font)

    a = vb.clamp01((p - 0.75) / 0.25)
    if a > 0:
        ay = ty + h + pad * 0.55
        sh = vb.text.line_height(small)
        rule = 36 * vb.ease_out_quint(vb.clamp01(a / 0.5))
        cv.line(x, ay + sh / 2, x + rule, ay + sh / 2, accent, width=3)
        s = vb.ease_out_quint(vb.clamp01((a - 0.2) / 0.8))
        if s > 0:
            nx = x + 52 + 16 * (1 - s)
            vb.text.draw(cv, [name], small, nx, ay, ink, alpha=s)
            if role:
                vb.text.draw(cv, [role], small, nx, ay + sh, demo.MUTED, alpha=s * 0.9)
    return vb.Box(x, ty, w, h)


QUOTE = ('Simplicity is the art of', 'leaving the right things out.')


def draw(n, cv):
    box = vb.Box(demo.W / 2 - 330, demo.H / 2 - 210, 660, 420)
    out = draw_quote_card(cv, box, QUOTE, 'Ada Lindqvist', demo.phase(n, 0.2, 2.5),
                          demo.font(40, 800), demo.font(22, 600), demo.INK, '#f2b632',
                          role='Product designer')
    cv.mark('text', *out)


CAPABILITY = Capability(
    id='quote-card-reveal',
    name='Quote card reveal',
    family='broadcast',
    group='Social media',
    aliases=('pull quote card', 'quotation graphic', 'testimonial card'),
    definition='A card eases in, a large opening quote mark draws itself on, then the quoted words '
               'rise into place and the speaker\'s name follows underneath.',
    phrasings=('animate a quote for social with a big quotation mark and the person\'s name',
               'a testimonial card where the quote marks draw in and the text appears after',
               'show a pull quote on a card, words first, then who said it'),
    related=('title-card-reveal', 'text-mask-reveal', 'stacked-card-reveal', 'scroll-driven-text-reveal',
             'scroll-linked-clip-reveal', 'wipe-reveal'),
    api=('videobuilder.capabilities.broadcast.quote_card_reveal.draw_quote_card',
         'videobuilder.capabilities.broadcast.quote_card_reveal.draw_quote_mark'),
    demo=lambda: demo.film(draw),
)
