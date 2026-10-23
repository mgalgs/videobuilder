"""Freeze Frame: the scene's clock stops on one moment, the picture holds
there for a beat, then the action picks up again from where it stopped."""
from .. import _demo as demo
from ..schema import Capability


def freeze_frame(t, at, hold):
    """Film time `t` (seconds) -> the scene time to draw: `t` up to `at`,
    stuck on `at` for `hold` seconds, then `t - hold` so the action resumes
    exactly where it froze.

    In a film, draw the scene at the remapped time, e.g.
    `scene(cv, freeze_frame(n / fps, 1.2, 0.8))`; `freeze_frame(t, at, inf)` never resumes."""
    if t <= at:
        return t
    if t <= at + hold:
        return at
    return t - hold


HOLD = 1.6                      # the freeze lasts 1.6 s of film time, so the gallery poster (70%) lands in it
FLIGHT = demo.SECONDS - HOLD    # how long the throw itself takes, in scene time
AT = FLIGHT / 2                 # it freezes at the top of the arc


def ball(cv, s):
    """The scene at scene time `s`: a ball thrown in an arc across the floor,
    with a short trail of where it has just been."""
    W, H = demo.W, demo.H
    ground, r = H * 0.78, H * 0.06
    x0, x1, top = W * 0.15, W * 0.85, H * 0.2

    def at(u):
        u = min(max(u / FLIGHT, 0.0), 1.0)
        return x0 + (x1 - x0) * u, ground - r - (ground - r - top) * 4 * u * (1 - u)

    demo.floor(cv, ground)
    for k in range(1, 5):
        tx, ty = at(s - 0.06 * k)
        demo.dot(cv, tx, ty, r * (0.3 - 0.05 * k), color=demo.TEAL, alpha=0.9 - 0.18 * k)
    x, y = at(s)
    demo.dot(cv, x, y, r)
    cv.mark('ball', x - r, y - r, 2 * r, 2 * r)


def draw(n, cv):
    t = n / demo.FPS
    ball(cv, freeze_frame(t, AT, HOLD))
    held = demo.phase(n, AT, AT + 0.12) * (1 - demo.phase(n, AT + HOLD - 0.12, AT + HOLD))
    if held > 0:  # mark the beat: a quick flash, a frame around the picture and a pause sign
        cv.fill('#ffffff', alpha=0.5 * max(0.0, 1 - (t - AT) / 0.2))
        m, u = demo.H * 0.03, demo.H / 540
        cv.outline(m, m, demo.W - 2 * m, demo.H - 2 * m, demo.INK, width=3 * u, radius=8 * u, alpha=0.6 * held)
        for dx in (0, 14 * u):
            cv.rect(demo.W - 2 * m - 22 * u + dx, 2 * m, 8 * u, 26 * u, demo.INK, radius=2 * u, alpha=0.8 * held)
    # a scene clock along the bottom: it stalls during the freeze while film time runs on
    span, x, y, h = demo.W * 0.7, demo.W * 0.15, demo.H * 0.88, demo.H * 0.01
    cv.rect(x, y, span, h, demo.LINE, radius=h / 2)
    cv.rect(x, y, span * min(freeze_frame(t, AT, HOLD) / FLIGHT, 1.0), h, demo.MUTED, radius=h / 2)


CAPABILITY = Capability(
    id='freeze-frame',
    name='Freeze Frame',
    family='principles',
    group='Time remapping',
    aliases=('time freeze', 'frame hold', 'still moment', 'frozen moment', 'still hold'),
    definition='The action stops dead on one instant and the picture stays put for a beat, '
               'then everything carries on from exactly where it stopped.',
    phrasings=('pause the action mid-move for a dramatic moment',
               'stop time right at the peak, then let it play on',
               'hold on that frame for a second before it continues'),
    related=('hold', 'moving-hold', 'timing', 'delay', 'scatter-time-playback', 'timecode-counter'),
    api=('videobuilder.capabilities.principles.freeze_frame.freeze_frame',),
    demo=lambda: demo.film(draw),
)
