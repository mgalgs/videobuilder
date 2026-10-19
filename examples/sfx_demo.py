"""Sound effects on the frame: a 15 s 9:16 film whose motion each sound sells.

    python -m videobuilder sfx fetch            # once: the sound-effects pack
    python -m videobuilder render examples/sfx_demo.py

A card whips in (a whoosh peaking on its fastest frame), the picture whip-pans
to a phone (a whoosh on the pan's middle), a finger flips a switch and taps
Send (a switch and a click, each on the press), two notifications drop in
(dings a semitone apart, on their landing frames), a pan to a word that a
riser builds into and a hit slams on its impact frame (with a sub drop under
it), and a shimmer on the end card. Under it, a quiet bed from the skill's
make_track.py. Every sound is placed with `vb.sfx.sound(id, at=frame)`, its
peak on that frame; `check.py --video` confirms they land there.
"""
import math
import os
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
import videobuilder as vb  # noqa: E402
from videobuilder import impact, text  # noqa: E402

for _f in sorted((HERE / 'assets').glob('*.[ot]tf')):
    text.register(_f)

FPS, BPM = 30, 120
GRID = vb.Grid(fps=FPS, bpm=BPM)
FPB = round(GRID.frames_per_beat)          # 15
TOTAL = 30 * FPB                           # 450 frames, 15 s
W, H = 1080, 1920

BG, INK, MUTED, ACCENT, TEAL, LINE = '#14151a', '#f4f4f2', '#9397a1', '#ef5b4c', '#4fc3b0', '#2a2c33'
PHONE_BG = '#1e2027'


def font(size, weight=400):
    return vb.Font('Inter', size, weight=weight)


# ---- the beats of the film, in frames ----
CARD_IN = (8, 20)          # the title card flies in; fastest at its start
PAN_1 = (84, 96)           # whip pan: title -> phone
TOGGLE_PRESS = 132
SEND_PRESS = 168
NOTE_1, NOTE_2 = 204, 234  # notification banners land
PAN_2 = (264, 276)         # whip pan: phone -> launch
IMPACT = 336
HIT = impact.Hit(at=IMPACT, seed=4, ink=BG)
END_AT = 384
SHIMMER = END_AT + 10


def mid(span):
    return (span[0] + span[1]) // 2


SOUNDS = (
    vb.sfx.sound('whoosh_fast/tight', at=CARD_IN[0] + 3, dur=0.5, gain_db=-8),
    vb.sfx.sound('whoosh_fast/heavy', at=mid(PAN_1), dur=0.5, gain_db=-8),
    vb.sfx.sound('fit/snap/switch_flip', at=TOGGLE_PRESS, gain_db=-6),
    vb.sfx.sound('fit/click/floss_lid', at=SEND_PRESS, gain_db=-5),
    vb.sfx.sound('pro_notify/ding_2045', at=NOTE_1, note='G5', gain_db=-11),
    vb.sfx.sound('pro_notify/ding_2045', at=NOTE_2, note='Gs5', gain_db=-11),
    vb.sfx.sound('whoosh_fast/tight', at=mid(PAN_2), dur=0.5, gain_db=-8),
    vb.sfx.sound('pro_riser/air_gate', at=IMPACT, dur=1.0, gain_db=-13),
    vb.sfx.sound('pro_impact/short', at=IMPACT, gain_db=-8),
    vb.sfx.sound('pro_sub_drop/ref', at=IMPACT, align='onset', dur=1.0, gain_db=-16),
    vb.sfx.sound('pro_shimmer/m0', at=SHIMMER, dur=1.0, align='onset', gain_db=-12),
)


