"""The shared demo for the Looks family: one scene (looks.lighthouse, a
lighthouse on a cliff, a moon, a boat on the sea), painted by one look per
demo so they compare well, with a plaque naming the look. See STYLE.md's
note on the Looks family.

    FILM = _looks.film('pop-art')       # one look's 3 s demo
    FILM = _looks.relay_film()          # the family card: every look in turn
    FILM = _looks.filter_film('pop-art', 'dashboard')   # a filter look on a held screenshot

A filter look's demo restyles a picture instead: the committed screenshot
(assets/dashboard.png, a made-up analytics app) or the fox photo (the fox
cut-out standing in a meadow), held still for the whole demo so all the
motion on screen is the filter's own.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, looks, text  # noqa: E402

FPS = 30
FRAMES = 90          # 3.0 s: long enough for the one-off moves (the wave, the blueprint) to land
HOLD = 24            # frames per look in the family relay
PLAQUE = '#0e1016'   # the plaque reads on every look: dark, nearly opaque
LINE_INK = '#c8ccd6'

TITLE_F = _kit.font(30, 700)
LINE_F = _kit.font(21, 500)
SFX_F = _kit.font(40, 900)


def _opts(name):
    """The extras a look takes in this demo: the pop-art burst's word, the blueprint's labels."""
    return {'pop-art': {'sfx': 'POP!', 'font': SFX_F}, 'blueprint': {'font': _kit.font(20, 600)}}.get(name, {})


def plaque(cv, title, line, pad=44):
    """The look's name and what moves, on a dark plaque at the bottom left, marked."""
    s = _kit.safe(cv, pad)
    tl = text.wrap(title, TITLE_F, s.w - 220)
    ll = text.wrap(line, LINE_F, s.w - 220)
    tw, th = text.block_size(tl, TITLE_F)
    lw, lh = text.block_size(ll, LINE_F)
    w, h = max(tw, lw) + 44, th + 8 + lh + 36
    box = Box(s.x, s.bottom - h, w, h)
    cv.rect(*box, (14, 16, 22, 0.86), radius=16)
    text.draw(cv, tl, TITLE_F, box.x + 22, box.y + 18, _kit.INK)
    text.draw(cv, ll, LINE_F, box.x + 22, box.y + 18 + th + 8, LINE_INK)
    cv.mark('plaque', *box)


def film(name):
    """One look's demo: the lighthouse painted in `name`, its plaque on top."""
    look = looks.get(name)

    def draw(n, cv):
        t = n / FPS
        looks.paint(cv, look.name, looks.lighthouse(cv.width, cv.height, t), t, **_opts(look.name))
        plaque(cv, look.title, look.line)

    return vb.Film(draw=draw, fps=FPS, frames=FRAMES, formats=(_kit.FORMAT,), background=_kit.BG,
                   keyframes=(FRAMES // 2, FRAMES - 1))


def relay_film(names=None):
    """The family card's demo: the lighthouse wiping from each look to the next."""
    names = list(names or looks.names()[:8])
    hold = HOLD / FPS

    def draw(n, cv):
        t = n / FPS
        name = looks.relay(cv, looks.lighthouse(cv.width, cv.height, t), t, names, hold=hold, wipe=0.3,
                           opts={k: _opts(k) for k in names})
        i = names.index(name)
        plaque(cv, looks.get(name).title, f'{len(names)} looks · {i + 1} of {len(names)}')

    return vb.Film(draw=draw, fps=FPS, frames=HOLD * len(names), formats=(_kit.FORMAT,), background=_kit.BG,
                   keyframes=tuple(k * HOLD + HOLD // 2 for k in range(len(names))))


DASHBOARD = vb.Image.load(str(_kit.ASSETS / 'dashboard.png'))
FOX = vb.Image.load(str(_kit.ASSETS / 'fox' / 'idle.png'))


def fox_photo(cv):
    """The fox standing in a meadow under a summer sky: the demos' "photo"."""
    w, h = cv.width, cv.height
    for i in range(24):                                     # the sky, deepening upwards
        p = i / 23
        cv.rect(0, h * 0.62 * i / 24, w, h * 0.62 / 24 + 1, tuple(round(a + (b - a) * p) for a, b in
                                                                   zip((92, 150, 220), (196, 226, 246))))
    cv.rect(w * 0.70, h * 0.10, w * 0.14, w * 0.14, '#fff4c8', radius=w * 0.07)
    for k, (y, col) in enumerate(((0.56, '#7aa860'), (0.62, '#5a9a48'), (0.74, '#4a8a3a'))):
        pts = [(x * w / 32, h * y + h * 0.03 * math.sin(x / 32 * 2 * math.pi * (1 + k) + k * 2)) for x in range(33)]
        vb.paths.draw(cv, pts + [(w, h), (0, h)], col, closed=True, fill=True)
    s = min(w, h) * 0.7
    cv.image(FOX, w * 0.64 - s / 2, h - s * 0.98, s, s)


def picture(cv, name):
    """Draws the demo picture `name` ('dashboard' or 'fox') to fill the frame."""
    if name == 'fox':
        fox_photo(cv)
    else:
        cv.view(DASHBOARD, (0, 0, cv.width, cv.height), center=(DASHBOARD.w * 0.55, DASHBOARD.h * 0.47),
                scale=max(cv.width, cv.height) / (DASHBOARD.h * 0.9))


def filter_film(name, subject):
    """A filter look's demo: the picture `subject`, held still, restyled by
    the filter `name`, its plaque on top (outside the filter, so it reads)."""
    flt = looks.get_filter(name)

    def draw(n, cv):
        t = n / FPS
        with looks.filter(cv, flt.name, t):
            picture(cv, subject)
        plaque(cv, flt.title, flt.line)

    return vb.Film(draw=draw, fps=FPS, frames=FRAMES, formats=(_kit.FORMAT,), background=_kit.BG,
                   keyframes=(FRAMES // 2, FRAMES - 1))
