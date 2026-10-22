"""Typing sounds: a key click on the frame every letter of typed-on text
appears, a heavier thock on each space, in a human, uneven cadence. The
cadence is the type styles' own keystroke schedule
(`vb.type.typewriter.schedule`); the clicks come from `vb.sfx`'s keys, a few
takes taken in turn and each a touch louder or softer so the run never
sounds like one sample on repeat."""
import math
import random

import videobuilder as vb
from videobuilder.type.typewriter import schedule

from .. import _demo as demo
from ..schema import Capability

KEYS = ('fit/key/medium', 'fit/key/lubed', 'fit/key/thock')
SPACE = 'fit/key.space/thock_space'
STANDINS = ('key', 'click', 'tick')   # roles to fall back on in a pack without keyboard keys


def pick(ids, roles=STANDINS):
    """The ones of `ids` the sound-effects pack has; if none, the first
    sound of the first of `roles` it has; else ()."""
    have = []
    for i in ids:
        try:
            vb.sfx.get(i)
        except ValueError:
            continue
        have.append(i)
    if have:
        return tuple(have)
    known = vb.sfx.roles()
    for role in roles:
        if role in known:
            return (vb.sfx.find(role)[0].id,)
    return ()


def keystrokes(text, at=0, per_char=0.09, seed=0, fps=30):
    """The film frame each character of `text` appears on, typing from frame
    `at` at about `per_char` seconds a key: a little uneven, a longer reach
    after a space or a comma. The same `seed` gives the same rhythm."""
    times, _ = schedule(text, f'typing-sounds:{seed}', per_char)
    return tuple(at + math.ceil(t * fps - 1e-9) for t in times)


def typing_sounds(text, frames, fps=30, keys=KEYS, space=SPACE, gain_db=-8.0, vary_db=3.0, seed=0):
    """`vb.sfx` sounds for `text` typed on: one key click per character, its
    onset on `frames[i]` (from `keystrokes`), `space` under each space,
    nothing for line breaks. Letters cycle through `keys`, never the same
    take twice running, each `gain_db` give or take `vary_db / 2`. A pack
    without these keys stands in its own key, click or tick (`pick`). Put
    the result in a Film's `sounds`."""
    keys = pick(keys)
    if not keys:
        return ()
    space = (pick((space,), ()) or keys)[0]
    rnd = random.Random(f'typing-sounds:{seed}')
    out, last = [], None
    for ch, f in zip(text, frames):
        if ch in '\n\r':
            continue
        if ch.isspace():
            sid = space
        else:
            sid = rnd.choice([k for k in keys if k != last] or keys)
            last = sid
        gain = gain_db + rnd.uniform(-vary_db / 2, vary_db / 2)
        out.append(vb.sfx.sound(sid, at=f, fps=fps, align='onset', gain_db=gain))
    return tuple(out)


TEXT = 'hello, world'
FRAMES = keystrokes(TEXT, at=round(0.35 * demo.FPS), per_char=0.14, seed=3, fps=demo.FPS)
BARS = 29


def draw(n, cv):
    f = demo.mono(92, 600)
    typed = sum(1 for k in FRAMES if k <= n)
    w, h = vb.text.block_size([TEXT], f)
    x, y = (demo.W - w) / 2, demo.H / 2 - h - 20
    if typed:
        box = vb.text.draw(cv, [TEXT[:typed]], f, x, y, demo.INK)
        cv.mark('text', *box)
    # The block cursor: solid while keys land, blinking once the line is in.
    cx = x + vb.text.measure(TEXT[:typed], f)
    if typed < len(TEXT) or (n - FRAMES[-1]) % 16 < 9:
        cv.rect(cx + 4, y + h * 0.1, f.size * 0.55, h * 0.8, demo.ACCENT)
    # A level meter that jumps on every keystroke and falls away: the clicks, seen.
    level = max((math.exp(-(n - k) / 2.5) * (1.4 if ch == ' ' else 1.0)
                 for ch, k in zip(TEXT, FRAMES) if 0 <= n - k < 12), default=0)
    mid, gap, bw = demo.H / 2 + 150, 30, 14
    left = demo.W / 2 - (BARS - 1) * gap / 2
    for i in range(BARS):
        shape = 1 - abs(i - (BARS - 1) / 2) / (BARS / 2)
        jag = random.Random(f'bar:{i}:{n}').uniform(0.55, 1.0)
        bh = 8 + 170 * min(1.0, level) * shape * jag
        cv.rect(left + i * gap - bw / 2, mid - bh / 2, bw, bh, demo.TEAL, radius=bw / 2,
                alpha=0.35 + 0.65 * min(1.0, level))


CAPABILITY = Capability(
    id='typing-sounds',
    name='Typing sounds',
    family='sound',
    group='Sound effects',
    aliases=('keyboard sounds', 'key clicks', 'keystroke sfx', 'typing sfx'),
    definition='Text typing itself on screen with a keyboard click landing on each letter as it appears, '
               'so the words sound typed as well as look it.',
    phrasings=('add keyboard clicking while the text types out',
               'make every letter make a key sound as it appears',
               'I want to hear typing when the words come in'),
    related=('keystroke-overlay', 'typewriter-reveal', 'blinking-cursor', 'silence-drop',
             'cursor-follow-auto-zoom', 'magnetic-button'),
    api=('videobuilder.capabilities.sound.typing_sounds.typing_sounds',
         'videobuilder.capabilities.sound.typing_sounds.keystrokes',
         'videobuilder.type.typewriter.schedule'),
    demo=lambda: demo.film(draw, sounds=typing_sounds(TEXT, FRAMES, fps=demo.FPS, seed=3)),
)