def _music():
    """A quiet pad-and-bass bed on the grid, made once (`make_track.synth`)."""
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-sfx-demo-{BPM}-{TOTAL // FPB}.wav')
    if not os.path.exists(path):
        sys.path.insert(0, str(HERE.parent / 'skill' / 'make-a-video' / 'scripts'))
        from make_track import synth
        data = synth(BPM, TOTAL // FPB, loop='major', voices=('hat', 'bass', 'pad'), tail=1.0)
        with wave.open(path, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(data.tobytes())
    return path


def ease_out(p):
    return 1 - (1 - min(1, max(0, p))) ** 4


def prog(n, a, z):
    return min(1.0, max(0.0, (n - a) / (z - a)))


# ---- scenes ----
def title(cv, n):
    cv.fill(BG)
    p = ease_out(prog(n, *CARD_IN))
    x = W + 40 - (W + 40 - 90) * p
    with cv.layer(dx=x - 90):
        cv.rect(90, 700, W - 180, 420, '#20222a', radius=36)
        cv.rect(90, 700, 14, 420, ACCENT, radius=7)
        f = font(92, 800)
        text.draw(cv, text.wrap('Sound on\nthe frame', f, W - 300), f, 150, 760, INK)
        cv.mark('card', 90, 700, W - 180, 420)
    sub = font(42, 500)
    a = prog(n, 36, 48)
    text.draw(cv, ['every whoosh, click and hit'], sub, 0, 1180, MUTED, align='center', width=W, alpha=a)
    text.draw(cv, ['lands where you put it'], sub, 0, 1240, MUTED, align='center', width=W, alpha=prog(n, 44, 56))


def phone(cv, n):
    cv.fill(BG)
    px, py, pw, ph = 170, 330, W - 340, 1260
    cv.rect(px - 14, py - 14, pw + 28, ph + 28, '#30333c', radius=84)
    cv.rect(px, py, pw, ph, PHONE_BG, radius=72)
    cv.mark('phone', px, py, pw, ph)
    head = font(48, 750)
    text.draw(cv, ['Share the cut'], head, px + 60, py + 150, INK)
    # A switch row.
    row_y = py + 300
    text.draw(cv, ['Include music'], font(38, 500), px + 60, row_y + 18, INK)
    on = n >= TOGGLE_PRESS
    sw_x, sw_y = px + pw - 220, row_y
    k = ease_out(prog(n, TOGGLE_PRESS, TOGGLE_PRESS + 6))
    cv.rect(sw_x, sw_y, 150, 80, TEAL if on else '#3a3d47', radius=40)
    cv.sector(sw_x + 40 + 70 * k, sw_y + 40, 32, 0, 2 * math.pi, INK)
    cv.line(px + 60, row_y + 130, px + pw - 60, row_y + 130, LINE, width=2)
    # The Send button.
    bx, by, bw, bh = px + 60, py + ph - 260, pw - 120, 130
    pressed = SEND_PRESS <= n < SEND_PRESS + 5
    s = 0.96 if pressed else 1.0
    with cv.layer(dx=(bx + bw / 2) * (1 - s), dy=(by + bh / 2) * (1 - s), scale=s):
        cv.rect(bx, by, bw, bh, ACCENT, radius=34)
        text.draw(cv, ['Send'], font(48, 750), bx, by + 34, '#1a0f0e', align='center', width=bw)
    # The finger: to the switch, then to Send.
    fx, fy = finger_at(n, (sw_x + 75, sw_y + 40), (bx + bw / 2, by + bh / 2))
    down = any(t <= n < t + 4 for t in (TOGGLE_PRESS, SEND_PRESS))
    cv.sector(fx, fy, 46 if down else 54, 0, 2 * math.pi, INK, alpha=0.30 if down else 0.22)
    cv.sector(fx, fy, 22, 0, 2 * math.pi, INK, alpha=0.9)
    for t in (TOGGLE_PRESS, SEND_PRESS):
        age = n - t
        if 0 <= age < 14:
            cv.arc(fx, fy, 30 + age * 6, 0, 2 * math.pi, INK, width=4, alpha=0.6 * (1 - age / 14))
    # Notifications drop in from the top.
    for i, land in enumerate((NOTE_1, NOTE_2)):
        p = ease_out(prog(n, land - 8, land))
        if n < land - 8:
            continue
        y = py + 40 + i * 190 - 260 * (1 - p)
        bounce = 10 * math.sin(min(1, max(0, (n - land) / 10)) * math.pi) if n >= land else 0
        cv.rect(px + 30, y + bounce, pw - 60, 160, '#2b2e37', radius=34)
        cv.sector(px + 110, y + bounce + 80, 36, 0, 2 * math.pi, TEAL if i else ACCENT)
        text.draw(cv, ['Sent: launch-cut.mp4' if i == 0 else 'Mara reacted to your cut'], font(34, 650),
                  px + 170, y + bounce + 46, INK)
        text.draw(cv, ['just now'], font(28, 500), px + 170, y + bounce + 96, MUTED)


def finger_at(n, a, b):
    rest = (W * 0.62, 1500)
    if n < TOGGLE_PRESS:
        p = ease_out(prog(n, TOGGLE_PRESS - 26, TOGGLE_PRESS))
        return rest[0] + (a[0] - rest[0]) * p, rest[1] + (a[1] - rest[1]) * p
    if n < SEND_PRESS:
        p = ease_out(prog(n, SEND_PRESS - 24, SEND_PRESS))
        return a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p
    p = ease_out(prog(n, SEND_PRESS + 8, SEND_PRESS + 30))
    return b[0] + (rest[0] - b[0]) * p, b[1] + 120 * p


def launch(cv, n):
    def scene(c):
        c.fill(BG)
        for k in range(9):    # the build: lines closing in toward the word
            r = 1400 - 1100 * prog(n, IMPACT - 30, IMPACT) - k * 60
            if r > 0 and n < IMPACT:
                c.arc(W / 2, H / 2, r, 0, 2 * math.pi, LINE, width=3, alpha=0.7)
        if n >= IMPACT:
            word(c, INK)
        else:
            text.draw(c, ['ready?'], font(54, 600), 0, H / 2 - 30, MUTED, align='center', width=W,
                      alpha=prog(n, PAN_2[1], PAN_2[1] + 10))

    def word(c, colour):
        f = font(176, 900)
        text.draw(c, ['LAUNCH'], f, 0, H / 2 - 120, colour, align='center', width=W)
        c.mark('word', 120, H / 2 - 120, W - 240, 250)

    HIT.draw(cv, n, scene, lambda c: word(c, INK))


def end(cv, n):
    cv.fill(BG)
    a = ease_out(prog(n, END_AT, END_AT + 14))
    s = 0.92 + 0.08 * a
    with cv.layer(opacity=a, dx=W / 2 * (1 - s), dy=H / 2 * (1 - s), scale=s):
        cv.sector(W / 2, 760, 90, 0, 2 * math.pi, ACCENT)
        cv.sector(W / 2, 760, 46, 0, 2 * math.pi, BG)
        text.draw(cv, ['vb.sfx'], font(120, 850), 0, 900, INK, align='center', width=W)
        text.draw(cv, ['a sound on every frame you ask for'], font(40, 500), 0, 1060, MUTED, align='center', width=W)
        cv.mark('end', 140, 670, W - 280, 440)
    for k in range(14):    # the sparkle the shimmer sells
        age = n - SHIMMER - k * 2
        if 0 <= age < 24:
            ang = k * 2.4
            r = 140 + 12 * age
            x, y = W / 2 + r * math.cos(ang), 760 + r * math.sin(ang) * 0.8
            cv.sector(x, y, 6 * (1 - age / 24) + 2, 0, 2 * math.pi, INK, alpha=1 - age / 24)


SCENES = ((0, title), (mid(PAN_1), phone), (mid(PAN_2), launch), (END_AT, end))


def whip(cv, n, a, b, span):
    """A whip pan from scene `a` to `b`: both slide left, smeared along the move."""
    p = prog(n, span[0], span[1])
    p = p * p * (3 - 2 * p)
    blur = math.sin(p * math.pi)
    for k in range(5):    # a few offset copies for the motion blur, strongest mid-pan
        off = (k - 2) * 60 * blur
        alpha = 1.0 if k == 2 else 0.22 * blur
        if alpha <= 0.01:
            continue
        with cv.layer(opacity=alpha, dx=-W * p + off):
            a(cv, n)
        with cv.layer(opacity=alpha, dx=W * (1 - p) + off):
            b(cv, n)


def draw(n, cv):
    for span, (a, b) in ((PAN_1, (title, phone)), (PAN_2, (phone, launch))):
        if span[0] <= n < span[1]:
            cv.fill(BG)
            whip(cv, n, a, b, span)
            return
    scene = [s for start, s in SCENES if n >= start][-1]
    scene(cv, n)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=('9x16',), background=BG,
               audio=vb.Audio(_music(), gain_db=-4, fade_out_frames=2 * FPB),
               sounds=SOUNDS,
               keyframes=((14, 'card in'), (TOGGLE_PRESS, 'switch'), (SEND_PRESS, 'send'),
                          (NOTE_2 + 4, 'dings'), (IMPACT, 'impact frame'), (IMPACT + 20, 'launch'),
                          (SHIMMER + 8, 'end')))

if __name__ == '__main__':
    vb.main(__file__)
