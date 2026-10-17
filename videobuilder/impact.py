"""Impact frames: the anime hit that punctuates a moment. A fast push-in, a
couple of held two-tone frames (the subject a flat silhouette on a white
ground, speed lines bursting out round it), a short shake that settles, and
speed lines that linger and fade.

    from videobuilder import impact
    HIT = impact.Hit(at=60)                     # the frame the fox lands
    def draw(n, cv):
        HIT.draw(cv, n, scene, fox_only, centre=(x, ground_y - 120))

`scene(cv)` draws the whole ordinary frame; `subject(cv)` draws only the
thing being hit (the fox, the number), for its silhouette. The building
blocks are here too: `speed_lines`, `silhouette`, `shake`.

One hit is one full-frame flash. Keep hits at least a second apart, never a
strobe: no more than two flashes in any one second.
"""
import math
import random

from .canvas import rgba
from .ease import ease_out_expo, interpolate


def speed_lines(cv, cx, cy, seed, inner, count=56, width=30, colour='#14151a', alpha=1.0):
    """Radial speed lines bursting out from (cx, cy): `count` thin wedges, each
    a point at about `inner` px from the centre (give the subject room)
    widening to up to `width` px past the frame's edge. Seeded: the same
    `seed` draws the same burst; pass the frame in the seed to vary it from
    one held frame to the next."""
    rnd = random.Random(seed)
    reach = math.hypot(cv.width, cv.height)
    c = cv.ctx
    c.new_path()
    for i in range(count):
        a = 2 * math.pi * (i + rnd.uniform(-0.35, 0.35)) / count
        r0 = inner * rnd.uniform(1.0, 1.6)
        half = width * rnd.uniform(0.25, 1.0) / 2 / reach      # the wedge's half-angle at the far end
        c.move_to(cx + r0 * math.cos(a), cy + r0 * math.sin(a))
        c.line_to(cx + reach * math.cos(a - half), cy + reach * math.sin(a - half))
        c.line_to(cx + reach * math.cos(a + half), cy + reach * math.sin(a + half))
        c.close_path()
    c.set_source_rgba(*rgba(colour, alpha))
    c.fill()


def silhouette(cv, draw, colour, alpha=1.0):
    """Whatever `draw(cv)` paints, as one flat `colour`: its shape kept, its
    colours and lines gone. Marks it makes are kept."""
    c = cv.ctx
    c.push_group()
    draw(cv)
    shape = c.pop_group()
    c.set_source_rgba(*rgba(colour, alpha))
    c.mask(shape)


def shake(n, at, frames=12, amount=14, seed=0):
    """(dx, dy) px to offset the frame at frame `n` for a shake starting at
    `at`: a sharp jolt, rattling side to side, settling to (0, 0) over
    `frames` frames. Seeded from the frame, so a frame always shakes the same
    way."""
    k = n - at
    if not 0 <= k < frames:
        return 0.0, 0.0
    rnd = random.Random(seed * 7919 + k)
    a = amount * (1 - k / frames) ** 2
    return a * (-1) ** k * rnd.uniform(0.6, 1.0), a * rnd.uniform(-0.6, 0.6)


class Hit:
    """An impact frame landing on frame `at`.

    `push` frames of fast push-in before it, to `zoom`; `hold` frames
    (1 to 3) of the two-tone impact itself, `ink` on `paper`; then the
    ordinary frame again, zooming back out while it shakes for `settle`
    frames, with the white flash fading over `flash` frames and the speed
    lines, in `paper`, over `linger`. `push`, `settle`, `flash` and `linger`
    may be 0 to leave that part out. `seed` picks the burst."""

    def __init__(self, at, push=6, hold=2, settle=14, flash=5, linger=20, zoom=1.15, shake=16, seed=0,
                 ink='#14151a', paper='#f4f4f2'):
        if not 1 <= hold <= 3:
            raise ValueError('an impact holds for 1 to 3 frames')
        if min(push, settle, flash, linger) < 0:
            raise ValueError('push, settle, flash and linger are frame counts: 0 or more')
        self.at, self.push, self.hold, self.settle, self.flash, self.linger = at, push, hold, settle, flash, linger
        self.zoom, self.shake, self.seed, self.ink, self.paper = zoom, shake, seed, ink, paper

    @property
    def span(self):
        """(first, end) frames the hit changes anything in."""
        return self.at - self.push, self.at + self.hold + max(self.settle, self.flash, self.linger)

    def held(self, n):
        """Whether frame `n` is one of the held two-tone frames."""
        return self.at <= n < self.at + self.hold

    def zoom_at(self, n):
        """The camera's zoom at frame `n`: 1 at rest, pushing in fast to the
        hit, a touch closer on the held frames, easing back out after."""
        back = self.at + self.hold
        if n < back:
            z = interpolate(n, [self.at - self.push, self.at], [1, self.zoom], ease=lambda p: p ** 3) \
                if self.push else self.zoom
            return z * (1.05 if self.held(n) else 1.0)
        if not self.settle:
            return 1.0
        return interpolate(n, [back, back + self.settle], [self.zoom, 1], ease=ease_out_expo)

    def offset_at(self, n):
        """The shake's (dx, dy) at frame `n`."""
        return shake(n, self.at + self.hold, self.settle, self.shake, self.seed)

    def draw(self, cv, n, scene, subject, centre=None):
        """Frame `n`: `scene(cv)` as usual outside the hit; through it, pushed
        in on `centre` (default the frame's middle) and shaken, or on the held
        frames, `subject(cv)` as an `ink` silhouette in a burst of `ink` speed
        lines on `paper`."""
        first, end = self.span
        if not first <= n < end:
            scene(cv)
            return
        cx, cy = centre or (cv.width / 2, cv.height / 2)
        z = self.zoom_at(n)
        dx, dy = self.offset_at(n)
        inner = 0.24 * min(cv.width, cv.height)
        with cv.layer(dx=cx * (1 - z) + dx, dy=cy * (1 - z) + dy, scale=z):
            if self.held(n):
                cv.fill(self.paper)
                speed_lines(cv, cx, cy, self.seed * 31 + n, inner, colour=self.ink)
                silhouette(cv, subject, self.ink)
                return
            scene(cv)
        k = n - self.at - self.hold
        if k < 0:
            return
        fade = 1 - k / self.linger if self.linger else 0
        if fade > 0:
            speed_lines(cv, cx, cy, self.seed * 31 + self.at, inner * (1 + 0.5 * (1 - fade)), colour=self.paper,
                        alpha=0.75 * fade * fade)
        if k < self.flash:
            cv.fill(self.paper, alpha=0.7 * (1 - k / self.flash) ** 2)
