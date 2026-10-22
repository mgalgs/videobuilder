"""Step-by-step Process Reveal: numbered steps build down a column one at a
time, each a number badge and a card with a title and a short line of text,
joined by a connector. The newest step is the active one: its badge and card
are lit, and the steps before it settle back to a quieter "done" look."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def step_reveal(t, count, start=0.3, gap=0.6, enter=0.45, settle=0.25):
    """Where a `count`-step build stands at time `t` (seconds): a list of
    `(shown, active)` pairs, each 0 -> 1. Step `i` begins at `start + i * gap`
    and `shown` rises over `enter` s; `active` is 1 from then until the next
    step begins, then falls over `settle` s (the last step stays active)."""
    out = []
    for i in range(count):
        t0 = start + i * gap
        shown = vb.clamp01((t - t0) / enter)
        active = 1.0 if shown > 0 else 0.0
        if i < count - 1:
            active *= 1 - vb.clamp01((t - t0 - gap) / settle)
        out.append((shown, active))
    return out


def _mix(a, b, k):
    """Hex colour `a` blended toward `b` by `k`."""
    ca = [int(a[j:j + 2], 16) for j in (1, 3, 5)]
    cb = [int(b[j:j + 2], 16) for j in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * k):02x}' for x, y in zip(ca, cb))


def draw_process_steps(cv, steps, x, y, t, row=104, card_w=440, r=24, active=demo.ACCENT, done=demo.TEAL,
                       panel=demo.LINE, ink=demo.INK, muted=demo.MUTED, slide=40, **timing):
    """Draw a vertical numbered process at time `t`. `steps` is a list of
    `(title, description)`; badges are centred on column `x`, the first at
    height `y`, `row` px apart, each with a card `card_w` wide to its right.
    A step slides in from the left and fades up while its badge pops in and
    the connector from the step above draws down to it. The active step
    (see `step_reveal`, which takes `timing`) gets the `active` colour and a
    lit card; earlier steps settle to `done`. Returns the list of
    `(shown, active)` amounts."""
    states = step_reveal(t, len(steps), **timing)
    title_f = demo.font(26, 800)
    desc_f = demo.font(17, 500)
    num_f = demo.font(round(r * 0.8), 800)
    card_h = row - 24
    for i, (shown, _) in enumerate(states[1:], 1):  # connectors first, under the badges
        if shown > 0:
            y0, y1 = y + (i - 1) * row + r, y + i * row - r
            cv.line(x, y0, x, y0 + (y1 - y0) * vb.ease_out_quint(vb.clamp01(shown * 1.6)), muted, width=3,
                    alpha=0.7)
    for i, ((title, desc), (shown, act)) in enumerate(zip(steps, states)):
        if shown <= 0:
            continue
        cy = y + i * row
        e = vb.ease_out_quint(shown)
        dx = -slide * (1 - e)
        color = _mix(done, active, act)
        with cv.layer(opacity=e):
            # the card: lit (tinted, outlined) while active
            cx0, cy0 = x + r + 22 + dx, cy - card_h / 2
            cv.shadow(cx0, cy0, card_w, card_h, radius=14, dy=6, blur=18, color=(0, 0, 0, 0.35))
            cv.rect(cx0, cy0, card_w, card_h, _mix(panel, active, 0.16 * act), radius=14)
            if act > 0:
                cv.outline(cx0, cy0, card_w, card_h, active, width=2, radius=14, alpha=0.8 * act)
                cv.rect(cx0, cy0 + 14, 5, card_h - 28, active, radius=2.5, alpha=act)
            vb.text.draw(cv, [title], title_f, cx0 + 24, cy0 + 13, _mix(muted, ink, 0.55 + 0.45 * act))
            vb.text.draw(cv, [desc], desc_f, cx0 + 24, cy0 + 49, muted, alpha=0.75 + 0.25 * act)
            cv.mark('step', cx0, cy0, card_w, card_h)
        # the badge: pops in, with a halo while active
        s = vb.ease_out_back(shown)
        if act > 0:
            demo.dot(cv, x, cy, r * s * (1.25 + 0.25 * act), active, alpha=0.22 * act)
        demo.dot(cv, x, cy, r * s, color)
        num = f'{i + 1:02d}'
        w, h = vb.text.block_size([num], num_f)
        vb.text.draw(cv, [num], num_f, x - w / 2, cy - h / 2, demo.BG, alpha=vb.clamp01(shown * 2))
    return states


STEPS = (('Discover', 'Listen to people and collect ideas'),
         ('Define', 'Pick one direction and write the brief'),
         ('Build', 'Make it, test it, make it better'),
         ('Launch', 'Ship it and watch how it lands'))


def draw(n, cv):
    x = demo.W / 2 - 250
    draw_process_steps(cv, STEPS, x, demo.H / 2 - 1.5 * 104, n / demo.FPS, start=0.25, gap=0.62)


TECHNIQUE = Technique(
    id='step-by-step-process-reveal',
    name='Step-by-step process reveal',
    family='broadcast',
    group='Process diagrams',
    aliases=('stepper', 'numbered steps build', 'process steps', 'how-it-works steps'),
    definition='Numbered stages of a process appear one after another down the screen, each with a heading '
               'and a short note, and the newest stage is highlighted while earlier ones quieten.',
    phrasings=('build up the steps of our process one at a time, numbered',
               'a how-it-works list where each stage pops in and gets highlighted in turn',
               'show step 1, then step 2, then step 3 with a line connecting them'),
    related=('progress-steps-connector-fill', 'steps-easing', 'staged-onboarding-walkthrough',
             'infographic-icon-sequence', 'funnel-stage-reveal', 'staggered-cascade-reveal'),
    api=('videobuilder.techniques.broadcast.step_by_step_process_reveal.draw_process_steps',
         'videobuilder.techniques.broadcast.step_by_step_process_reveal.step_reveal'),
    demo=lambda: demo.film(draw),
)
