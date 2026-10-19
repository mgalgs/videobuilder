"""The shared demo for the Type family: the same three lines in the same
three colours for every style, so the cards compare like for like (see
STYLE.md's note on the Type family).

    FILM = _type.film('split-flap')     # one style's 5 s demo, with its sound
    FILM = _type.relay_film()           # the family card: a few styles in turn

The square 720x720 format comes first (the clip the page plays); a tall and
a wide format follow for the preview, since every style lays itself out per
frame shape.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402

FPS = 30
LENGTH = 5.0           # enter, hold, exit: longer than STYLE.md's 2-4 s, as a type style needs all three
EACH = 3.0             # per style, in the family card's relay
LEAD = ('split-flap', 'rubber', 'rack-focus', 'editorial')
FORMATS = (_kit.FORMAT, vb.Format('9x16', 540, 960), vb.Format('16x9', 960, 540))

PROPS = vb.type.props(lines=['Words that', 'move the way', 'they mean it'], ink=_kit.INK, paper=_kit.BG,
                      accent='#ffb000', length=LENGTH, sound=True)


def film(name):
    """One style's demo: PROPS in `name`, with its sound where it has one."""
    return vb.type.film(name, PROPS, formats=FORMATS, fps=FPS)


def relay_film(names=LEAD):
    """The family card's demo: each of `names` in turn, EACH seconds apiece."""
    names = list(names)

    def draw(n, cv):
        vb.type.relay(cv, names, PROPS, n / FPS, each=EACH)

    frames = round(EACH * FPS) * len(names)
    return vb.Film(draw=draw, fps=FPS, frames=frames, formats=FORMATS, background=_kit.BG,
                   sounds=vb.type.relay_sounds(names, PROPS, each=EACH, fps=FPS),
                   keyframes=tuple(round((k + 0.6) * EACH * FPS) for k in range(len(names))))
