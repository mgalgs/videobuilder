"""De Jong attractor: one point is fed again and again through a pair of
sine/cosine equations; every landing spot is tallied on a grid, and the tally,
drawn as brightness, thickens into a lacy swirl of folded ribbons."""
import math

from PIL import Image, ImageOps

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def de_jong(a, b, c, d, x=0.1, y=0.1):
    """The endless orbit of the De Jong map from (x, y):
    x' = sin(a y) - cos(b x), y' = sin(c x) - cos(d y). Every point lies in
    [-2, 2] on both axes."""
    sin, cos = math.sin, math.cos
    while True:
        x, y = sin(a * y) - cos(b * x), sin(c * x) - cos(d * y)
        yield x, y


class DeJongField:
    """A density grid of `size` x `size` cells over [-2, 2]^2 that a De Jong
    orbit is poured into. `upto(k)` brings the tally to the first `k` points
    (cheaply, when frames come in order); `image(...)` tone-maps it to a
    `vb.Image` for `cv.image`. Build one per film and call both from `draw`."""

    def __init__(self, a, b, c, d, size=540, warmup=100):
        self.params, self.size, self.warmup = (a, b, c, d), size, warmup
        self._reset()

    def _reset(self):
        self.counts = [0] * (self.size * self.size)
        self.k = 0
        self._orbit = de_jong(*self.params)
        for _ in range(self.warmup):  # let the orbit settle onto the attractor
            next(self._orbit)

    def upto(self, k):
        """Tally the first `k` points of the orbit (restarting if `k` went back).
        Returns the last few new points as (x, y) pairs, newest last."""
        if k < self.k:
            self._reset()
        counts, s, orbit, recent = self.counts, self.size, self._orbit, []
        for _ in range(k - self.k):
            x, y = next(orbit)
            counts[min(s - 1, int((2 - y) * s / 4)) * s + min(s - 1, int((x + 2) * s / 4))] += 1
            recent.append((x, y))
        self.k = k
        return recent[-400:]

    def image(self, full, low=demo.BG, mid='#5b6cff', high=demo.INK):
        """The tally as an image: each cell's brightness is log(1 + hits) over
        log(1 + `full`), so a field of `full` hits per busy cell reaches full
        brightness; colours run `low` -> `mid` -> `high`."""
        norm = 255 / math.log1p(full)
        lut = bytes(min(255, round(math.log1p(n) * norm)) for n in range(int(full) + 1))
        top = len(lut) - 1
        lum = Image.frombytes('L', (self.size, self.size), bytes(lut[min(top, n)] for n in self.counts))
        return vb.Image.from_pil(ImageOps.colorize(lum, low, high, mid=mid))


POINTS = 700_000
SIZE = 500
_field = DeJongField(-2.0, -2.0, -1.2, 2.0, size=SIZE)


def draw(n, cv):
    p = demo.phase(n, 0.15, 2.7)
    k = round(POINTS * p * p)  # slow trickle first, then a flood as the lace fills in
    recent = _field.upto(k)
    x0, y0 = (demo.W - SIZE) / 2, (demo.H - SIZE) / 2
    cv.image(_field.image(full=60), x0, y0, SIZE, SIZE)
    for x, y in recent[-120:]:  # the newest landings, so the orbit itself shows hopping about
        demo.dot(cv, x0 + (x + 2) * SIZE / 4, y0 + (2 - y) * SIZE / 4, 1.6, color=demo.INK, alpha=0.8)
    cv.mark('attractor', x0, y0, SIZE, SIZE)


CAPABILITY = Capability(
    id='de-jong-attractor',
    name='De Jong attractor',
    family='particles',
    group='Strange attractors',
    aliases=('de Jong map', 'Peter de Jong attractor'),
    definition='A single point hops endlessly under a simple trig formula, and the places it lands, '
               'piled up as glowing density, build a delicate tangle of curling ribbons.',
    phrasings=('a glowing generative swirl that fills in out of millions of dots',
               'a strange attractor that builds up like silk threads',
               'chaotic math art that slowly paints a lacy pattern'),
    related=('sierpinski-gasket', 'swirl', 'globe-spin', 'gravity-well-attraction', 'particle-morph',
             'circle-pop'),
    api=('videobuilder.capabilities.particles.de_jong_attractor.DeJongField',
         'videobuilder.capabilities.particles.de_jong_attractor.de_jong'),
    demo=lambda: demo.film(draw),
)
