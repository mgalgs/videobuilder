"""Additive Dissolve: the two scenes are added together as light rather than
mixed, so through the middle of the change both are at full strength at once
and everything bright piles up into a glow before the outgoing scene drains away."""
import cairo

from .. import _demo as demo
from ..schema import Capability


def additive_dissolve(cv, a, b, p, overlap=1.0):
    """Draw the dissolve at progress `p` (0 -> 1): `a(cv)` and `b(cv)` summed
    with cairo's ADD operator over black. `b` ramps up while `a` ramps down;
    `overlap` (0 -> 1) is how much of the run both sit near full strength
    together: 1 brings `b` fully in by the midpoint before `a` starts to
    leave (the brightest blowout), 0 is a plain crossfade with no glow.

    In a film, call it while two shots are live in an overlap, e.g.
    `additive_dissolve(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    k = 1 + max(0.0, min(1.0, overlap))
    wa, wb = min(1.0, k * (1 - p)), min(1.0, k * p)
    c = cv.ctx
    cv.fill('#000000')
    for draw, w in ((a, wa), (b, wb)):
        if w <= 0:
            continue
        c.save()
        c.push_group()
        draw(cv)
        c.pop_group_to_source()
        c.set_operator(cairo.OPERATOR_ADD)
        c.paint_with_alpha(w)
        c.restore()


def _scene_b(cv):
    """A dark incoming scene, so the light the two scenes add up to reads."""
    cv.fill(demo.BG)
    demo.dot(cv, demo.W / 2, demo.H / 2, r=300, color=demo.TEAL, alpha=0.35)
    demo.card(cv, demo.W / 2, demo.H / 2, w=420, h=260, color=demo.TEAL)
    demo._label(cv, 'B')


CAPABILITY = Capability(
    id='additive-dissolve',
    name='Additive dissolve',
    family='transitions',
    group='Dissolves',
    aliases=('additive mix', 'light dissolve', 'add dissolve'),
    definition='One scene gives way to the next by stacking their light, so the picture '
               'flares brighter in the middle where both are showing before settling on the new shot.',
    phrasings=('a dissolve that glows and blows out a bit halfway through',
               'blend the two shots so the bright parts add up and flare',
               'crossfade like light being added, not a flat mix'),
    related=('screen-blend', 'multiply-blend', 'difference-blend', 'pixelate-transition', 'noise-dissolve',
             'unsharp-mask'),
    api=('videobuilder.capabilities.transitions.additive_dissolve.additive_dissolve',),
    # Centred on 2.1 s, so the gallery's poster frame (70% in) lands on the flare.
    demo=lambda: demo.two_scenes(additive_dissolve, b=_scene_b, start=1.4, length=1.4),
)
