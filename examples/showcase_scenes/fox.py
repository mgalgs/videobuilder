"""Puppet motion and pose swaps: a cut-out fox talks up Lumen, flapping its
mouth on the syllables, snaps to point at the logo on the beat, hops up
cheering and lands back in idle, breathing under every hold."""
from videobuilder import Puppet

from . import kit
from .kit import ASSETS, INK

POSES = ('idle', 'talk', 'blink', 'point', 'cheer')
FOX = Puppet({name: ASSETS / 'fox' / f'{name}.png' for name in POSES}, height=360)

FPB = kit.FPB
SYLLABLES = ((2, 6, 'Lumen'), (9, 13, 'plans'), (16, 20, 'my'), (23, 28, 'day!'))
POINT, CHEER, LAND = 2 * FPB, 3 * FPB, 4 * FPB
HOLDS = ([(0, 'idle')] + [h for a, z, _ in SYLLABLES for h in ((a, 'talk'), (z, 'idle'))]
         + [(POINT, 'point'), (CHEER, 'cheer'), (LAND, 'idle'), (LAND + 7, 'blink'), (LAND + 9, 'idle')])
POP = ((1.07, 0.93), (0.96, 1.05), (1.015, 0.985))
HOP = 60
SQUASH = (1.12, 0.88)
LAND_SPRING = kit.vb.damped(0.3, hz=2.6)


def _layout(st):
    """(feet x, ground y, scale, logo centre and radius)."""
    c = st.content
    if st.wide:
        return c.cx - 220, c.bottom - 30, 1.25, (c.cx + 190, c.bottom - 300, 90)
    return c.cx - 90, c.bottom - 120, 1.3, (c.cx + 220, c.bottom - 410, 80)


def fox(cv, s, st):
    cv.fill(kit.BG)
    n = s.f
    x, ground, scale, (lx, ly, lr) = _layout(st)
    pose, age = FOX.pose_at(n, HOLDS)
    sx, sy = FOX.breath(n, 60)
    if n - age in (POINT, CHEER) and age < len(POP):
        sx, sy = sx * POP[age][0], sy * POP[age][1]
    lift = 0.0
    if CHEER <= n < LAND:
        p = (n - CHEER) / (LAND - CHEER)
        lift = HOP * 4 * p * (1 - p)
    if n >= LAND:
        sp = kit.spring(n - LAND, 0, LAND_SPRING)
        sx *= SQUASH[0] + (1 - SQUASH[0]) * sp
        sy *= SQUASH[1] + (1 - SQUASH[1]) * sp

    cv.line(st.content.x, ground, st.content.right, ground, kit.LINE, width=2)
    FOX.draw(cv, pose, x, ground - lift * scale, sx=sx, sy=sy, scale=scale, mark='fox')

    if n < POINT:
        words = ' '.join(w for a, _, w in SYLLABLES if n >= a)
        if words:
            f = kit.font(kit.pick(st, 48, 44), 700)
            head = ground - FOX.height * scale
            if st.wide:   # beside the head, where the logo lands next
                kit.write(cv, 'speech', words, f, x + 150 * scale, head + 40, INK)
            else:
                top = head - 40 - kit.vb.text.line_height(f)
                kit.write(cv, 'speech', words, f, x - kit.vb.text.measure('Lumen plans my day!', f) / 2, top, INK)
    if n >= POINT:
        k = kit.spring(n, POINT, kit.BOUNCY)
        with kit.scaled(cv, lx, ly, k):
            kit.logo(cv, lx, ly, lr)


SCENES = {'fox': fox}
