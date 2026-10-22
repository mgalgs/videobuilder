"""3D Word Cube: one word on each side face of a cube seen in perspective; the
cube turns a quarter at a time, carrying one word away round the edge as the
next swings in to face the camera."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _face(word, side, font, color, ink, k):
    """A square `side` x `side` face texture at pixel scale `k`: `color` with
    `word` centred on it."""
    face = vb.Canvas(side, side, background=color, scale=k)
    w, h = vb.text.block_size([word], font)
    vb.text.draw(face, [word], font, (side - w) / 2, (side - h) / 2, ink)
    return face.surface


def draw_word_cube(cv, words, cx, cy, size, turn, font=None, colors=('#2b2f3a',), ink='#f4f4f2',
                   lid_color='#3b404c', tilt=0.32, yaw=0.0, distance=3.2, shading=0.55, strips=40):
    """Draw a cube of edge `size` centred on (cx, cy), one of `words` on each
    of its four side faces (cycling if there are more than four, so any list
    works), turned about its vertical axis to `turn`: 0 shows `words[0]` square
    to the camera, 1 shows `words[1]`, and 0.5 sits on the edge between them.
    Turning forward carries the front word off to the left. `colors` cycle
    across the words' faces; `ink` is the word colour, `lid_color` the top's.
    `tilt` (radians) looks down onto the lid; `yaw` (radians, under a quarter
    turn) keeps the cube that far from square at rest, negative showing the
    next face; `distance` is the camera distance in edges (smaller is a
    stronger perspective); faces turned away from the light are darkened by
    up to `shading`. Each face is mapped onto its projected shape in
    `strips` thin affine slices, so the words foreshorten with the face.
    Returns the Box the cube covers on screen."""
    font = font or demo.font(round(size * 0.2), 800)
    h = size / 2
    cam = distance * size
    angle = yaw - turn * math.pi / 2
    ct, st = math.cos(tilt), math.sin(tilt)

    def project(x, y, z):
        # about the vertical axis, then tilted toward the camera, then a perspective divide
        x, z = x * math.cos(angle) + z * math.sin(angle), -x * math.sin(angle) + z * math.cos(angle)
        y, z = y * ct + z * st, -y * st + z * ct
        f = cam / (cam - z)
        return cx + x * f, cy + y * f

    def facing(pts):  # screen-space winding: clockwise (y down) faces the camera
        return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) > 0

    def poly(pts, color):
        c = cv.ctx
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
        c.set_source_rgba(*color)
        c.fill()

    k = max(1.0, cv.scale_factor())
    current = round(turn)
    seen = []
    for i in range(4):
        # face i's outward normal points along a; its texture runs left to right along t
        a = i * math.pi / 2
        nx, nz = math.sin(a), math.cos(a)
        tx, tz = math.cos(a), -math.sin(a)
        point = lambda u, y: project(h * nx + u * tx, y, h * nz + u * tz)  # noqa: E731
        quad = [point(-h, -h), point(h, -h), point(h, h), point(-h, h)]
        if not facing(quad):
            continue
        seen += quad
        # the word on face i is whichever of the cycle the nearest turn puts there
        n = current + (i - current) % 4
        if (i - current) % 4 == 3:
            n -= 4
        word, color = words[n % len(words)], colors[n % len(colors)]
        poly(quad, vb.rgba(color))
        tex = _face(word, size, font, color, ink, k)
        for s in range(strips):
            u0, u1 = -h + size * s / strips, -h + size * (s + 1) / strips
            (ax, ay), (bx, by), (dx, dy) = point(u0, -h), point(u1, -h), point(u0, h)
            e1x, e1y = (bx - ax) / (size / strips * k), (by - ay) / (size / strips * k)
            e2x, e2y = (dx - ax) / (size * k), (dy - ay) / (size * k)
            x0 = (u0 + h) * k
            c = cv.ctx
            c.save()
            c.transform(cairo.Matrix(e1x, e1y, e2x, e2y, ax - e1x * x0, ay - e1y * x0))
            c.rectangle(x0 - 0.5, 0, size / strips * k + 1, size * k)
            c.clip()
            c.set_source_surface(tex, 0, 0)
            c.paint()
            c.restore()
        # light from the front: faces turned away darken
        lit = vb.clamp01(-nx * math.sin(angle) + nz * math.cos(angle))
        poly(quad, (0, 0, 0, shading * (1 - lit)))
    lid = [project(-h, -h, -h), project(h, -h, -h), project(h, -h, h), project(-h, -h, h)]
    if facing(lid):
        seen += lid
        poly(lid, vb.rgba(lid_color))
    xs, ys = [p[0] for p in seen], [p[1] for p in seen]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def cube_turn(t, hold=0.5, move=0.6, ease=vb.ease_in_out_quart):
    """The `turn` for `draw_word_cube` at `t` seconds when each word holds
    `hold` seconds and each quarter turn takes `move`, eased by `ease`."""
    step = hold + move
    n, r = divmod(max(0.0, t), step)
    return n + ease(vb.clamp01((r - hold) / move))


WORDS = ('MOTION', 'DEPTH', 'SPACE', 'FORM')
COLORS = ('#2b2f3a', demo.ACCENT, demo.TEAL, '#3a3550')


def draw(n, cv):
    turn = cube_turn(n / demo.FPS, hold=0.3, move=0.6)
    box = draw_word_cube(cv, WORDS, demo.W / 2, demo.H / 2 + 20, 250, turn, colors=COLORS, yaw=-0.3)
    cv.mark('cube', *box)


CAPABILITY = Capability(
    id='three-d-word-cube',
    name='3D word cube',
    family='typography',
    group='Depth and 3D',
    aliases=('text cube rotation', 'word carousel 3D', 'rotating word cube'),
    definition='Words sit on the sides of a solid cube that turns in perspective, '
               'each quarter turn bringing the next word round to face the viewer.',
    phrasings=('put each word on a side of a spinning cube',
               'the cube rotates to show the next word',
               'swap the words by turning a 3D box between them'),
    related=('word-flip-in', 'cube-rotate', 'word-carousel-rotate', 'tesseract-rotation', 'globe-spin',
             'beveled-3d-text'),
    api=('videobuilder.capabilities.typography.three_d_word_cube.draw_word_cube',
         'videobuilder.capabilities.typography.three_d_word_cube.cube_turn'),
    demo=lambda: demo.film(draw),
)
