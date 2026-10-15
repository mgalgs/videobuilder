"""The showcase: every capability in the catalog, one quick shot each, cut on
the beat of a generated music bed while a made-up app, Lumen, gets launched.

    python -m videobuilder preview examples/showcase.py
    python -m videobuilder render examples/showcase.py --format all

Shots run in the catalog's order (videobuilder/capabilities.py), each with a
small corner tag carrying its card's title, so a viewer can find on the
/capabilities page what they just saw. Three capabilities are properties of
the whole film as well as a shot: every cut is on the beat (beat-lock), it
renders in two shapes laid out separately (every-format), and the end card
comes to rest exactly where the opening starts (seamless-loops).

The shots live in examples/showcase_scenes/; this file holds the timeline,
the music, the opening, the end card and the tag.
"""
import array
import hashlib
import math
import os
import random
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import videobuilder as vb  # noqa: E402
from videobuilder import capabilities  # noqa: E402
from showcase_scenes import data, imagery, kit, motion, paper, timing  # noqa: E402
from showcase_scenes.kit import ACCENT, BG, INK, MUTED  # noqa: E402

GRID = kit.GRID
FPB = kit.FPB

# ---- the timeline: beats at 120 bpm, 15 frames each ----
# (segment, beats); capability shots are named by their catalog id.
CUT = [
    ('title', 4),
    ('eased-entrances', 3), ('springs-with-character', 3), ('staggered-reveals', 3), ('pop-on-the-beat', 4),
    ('character-motion', 4), ('overlap-transitions', 4), ('drawn-on-diagram', 5), ('shape-morph', 4),
    ('kinetic-typography', 4), ('counting-numbers', 3), ('bar-charts', 4), ('gauges-and-rings', 3),
    ('line-chart-callout', 4),
    ('camera-on-a-screenshot', 4), ('redrawn-product-ui', 4), ('image-treatments', 4), ('generated-art', 3),
    ('orbit-3d', 3), ('hard-light-sweep', 4), ('comic-halftone', 3), ('pixel-art-layer', 4), ('paper-collage', 6),
    ('beat-lock', 4), ('every-format', 5),
]
HOOK = 6     # beats of kinetic-type hook before the title hit
END_CARD = 13


def _timeline():
    segs = [vb.Segment('hook', 0, HOOK, children=vb.sequence(0, [('hook-1', 2), ('hook-2', 2), ('hook-3', 2)]))]
    at = HOOK
    for name, beats in CUT:
        kw = {}
        if name == 'beat-lock':  # a hard cut on each of its four beats
            kw['children'] = vb.sequence(at, [(f'beat-{i + 1}', 1) for i in range(beats)])
        if name == 'overlap-transitions':
            kw['overlap'] = 1
        segs.append(vb.Segment(name, at, at + beats, **kw))
        at += beats
    segs.append(vb.Segment('end', at, at + END_CARD, data={'copy': list(END_COPY), 'copy_at': 0}))
    return vb.Timeline(GRID, segs, end=at + END_CARD)


END_COPY = ('Made with videobuilder', 'Every shot here is a capability.', 'Tell the builder which one you want.')
TIMELINE = _timeline()
END = TIMELINE.end

# Each catalog id and the segment that shows it. Three are also properties of
# the whole film; their segment is where they're shown on their own.
SHOTS = {e['id']: e['id'] for e in capabilities.CATALOG}
SHOTS['seamless-loops'] = 'end'
TAGS = {seg: capabilities.get(cap)['title'] for cap, seg in SHOTS.items()}
for _i in range(4):
    TAGS[f'beat-{_i + 1}'] = TAGS['beat-lock']

LOOP = True  # the end card comes to rest on the opening's first frame


# ---- music: the skill's make_track.py bed, with a build into the title hit ----
RATE = 48000


