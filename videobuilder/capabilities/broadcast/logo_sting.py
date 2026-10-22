"""Logo sting: slanted colour bars whip across the frame, a white flash hits,
and the logo punches in from slightly too big with a jolt, then holds."""
import videobuilder as vb
from videobuilder import impact

from .. import _demo as demo
from ..schema import Capability


def _bar(cv, x, w, slant, color):
    """A full-height parallelogram whose top edge starts at `x`, leaning right by `slant`."""
    c = cv.ctx
    c.new_path()
    c.move_to(x + slant, 0)
    c.line_to(x + slant + w, 0)
    c.line_to(x + w, cv.height)
    c.line_to(x, cv.height)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill()


def logo_sting(cv, t, mark, centre=None, whip=0.45, colors=(demo.TEAL, demo.ACCENT, demo.INK), flash='#f4f4f2',
               punch=1.3, settle=0.55, fps=30, seed=0):
    """Frame of a logo sting `t` seconds after it starts. Bars in `colors`
    whip left to right across the frame over `whip` seconds; as the last one
    clears, a `flash` fills the frame and fades, and `mark(cv)` (the logo,
    drawn about `centre`, default the frame's middle) lands at `punch` times
    its size, easing to rest over `settle` seconds while the frame shakes.
    After that the mark simply holds. Draws over whatever is underneath, so
    call it after the background."""
    cx, cy = centre or (cv.width / 2, cv.height / 2)
    if t >= whip:
        k = vb.clamp01((t - whip) / settle)
        z = 1 + (punch - 1) * (1 - vb.ease_out_expo(k))
        dx, dy = impact.shake(round(t * fps), round(whip * fps), frames=round(settle * fps * 0.6), amount=18,
                              seed=seed)
        with cv.layer(dx=cx * (1 - z) + dx, dy=cy * (1 - z) + dy, scale=z):
            mark(cv)
        glow = 1 - vb.clamp01((t - whip) / 0.3)
        if glow > 0:
            cv.fill(flash, alpha=0.9 * glow * glow)
    # Each bar crosses from fully off-left to fully off-right, staggered and accelerating.
    slant = cv.height * 0.35
    widths = [cv.width * f for f in (0.22, 0.05, 0.12)]
    for i, (color, w) in enumerate(zip(colors, widths)):
        lag = 0.06 * i
        q = (t - lag) / (whip - lag) if whip > lag else 1.0
        if 0 < q < 1:
            q = vb.ease_in_expo(q) * 0.75 + q * 0.25
            x = -w - slant + (cv.width + w + slant) * q
            _bar(cv, x, w, slant, color)


def _mark(cv):
    """The demo's stand-in brand: a coral tile with a bold V, and a wordmark under it."""
    x, y = demo.W / 2, demo.H / 2 - 40
    cv.rect(x - 110, y - 110, 220, 220, demo.ACCENT, radius=36)
    demo.word(cv, 'V', x, y + 6, size=170, color=demo.INK, weight=900)
    demo.word(cv, 'NORTHWIND', x, y + 180, size=54, color=demo.INK, weight=800)


def draw(n, cv):
    t = n / demo.FPS - 0.3
    if t >= 0:
        logo_sting(cv, t, _mark, centre=(demo.W / 2, demo.H / 2 - 40))
    cv.mark('logo', demo.W / 2 - 110, demo.H / 2 - 150, 220, 220)


CAPABILITY = Capability(
    id='logo-sting',
    name='Logo sting',
    family='broadcast',
    group='Bumpers & idents',
    aliases=('stinger', 'logo stinger', 'brand sting'),
    definition='A quick, punchy burst of motion such as a whip of colour bars and a white flash that slams '
               'a logo into place and leaves it holding on screen.',
    phrasings=('a fast flashy intro that ends on our logo',
               'whip some colour across the screen, flash, and land the brand mark',
               'a short punchy logo hit for the start or end of the video'),
    related=('stinger', 'sonic-logo', 'logo-glitch-reveal', 'logo-mask-wipe-reveal', 'sine-wave-text',
             'impact-shake'),
    api=('videobuilder.capabilities.broadcast.logo_sting.logo_sting', 'videobuilder.impact.shake'),
    demo=lambda: demo.film(draw),
)
