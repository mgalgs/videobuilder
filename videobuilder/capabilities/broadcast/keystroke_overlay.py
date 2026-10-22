"""Keystroke overlay: while a screen recording plays, every shortcut the
presenter presses pops up as a row of keycaps in a dark pill near the bottom
of the frame, each key dipping as it is struck, then fading out."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def keystroke_state(t, presses, hold=0.7, enter=0.12, leave=0.25):
    """Which press the overlay shows at `t` seconds, as `(keys, appear, age)`,
    or `None` when it is empty. `presses` is `[(time, keys), ...]` sorted by
    time, `keys` a tuple of key labels pressed together. A press shows from
    its time until the next one replaces it or `hold` seconds pass, then
    fades over `leave`. `appear` (0 -> 1) is its pop-in over `enter`, times
    its fade-out; `age` is seconds since it was pressed."""
    for i, (at, keys) in enumerate(presses):
        nxt = presses[i + 1][0] if i + 1 < len(presses) else None
        if t < at or (nxt is not None and t >= nxt):
            continue
        age = t - at
        out = 1.0 - vb.clamp01((age - hold) / leave)
        if out <= 0:
            return None
        return keys, vb.ease_out_back(vb.clamp01(age / enter)) * out, age
    return None


def key_depth(age, down=0.06, up=0.14):
    """How far one key of a combo is pushed in (0 up, 1 down) `age` seconds
    after its own strike: down fast over `down`, back up over `up`."""
    if age < 0:
        return 0.0
    if age < down:
        return vb.ease_out_quint(age / down)
    return 1.0 - vb.ease_out_quint(vb.clamp01((age - down) / up))


def keycap_width(label, font, h):
    """The width of a keycap `h` tall holding `label`: square for a single
    character, wider for words like Shift."""
    return max(h, vb.text.measure(label, font) + h * 0.56)


def draw_keycap(cv, x, y, label, font, h, depth=0.0, face='#f4f2ec', ink='#1d1d22', lift=None):
    """One keycap with its top-left at (x, y) and its base `h` tall: a light
    face riding `lift` px above a darker skirt, pushed flush by `depth`.
    Returns its Box."""
    lift = h * 0.1 if lift is None else lift
    w = keycap_width(label, font, h)
    r = h * 0.18
    rr, gg, bb, _ = vb.rgba(face)
    cv.rect(x, y, w, h, (rr * 0.62, gg * 0.62, bb * 0.62, 1), radius=r)
    fy = y - lift * (1 - depth)
    cv.rect(x, fy, w, h - lift, face, radius=r)
    lw, lh = vb.text.block_size([label], font)
    vb.text.draw(cv, [label], font, x + (w - lw) / 2, fy + (h - lift - lh) / 2, ink)
    return vb.Box(x, y, w, h)


def draw_keystroke_overlay(cv, t, presses, cx, y, h=78, font=None, plate=(0.06, 0.06, 0.08, 0.78),
                           joiner='+', ink=demo.INK, stagger=0.05, **kw):
    """The overlay at `t` seconds: the current press of `presses` (see
    `keystroke_state`, which `kw` goes to) as keycaps joined by `joiner`,
    centred on `cx` with the plate's bottom at `y`. Keys in a combo strike
    `stagger` seconds apart. Returns the plate's Box, or `None` when empty."""
    state = keystroke_state(t, presses, **kw)
    if state is None:
        return None
    keys, appear, age = state
    font = font or demo.font(round(h * 0.34), 700)
    jf = demo.font(round(h * 0.42), 600)
    gap, pad = h * 0.22, h * 0.32
    jw = vb.text.measure(joiner, jf)
    widths = [keycap_width(k, font, h) for k in keys]
    inner = sum(widths) + (len(keys) - 1) * (jw + 2 * gap)
    pw, ph = inner + 2 * pad, h + 2 * pad
    px, py = cx - pw / 2, y - ph
    with cv.layer(opacity=min(1.0, max(0.0, appear)), scale=0.85 + 0.15 * appear, dy=16 * (1 - min(1.0, appear))):
        cv.shadow(px, py, pw, ph, radius=ph * 0.3, dy=8, blur=24, color=(0, 0, 0, 0.45))
        cv.rect(px, py, pw, ph, plate, radius=ph * 0.3)
        x = px + pad
        for i, (k, w) in enumerate(zip(keys, widths)):
            draw_keycap(cv, x, py + pad, k, font, h, key_depth(age - i * stagger))
            x += w
            if i < len(keys) - 1:
                jh = vb.text.block_size([joiner], jf)[1]
                vb.text.draw(cv, [joiner], jf, x + gap, py + (ph - jh) / 2, ink, alpha=0.75)
                x += jw + 2 * gap
    box = vb.Box(px, py, pw, ph)
    cv.mark('keystrokes', *box)
    return box


