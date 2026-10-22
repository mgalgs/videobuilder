"""Staged Onboarding Walkthrough: a highlight ring lands on one part of the
interface, then a numbered caption for that step slides in. Only after that
does the ring move on to the next part, so the tour plays one step at a time."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def tour_step(t, start, step, count):
    """Where a tour is at time `t` (seconds): `(index, p)`. `index` is the
    current step, from 0 to `count - 1` (-1 before `start`). `p` runs 0 -> 1
    across that step, which lasts `step` seconds. The last step holds at 1."""
    if t < start:
        return -1, 0.0
    i = int((t - start) // step)
    if i >= count:
        return count - 1, 1.0
    return i, (t - start - i * step) / step


def draw_walkthrough(cv, targets, captions, t, start=0.2, step=0.9, caption_at=None, font=None,
                     color=demo.ACCENT, ink=demo.INK, panel=demo.LINE, muted=demo.MUTED, move=0.4):
    """Draw a tour over a UI you have already drawn. `targets` are the Boxes
    to point at, in order, and `captions` the text for each step. During each
    `step` seconds, the ring travels from the last target to this one for the
    first `move` of the step. Then a caption pill (number badge and text) rises
    in, centred at `caption_at` (default: below the lowest target), above a
    row of progress dots. Returns `(index, p)` from `tour_step`."""
    count = len(targets)
    i, p = tour_step(t, start, step, count)
    if i < 0:
        return i, p
    font = font or demo.font(22, 700)
    cx, cy = caption_at or (sum(b.cx for b in targets) / count, max(b.bottom for b in targets) + 90)

    # The ring: grows in on the first step and glides between targets after that.
    k = vb.ease_in_out_quart(vb.clamp01(p / move))
    cur = targets[i]
    prev = targets[i - 1] if i else vb.Box(cur.cx, cur.cy, 0, 0)
    pad = 8
    x, y, w, h = (a + (b - a) * k for a, b in zip((prev.x, prev.y, prev.w, prev.h), (cur.x, cur.y, cur.w, cur.h)))
    grow = vb.clamp01(p / move) if i == 0 else 1.0
    cv.outline(x - pad, y - pad, w + 2 * pad, h + 2 * pad, color, width=3, radius=10, alpha=grow)
    cv.outline(x - pad - 4, y - pad - 4, w + 2 * pad + 8, h + 2 * pad + 8, color, width=7, radius=14,
               alpha=0.18 * grow)
    cv.mark('ring', x - pad, y - pad, w + 2 * pad, h + 2 * pad)

    # The caption: in only once the ring has landed.
    c = vb.ease_out_back(vb.clamp01((p - move) / (1 - move) * 2.5))
    if c > 0:
        text = captions[i]
        tw, th = vb.text.block_size([text], font)
        bh = th + 24
        bw = tw + bh + 30
        bx, by = cx - bw / 2, cy - bh / 2 + 20 * (1 - c)
        with cv.layer(opacity=vb.clamp01(c)):
            cv.shadow(bx, by, bw, bh, radius=bh / 2, dy=6, blur=16, color=(0, 0, 0, 0.4))
            cv.rect(bx, by, bw, bh, panel, radius=bh / 2)
            r = bh / 2 - 7
            demo.dot(cv, bx + bh / 2, by + bh / 2, r, color)
            nf = demo.font(int(r * 1.1), 800)
            nw, nh = vb.text.block_size([str(i + 1)], nf)
            vb.text.draw(cv, [str(i + 1)], nf, bx + bh / 2 - nw / 2, by + bh / 2 - nh / 2, demo.BG)
            vb.text.draw(cv, [text], font, bx + bh + 6, by + (bh - th) / 2, ink)
        cv.mark('caption', bx, by, bw, bh)

    # Progress dots: one per step, lit up to the current one.
    gap = 18
    for j in range(count):
        dx = cx + (j - (count - 1) / 2) * gap
        on = j < i or (j == i and c > 0)
        demo.dot(cv, dx, cy + 46, 5, color if on else muted, alpha=1.0 if on else 0.5)
    return i, p


def ui(cv):
    """The demo's stand-in app window: a title, an input field and a button.
    Returns their Boxes."""
    win = vb.Box(demo.W / 2 - 230, 50, 460, 260)
    cv.shadow(win.x, win.y, win.w, win.h, radius=16, dy=10, blur=28, color=(0, 0, 0, 0.5))
    cv.rect(win.x, win.y, win.w, win.h, '#1d1f26', radius=16)
    cv.outline(win.x, win.y, win.w, win.h, demo.LINE, width=2, radius=16)
    title = vb.text.draw(cv, ['Workspace'], demo.font(30, 800), win.x + 36, win.y + 32, demo.INK)
    field = vb.Box(win.x + 36, win.y + 96, win.w - 72, 52)
    cv.rect(*field, '#14151a', radius=8)
    cv.outline(*field, demo.LINE, width=2, radius=8)
    vb.text.draw(cv, ['Your first idea'], demo.font(20, 500), field.x + 18, field.y + 14, demo.MUTED)
    button = vb.Box(win.x + 36, win.y + 180, 130, 50)
    cv.rect(*button, demo.TEAL, radius=10)
    bf = demo.font(20, 800)
    bw, bh = vb.text.block_size(['Share'], bf)
    vb.text.draw(cv, ['Share'], bf, button.cx - bw / 2, button.cy - bh / 2, demo.BG)
    return [title, field, button]


def draw(n, cv):
    targets = ui(cv)
    draw_walkthrough(cv, targets, ['Name your workspace', 'Add your first idea', 'Share it with the team'],
                     n / demo.FPS, start=0.2, step=0.9, caption_at=(demo.W / 2, 400))


CAPABILITY = Capability(
    id='staged-onboarding-walkthrough',
    name='Staged onboarding walkthrough',
    family='ui',
    group='Feedback & status',
    aliases=('step-by-step tour', 'feature tour', 'product tour', 'coach marks'),
    definition='A highlight moves from one part of an interface to the next, and each stop gets its own '
               'numbered caption that only appears once the previous step has finished.',
    phrasings=('walk the viewer through the app one feature at a time',
               'a guided tour that highlights each button with a numbered tip',
               'show the setup steps in order, pointing at each part of the screen'),
    related=('step-by-step-process-reveal', 'staging', 'page-load-sequence', 'scrollytelling-step-sequence',
             'walk-cycle', 'run-cycle'),
    api=('videobuilder.capabilities.ui.staged_onboarding_walkthrough.draw_walkthrough',
         'videobuilder.capabilities.ui.staged_onboarding_walkthrough.tour_step'),
    demo=lambda: demo.film(draw),
)
