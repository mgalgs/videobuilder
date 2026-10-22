"""Breaking News Banner Slam: a loud two-part bar -- a red tag and a headline
strip -- shoots in from the side of the frame, overshoots its mark, snaps back
with a jolt and a flash, then stays put over the picture."""
import videobuilder as vb
from videobuilder.ease import ease_out_back
from videobuilder.impact import shake

from .. import _demo as demo
from ..schema import Technique


def slam_x(p, rest, start, overshoot=ease_out_back):
    """The banner's left edge at progress `p` (0 -> 1): from `start` (off
    frame) to `rest`, past it and back on `overshoot`."""
    return start + (rest - start) * overshoot(vb.clamp01(p))


def draw_banner_slam(cv, p, tag='BREAKING', headline='NEWS', y=None, h=None, x=0.0, width=None,
                     tag_color='#d62828', strip_color='#f4f4f2', tag_ink='#ffffff', strip_ink='#14151a',
                     flash=0.18, seed=0):
    """Draw the banner at progress `p` (0 -> 1) of its slam; at 1 and beyond
    it is pinned at (`x`, `y`). It enters from the left edge: the red `tag`
    block first, the `headline` strip riding on it. Just after landing it
    jolts a few px and flashes white for `flash` of the move. Defaults: a bar
    `h` = 13% of the frame tall in the lower third, `width` the full frame.
    Returns the Box it rests in.

    In a film, drive it with the shot's clock, e.g.
    `draw_banner_slam(cv, (n - at) / 12, headline='STORM HITS COAST')` for a 12-frame slam."""
    W, H = cv.width, cv.height
    h = h or round(H * 0.13)
    y = H * 0.68 if y is None else y
    width = W - x if width is None else width
    tag_font = demo.font(round(h * 0.42), 900)
    strip_font = demo.font(round(h * 0.34), 800)
    tag_w = vb.text.measure(tag, tag_font) + h * 0.8

    left = slam_x(p, x, x - width - 40)
    landed = vb.clamp01((p - 0.55) / 0.45)            # 0 -> 1 across the settle after first contact
    dx, dy = shake(round(landed * 10), 0, frames=10, amount=h * 0.08, seed=seed) if 0 < landed < 1 else (0, 0)
    left += dx
    top = y + dy

    cv.shadow(left, top, width, h, dy=6, blur=18, color=(0, 0, 0, 0.5))
    cv.rect(left, top, width, h, strip_color)
    cv.rect(left, top, tag_w, h, tag_color)
    cv.rect(left, top + h - h * 0.06, width, h * 0.06, tag_color)        # a red rule under the strip
    th = vb.text.block_size([tag], tag_font)[1]
    vb.text.draw(cv, [tag], tag_font, left + h * 0.4, top + (h - th) / 2, tag_ink)
    sh = vb.text.block_size([headline], strip_font)[1]
    vb.text.draw(cv, [headline], strip_font, left + tag_w + h * 0.4, top + (h - sh) / 2, strip_ink)
    if 0 < landed < flash / 0.45:                       # the hit flash, fading fast
        cv.rect(left, top, width, h, '#ffffff', alpha=0.85 * (1 - landed * 0.45 / flash))
    cv.mark('banner', x, y, width, h)
    return vb.Box(x, y, width, h)


def _program(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.fill(demo.BG, alpha=0.25)


def draw(n, cv):
    _program(cv)
    draw_banner_slam(cv, demo.phase(n, 0.6, 1.2), headline='MARKETS PLUNGE AT THE OPENING BELL', seed=3)


TECHNIQUE = Technique(
    id='breaking-news-banner-slam',
    name='Breaking news banner slam',
    family='broadcast',
    group='Tickers & banners',
    aliases=('breaking bar', 'alert banner slam', 'breaking news lower third'),
    definition='A bold red-and-white news bar shoots in from the side, overshoots, snaps back into place '
               'with a jolt, and then sits fixed across the lower part of the picture.',
    phrasings=('slam a breaking news bar onto the screen',
               'a big urgent headline banner that crashes in at the bottom like on TV news',
               'make an alert strip punch in from the side and stay there'),
    related=('shatter', 'coachmark-spotlight-cutout', 'scanline-tear', 'smash-cut', 'fracture-shatter',
             'refresh-bar'),
    api=('videobuilder.techniques.broadcast.breaking_news_banner_slam.draw_banner_slam',
         'videobuilder.techniques.broadcast.breaking_news_banner_slam.slam_x',
         'videobuilder.ease.ease_out_back',
         'videobuilder.impact.shake'),
    demo=lambda: demo.film(draw),
)
