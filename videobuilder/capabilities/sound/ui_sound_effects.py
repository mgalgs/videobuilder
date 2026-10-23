"""UI sounds: small, quiet sounds tied to interface actions -- a tick as the
pointer comes over a button, a click as it is pressed, a snap as a switch
flips, a ding as a notification lands -- each one on the action's frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..ui.cursor_state_change import draw_cursor
from ..ui.press_depress import draw_press_button, press_depth
from ..ui.toggle_switch_slide import draw_toggle

# One sound per kind of interface event: the sounds to try, in order (the
# pack's `designed` family first, so a screen's sounds belong together), the
# roles to fall back on when none is in the pack, its level and its sync.
UI_SOUNDS = {
    'hover': (('pro_hover_tick/soft', 'hover_tick/detent'), ('tick',), -10, 'onset'),
    'press': (('pro_click/soft', 'fit/click/floss_lid'), ('click',), -6, 'onset'),
    'tap': (('pro_tap/soft', 'fit/land.light/finger_phone'), ('tap', 'click'), -6, 'onset'),
    'toggle': (('pro_click/snap', 'toggle/latch', 'fit/snap/switch_flip'), ('toggle', 'click'), -6, 'onset'),
    'pop': (('pro_pop_in/round', 'fit/pop/mouth_plop'), ('pop', 'click'), -8, 'peak'),
    'notify': (('pro_notify/ding_2045', 'notify/m0'), ('ding',), -10, 'peak'),
}


def ui_effect(event):
    """The pack's `vb.sfx` effect for interface `event` (a key of
    `UI_SOUNDS`): its first listed sound the pack has, else the first of its
    fallback roles' sounds, designed ones first."""
    if event not in UI_SOUNDS:
        raise KeyError(f'no UI sound for {event!r}; events are {", ".join(UI_SOUNDS)}')
    ids, roles, _, _ = UI_SOUNDS[event]
    for sid in ids:
        try:
            return vb.sfx.get(sid)
        except ValueError:
            pass
    have = vb.sfx.roles()
    for role in roles:
        if role in have:
            found = vb.sfx.find(role)
            return next((e for e in found if e.family == 'designed'), found[0])
    raise ValueError(f'the sound pack has nothing for the UI event {event!r} (roles {", ".join(roles)})')


def ui_sound(event, at, gain_db=None, fps=30, align=None, **kw):
    """A `vb.sfx` sound for interface `event` (a key of `UI_SOUNDS`: 'hover',
    'press', 'tap', 'toggle', 'pop', 'notify') on film frame `at`. Clicks,
    ticks and taps start on their frame (onset); pops and dings peak on it.
    `gain_db` overrides the event's default level; `kw` goes to the sound
    (`note='G5'` for a ding, `through=True`, ...). Put the result in the
    film's `sounds`."""
    effect = ui_effect(event)
    _, _, gain, sync = UI_SOUNDS[event]
    return effect.sound(at, fps=fps, align=align or sync, gain_db=gain if gain_db is None else gain_db, **kw)


def ui_sounds(events, fps=30, **kw):
    """`ui_sound` for each `(event, frame)` pair in `events`, as a tuple for
    a film's `sounds`."""
    return tuple(ui_sound(e, at, fps=fps, **kw) for e, at in events)


def draw_sound_ring(cv, cx, cy, age, r=60, color=demo.TEAL, life=0.5, rings=2):
    """The visual half of a UI sound: `rings` thin circles spreading from
    (cx, cy) and fading, `age` seconds after the sound fired. Nothing before
    it fires (`age` < 0) or once `life` seconds have passed."""
    for i in range(rings):
        p = (age - i * 0.08) / life
        if 0 <= p < 1:
            e = vb.ease_out_quint(p)
            cv.arc(cx, cy, r + 70 * e, 0, 2 * math.pi, color, width=4 * (1 - p) + 1, alpha=0.8 * (1 - p))


# The demo: a pointer hovers a button, presses it, flips a switch, and a
# notification drops in -- four sounds, each marked on a strip below.
HOVER, PRESS, TOGGLE, NOTIFY = 0.45, 0.8, 1.4, 1.85
EVENTS = (('hover', HOVER), ('press', PRESS), ('toggle', TOGGLE), ('notify', NOTIFY))
LABELS = {'hover': 'tick', 'press': 'click', 'toggle': 'snap', 'notify': 'ding'}
BX, BY, BW, BH = demo.W * 0.34, demo.H * 0.52, 340, 110
SX, SY, SW = demo.W * 0.68, demo.H * 0.52, 220
STRIP_Y = demo.H * 0.86


