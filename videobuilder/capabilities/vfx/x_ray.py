"""X-ray: the picture turned into a radiograph -- brightness inverted so the
light surroundings go near-black, soft tissue a dim cool grey and anything
dense (drawn dark) glows pale blue-white, with a faint bloom around it.

`radiograph(im)` treats a PIL image; `x_ray(cv, ...)` is the canvas form, a
context manager like `looks.filter`: everything drawn inside the block (and
what was already there) comes out as an X-ray, in the whole frame or only
in `box` -- a scanner window sliding over the subject, say. Draw the dense
insides (bones, wiring, a key in a pocket) only inside the block, in a dark
ink, so they show up only where the X-ray is."""
import math

from PIL import Image, ImageChops, ImageFilter, ImageOps

from .. import _demo as demo
from ..schema import Capability
from ...ease import ease_in_out_quart
from ...looks.fx import Filter, apply

FILM_DARK = (4, 9, 18)        # where nothing absorbs: the empty film
FILM_MID = (62, 98, 132)      # soft tissue
FILM_LIGHT = (232, 244, 255)  # bone


def radiograph(im, amount=1.0, glow=0.45, u=1.0):
    """`im` (PIL RGB) as an X-ray: luma inverted, pushed down so the
    background sinks to black, tinted cold blue, with a bloom of `glow`
    around the bright parts. `amount` blends from the original (0) to the
    full look (1); `u` scales the bloom (the frame's short side over 1080)."""
    inv = ImageOps.invert(im.convert('L'))
    inv = inv.point(lambda v: int(255 * (v / 255) ** 1.6))
    if glow:
        bloom = inv.filter(ImageFilter.GaussianBlur(max(1.0, 14 * u))).point(lambda v: int(v * glow))
        inv = ImageChops.add(inv, bloom)
    out = ImageOps.colorize(inv, FILM_DARK, FILM_LIGHT, mid=FILM_MID)
    return out if amount >= 1 else Image.blend(im.convert('RGB'), out, max(0.0, amount))


def _treat(im, t, age, u, amount=1.0, glow=0.45):
    return radiograph(im, amount, glow, u)


XRAY = Filter('x-ray', 'X-ray', 'inverted, cold-blue radiograph; dense parts glow', _treat)


def x_ray(cv, box=None, amount=1.0, glow=0.45):
    """A context manager: what is drawn on `cv` inside the block, over what
    was there, turns into a radiograph (`radiograph`) when the block ends --
    only within `box` (x, y, w, h) when given. `amount` fades the look in."""
    return apply(cv, XRAY, 0.0, box=box, opts={'amount': amount, 'glow': glow})


# ---- the demo: a scanner window slides across a hand, showing its bones ----

PAPER = '#e4e0d6'
SKIN = '#c9967a'
BONE = '#141414'
CX, CY = demo.W / 2, demo.H / 2 + 45
SIZE = 0.82                   # the hand is drawn about the frame's centre at this scale
# each digit: angle (degrees from straight up), knuckle offset from (CX, CY), bone lengths from the knuckle out
DIGITS = ((-58, (-150, 60), (95, 70, 55)),
          (-12, (-95, -110), (80, 55, 45)),
          (-3, (-30, -125), (90, 60, 48)),
          (6, (35, -120), (85, 58, 46)),
          (16, (95, -100), (65, 45, 40)))


def _capsule(cv, x0, y0, x1, y1, width, color):
    cv.line(x0, y0, x1, y1, color, width=width)
    demo.dot(cv, x0, y0, width / 2, color)
    demo.dot(cv, x1, y1, width / 2, color)


def _digit_points(angle, base, lengths):
    a = math.radians(angle)
    dx, dy = math.sin(a), -math.cos(a)
    x, y = CX + base[0], CY + base[1]
    pts = [(x, y)]
    for n in lengths:
        x, y = x + dx * n, y + dy * n
        pts.append((x, y))
    return pts


def _hand(cv):
    cv.rect(CX - 160, CY - 140, 300, 300, SKIN, radius=110)          # palm
    cv.rect(CX - 105, CY + 120, 190, 240, SKIN, radius=40)           # wrist
    for angle, base, lengths in DIGITS:
        pts = _digit_points(angle, base, lengths)
        _capsule(cv, *pts[0], *pts[-1], 66, SKIN)


def _bones(cv):
    for i, (angle, base, lengths) in enumerate(DIGITS):
        pts = _digit_points(angle, base, lengths)
        tip = pts[-1]                                                # stop short of the fingertip
        pts[-1] = (tip[0] + (pts[-2][0] - tip[0]) * 0.3, tip[1] + (pts[-2][1] - tip[1]) * 0.3)
        pts.insert(0, (CX - 60 + i * 30, CY + 150))                  # the metacarpal runs back to the wrist
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            gap = 9                                                  # joints show as gaps
            d = math.hypot(x1 - x0, y1 - y0)
            ux, uy = (x1 - x0) / d, (y1 - y0) / d
            _capsule(cv, x0 + ux * gap, y0 + uy * gap, x1 - ux * gap, y1 - uy * gap, 20, BONE)
    for k in range(6):                                               # carpals
        demo.dot(cv, CX - 62 + (k % 3) * 46, CY + 175 + (k // 3) * 42, 19, BONE)
    _capsule(cv, CX - 55, CY + 260, CX - 55, CY + 380, 30, BONE)     # radius and ulna
    _capsule(cv, CX + 35, CY + 260, CX + 35, CY + 380, 26, BONE)


def _sized(cv, draw):
    c = cv.ctx
    c.save()
    c.translate(demo.W / 2, demo.H / 2)
    c.scale(SIZE, SIZE)
    c.translate(-demo.W / 2, -demo.H / 2)
    draw(cv)
    c.restore()


def _draw(n, cv):
    cv.fill(PAPER)
    _sized(cv, _hand)
    w = 520
    enter = ease_in_out_quart(demo.phase(n, 0.2, 1.1))           # slide in, hold over the hand, slide out
    leave = ease_in_out_quart(demo.phase(n, 2.0, 2.9))
    x = -w + (demo.W / 2 + w / 2) * enter + (demo.W / 2 + w / 2) * leave
    with x_ray(cv, box=(x, 0, w, demo.H)):
        _sized(cv, _bones)
    for edge in (x, x + w):                                          # the scanner's bright edges
        cv.rect(edge - 3, 0, 6, demo.H, '#bfe3ff', alpha=0.9)
    demo.word(cv, 'X-RAY', x + w / 2, 56, size=40, color='#bfe3ff', font=demo.mono(40))


CAPABILITY = Capability(
    id='x-ray',
    name='X-ray',
    family='vfx',
    group='Thermal & sensor',
    aliases=('X-ray inversion', 'radiograph look', 'skeletal view'),
    definition='The image turns into a dark-blue radiograph where the surroundings go black, flesh fades to '
               'a dim glow and the bones or dense parts inside shine pale white.',
    phrasings=('show the bones through the hand like an x-ray',
               'make it look like a medical scan',
               'a scanner window that sees through things as it slides past'),
    related=('x-ray-view', 'crt-scanlines', 'god-rays', 'photographic-negative', 'mandelbulb-raymarch',
             'solarization'),
    api=('videobuilder.capabilities.vfx.x_ray.x_ray', 'videobuilder.capabilities.vfx.x_ray.radiograph'),
    demo=lambda: demo.film(_draw),
)
