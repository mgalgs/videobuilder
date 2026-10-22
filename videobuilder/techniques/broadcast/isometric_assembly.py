"""Isometric Assembly: the parts of an object drawn in isometric projection
start scattered around it, then fly in one after another and lock into place
until the finished object stands assembled and holds."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..shapes.isometric_bar_rise import iso, shade
from ...compendium import kit
from ...looks import kit as looks


def draw_iso_block(cv, ox, oy, x0, y0, x1, y1, z0, z1, color, tile=100.0, outline=None):
    """One isometric block spanning grid cells x0..x1 by y0..y1 and floating
    from `z0` to `z1` pixels above the floor (grid origin at screen (ox, oy),
    as `isometric_bar_rise.iso`): a lit top face in `color` and the two
    visible sides, left (+y) and right (+x), in darker shades."""
    P = lambda a, b, z: iso(ox, oy, a, b, z, tile)  # noqa: E731
    line = dict(outline=outline, width=1.5) if outline else {}
    if z1 > z0:
        looks.fill(cv, [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], shade(color, 0.28), **line)
        looks.fill(cv, [P(x1, y1, z0), P(x1, y0, z0), P(x1, y0, z1), P(x1, y1, z1)], shade(color, 0.48), **line)
    looks.fill(cv, [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], color, **line)


def isometric_assembly(cv, parts, p, ox, oy, tile=100.0, stagger=0.7, ease=vb.ease_out_quint, fade=False,
                       outline=None):
    """Draw `parts` assembling at progress `p` (0 -> 1). Each part is
    `((x0, y0, x1, y1, z0, z1), color, (dx, dy, dz))`: its block in place
    (grid cells and pixel heights, as `draw_iso_block`) and where it starts
    from, offset `dx`, `dy` cells and `dz` pixels. At p = 0 every part sits at
    its offset (the exploded view; `fade=True` hides them instead and fades
    each in as it moves); each then eases home over the last `1 - stagger`
    of the run, starts spread across the first `stagger` in list order. Parts
    are painted in list order too, so list them as built: bottom to top, back
    to front. Returns each part's own progress."""
    n = max(1, len(parts) - 1)
    out = []
    for i, ((x0, y0, x1, y1, z0, z1), color, (dx, dy, dz)) in enumerate(parts):
        start = stagger * i / n
        q = vb.clamp01((p - start) / (1 - stagger)) if stagger < 1 else float(p >= start)
        k = 1 - ease(q)  # 1 at the offset, 0 home
        with cv.layer(opacity=vb.clamp01(q * 3) if fade else 1.0):
            draw_iso_block(cv, ox, oy, x0 + dx * k, y0 + dy * k, x1 + dx * k, y1 + dy * k, z0 + dz * k,
                           z1 + dz * k, color, tile, outline)
        out.append(q)
    return out


TILE = 46
SLATE, ROOF = '#4a5263', demo.ACCENT
WALL, WING = demo.TEAL, kit.mix(demo.TEAL, '#ffffff', 0.25)
GLASS = '#cfe9f2'
# A little house, in build order (which is also back-to-front paint order).
PARTS = (
    ((0, 0, 4.2, 3.2, 0, 9), SLATE, (0, 0, -30)),                 # ground plate rises from below
    ((0.4, 0.4, 2.6, 2.5, 9, 69), WALL, (-1.6, 0, 80)),           # main block drops in from up-left
    ((2.6, 0.9, 3.7, 2.5, 9, 45), WING, (2.0, 0, 15)),            # wing slides in from the right
    ((0.75, 2.5, 1.25, 2.56, 31, 56), GLASS, (0, 1.6, 0)),        # windows fly in at the front face
    ((1.7, 2.5, 2.2, 2.56, 31, 56), GLASS, (0, 1.6, 0)),
    ((2.95, 2.5, 3.35, 2.56, 9, 36), SLATE, (0, 1.6, 0)),         # door
    ((2.6, 0.8, 3.85, 2.65, 45, 52), ROOF, (1.0, 0, 85)),         # wing roof
    ((0.25, 0.25, 2.75, 2.65, 69, 79), ROOF, (0, 0, 100)),        # main roof drops last
    ((0.8, 0.8, 1.25, 1.25, 79, 103), SLATE, (0, 0, 130)),        # chimney caps it
)


def draw(n, cv):
    ox, oy = demo.W / 2 - 0.5 * TILE * 0.866, demo.H / 2 - 10
    # shadow of the plate's footprint, there from the start so the build has a place to land
    shadow = [iso(ox, oy + 7, x, y, 0, TILE) for x, y in ((0, 0), (4.2, 0), (4.2, 3.2), (0, 3.2))]
    cv.shape_shadow(shadow, dy=5, blur=16, color=(0, 0, 0, 0.5))
    isometric_assembly(cv, PARTS, demo.phase(n, 0.35, 2.4), ox, oy, TILE, outline=demo.BG)
    pts = [iso(ox, oy, x, y, z, TILE) for x in (0, 4.2) for y in (0, 3.2) for z in (0, 103)]
    xs, ys = zip(*pts)
    cv.mark('house', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='isometric-assembly',
    name='Isometric assembly',
    family='broadcast',
    group='Explainers',
    aliases=('exploded assembly', 'parts assemble', 'isometric scene assembly', 'isometric build-up',
             'isometric room build', 'isometric diorama assemble'),
    definition='The pieces of an object drawn at a flat isometric angle drift in from around it, one after '
               'another, and snap together until the whole thing stands complete.',
    phrasings=('build the 3D-looking object up piece by piece as its parts fly together',
               'start with the parts spread out and have them come together into the finished model',
               'an isometric illustration that puts itself together, layer on layer'),
    related=('isometric-rotation', 'exploded-view', 'isometric-bar-rise', 'shape-assemble-from-fragments',
             'voxel-build', 'isometric-view'),
    api=('videobuilder.techniques.broadcast.isometric_assembly.isometric_assembly',
         'videobuilder.techniques.broadcast.isometric_assembly.draw_iso_block',
         'videobuilder.techniques.shapes.isometric_bar_rise.iso'),
    demo=lambda: demo.film(draw),
)
