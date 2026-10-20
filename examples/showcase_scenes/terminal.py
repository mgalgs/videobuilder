"""Lumen's release, run by an agent in a terminal: its thinking in italics,
commands typed at a prompt, the output printed whole, the window scrolling
up as lines arrive (`vb.TerminalLog`)."""
import videobuilder as vb
from videobuilder import Box

from . import kit
from .kit import BG, CARD, FPS, INK, MUTED, TEAL, pick

AMBER = '#d9b76a'
SESSION = [('out', 'lumen 0.9.4 on main, 212 tests'),
           ('think', 'Ship it once the build is green.', 0.2),
           ('cmd', 'make release', 0.15),
           ('out', 'tests ............ 212 passed', 0.1),
           ('out', 'build lumen-1.0.0.ipa', 0.1),
           ('out', 'uploaded to the App Store', 0.1)]


def kinds(size):
    return {'think': vb.terminal.Kind(kit.mono(size, 380, style='italic'), MUTED),
            'cmd': vb.terminal.Kind(kit.mono(size, 620), INK, prefix='$ ', prefix_color=TEAL, typed=True,
                                    per_char=0.04),
            'out': vb.terminal.Kind(kit.mono(size, 430), AMBER)}


EVENTS = vb.terminal.paced(SESSION, kinds(28), start=0.15, gap=0.1)
LOGS = {True: vb.TerminalLog(EVENTS, kinds(28), gap=0.25), False: vb.TerminalLog(EVENTS, kinds(30), gap=0.25)}


def window(st):
    """Four lines and a bit high, so the release scrolls."""
    c = st.content
    lh = 1.3 * pick(st, 28, 30)
    w, h = pick(st, c.w * 0.72, c.w), lh * 4.6 + 56
    return Box(c.cx - w / 2, c.cy - h / 2, w, h)


def terminal(cv, s, st):
    cv.fill(BG)
    box = window(st)
    p = kit.spring(s.f, -4)
    with kit.scaled(cv, box.cx, box.cy, 0.96 + 0.04 * min(1.0, p)):
        cv.shadow(*box, radius=20, dy=14, blur=36, color=(0, 0, 0, 0.5))
        cv.rect(*box, CARD, radius=20)
        LOGS[st.wide].draw(cv, s.f / FPS, box.pad(28, 32))
    cv.mark('terminal', *box)


SCENES = {'terminal': terminal}