def _music():
    args = dict(bpm=GRID.bpm, beats=int(END), hook=HOOK, v=3)
    key = hashlib.sha1(repr(sorted(args.items())).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-showcase-{key}.wav')
    if os.path.exists(path):
        return path
    sys.path.insert(0, str(HERE.parent / 'skill' / 'make-a-video' / 'scripts'))
    from make_track import synth
    spb = 60 / GRID.bpm
    full = synth(GRID.bpm, int(END), rate=RATE, loop='minor', tail=1.0)
    thin = synth(GRID.bpm, int(END), rate=RATE, loop='minor', voices=('kick', 'pad'), tail=1.0)
    n = len(full)
    hit = int(HOOK * spb * RATE)
    out = [(thin[i] if i < hit else full[i]) / 32767 for i in range(n)]
    rnd = random.Random(5)
    noise, lp = [], 0.0
    for _ in range(RATE * 2):  # white noise, gently low-passed so the hits stay round
        lp += 0.45 * (rnd.uniform(-1, 1) - lp)
        noise.append(lp * 1.8)

    def add(t0, seconds, fn):
        a = int(t0 * RATE)
        for i in range(max(0, a), min(n, a + int(seconds * RATE))):
            out[i] += fn((i - a) / RATE, i - a)

    def snare(gain):
        def fn(x, k):
            return gain * (0.75 * noise[k % len(noise)] * math.exp(-x * 28)
                           + 0.5 * math.sin(2 * math.pi * 190 * x) * math.exp(-x * 40))
        return fn

    # The build: a snare roll that doubles up into the hit, over a rising noise wash.
    for k in range(2 * 2, 2 * HOOK):  # eighths from beat 2
        step = 2 if k < 2 * (HOOK - 2) else 4
        for j in range(step // 2):
            t = (k + j * 2 / step) * spb / 2
            add(t, 0.12, snare(0.18 + 0.32 * t / (HOOK * spb)))
    rise = HOOK * spb - 2 * spb
    add(2 * spb, rise, lambda x, k: 0.22 * (x / rise) ** 2 * noise[(k * 7) % len(noise)])
    # The hit on the title: a sub drop and a long crash.
    add(HOOK * spb, 1.6, lambda x, k: 0.5 * math.sin(2 * math.pi * (38 + 60 * math.exp(-x * 12)) * x) * math.exp(-x * 2.6))
    add(HOOK * spb, 2.2, lambda x, k: 0.4 * noise[k % len(noise)] * math.exp(-x * 2.2))
    # Punch: a snare on beats 2 and 4 of every bar after the hit; a smaller crash on the end card.
    for k in range(HOOK + 1, int(END), 2):
        add(k * spb, 0.2, snare(0.42))
    end_at = (END - END_CARD) * spb
    add(end_at, 1.8, lambda x, k: 0.26 * noise[k % len(noise)] * math.exp(-x * 2.6))
    # A soft clip glues it together and lifts the body of the mix under the drum peaks.
    out = [math.tanh(1.5 * v) for v in out]
    peak = max(1e-9, max(abs(v) for v in out))
    data = array.array('h', (int(v / peak * 0.9 * 32767) for v in out))
    tmp = f'{path}.{os.getpid()}.tmp'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    os.replace(tmp, path)
    return path


# ---- the loop's resting state: the Lumen logo alone, centred, its moon turning ----
ORBIT = 75  # frames per turn of the logo's moon; divides the film's length, so the loop has no seam


def orb_spin(n):
    return 2 * math.pi * (n % ORBIT) / ORBIT


def orb_rest(st):
    return st.content.cx, st.content.cy, kit.pick(st, 64, 72)


def _frame_n(s):
    return TIMELINE.start(s.segment) + s.f


# ---- the hook: three phrases of kinetic type, a cut on every second beat ----
HOOK_COPY = {'hook-1': 'Too many apps.', 'hook-2': 'Too many lists.', 'hook-3': 'Not enough day.'}
_rnd = random.Random(11)
SCRAPS = [(_rnd.uniform(0.04, 0.96), _rnd.uniform(0.06, 0.94), _rnd.uniform(0.6, 1.3), _rnd.choice((0, 1, 2)),
           _rnd.uniform(-1, 1)) for _ in range(16)]


def _scraps(cv, s, st, kind):
    """App icons (hook-1) or list rows (hook-2) scattered around the type, drifting."""
    fr = st.frame
    for i, (u, v, size, colour, drift) in enumerate(SCRAPS):
        x, y = fr.x + u * fr.w, fr.y + v * fr.h + drift * s.f * 0.8
        a = kit.spring(s.f, 4 + i % 5)
        col = (kit.ACCENT, kit.TEAL, kit.CARD_HI)[colour]
        with kit.scaled(cv, x, y, min(1.0, a)), cv.layer(opacity=0.5 * min(1, a)):
            if kind == 'apps':
                d = 46 * size
                cv.rect(x - d / 2, y - d / 2, d, d, col, radius=d * 0.26)
            else:
                cv.rect(x - 60 * size, y - 8, 16, 16, col, radius=4)
                cv.rect(x - 60 * size + 26, y - 5, 110 * size, 10, kit.CARD_HI, radius=5)


def hook(cv, s, st):
    cv.fill(BG)
    words = HOOK_COPY[s.name].split()
    if s.name == 'hook-1':
        x, y, r = orb_rest(st)
        out = kit.prog(s.f, 3, 10, kit.SMOOTH)  # held for a few frames: the loop's seam
        if out < 1:
            with kit.scaled(cv, x, y, 1 - out):
                kit.logo(cv, x, y, r, orb_spin(s.f), alpha=1 - out)
    if s.name in ('hook-1', 'hook-2'):
        _scraps(cv, s, st, 'apps' if s.name == 'hook-1' else 'lists')
    f = kit.font(kit.pick(st, 132, 124), 850, tracking=-0.03, line_height=1.0)
    width = kit.pick(st, st.content.w, st.content.w * 0.8)
    lines, (w, h) = kit.lines_of(' '.join(words), f, width)
    lh = vb.text.line_height(f)
    top = st.content.cy - h / 2
    k = 0
    first = 4 if s.name == 'hook-1' else -3   # later phrases are already landing on their cut
    for li, line in enumerate(lines):
        lw = vb.text.measure(line, f)
        x = st.content.cx - lw / 2
        for word in line.split(' '):
            ww = vb.text.measure(word + ' ', f)
            p = kit.spring(s.f, first + 6 * k, kit.BOUNCY)
            colour = ACCENT if k == len(words) - 1 else INK
            sc = 1.5 - 0.5 * min(1.2, p)
            cy = top + li * lh + lh / 2
            if p > 0.01:
                with kit.scaled(cv, x + ww / 2, cy, sc), cv.layer(opacity=min(1, p)):
                    vb.text.draw(cv, word, f, x, top + li * lh, colour)
            x += ww
            k += 1
    if s.f > first:
        cv.mark('hook', st.content.cx - w / 2, top, w, h)


# ---- the title: the hit ----
def title(cv, s, st):
    cv.fill(BG)
    hit = kit.prog(s.f, 0, 24)
    kit.glow(cv, st.content.cx, st.content.cy, kit.pick(st, 620, 560) * (0.6 + 0.4 * hit), ACCENT, 0.32 * (1 - 0.5 * hit))
    word_f = kit.font(kit.pick(st, 168, 150), 300 + 550 * kit.prog(s.f, 0, 18), tracking=-0.035)
    ww = vb.text.measure('Lumen', word_f)
    lh = vb.text.line_height(word_f)
    r = kit.pick(st, 74, 80)
    p = kit.spring(s.f, -2, kit.BOUNCY)
    sub_f = kit.font(kit.pick(st, 38, 36), 500)
    sub = 'One calm plan for your day.'
    sub_lines, (sw, sh) = kit.lines_of(sub, sub_f, kit.pick(st, 900, 520))
    if st.wide:
        total = 2 * r + 36 + ww
        x0 = st.content.cx - total / 2
        cy = st.content.cy - 40
        lx, ly = x0 + r, cy
        wx, wy = x0 + 2 * r + 36, cy - lh / 2
        sy = cy + lh / 2 + 28
    else:
        block = 2 * r + 30 + lh + 30 + sh
        top = st.content.cy - block / 2
        lx, ly = st.content.cx, top + r
        wx, wy = st.content.cx - ww / 2, top + 2 * r + 30
        sy = wy + lh + 30
    with kit.scaled(cv, lx, ly, max(0.0, p)):
        kit.logo(cv, lx, ly, r, orb_spin(_frame_n(s)) + 2 * math.pi * (1 - p))
    q = kit.prog(s.f, 0, 12)
    with cv.layer(opacity=q, dy=(1 - q) * 30):
        box = vb.text.draw(cv, 'Lumen', word_f, wx, wy, INK)
    cv.mark('wordmark', *box)
    a = kit.prog(s.f, FPB, FPB + 14)
    with cv.layer(opacity=a, dy=(1 - a) * 18):
        vb.text.draw(cv, sub_lines, sub_f, st.content.cx - sw / 2, sy, MUTED, align='center', width=sw)
    cv.mark('subtitle', st.content.cx - sw / 2, sy, sw, sh)


# ---- the end card, which comes to rest on the opening frame ----
def end(cv, s, st):
    cv.fill(BG)
    big = kit.font(kit.pick(st, 80, 70), 800, tracking=-0.025, line_height=1.05)
    body = kit.font(kit.pick(st, 36, 36), 500, line_height=1.3)
    lines, (w, h) = kit.lines_of(END_COPY[0], big, kit.pick(st, 1000, 560))
    l2, (w2, h2) = kit.lines_of(END_COPY[1], body, kit.pick(st, 1000, 560))
    l3, (w3, h3) = kit.lines_of(END_COPY[2], body, kit.pick(st, 1000, 560))
    rx, ry, rr = orb_rest(st)
    r = kit.pick(st, 44, 52)
    gap = kit.pick(st, 30, 36)
    block = 2 * r + gap + h + gap + h2 + 10 + h3
    top = st.content.cy - block / 2
    leave = kit.prog(s.f, 10 * FPB, 11 * FPB, kit.SMOOTH)   # copy goes, the logo glides home
    land = kit.prog(s.f, 10 * FPB + 5, 11 * FPB + 10, kit.SMOOTH)
    lx, ly = st.content.cx, kit.lerp(top + r, ry, land)
    with kit.scaled(cv, lx, ly, kit.lerp(r / rr, 1, land) * min(1, kit.spring(s.f, -3, kit.BOUNCY))):
        kit.logo(cv, lx, ly, rr, orb_spin(_frame_n(s)))
    y = top + 2 * r + gap
    p = kit.spring(s.f, -3)
    with cv.layer(opacity=min(1, p) * (1 - leave), dy=(1 - min(1, p)) * 24):
        vb.text.draw(cv, lines, big, st.content.cx - w / 2, y, INK, align='center', width=w)
        cv.mark('made-with', st.content.cx - w / 2, y, w, h)
    y += h + gap
    for i, (ls, lw, lh, colour) in enumerate(((l2, w2, h2, MUTED), (l3, w3, h3, INK))):
        a = kit.prog(s.f, (2 + 2 * i) * FPB - 3, (2 + 2 * i) * FPB + 12)
        with cv.layer(opacity=a * (1 - leave), dy=(1 - a) * 16):
            vb.text.draw(cv, ls, body, st.content.cx - lw / 2, y, colour, align='center', width=lw)
            cv.mark(f'line-{i + 1}', st.content.cx - lw / 2, y, lw, lh)
        y += lh + 10


SCENES = {'hook-1': hook, 'hook-2': hook, 'hook-3': hook, 'title': title, 'end': end,
          **motion.SCENES, **data.SCENES, **imagery.SCENES, **paper.SCENES, **timing.SCENES}


def draw(n, cv):
    st = kit.stage(cv)
    live = TIMELINE.live(n)
    for s in live:
        SCENES[s.name](cv, s, st)
    front = live[-1]
    title = TAGS.get(front.name)
    if title:
        kit.tag(cv, st, title, tag_alpha(front))


def tag_alpha(s):
    """The tag is up from a shot's first frame; the end card's goes before the loop."""
    if s.name == 'end':
        return kit.prog(s.f, 6 * FPB, 6 * FPB + 8) * (1 - kit.prog(s.f, 10 * FPB, 11 * FPB, kit.SMOOTH))
    return 1.0


# Pairs drawn over each other by design (a callout inside its chart, a stamp slammed across the page).
OVERLAP_OK = {('axes', 'callout'), ('stamp', 'arrow'), ('stamp', 'notepad')}

LAYOUTS = {name: {'safe': kit.SAFE[name]} for name in ('16x9', '9x16')}

FILM = vb.Film(
    draw=draw,
    timeline=TIMELINE,
    formats=(kit.F16, kit.F9),
    background=BG,
    audio=vb.Audio(_music(), fade_out_frames=round(2 * FPB)),
)

if __name__ == '__main__':
    vb.main(__file__)
