"""Lower third slide-in bar: a solid bar carrying a name and a subtitle slides
in from the left edge near the bottom of the frame, holds, then slides back
out the way it came."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def lower_third_bar(cv, title, subtitle, enter, leave=0.0, x=80, bottom=None, width=640,
                    title_font=None, subtitle_font=None, color='#14181d', accent=demo.ACCENT,
                    ink=demo.INK, muted=demo.MUTED, pad=28, stripe=8, alpha=0.94):
    """Draw a two-line lower third whose bar has slid `enter` (0 -> 1) of the
    way in from beyond the frame's left edge, and `leave` (0 -> 1) of the way
    back out. Both are raw progress; the easing is applied here. The bar rests
    with its left edge at `x` and its bottom at `bottom` (default: 12% above
    the frame's foot). The text rides with the bar a beat behind it, clipped
    to the bar, so it never shows outside it. Returns the resting Box.

    In a film, drive it from the shot's clock, e.g.
    `lower_third_bar(cv, 'Ada Park', 'Field reporter', shot.f / 18, (shot.f - 90) / 15)`."""
    title_font = title_font or demo.font(44, 800)
    subtitle_font = subtitle_font or demo.font(24, 500)
    th, sh = vb.text.line_height(title_font), vb.text.line_height(subtitle_font)
    h = pad * 2 + th + 8 + sh
    bottom = cv.height * 0.88 if bottom is None else bottom
    rest = vb.Box(x, bottom - h, width, h)
    e_in = vb.ease_out_expo(vb.clamp01(enter))
    e_out = vb.ease_in_expo(vb.clamp01(leave))
    if e_in <= 0 or e_out >= 1:
        return rest
    away = x + width + 40  # far enough left that the whole bar is off frame
    bx = x - away * (1 - e_in) - away * e_out
    # The text trails the bar in, settling a beat after it lands.
    lag = vb.ease_out_expo(vb.clamp01(enter * 1.25 - 0.25))
    tx = bx + pad + stripe + 60 * (lag - 1)
    cv.shadow(bx, rest.y, width, h, dy=8, blur=24, color=(0, 0, 0, 0.4))
    cv.rect(bx, rest.y, width, h, color, alpha=alpha)
    cv.rect(bx, rest.y, stripe, h, accent)
    with cv.clip(bx + stripe, rest.y, width - stripe, h):
        vb.text.draw(cv, [title], title_font, tx, rest.y + pad, ink)
        vb.text.draw(cv, [subtitle], subtitle_font, tx, rest.y + pad + th + 8, muted)
    cv.mark('lower-third', bx, rest.y, width, h)
    return rest


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    lower_third_bar(cv, 'Maya Lindqvist', 'Lead designer, Northwind Studio',
                    demo.phase(n, 0.3, 1.1), demo.phase(n, 2.3, 2.8), x=96, width=720)


CAPABILITY = Capability(
    id='lower-third-slide-in-bar',
    name='Lower third slide-in bar',
    family='broadcast',
    group='Lower thirds',
    aliases=('straight lower third', 'lower-third bar', 'name strap', 'name super', 'super caption',
             'lower third title'),
    definition='A solid strip with a name and a short title on it glides in from the left near the '
               'bottom of the picture, stays a moment, then glides back off.',
    phrasings=('slide a name tag in at the bottom left while the person talks',
               'put a bar with their name and job under them, coming in from the side',
               'a TV-style caption strip that slides on and off screen'),
    related=('refresh-bar', 'carousel-slide', 'tab-panel-slide', 'character-slide-in',
             'tab-underline-slide', 'indeterminate-bar'),
    api=('videobuilder.capabilities.broadcast.lower_third_slide_in_bar.lower_third_bar',),
    demo=lambda: demo.film(draw),
)
