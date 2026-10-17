"""The scene a look paints: a few shapes with roles, a couple of point
features, and the frame's size. See skill/make-a-video/reference/looks.md.

A video describes its picture once in this small vocabulary (a function of
film time if things move), and any look can repaint it: the look decides how
sky, water, land, buildings, figures and lights are drawn and how they move.
"""
import math
import random

import cairo

ROLES = ('sky', 'water', 'land', 'building', 'figure', 'light')


class Region:
    """One shape in the scene: a closed polygon (film pixels) with a role
    from ROLES. `name` is free for the video's own use (looks ignore it)."""
    __slots__ = ('role', 'points', 'name')

    def __init__(self, role, points, name=''):
        if role not in ROLES:
            raise ValueError(f'unknown role {role!r}: use one of {", ".join(ROLES)}')
        if len(points) < 3:
            raise ValueError('a region needs at least three points')
        self.role = role
        self.points = [(float(x), float(y)) for x, y in points]
        self.name = name

    @property
    def bbox(self):
        """(x, y, w, h) around the polygon."""
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)

    def __repr__(self):
        return f'Region({self.role!r}, {len(self.points)} points{", " + repr(self.name) if self.name else ""})'


def _box_points(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


class Scene:
    """What a look paints.

    - `w`, `h`: the area to paint, in film pixels (the whole frame, or a box
      the video translates to with `cv.layer(dx=, dy=)`).
    - `regions`: Regions, back to front. Anything a region doesn't cover is
      sky above `horizon` and water below it (all sky when `horizon` is None).
    - `horizon`: the y where sky meets open water, or None for no water.
    - `sun`: (x, y, r), the sun or moon, or None.
    - `beacon`: (x, y), a point light that throws turning beams (a lamp, a
      headlight, a screen's glow), or None.
    - `stars`: (x, y, phase) points; None scatters `star_count` seeded ones
      over the sky, clear of the sun.
    - `bpm`: the beat looks pulse on (Bauhaus, pop art).
    - `seed`: varies the seeded scatter (stars) between scenes.

    Build one per frame if anything moves: it is only a few lists, and the
    looks cache what they derive from it.
    """

    def __init__(self, w, h, regions=(), horizon=None, sun=None, beacon=None, stars=None, star_count=24,
                 bpm=120, seed=0):
        self.w, self.h = float(w), float(h)
        self.regions = tuple(regions)
        for r in self.regions:
            if not isinstance(r, Region):
                raise TypeError('regions must be looks.Region objects')
        self.horizon = None if horizon is None else float(horizon)
        self.sun = None if sun is None else tuple(float(v) for v in sun)
        self.beacon = None if beacon is None else tuple(float(v) for v in beacon)
        self.bpm = float(bpm)
        self.seed = seed
        self.stars = tuple(stars) if stars is not None else self._scatter_stars(star_count)

    # ---- sizes ----
    @property
    def u(self):
        """One unit: the scene's short side over 1080. Looks scale strokes,
        dabs and dots by it, so a look reads the same at any size."""
        return min(self.w, self.h) / 1080.0

    @property
    def sky_bottom(self):
        """Where the sky ends: the horizon, or the bottom of the frame."""
        return self.h if self.horizon is None else self.horizon

    def of(self, role):
        """The regions with `role`, in paint order."""
        return [r for r in self.regions if r.role == role]

    def sun_or_default(self):
        """The sun, or where one would sit (upper right) for looks whose
        signature move turns round it."""
        if self.sun:
            return self.sun
        return (self.w * 0.72, self.sky_bottom * 0.32, 80 * self.u)

    def _scatter_stars(self, n):
        rnd = random.Random(1009 + int(self.seed))
        sx, sy, sr = self.sun if self.sun else (-1e9, -1e9, 0)
        out = []
        for _ in range(n * 4):
            x, y = rnd.uniform(0.03, 0.97) * self.w, rnd.uniform(0.04, 0.92) * self.sky_bottom
            if math.hypot(x - sx, y - sy) > sr * 1.8:
                out.append((x, y, rnd.uniform(0, 2 * math.pi)))
            if len(out) == n:
                break
        return tuple(out)

    # ---- where things are ----
    def role_at(self, x, y):
        """The role painted at (x, y): the front-most region covering it, or
        sky/water by the horizon. Answered from a small raster of the
        regions, so it is cheap to ask thousands of times a frame."""
        mask = _mask(self)
        mx = min(mask.w - 1, max(0, int(x * mask.k)))
        my = min(mask.h - 1, max(0, int(y * mask.k)))
        idx = mask.data[my * mask.stride + mx]
        if idx:
            return self.regions[idx - 1].role
        return 'sky' if self.horizon is None or y < self.horizon else 'water'

    def open_water(self):
        """(x0, x1): the widest stretch of open water along a line halfway
        between the horizon and the bottom, or None with no water. Where a
        look puts its big wave."""
        if self.horizon is None:
            return None
        y = (self.horizon + self.h) / 2
        best, start = None, None
        steps = 64
        for i in range(steps + 1):
            x = self.w * i / steps
            wet = i < steps and self.role_at(x, y) == 'water'
            if wet and start is None:
                start = x
            elif not wet and start is not None:
                if best is None or x - start > best[1] - best[0]:
                    best = (start, x)
                start = None
        return best

    def ledge(self):
        """(x, y): the top outer corner of the land -- the vertex of the
        land regions furthest towards open water and up. Where the melt look
        drapes its clock. None without land."""
        land = [p for r in self.of('land') for p in r.points]
        if not land:
            return None
        water = self.open_water()
        towards = 1 if water is None or (water[0] + water[1]) / 2 >= self.w / 2 else -1
        inner = [p for p in land if 0 < p[0] < self.w]
        return max(inner or land, key=lambda p: towards * p[0] - 0.8 * p[1])


class _Mask:
    __slots__ = ('w', 'h', 'k', 'stride', 'data')


_MASKS = {}
_MASK_SCALE = 0.25


def _mask(scene):
    """The scene's regions rasterised at quarter size, one byte per pixel:
    0 for uncovered, i + 1 for scene.regions[i] (front-most wins). Cached
    on the geometry, so a still scene rasterises once."""
    key = (scene.w, scene.h, tuple((r.role, tuple(r.points)) for r in scene.regions))
    mask = _MASKS.get(key)
    if mask is not None:
        return mask
    k = _MASK_SCALE
    w, h = max(1, int(math.ceil(scene.w * k))), max(1, int(math.ceil(scene.h * k)))
    surf = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_NONE)
    ctx.set_operator(cairo.OPERATOR_SOURCE)
    ctx.scale(k, k)
    for i, r in enumerate(scene.regions[:254]):
        ctx.new_path()
        ctx.move_to(*r.points[0])
        for p in r.points[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgba(0, 0, 0, (i + 1) / 255)
        ctx.fill()
    surf.flush()
    mask = _Mask()
    mask.w, mask.h, mask.k, mask.stride = w, h, k, surf.get_stride()
    mask.data = bytes(surf.get_data())
    if len(_MASKS) > 16:
        _MASKS.clear()
    _MASKS[key] = mask
    return mask


def lighthouse(w, h, t=0.0):
    """A ready-made scene, and a worked example of the vocabulary: a
    lighthouse on a cliff, a moon, a boat bobbing on the sea. Laid out from
    `w` and `h`, so it fits any shape; `t` (seconds) bobs the boat. The look
    demos on the Capabilities page all paint this one."""
    u = min(w, h) / 1080.0
    wide = w / h
    horizon = h * (0.6 if wide < 1.3 else 0.62)
    cx = w * (0.26 if wide < 1.3 else 0.2)          # the cliff's top, left of centre
    top = horizon - h * 0.17
    cliff = [(0, top + 8 * u), (cx - 170 * u, top - 18 * u), (cx - 40 * u, top - 10 * u), (cx + 110 * u, top + 10 * u),
             (cx + 180 * u, top + 60 * u), (cx + 230 * u, horizon - 20 * u), (cx + 270 * u, horizon + 90 * u),
             (cx + 310 * u, h * 0.86), (cx + 270 * u, h + 10), (0, h + 10)]
    base = top - 4 * u
    k = min(u, (base - h * 0.07) / 430)        # the tower, lantern and roof fit under the top of the frame
    tw, th = 124 * k, 290 * k
    tower = [(cx - tw / 2, base), (cx + tw / 2, base), (cx + tw / 2 - 20 * k, base - th), (cx - tw / 2 + 20 * k, base - th)]
    gy = base - th - 14 * k
    gallery = _box_points(cx - 74 * k, gy, 148 * k, 16 * k)
    lantern = _box_points(cx - 36 * k, gy - 68 * k, 72 * k, 68 * k)
    roof = [(cx - 46 * k, gy - 66 * k), (cx + 46 * k, gy - 66 * k), (cx, gy - 122 * k)]
    bx = w * (0.74 if wide < 1.3 else 0.72)
    by = horizon + (h - horizon) * 0.42 + 10 * u * math.sin(2 * math.pi * t / 1.6)
    tilt = 0.06 * math.sin(2 * math.pi * t / 1.6 + 0.8)

    def tilted(pts):
        c, s = math.cos(tilt), math.sin(tilt)
        return [(bx + (x - bx) * c - (y - by) * s, by + (x - bx) * s + (y - by) * c) for x, y in pts]

    hull = tilted([(bx - 80 * u, by), (bx + 80 * u, by), (bx + 56 * u, by + 34 * u), (bx - 56 * u, by + 34 * u)])
    sail = tilted([(bx - 4 * u, by - 8 * u), (bx - 4 * u, by - 150 * u), (bx + 70 * u, by - 14 * u)])
    moon = (w * 0.73, horizon * 0.36, 86 * u)
    return Scene(w, h, [
        Region('land', cliff, 'cliff'),
        Region('building', tower, 'tower'),
        Region('building', gallery, 'gallery'),
        Region('light', lantern, 'lantern'),
        Region('building', roof, 'roof'),
        Region('figure', hull, 'hull'),
        Region('figure', sail, 'sail'),
    ], horizon=horizon, sun=moon, beacon=(cx, gy - 34 * k), seed=11)
