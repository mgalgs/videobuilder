"""News ticker crawl: the same idea as Infinite marquee
(`../ui/infinite_marquee.py`, which keeps the capability) -- both slide a
strip sideways without end, calling that module's own `marquee_offset`; this
one adds the fixed broadcast tag at the left and bullets between headlines.
This module's own code stays (a film may still import it), but it is no
longer a capability of its own."""
import videobuilder as vb

from .. import _demo as demo
from ..ui.infinite_marquee import marquee_offset

MERGED_INTO = 'infinite-marquee'

SEPARATOR = 0.6  # the bullet between stories, as a fraction of the font size


def crawl_cycle(headlines, font, gap=None):
    """The width in px of one full run of `headlines` set in `font`, each
    followed by `gap` px (default 3x the font size) holding a bullet. Feed it
    to `marquee_offset` as the `cycle`."""
    gap = font.size * 3 if gap is None else gap
    return sum(vb.text.measure(h, font) + gap for h in headlines)


def ticker_crawl(cv, headlines, font, x, y, w, h, offset, color=demo.INK, bullet=demo.ACCENT,
                 bar=demo.BG, label=None, label_font=None, label_color=demo.ACCENT, label_ink=demo.INK,
                 gap=None):
    """Draw a news ticker band at (x, y, w, h): a `bar`-coloured strip whose
    `headlines` (strings) run end to end, each followed by a bullet, shifted
    left by `offset` px (`marquee_offset(t, speed, crawl_cycle(...))`) and
    repeated so the line never runs dry. `label` (e.g. 'LIVE') sits in a
    fixed `label_color` tag at the left that the text slides under. Returns
    the Box of the crawling region (the band less the tag)."""
    gap = font.size * 3 if gap is None else gap
    widths = [vb.text.measure(t, font) + gap for t in headlines]
    cycle = sum(widths)
    cv.rect(x, y, w, h, bar)
    tag_w = 0
    if label:
        lf = label_font or vb.Font(font.family, font.size * 0.9, weight=900)
        lw, lh = vb.text.block_size([label], lf)
        tag_w = lw + h * 0.8
    cx, cw = x + tag_w, w - tag_w
    th = vb.text.block_size(['Ag'], font)[1]
    ty = y + (h - th) / 2
    r = font.size * SEPARATOR / 2
    with cv.clip(cx, y, cw, h):
        i, left = 0, cx - (offset % cycle)
        while left < cx + cw:
            k = i % len(headlines)
            if left + widths[k] > cx:
                tw = widths[k] - gap
                vb.text.draw(cv, [headlines[k]], font, left, ty, color)
                cv.rect(left + tw + (gap - 2 * r) / 2, y + h / 2 - r, 2 * r, 2 * r, bullet, radius=r * 0.3)
            i, left = i + 1, left + widths[k]
    if label:
        cv.rect(x, y, tag_w, h, label_color)
        cv.shadow(x + tag_w - 2, y, 2, h, blur=14, dx=6, color=(0, 0, 0, 0.5))
        vb.text.draw(cv, [label], lf, x + (tag_w - lw) / 2, y + (h - lh) / 2, label_ink)
    return vb.Box(cx, y, cw, h)


# ---- the demo: a programme picture with a crawl along its foot ----

HEADLINES = ('Harbour bridge reopens after a week of repairs',
             'Storm warning lifted for the coast',
             'City council approves the new night bus routes',
             'Local team through to the cup final')
SPEED = 300  # px/s; a broadcast crawl is slower, but the demo has only three seconds


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.rect(0, 0, demo.W, demo.H, '#000000', alpha=0.25)
    h = 96
    rise = vb.ease_out_quint(demo.phase(n, 0.0, 0.4))
    y = demo.H - 70 - h + (h + 70) * (1 - rise)
    f = demo.font(44, 700)
    cv.rect(0, y - 6, demo.W, 6, demo.TEAL)
    off = marquee_offset(n / demo.FPS, SPEED, crawl_cycle(HEADLINES, f))
    box = ticker_crawl(cv, HEADLINES, f, 0, y, demo.W, h, off, bar='#101218', label='LIVE')
    cv.mark('ticker', *box)
