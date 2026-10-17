"""Walk in place, a parallax scene and an impact frame: the fox walks two
steps a beat through hills and trees that slide past at their own speeds,
hops on beat 4 and lands on beat 5 with an impact -- a push-in, a held
silhouette in a burst of speed lines, a shake that settles."""
import math
import random

from videobuilder import Puppet, impact, parallax, paths

from . import kit
from .kit import ASSETS, BG

FOX = Puppet({name: ASSETS / 'fox' / f'{name}.png' for name in ('idle', 'cheer', 'surprised')}, height=300)

FPB = kit.FPB
STEP = FPB / 2           # two steps a beat
SPEED = 12               # px a frame the ground passes
HOP_AT, LAND = 3 * FPB, 4 * FPB
HOP = 110
HIT = impact.Hit(at=LAND, seed=5, ink=BG)
LAND_SPRING = kit.vb.damped(0.3, hz=2.4)

HILLS, TREES, GROUND, GRASS, NEAR = '#3a4458', '#24403f', '#1c2622', '#2f4a3c', '#08090c'


def _layers(w, h, ground):
    ridge = parallax.ridge(720, 90, seed=2)
    hills = [(-1, ridge[0][1])] + ridge + [(721, ridge[-1][1]), (721, 400), (-1, 400)]
    rnd = random.Random(7)
    trees = [(tx + rnd.uniform(-20, 20), rnd.uniform(100, 150)) for tx in (50, 170, 260)]
    blades = [(30 + i * 9 + rnd.uniform(-3, 3), rnd.uniform(70, 170), rnd.uniform(-0.35, 0.35)) for i in range(16)]

    def hill(cv, x):
        paths.draw(cv, [(x + px, ground - 200 + py) for px, py in hills], HILLS, fill=True)

    def tree(cv, x):
        for tx, th in trees:
            cx = x + tx
            cv.rect(cx - 5, ground - th * 0.35, 10, th * 0.35, TREES)
            paths.draw(cv, [(cx, ground - th), (cx + th * 0.24, ground - th * 0.28),
                            (cx - th * 0.24, ground - th * 0.28)], TREES, fill=True)

    def soil(cv, x):
        cv.rect(x - 1, ground, 242, h - ground, GROUND)
        cv.rect(x - 1, ground, 242, 6, GRASS)
        for sx, sy, sw in ((20, 30, 70), (150, 30, 40), (90, 70, 56)):
            cv.rect(x + sx, ground + sy, sw, 8, GRASS, radius=4)

    def near(cv, x):
        for bx, bh, tilt in blades:
            paths.draw(cv, [(x + bx - 7, h + 2), (x + bx + 7, h + 2), (x + bx + tilt * bh, h - bh)], NEAR, fill=True)

    return (parallax.Layer(0.2, 720, hill), parallax.Layer(0.5, 360, tree), parallax.Layer(1.0, 240, soil),
            parallax.Layer(1.7, 1100, near))


def _ground(st):
    return st.content.bottom - kit.pick(st, 60, 260)


_LAYERS = {}


def layers(cv, st):
    key = cv.format.name
    if key not in _LAYERS:
        _LAYERS[key] = _layers(cv.width, cv.height, _ground(st))
    return _LAYERS[key]


def camera(n):
    """Steady while it walks and through the hop; stopped dead on the landing."""
    return SPEED * min(n, LAND)


def body(n):
    """(pose, sx, sy, lean, lift)."""
    if n < HOP_AT:
        g = FOX.walk(n, STEP, rise=0.05, squash=0.06, lean=0.05)
        return 'idle', g.sx, g.sy, g.lean, g.lift
    if n < LAND:
        p = (n - HOP_AT) / (LAND - HOP_AT)
        return 'cheer', 0.96, 1.06, 0.03, HOP * 4 * p * (1 - p)
    sp = kit.spring(n - LAND, 0, LAND_SPRING)
    return 'surprised', 1.16 - 0.16 * sp, 0.84 + 0.16 * sp, 0.0, 0.0


def walk(cv, s, st):
    n = s.f
    ground = _ground(st)
    x = st.content.cx
    ls = layers(cv, st)
    pose, sx, sy, lean, lift = body(n)

    def fox(c):
        FOX.draw(c, pose, x, ground - lift, sx=-sx, sy=sy, lean=lean, scale=kit.pick(st, 1.0, 1.3), mark='fox')

    def scene(c):
        c.fill(BG)
        parallax.draw(c, ls[:3], camera(n))
        k = 1 - 0.4 * lift / HOP
        ctx = c.ctx
        ctx.save()
        ctx.translate(x, ground + 3)
        ctx.scale(110 * k, 10 * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.set_source_rgba(0, 0, 0, 0.45 * k)
        ctx.fill()
        ctx.restore()
        fox(c)
        parallax.draw(c, ls[3:], camera(n))

    HIT.draw(cv, n, scene, fox, centre=(x, ground - 140))


SCENES = {'walk': walk}
