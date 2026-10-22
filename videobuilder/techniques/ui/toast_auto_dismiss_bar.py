"""Toast auto-dismiss bar: a small notification slides in, a thin bar along
its bottom edge drains like a countdown, and when it runs out the toast
slides away by itself."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def toast_timeline(t, life, enter=0.35, leave=0.35):
    """`t` seconds since the toast was triggered -> `(shown, left)`.
    `shown` eases 0 -> 1 over `enter`, holds while the bar drains, then eases
    back to 0 over `leave`. `left` is the bar's remaining fraction, 1 -> 0
    linearly over the `life` seconds after the toast has arrived."""
    if t < enter:
        return vb.ease_out_back(vb.clamp01(t / enter)), 1.0
    t -= enter
    if t < life:
        return 1.0, 1 - t / life
    return 1 - vb.ease_in_expo(vb.clamp01((t - life) / leave)), 0.0


def draw_toast(cv, cx, y, text, left, shown=1.0, w=520, h=96, travel=160, color='#262830',
               ink=demo.INK, bar=demo.TEAL, track=demo.LINE, icon=demo.TEAL, font=None):
    """A toast whose resting top-left sits at (cx - w/2, y), `shown` (0 -> 1)
    of the way in from `travel` px below and faded, with its auto-dismiss bar
    `left` (1 -> 0) full, draining from right to left. Pair with
    `toast_timeline`. Returns the toast's Box as drawn."""
    if shown <= 0:
        return vb.Box(cx - w / 2, y + travel, w, h)
    x, y = cx - w / 2, y + travel * (1 - shown)
    r, bh = 16, 8
    f = font or demo.font(34, 700)
    with cv.layer(opacity=vb.clamp01(shown)):
        cv.shadow(x, y, w, h, radius=r, dy=12, blur=30, color=(0, 0, 0, 0.5))
        with cv.clip(x, y, w, h, radius=r):
            cv.rect(x, y, w, h, color)
            cv.rect(x, y + h - bh, w, bh, track)
            cv.rect(x, y + h - bh, w * vb.clamp01(left), bh, bar)
        ix, iy, ir = x + 30 + 20, y + (h - bh) / 2, 20
        cv.sector(ix, iy, ir, 0, 2 * math.pi, icon)
        cv.line(ix - 9, iy + 1, ix - 3, iy + 8, demo.BG, width=4)   # a check mark
        cv.line(ix - 3, iy + 8, ix + 10, iy - 7, demo.BG, width=4)
        tw, th = vb.text.block_size([text], f)
        vb.text.draw(cv, [text], f, ix + ir + 22, iy - th / 2, ink)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    # a faint app window behind, so the toast reads as a notification over UI
    cv.outline(160, 90, demo.W - 320, demo.H - 180, demo.LINE, width=2, radius=22)
    for i, frac in enumerate((0.55, 0.4, 0.48)):
        cv.rect(240, 180 + 70 * i, (demo.W - 480) * frac, 22, demo.LINE, radius=11)
    shown, left = toast_timeline(n / demo.FPS - 0.25, life=1.8)
    box = draw_toast(cv, demo.W / 2, demo.H - 290, 'Changes saved', left, shown)
    cv.mark('toast', *box)


TECHNIQUE = Technique(
    id='toast-auto-dismiss-bar',
    name='Toast auto-dismiss bar',
    family='ui',
    group='Feedback & status',
    aliases=('toast timer bar', 'snackbar countdown', 'notification progress bar', 'auto-hide toast'),
    definition='A small pop-up message slides in with a thin strip along its edge that shrinks away '
               'like a timer, and once the strip is gone the message slides off by itself.',
    phrasings=('a notification that pops up and has a little bar counting down until it disappears',
               'show a toast with a shrinking progress line, then have it go away on its own',
               'a "saved" message that times out with a draining bar'),
    related=('swipe-to-dismiss', 'hover-reveal-actions', 'number-count-down', 'tooltip-fade-follow',
             'tab-underline-slide', 'bottom-sheet-slide-up'),
    api=('videobuilder.techniques.ui.toast_auto_dismiss_bar.draw_toast',
         'videobuilder.techniques.ui.toast_auto_dismiss_bar.toast_timeline'),
    demo=lambda: demo.film(draw),
)
