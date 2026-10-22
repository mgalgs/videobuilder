"""Toast Slide-in Stack: small notices slide in from the side of the screen
one after another, each new arrival nudging the ones already there up a
place so they pile into a neat column."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def toast_stack(t, arrivals, slide=0.55, push=0.4, ease=vb.ease_out_quint):
    """Where each toast is at time `t` (seconds), for toasts arriving at the
    times in `arrivals` (ascending). One `(enter, rise)` per toast: `enter`
    runs 0 -> 1 as it slides in over `slide` seconds (0 before it arrives),
    `rise` is how many places it has been pushed up by later arrivals, each
    push easing in over `push` seconds -- fractional mid-push."""
    out = []
    for i, a in enumerate(arrivals):
        enter = ease(vb.clamp01((t - a) / slide)) if t >= a else 0.0
        rise = sum(ease(vb.clamp01((t - b) / push)) for b in arrivals[i + 1:])
        out.append((enter, rise))
    return out


def draw_toast_stack(cv, t, arrivals, draw_toast, right, bottom, w, h, gap=18, travel=None, **kw):
    """Draw a stack of `w` x `h` toasts anchored with the newest's bottom-right
    corner at (`right`, `bottom`), sliding in from the right by `travel` px
    (default: just past the frame's right edge) and pushed up by `h + gap`
    per later arrival. `draw_toast(cv, i, x, y, w, h)` draws toast `i` at its
    top-left; toasts not yet arrived are skipped. `kw` goes to `toast_stack`."""
    if travel is None:
        travel = cv.width - right + w + 40
    for i, (enter, rise) in enumerate(toast_stack(t, arrivals, **kw)):
        if enter <= 0:
            continue
        x = right - w + (1 - enter) * travel
        y = bottom - h - rise * (h + gap)
        draw_toast(cv, i, x, y, w, h)


MESSAGES = ('Changes saved', 'Preview is ready', 'Export complete')
PANEL = '#22242b'


def _toast(cv, i, x, y, w, h):
    cv.shadow(x, y, w, h, radius=16, dy=8, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, PANEL, radius=16)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=16)
    cx, cy, r = x + 52, y + h / 2, 20
    demo.dot(cv, cx, cy, r=r, color=demo.TEAL)
    cv.line(cx - 9, cy + 1, cx - 3, cy + 7, demo.BG, width=4)
    cv.line(cx - 3, cy + 7, cx + 9, cy - 6, demo.BG, width=4)
    f = demo.font(32, 700)
    _, th = vb.text.block_size([MESSAGES[i]], f)
    vb.text.draw(cv, [MESSAGES[i]], f, x + 92, y + (h - th) / 2, demo.INK)
    kx, ky, k = x + w - 44, y + h / 2, 8
    cv.line(kx - k, ky - k, kx + k, ky + k, demo.MUTED, width=3)
    cv.line(kx - k, ky + k, kx + k, ky - k, demo.MUTED, width=3)
    cv.mark('toast', x, y, w, h)


def draw(n, cv):
    draw_toast_stack(cv, n / demo.FPS, (0.3, 1.1, 1.9), _toast, right=demo.W - 120, bottom=demo.H - 120,
                     w=520, h=100)


TECHNIQUE = Technique(
    id='toast-slide-in-stack',
    name='Toast slide-in stack',
    family='ui',
    group='Feedback & status',
    aliases=('snackbar', 'notification toast', 'toast stack', 'notification stack', 'alert stack'),
    definition='Short notification cards glide in from the edge of the screen one at a time, '
               'and each new one shoves the earlier cards up so they build a tidy column.',
    phrasings=('little notifications pop in from the corner and pile up',
               'stack of alerts sliding in, each new one pushing the old ones up',
               'show a few "saved" messages arriving one after another in the corner'),
    related=('comment-pop-up-stack', 'stacked-card-reveal', 'tab-panel-slide', 'sticky-card-stack-on-scroll',
             'chat-bubble-sequence', 'hover-reveal-actions'),
    api=('videobuilder.techniques.ui.toast_slide_in_stack.draw_toast_stack',
         'videobuilder.techniques.ui.toast_slide_in_stack.toast_stack'),
    demo=lambda: demo.film(draw),
)