PRESSES = [(0.35, ('Ctrl', 'C')), (1.15, ('Ctrl', 'V')), (1.95, ('Ctrl', 'Shift', 'S'))]


def _editor(cv, t):
    """A plain app window standing in for the screen recording: lines of
    text, with a selection that is copied, then pasted as a new line."""
    x, y, w, h = 150, 36, demo.W - 300, 336
    cv.shadow(x, y, w, h, radius=16, dy=10, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, '#24242c', radius=16)
    cv.rect(x, y, w, 40, '#2f2f39', radius=16)
    cv.rect(x, y + 24, w, 16, '#2f2f39')
    for i, c in enumerate(('#e0605a', '#e0b44a', '#5cc06a')):
        demo.dot(cv, x + 26 + i * 22, y + 20, r=6, color=c)
    widths = [0.62, 0.48, 0.7, 0.36, 0.55]
    pasted = t >= PRESSES[1][0]
    if pasted:
        widths.insert(3, 0.48)
    for i, f in enumerate(widths):
        ly = y + 80 + i * 40
        if i == 1 and PRESSES[0][0] - 0.3 <= t:
            cv.rect(x + 42, ly - 7, w * f + 12, 30, demo.TEAL, radius=5, alpha=0.35)
        alpha = 0.85 if not (pasted and i == 3) else vb.clamp01((t - PRESSES[1][0]) / 0.2)
        cv.rect(x + 48, ly, w * f, 16, demo.MUTED, radius=8, alpha=alpha)
    if t >= PRESSES[2][0]:
        f = demo.font(18, 700)
        a = vb.clamp01((t - PRESSES[2][0]) / 0.2)
        vb.text.draw(cv, ['Saved'], f, x + w - 90, y + 9, demo.TEAL, alpha=a)


def draw(n, cv):
    t = n / demo.FPS
    _editor(cv, t)
    draw_keystroke_overlay(cv, t, PRESSES, demo.W / 2, demo.H - 36, h=60)


CAPABILITY = Capability(
    id='keystroke-overlay',
    name='Keystroke overlay',
    family='broadcast',
    group='UI walkthroughs',
    aliases=('key overlay', 'keypress display', 'shortcut overlay', 'keycast', 'screencast keys'),
    definition='Keyboard shortcuts pressed during a screen recording appear as little keycaps on a dark '
               'pill near the bottom of the frame, each one tapping down before the combo fades away.',
    phrasings=('show which keys I am pressing in the tutorial',
               'pop up the keyboard shortcut on screen when I use it',
               'little key buttons at the bottom showing Ctrl+C as I hit it'),
    related=('camcorder-timecode-overlay', 'typing-sounds', 'luma-key', 'coachmark-spotlight-cutout',
             'chroma-key', 'typewriter-reveal'),
    api=('videobuilder.capabilities.broadcast.keystroke_overlay.draw_keystroke_overlay',
         'videobuilder.capabilities.broadcast.keystroke_overlay.keystroke_state',
         'videobuilder.capabilities.broadcast.keystroke_overlay.draw_keycap'),
    demo=lambda: demo.film(draw),
)
