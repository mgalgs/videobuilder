"""Two-tier kicker and title stack: a small capitalised kicker line comes in
first, then the big title rises into place beneath it out of an invisible
floor -- the classic two-line lower third."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def kicker_title_progress(p, split=0.45, ease=vb.ease_out_quint):
    """The kicker's and the title's own progress (each 0 -> 1, eased) at
    overall progress `p`: the kicker runs over the first `split` of the
    build, the title starts a third of the way into it and ends at `p = 1`."""
    k = ease(vb.clamp01(p / split))
    t0 = split / 3
    t = ease(vb.clamp01((p - t0) / (1 - t0)))
    return k, t


def draw_kicker_title(cv, kicker, title, x, y, p, kicker_font, title_font, kicker_color, title_color,
                      gap=10, slide=24, split=0.45, rule=True):
    """Draw a kicker line over a title, top-left at (x, y), building at
    progress `p`. The kicker (shown in capitals) slides in from the left by
    `slide` px and fades up, led by a short accent rule when `rule`; the
    title then rises from under a clip at its own baseline box, so it seems
    to come up out of a slot beneath the kicker. `gap` is the space between
    the two lines; `split` goes to `kicker_title_progress`. Returns the Box of
    the finished stack."""
    kicker = kicker.upper()
    k, t = kicker_title_progress(p, split)
    kw, kh = vb.text.block_size([kicker], kicker_font)
    tw, th = vb.text.block_size([title], title_font)
    kx = x
    if rule:
        bar = kh * 0.9
        cv.rect(x, y + (kh - bar) / 2, 4, bar * k, kicker_color, alpha=k)
        kx = x + 14
    if k > 0:
        vb.text.draw(cv, [kicker], kicker_font, kx - slide * (1 - k), y, kicker_color, alpha=k)
    ty = y + kh + gap
    if t > 0:
        with cv.clip(x - 4, ty, tw + 8, th):
            vb.text.draw(cv, [title], title_font, x, ty + th * (1 - t), title_color)
    return vb.Box(x, y, max(kx - x + kw, tw), kh + gap + th)


def draw(n, cv):
    x, y = 96, demo.H - 210
    box = draw_kicker_title(cv, 'Live from the studio', 'Evening Edition', x, y, demo.phase(n, 0.3, 1.9),
                            demo.font(24, 800, tracking=0.12), demo.font(84, 900), demo.ACCENT, demo.INK)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='two-tier-kicker-and-title-stack',
    name='Two-tier kicker and title stack',
    family='broadcast',
    group='Lower thirds',
    aliases=('kicker and headline', 'eyebrow title', 'kicker over title'),
    definition='A short line of small capitals shows up first as a label, and a much larger title '
               'then rises into place directly underneath it.',
    phrasings=('a little all-caps label pops in and then the big headline slides up below it',
               'lower third with a small tag line on top and the main title rising under it',
               'eyebrow text first, then the title comes up beneath'),
    related=('stacked-line-build', 'virtual-first-down-line', 'podium-rise', 'character-rise',
             'title-card-reveal', 'emboss'),
    api=('videobuilder.capabilities.broadcast.two_tier_kicker_and_title_stack.draw_kicker_title',
         'videobuilder.capabilities.broadcast.two_tier_kicker_and_title_stack.kicker_title_progress'),
    demo=lambda: demo.film(draw),
)
