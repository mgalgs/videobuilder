"""Logo 3D Spin Reveal: a flat logo turns about its vertical axis in
perspective, its thickness showing as it passes edge-on, and slows to rest
facing the camera."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def spin_angle(p, turns=1.25, ease=lambda t: 1 - (1 - t) ** 3):
    """The spin's angle in degrees at progress `p` (0 -> 1): `turns` full
    turns unwinding to 0 (face-on). The default 1.25 starts edge-on, so the
    logo appears out of nothing; a whole number starts face-on. `ease`
    shapes the slow-down (default: cubic ease-out)."""
    return 360 * turns * (1 - ease(vb.clamp01(p)))


def _shade(color, k):
    r, g, b, a = rgba(color)
    return (round(r * 255 * k), round(g * 255 * k), round(b * 255 * k), a)


def _path(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for x, y in pts[1:]:
        ctx.line_to(x, y)
    ctx.close_path()


def logo_spin(cv, outline, cx, cy, angle, color, decal=(), decal_color='#ffffff', back_color=None,
              depth=36, distance=1600, alpha=1.0):
    """Draw a flat logo turned `angle` degrees about its vertical axis, in
    perspective, centred at (cx, cy). `outline` is the logo's silhouette as
    (x, y) points about its centre, in px; it is extruded `depth` px thick so
    the edge shows as it turns. `decal` is a list of point lists (letters,
    a mark) drawn in `decal_color` on the front face only; the back face is
    plain `back_color` (default: `color` darkened). Faces dim as they turn
    away, so the spin reads as lit. `distance` is the camera distance:
    smaller exaggerates the perspective. Pair with `spin_angle` for the
    reveal: `logo_spin(cv, ..., spin_angle(p), ...)`."""
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)

    def project(x, y, z):  # rotate about the y axis, then perspective onto the z = 0 plane
        xr, zr = x * ca + z * sa, -x * sa + z * ca
        f = distance / (distance + zr)
        return (cx + xr * f, cy + y * f), zr

    half = depth / 2
    front = [project(x, y, -half) for x, y in outline]
    back = [project(x, y, half) for x, y in outline]
    sides = []
    n = len(outline)
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = (y1 - y0) / ln, -(x1 - x0) / ln       # outward normal for a clockwise-on-screen outline
        k = 0.25 + 0.25 * abs(nx * sa) + 0.1 * max(0.0, -ny)  # brighter as it faces the camera, lit from above
        quad = [front[i][0], front[(i + 1) % n][0], back[(i + 1) % n][0], back[i][0]]
        z = (front[i][1] + front[(i + 1) % n][1] + back[i][1] + back[(i + 1) % n][1]) / 4
        sides.append((z, quad, k))

    ctx = cv.ctx
    facing = ca >= 0  # the front face (at -z) points at the camera
    near = front if facing else back
    light = 0.35 + 0.65 * abs(ca)
    with cv.layer(opacity=alpha):
        for z, quad, k in sorted(sides, key=lambda s: -s[0]):
            _path(ctx, quad)
            ctx.set_source_rgba(*rgba(_shade(color, k)))
            ctx.fill()
        _path(ctx, [p for p, _ in near])
        ctx.set_source_rgba(*rgba(_shade(color if facing else (back_color or _shade(color, 0.6)), light)))
        ctx.fill()
        if facing:
            for shape in decal:
                _path(ctx, [project(x, y, -half - 0.5)[0] for x, y in shape])
                ctx.set_source_rgba(*rgba(_shade(decal_color, light)))
                ctx.fill()
    xs = [p[0] for p, _ in near]
    ys = [p[1] for p, _ in near]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _badge(r=190, sides=6):
    """A hexagonal badge, clockwise on screen, flat side up."""
    return [(r * math.cos(math.pi / 6 + i * 2 * math.pi / sides - math.pi / 2),
             r * math.sin(math.pi / 6 + i * 2 * math.pi / sides - math.pi / 2)) for i in range(sides)]


# A bold chevron mark for the badge's face.
MARK = [[(-96, -78), (-46, -78), (0, 30), (46, -78), (96, -78), (26, 92), (-26, 92)]]


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.6)
    box = logo_spin(cv, _badge(), demo.W / 2, demo.H / 2, spin_angle(p), demo.ACCENT, decal=MARK,
                    decal_color=demo.INK, depth=44, alpha=vb.clamp01(p * 12))
    cv.mark('logo', *box)


CAPABILITY = Capability(
    id='logo-3d-spin-reveal',
    name='Logo 3D spin reveal',
    family='shapes',
    group='Logo animation',
    aliases=('flip logo reveal', 'card spin logo', 'Y-axis logo flip'),
    definition='A logo swings round on its upright axis in perspective, its thin edge flashing past, '
               'and slows until it comes to rest facing straight out.',
    phrasings=('spin the logo in like a coin turning and let it settle facing us',
               'the logo flips around in 3D and lands front-on',
               'reveal the badge with a perspective turn that slows to a stop'),
    related=('character-3d-flip', 'flip', 'word-flip-in', 'tile-flip', 'line-draw-logo-reveal', 'spin'),
    api=('videobuilder.capabilities.shapes.logo_3d_spin_reveal.logo_spin',
         'videobuilder.capabilities.shapes.logo_3d_spin_reveal.spin_angle'),
    demo=lambda: demo.film(draw),
)
