"""Static noise: the picture drowns in grey snow that re-rolls every frame,
like a television tuned to a dead channel, with a faint brighter band
rolling down through it."""
import math

import cairo
from PIL import Image

import videobuilder as vb

from ...looks.fx import image_surface, noise
from .. import _demo as demo
from ..schema import Capability


def static_noise(cv, amount=1.0, t=0.0, seed=0, grain=2.0, box=None, fps=30, roll=0.25):
    """Lay TV static over what `cv` already holds, at strength `amount`
    (0: none, 1: the picture fully replaced). The snow is fresh grey noise at
    `t` seconds, re-rolled `fps` times a second, in cells `grain` px square;
    `roll` is the strength of a soft brighter band that drifts down the frame
    (0 for none). `box` (x, y, w, h) limits it to a region, else the whole
    frame. The same `seed` and `t` give the same snow.

    In a film, draw the shot, then e.g. `static_noise(cv, amount=0.6, t=f.t)`
    for a weak signal, or ramp `amount` to 1 to lose the picture."""
    amount = vb.clamp01(amount)
    if amount <= 0:
        return
    x, y, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    k = cv.scale_factor() / max(0.5, grain)
    nw, nh = max(2, math.ceil(w * k)), max(2, math.ceil(h * k))
    step = math.floor(t * fps + 1e-9)
    im = noise(nw, nh, f'static:{seed}:{step}')
    if roll > 0:
        im = _roll(im, (t * 0.45 + seed * 0.37) % 1.0, roll)
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    c.translate(x, y)
    c.scale(w / nw, h / nh)
    c.set_source_surface(image_surface(im), 0, 0)
    c.get_source().set_filter(cairo.FILTER_NEAREST)
    c.paint_with_alpha(amount)
    c.restore()


def _roll(im, at, strength):
    """`im` with a soft horizontal band centred `at` (0 top, 1 bottom) lifted
    towards white, the hum bar of a poorly tuned set."""
    h = im.height
    col = bytes(round(255 * strength * math.exp(-(((r / h - at + 0.5) % 1.0 - 0.5) / 0.09) ** 2)) for r in range(h))
    mask = Image.frombytes('L', (1, h), col).resize(im.size, Image.NEAREST)  # wraps: rolls off the bottom, back in at the top
    return Image.composite(Image.new('L', im.size, 255), im, mask)


def _scene(cv):
    """The programme the static breaks into: a card on the demo background."""
    demo.card(cv, demo.W / 2, demo.H / 2, w=420, h=260, color=demo.TEAL)
    demo.word(cv, 'Channel 3', demo.W / 2, demo.H * 0.8, size=48, color=demo.MUTED)


def _draw(n, cv):
    t = n / demo.FPS
    _scene(cv)
    # The signal flickers, drops out to pure snow, holds, then comes back.
    lose, regain = demo.phase(n, 0.4, 1.0), demo.phase(n, 2.1, 2.6)
    flicker = 0.15 * (1 - lose) * (math.sin(t * 37) > 0.6) if t < 1.0 else 0.0
    static_noise(cv, amount=max(flicker, vb.ease_in_out_quart(lose) * (1 - vb.ease_in_out_quart(regain))), t=t)


CAPABILITY = Capability(
    id='static-noise',
    name='Static noise',
    family='vfx',
    group='Glitch',
    aliases=('TV snow', 'analog snow', 'white noise overlay', 'TV static', 'dead channel'),
    definition='The frame fills with flickering grey speckles that change every frame, like an old '
               'television picking up no signal.',
    phrasings=('make it look like the TV lost its signal',
               'cover the shot in fuzzy black-and-white static',
               'cut to snow like a dead channel'),
    related=('snowfall', 'analog-ghosting', 'fractal-brownian-motion', 'glitch-sound', 'domain-warping',
             'film-grain'),
    api=('videobuilder.capabilities.vfx.static_noise.static_noise', 'videobuilder.looks.fx.noise'),
    demo=lambda: demo.film(_draw),
)
