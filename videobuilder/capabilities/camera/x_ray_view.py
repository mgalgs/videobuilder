"""X-ray View: an object's opaque outer surface turns glassy, so the parts
built inside it show through while the shell stays as a faint outline."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def x_ray_view(cv, shell, inside, p, ghost=0.15, rim=None, rim_width=2, box=None, radius=0):
    """Draw the x-ray at progress `p` (0 -> 1): `inside(cv)` underneath,
    then `shell(cv)` over it, fading from solid to `ghost` opacity so the
    interior shows through. With `rim` (a colour) and `box` (x, y, w, h), an
    outline of the shell's edge fades in as the fill fades out, so the
    object keeps its shape once it is see-through. The inside is skipped
    while the shell is fully opaque.

    In a film, drive `p` from a phase, e.g.
    `x_ray_view(cv, draw_case, draw_parts, vb.ease_in_out_quart(f.p), rim=INK, box=case_box)`."""
    p = vb.clamp01(p)
    if p > 0:
        inside(cv)
    with cv.layer(opacity=1 - (1 - ghost) * p):
        shell(cv)
    if rim is not None and box is not None and p > 0:
        cv.outline(*box, rim, width=rim_width, radius=radius, alpha=p)


BOX = (demo.W / 2 - 300, demo.H / 2 - 150, 600, 300)
RADIUS = 120
GLOW = '#f2c14e'


def case(cv):
    """The demo object's solid casing: a rounded pill with a soft top highlight."""
    x, y, w, h = BOX
    cv.shadow(x, y, w, h, radius=RADIUS, dy=14, blur=34, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, demo.ACCENT, radius=RADIUS)
    cv.rect(x + 40, y + 18, w - 80, h * 0.28, demo.INK, radius=RADIUS * 0.4, alpha=0.16)
    cv.rect(x + 40, y + h * 0.78, w - 80, h * 0.14, '#000000', radius=RADIUS * 0.3, alpha=0.18)


def parts(cv):
    """What's inside the casing: a chip, traces, a battery and a coil."""
    x, y, w, h = BOX
    cx, cy = x + w / 2, y + h / 2
    for dy in (-60, 0, 60):  # traces from the chip out to both ends
        cv.line(x + 70, cy + dy, x + w - 70, cy + dy, GLOW, width=3, alpha=0.75)
        demo.dot(cv, x + 70, cy + dy, r=8, color=GLOW)
        demo.dot(cv, x + w - 70, cy + dy, r=8, color=GLOW)
    cv.rect(cx - 60, cy - 60, 120, 120, '#2b2410', radius=10)  # the chip
    cv.outline(cx - 60, cy - 60, 120, 120, GLOW, width=4, radius=10)
    for i in range(5):
        t = cx - 44 + i * 22
        cv.line(t, cy - 74, t, cy - 60, GLOW, width=4)
        cv.line(t, cy + 60, t, cy + 74, GLOW, width=4)
    cv.outline(x + 120, cy - 38, 80, 76, demo.TEAL, width=4, radius=8)  # battery cell
    cv.rect(x + 200, cy - 14, 8, 28, demo.TEAL)
    for i in range(6):  # coil
        cv.arc(x + w - 190 + i * 14, cy, 30, 0, 6.283, demo.TEAL, width=3, alpha=0.85)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.6, 2.2))
    x_ray_view(cv, case, parts, p, rim=demo.INK, box=BOX, radius=RADIUS)
    cv.mark('object', *BOX)


CAPABILITY = Capability(
    id='x-ray-view',
    name='X-ray view',
    family='camera',
    group='3D motion',
    aliases=('x-ray reveal', 'internal reveal', 'see-through reveal'),
    definition='An object\'s solid outside fades to a glassy ghost of itself, '
               'letting the parts built inside it show through.',
    phrasings=('make the case go see-through so we can see what\'s inside',
               'x-ray the product to show its internals',
               'fade the shell away to reveal the inner workings'),
    related=('x-ray', 'uncover', 'zoom-out-reveal', 'extrusion-depth-reveal', 'depth-slicing',
             'text-mask-reveal'),
    api=('videobuilder.capabilities.camera.x_ray_view.x_ray_view',),
    demo=lambda: demo.film(draw),
)
