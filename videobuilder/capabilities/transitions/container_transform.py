"""Container transform: a card on the outgoing scene grows, corners
straightening, until it is the whole frame, and the incoming scene fades up
inside it as it grows."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

CARD = (demo.W * 0.5 - 150, demo.H * 0.62 - 70, 300, 140)   # the demo's tappable card, (x, y, w, h)


def _lerp(a, b, t):
    return a + (b - a) * t


def container_transform(cv, a, b, p, box=CARD, color=demo.ACCENT, radius=18, face=None,
                        ease=vb.ease_in_out_quart, scrim=0.45):
    """Draw the transform at progress `p` (0 -> 1): `a(cv)` underneath, dimmed
    by up to `scrim`, and over it a `color` container growing from `box`
    (x, y, w, h, with corner `radius`) to the full frame along `ease`. `face`,
    if given, is `face(cv, x, y, w, h, alpha)` drawing the card's own content
    into the container; it fades out over the first third. `b(cv)` is drawn
    inside the container, scaled to its width, and fades in over the middle
    of the move, so at `p = 1` the frame is exactly `b`.

    `box` should match the card as `a` draws it, so the hand-off is seamless.
    In a film, call it while both shots are live in an overlap, e.g.
    `container_transform(cv, lambda c: list_view(c), lambda c: detail(c), f / overlap_frames, box=tapped_card)`."""
    W, H = cv.width, cv.height
    t = ease(vb.clamp01(p))
    x0, y0, w0, h0 = box
    x, y, w, h = _lerp(x0, 0, t), _lerp(y0, 0, t), _lerp(w0, W, t), _lerp(h0, H, t)
    r = radius * (1 - t)
    a(cv)
    cv.fill('#000000', alpha=scrim * t)
    cv.shadow(x, y, w, h, radius=r, dy=14 * (1 - t), blur=40 * (1 - t) + 1, color=(0, 0, 0, 0.5 * (1 - t)))
    with cv.clip(x, y, w, h, r):
        cv.rect(x, y, w, h, color)
        if face is not None:
            fade = vb.clamp01(1 - p / 0.3)
            if fade > 0:
                face(cv, x, y, w, h, fade)
        s = w / W
        show = vb.clamp01((p - 0.3) / 0.5)
        if show > 0:
            with cv.layer(opacity=show, dx=x, dy=y + (h - H * s) / 2, scale=s):
                b(cv)


def _face(cv, x, y, w, h, alpha):
    """The demo card's content: one word, centred in the container."""
    demo.word(cv, 'Open', x + w / 2, y + h / 2, size=44, color=demo.INK, alpha=alpha)


def _list(cv):
    """The demo's outgoing view: a heading and the card that will open."""
    cv.fill(demo.BG)
    demo.word(cv, 'Inbox', demo.W / 2, demo.H * 0.3, size=88)
    x, y, w, h = CARD
    cv.shadow(x, y, w, h, radius=18, dy=14, blur=40, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, demo.ACCENT, radius=18)
    _face(cv, x, y, w, h, 1.0)


CAPABILITY = Capability(
    id='container-transform',
    name='Container transform',
    family='transitions',
    group='Interface and Views',
    aliases=('expand to sheet', 'material container transform', 'card expand'),
    definition='A small card or button stretches out to fill the whole screen, its corners squaring off, '
               'while the next view fades in inside it.',
    phrasings=('tap the card and have it open up into the full page',
               'make the button grow until it becomes the next screen',
               'expand this tile into the detail view'),
    related=('accordion-height-expand', 'scroll-linked-clip-reveal', 'corner-wipe', 'box-wipe',
             'title-card-reveal', 'modal-scale-fade-enter'),
    api=('videobuilder.capabilities.transitions.container_transform.container_transform',),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: container_transform(cv, a, b, p, face=_face),
                                 start=0.8, length=1.2, a=_list),
)
