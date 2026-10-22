"""Handheld Shake: the whole frame sways, bobs and rolls a little on smooth
noise, with a finer jitter on top, as if the camera were held in someone's
hands instead of locked on a tripod. Unlike `impact.shake` it never settles:
it is a steady, gentle unrest for the length of the shot."""
import math
from contextlib import contextmanager

from .. import _demo as demo
from ..principles.perlin_noise_drift import noise_drift
from ..schema import Technique


def handheld(t, seed=0, amount=10.0, roll=0.6, speed=0.9):
    """The camera's (dx, dy, angle) at time `t` seconds: a slow sway of up
    to `amount` px and `roll` degrees from smooth noise read at `speed`, plus
    a quicker tremor about a fifth as big. `angle` is in radians. The same
    `seed` gives the same take."""
    def channel(name, size):
        sway = noise_drift(t, f'{seed}:{name}', size, speed, octaves=2)
        tremor = noise_drift(t, f'{seed}:{name}:fast', size * 0.2, speed * 6, octaves=1)
        return sway + tremor
    return channel('x', amount), channel('y', amount * 0.7), math.radians(channel('r', roll))


@contextmanager
def handheld_camera(cv, t, seed=0, amount=10.0, roll=0.6, speed=0.9, overscan=None):
    """Draw the body through a handheld camera at time `t` seconds: the
    scene shifts and rolls about the frame's centre by `handheld(...)`, and
    is scaled up by `overscan` (by default just enough) so the frame's edges
    never show. Draw fixed overlays (titles, a viewfinder) after the block."""
    w, h = cv.width, cv.height
    dx, dy, a = handheld(t, seed, amount, roll, speed)
    if overscan is None:
        reach = 1.25 * (amount + math.radians(roll) * math.hypot(w, h) / 2)  # worst-case edge travel
        overscan = 1 + 2 * reach / min(w, h)
    c = cv.ctx
    c.save()
    c.translate(w / 2 + dx, h / 2 + dy)
    c.rotate(a)
    c.scale(overscan, overscan)
    c.translate(-w / 2, -h / 2)
    try:
        yield cv
    finally:
        c.restore()


def _scene(cv):
    """A tabletop: a back wall grid, a floor, a card on a stand, two dots."""
    W, H = demo.W, demo.H
    cv.fill(demo.BG)
    ground = H - 150
    for x in range(-40, W + 80, 80):
        cv.line(x, 0, x, ground, demo.LINE, width=1, alpha=0.6)
    for y in range(20, ground, 80):
        cv.line(-40, y, W + 40, y, demo.LINE, width=1, alpha=0.6)
    cv.rect(-40, ground, W + 80, H - ground + 40, '#000000', alpha=0.25)
    demo.floor(cv, ground)
    cv.rect(W / 2 - 90, ground - 70, 180, 70, demo.MUTED, radius=6)
    demo.card(cv, W / 2, ground - 170, w=280, h=170)
    demo.dot(cv, W / 2 - 300, ground - 34, 34, color=demo.TEAL)
    demo.dot(cv, W / 2 + 300, ground - 34, 34, color=demo.TEAL)


def _viewfinder(cv, n):
    """Fixed overlay: corner brackets, a centre cross and a blinking REC."""
    W, H, m, L = demo.W, demo.H, 36, 46
    for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        cv.line(x, y, x + sx * L, y, demo.INK, width=3, alpha=0.85)
        cv.line(x, y, x, y + sy * L, demo.INK, width=3, alpha=0.85)
    cx, cy = W / 2, H / 2
    cv.line(cx - 16, cy, cx + 16, cy, demo.INK, width=2, alpha=0.7)
    cv.line(cx, cy - 16, cx, cy + 16, demo.INK, width=2, alpha=0.7)
    if (n // 15) % 2 == 0:
        demo.dot(cv, m + 30, m + 34, 8, color='#e5484d')
    demo.word(cv, 'REC', m + 70, m + 34, size=22, weight=700)


def draw(n, cv):
    with handheld_camera(cv, 2.0 + n / demo.FPS, seed=7, amount=16, roll=1.2, speed=1.1):
        _scene(cv)
    _viewfinder(cv, n)
    cv.mark('scene', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='handheld-shake',
    name='Handheld shake',
    family='camera',
    group='Camera moves',
    aliases=('handheld wobble', 'documentary shake', 'handheld camera', 'shaky cam'),
    definition='The whole picture drifts, bobs and tilts by a few pixels in a restless, uneven way, '
               'so the shot feels filmed by someone holding the camera rather than from a fixed mount.',
    phrasings=('make it look like it was shot on a handheld camera',
               'add a little organic camera wobble so the shot feels alive',
               'give it that documentary, held-by-hand feel'),
    related=('shake', 'tape-wobble', 'jiggle', 'rolling-shutter-wobble', 'tilt-shift-miniature', 'hold'),
    api=('videobuilder.techniques.camera.handheld_shake.handheld_camera',
         'videobuilder.techniques.camera.handheld_shake.handheld',
         'videobuilder.techniques.principles.perlin_noise_drift.noise_drift'),
    demo=lambda: demo.film(draw),
)
