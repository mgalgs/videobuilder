"""Shake: videobuilder already has it as `impact.shake`, a seeded (dx, dy)
offset that jolts hard and settles to nothing, so this entry only names it
and demos it: a heavy block slams onto the floor and the whole view rattles."""
from videobuilder import impact

from .. import _demo as demo
from ..schema import Capability

LAND = round(1.0 * demo.FPS)  # the frame the block hits the floor


def draw(n, cv):
    ground, size = demo.H - 140, 200
    p = demo.phase(n, 0.55, LAND / demo.FPS)
    y = -size + (ground - size / 2 + size) * p ** 2  # falling, faster and faster
    dx, dy = impact.shake(n, LAND, frames=22, amount=40, seed=3)
    with cv.layer(dx=dx, dy=dy):
        demo.floor(cv, ground)
        demo.dot(cv, demo.W / 2 - 340, ground - 30, 30, color=demo.TEAL)
        demo.dot(cv, demo.W / 2 + 340, ground - 30, 30, color=demo.TEAL)
        demo.card(cv, demo.W / 2, y, w=size * 1.4, h=size)


CAPABILITY = Capability(
    id='shake',
    name='Shake',
    family='principles',
    group='Physics',
    aliases=('screen shake', 'camera shake', 'trauma shake', 'impact shake', 'hit shake text', 'kick jolt',
             'text jolt'),
    definition='The view or an object jolts about in small random jumps that die away quickly, '
               'selling the force of a hit.',
    phrasings=('make the screen shake when it lands',
               'rattle everything with a jolt on the hit',
               'give it a little camera shake on impact'),
    related=('handheld-shake', 'impact-shake', 'error-shake', 'smash-cut', 'accumulation-motion-blur', 'punch-in'),
    api=('videobuilder.impact.shake',),
    demo=lambda: demo.film(draw),
)
