"""Oner: the whole piece is one unbroken camera move -- the camera travels
from subject to subject through a world bigger than the frame and never
cuts away. `oner_camera` gives the camera along a route of stops; `oner`
draws a world through it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _catmull(p0, p1, p2, p3, u):
    u2, u3 = u * u, u * u * u
    return 0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (3 * p1 - p0 - 3 * p2 + p3) * u3)


def oner_camera(progress, stops, ease=None):
    """The camera `(x, y, zoom)` at `progress` (0 -> 1) along `stops`, a list of
    `(x, y, zoom)` world positions the take passes through. The route is a
    smooth spline through every stop, so the camera glides past each one
    without stopping or jumping; `ease` (default a gentle in-out) shapes the
    pace of the whole take, not each leg."""
    if len(stops) < 2:
        raise ValueError('a oner needs at least two stops')
    ease = ease or vb.bezier(0.45, 0, 0.55, 1)
    s = ease(vb.clamp01(progress)) * (len(stops) - 1)
    k = min(int(s), len(stops) - 2)
    u = s - k
    pts = [stops[max(k - 1, 0)], stops[k], stops[k + 1], stops[min(k + 2, len(stops) - 1)]]
    return tuple(_catmull(*(p[i] for p in pts), u) for i in range(3))


def oner(cv, world, progress, stops, ease=None):
    """Draw `world(cv)` (in world coordinates) through the oner camera at
    `progress`: the camera's point sits at the frame centre at its zoom.
    Returns the camera `(x, y, zoom)`. In a film, call it every frame with
    `progress = n / (frames - 1)` and draw any on-screen overlay after it."""
    cam = oner_camera(progress, stops, ease)
    x, y, z = cam
    with cv.layer(dx=cv.width / 2 - x * z, dy=cv.height / 2 - y * z, scale=z):
        world(cv)
    return cam


# ---- demo: one take through three subjects, a running take clock on top ----

STOPS = ((640, 380, 1.0), (1260, 760, 1.2), (1900, 420, 1.05), (2560, 780, 1.25))
WORLD_W, WORLD_H = 3200, 1160


def _world(cv):
    cv.rect(0, 0, WORLD_W, WORLD_H, '#151a22')
    for gx in range(0, WORLD_W + 1, 150):
        cv.line(gx, 0, gx, WORLD_H, demo.LINE, width=2, alpha=0.5)
    for gy in range(0, WORLD_H + 1, 150):
        cv.line(0, gy, WORLD_W, gy, demo.LINE, width=2, alpha=0.5)
    route = [oner_camera(i / 120, STOPS, ease=vb.linear)[:2] for i in range(121)]
    vb.paths.draw(cv, route, demo.MUTED, width=4, alpha=0.6)
    demo.card(cv, *STOPS[0][:2], w=340, h=210)
    x, y = STOPS[1][:2]
    for i, c in enumerate((demo.ACCENT, demo.TEAL, demo.INK)):
        demo.dot(cv, x - 110 + 110 * i, y, r=44, color=c)
    demo.card(cv, *STOPS[2][:2], w=300, h=190, color=demo.TEAL)
    demo.word(cv, 'one take', *STOPS[3][:2], size=110)


def _hud(cv, n):
    f = demo.mono(30, 600)
    on = (n // 15) % 2 == 0
    demo.dot(cv, 60, 56, r=12, color='#e5484d', alpha=1.0 if on else 0.35)
    secs = n / demo.FPS
    vb.text.draw(cv, [f'REC  TAKE 1  00:00:{int(secs):02d}:{n % demo.FPS:02d}'], f, 86, 38, demo.INK)
    # A minimap: the whole route, and where the one camera is on it now.
    mx, my, mw = demo.W - 300, demo.H - 140, 260
    k = mw / WORLD_W
    cv.rect(mx, my, mw, WORLD_H * k, '#000000', radius=6, alpha=0.55)
    route = [(mx + px * k, my + py * k) for px, py in
             (oner_camera(i / 60, STOPS, ease=vb.linear)[:2] for i in range(61))]
    vb.paths.draw(cv, route, demo.MUTED, width=2)
    x, y, z = oner_camera(n / (demo.SECONDS * demo.FPS - 1), STOPS)
    vw, vh = demo.W / z * k, demo.H / z * k
    cv.outline(mx + x * k - vw / 2, my + y * k - vh / 2, vw, vh, demo.ACCENT, width=2)


def draw(n, cv):
    oner(cv, _world, n / (demo.SECONDS * demo.FPS - 1), STOPS)
    _hud(cv, n)


TECHNIQUE = Technique(
    id='oner',
    name='Oner',
    family='camera',
    group='Camera moves',
    aliases=('one-take shot', 'continuous take', 'long take'),
    definition='The camera carries the viewer from one subject to the next in a single unbroken move, '
               'so the whole sequence plays without a single cut.',
    phrasings=('do it all in one shot with no cuts',
               'let the camera glide from thing to thing without cutting',
               'film the whole sequence as a single continuous take'),
    related=('multiples', 'match-cut', 'zoom-through', 'hard-cut', 'cut-on-action', 'jump-cut'),
    api=('videobuilder.techniques.camera.oner.oner',
         'videobuilder.techniques.camera.oner.oner_camera'),
    demo=lambda: demo.film(draw),
)
