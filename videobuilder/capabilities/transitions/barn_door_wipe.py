"""Barn door wipe: a split opens at the centre line and its two edges travel
outward to the frame's sides, uncovering the incoming scene between them."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def barn_door_wipe(cv, a, b, p, vertical=True, ease=vb.ease_in_out_quart, edge=demo.ACCENT, edge_width=6):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` everywhere, then
    `b(cv)` inside a band centred on the frame that grows from nothing to
    full frame. `vertical`: the split is a vertical line and the doors open
    left and right; False opens them up and down. `ease` shapes the opening;
    `edge`, if not None, draws a bright line `edge_width` wide on each moving
    edge so the doors read clearly.

    In a film, call it while two shots are live in an overlap, e.g.
    `barn_door_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    e = ease(vb.clamp01(p))
    a(cv)
    if vertical:
        half = W / 2 * e
        box = (W / 2 - half, 0, 2 * half, H)
    else:
        half = H / 2 * e
        box = (0, H / 2 - half, W, 2 * half)
    if half <= 0:
        return
    with cv.clip(*box):
        b(cv)
    if edge is not None and e < 1:
        x, y, w, h = box
        if vertical:
            cv.rect(x - edge_width / 2, 0, edge_width, H, edge)
            cv.rect(x + w - edge_width / 2, 0, edge_width, H, edge)
        else:
            cv.rect(0, y - edge_width / 2, W, edge_width, edge)
            cv.rect(0, y + h - edge_width / 2, W, edge_width, edge)


CAPABILITY = Capability(
    id='barn-door-wipe',
    name='Barn door wipe',
    family='transitions',
    group='Wipes',
    aliases=('split wipe', 'door wipe', 'curtain wipe', 'curtain transition', 'split curtain text'),
    definition='A gap opens along the centre line of the old shot and its two edges sweep out to the sides '
               'of the frame, uncovering the new shot as it widens.',
    phrasings=('open the scene like a pair of doors',
               'split the picture down the centre and pull it apart to show the next shot',
               'a wipe that starts in the middle and spreads out to both sides'),
    related=('split-screen-transition', 'curtain-reveal', 'split-screen-comparison', 'paint-brush-wipe',
             'cut-out-paper-animation', 'wipe-reveal'),
    api=('videobuilder.capabilities.transitions.barn_door_wipe.barn_door_wipe',
         'videobuilder.capabilities.typography.curtain_reveal.draw_curtain'),
    demo=lambda: demo.two_scenes(barn_door_wipe, start=1.5, length=1.2),
)