def _toast(cv, t):
    p = vb.ease_out_back(demo.phase(t * demo.FPS, NOTIFY - 0.25, NOTIFY))
    if p <= 0:
        return
    w, h = 460, 92
    x, y = demo.W / 2 - w / 2, -h - 20 + (h + 70) * p
    cv.shadow(x, y, w, h, radius=20, dy=10, blur=26, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, '#2a2d36', radius=20)
    demo.dot(cv, x + 50, y + h / 2, r=18, color=demo.ACCENT)
    vb.text.draw(cv, ['Saved'], demo.font(30, 800), x + 90, y + 18, demo.INK)
    vb.text.draw(cv, ['Your settings are on'], demo.font(22, 600), x + 90, y + 54, demo.MUTED)
    cv.mark('toast', x, y, w, h)
    draw_sound_ring(cv, x + 50, y + h / 2, t - NOTIFY, r=26, color=demo.ACCENT)


def _strip(cv, t):
    """A timeline under the scene: a playhead runs along it and each sound
    leaves a burst of waveform where it fired, with its name."""
    x0, x1, y = 160, demo.W - 160, STRIP_Y
    cv.line(x0, y, x1, y, demo.LINE, width=2)
    fx = lambda s: x0 + (x1 - x0) * s / demo.SECONDS  # noqa: E731
    for event, at in EVENTS:
        if t < at:
            continue
        cx, grow = fx(at), vb.ease_out_quint(vb.clamp01((t - at) / 0.15))
        for k in range(-6, 7):
            amp = 46 * grow * math.exp(-abs(k) * 0.35) * (0.55 + 0.45 * abs(math.sin(k * 2.1 + at)))
            cv.rect(cx + k * 7 - 2, y - amp / 2, 4, amp, demo.TEAL, radius=2)
        demo.word(cv, LABELS[event], cx, y + 54, size=26, color=demo.INK, alpha=grow)
    px = fx(t)
    cv.line(px, y - 34, px, y + 34, demo.ACCENT, width=3)


def draw(n, cv):
    t = n / demo.FPS
    depth = press_depth(t, PRESS, PRESS + 0.2)
    face = draw_press_button(cv, BX, BY, BW, BH, depth, color=demo.ACCENT, label='Save')
    cv.mark('button', *face)
    on = vb.ease_in_out_quart(demo.phase(n, TOGGLE, TOGGLE + 0.25))
    box = draw_toggle(cv, SX, SY, on, w=SW)
    cv.mark('switch', *box)
    draw_sound_ring(cv, BX, face.y + BH / 2, t - HOVER, r=BW / 2 - 40, color=demo.MUTED, rings=1)
    draw_sound_ring(cv, BX, face.y + BH / 2, t - PRESS, r=BW / 2 - 20)
    draw_sound_ring(cv, SX, SY, t - TOGGLE, r=SW / 2 - 20)
    _toast(cv, t)
    _strip(cv, t)
    # The pointer: in from the corner onto the button, then across to the switch.
    a = vb.interpolate(t, [0.0, HOVER], [0, 1], ease=vb.ease_out_quint)
    b = vb.interpolate(t, [1.0, TOGGLE - 0.05], [0, 1], ease=vb.ease_in_out_quart)
    tx, ty = BX + 60, BY + 20
    px = demo.W * 0.86 + (tx - demo.W * 0.86) * a + (SX + 50 - tx) * b
    py = demo.H * 0.72 + (ty - demo.H * 0.72) * a - 10 * b + 18 * (depth if b == 0 else 0)
    draw_cursor(cv, px, py, 0, size=1.6)


CAPABILITY = Capability(
    id='ui-sound-effects',
    name='UI sounds',
    family='sound',
    group='Sound effects',
    aliases=('UI sound effects', 'interface sounds', 'click sounds', 'microinteraction sounds', 'UI SFX'),
    definition='Small, quiet sounds placed on interface actions, such as a tick on hover, a click on a press, '
               'a snap on a toggle and a ding on a notification, each landing on the frame of its action.',
    phrasings=('add little click and ding sounds to the app demo',
               'make the buttons and toggles in the screen recording make sounds',
               'give the UI animation some tactile sound effects'),
    related=('silence-drop', 'icon-hover-bounce', 'audio-reactive-particles', 'ui-walkthrough-camera-zoom',
             'speed-dial-fan', 'stereo-panning'),
    api=('videobuilder.capabilities.sound.ui_sound_effects.ui_sound',
         'videobuilder.capabilities.sound.ui_sound_effects.ui_sounds',
         'videobuilder.capabilities.sound.ui_sound_effects.ui_effect',
         'videobuilder.capabilities.sound.ui_sound_effects.draw_sound_ring',
         'videobuilder.sfx.sound'),
    demo=lambda: demo.film(draw, sounds=ui_sounds((e, round(at * demo.FPS)) for e, at in EVENTS)),
)
