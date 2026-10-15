"""The showcase: every capability in the catalog, cut on the beat of a
generated music bed while a made-up app, Lumen, gets launched.

    python -m videobuilder preview examples/showcase.py
    python -m videobuilder render examples/showcase.py --format all

Sections: a kinetic-type hook and the title hit; the product (camera, UI,
Lumi checking off the day, a tester on camera, a diagram), the launch
numbers on one dashboard, then the looks, which get room to breathe (generated art, 3D, hard light,
comic, pixel art, paper collage), and the timing and formats block before
the end card. Sections meet on catalog moves (a shape morph, an overlap
slide, the paper rip), cuts within a section land on the beat.

A shot can show several capabilities at once: its corner tag names them all
(SHOTS), so a viewer can find on the /capabilities page what they just saw.
Three capabilities are properties of the whole film as well as a shot: every
cut is on the beat (beat-lock), it renders in two shapes laid out separately
(every-format), and the end card comes to rest exactly where the opening
starts (seamless-loops).

The shots live in examples/showcase_scenes/; this file holds the timeline,
the transitions, the music, the opening, the end card and the tag.
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
from videobuilder import capabilities, paths  # noqa: E402
from showcase_scenes import comic, data, imagery, kit, looks, motion, paper, pixel, timing, voice  # noqa: E402
from showcase_scenes.kit import ACCENT, BG, INK, MUTED  # noqa: E402

GRID = kit.GRID
FPB = kit.FPB

# ---- the timeline: beats at 120 bpm, 15 frames each ----
# A section is (name, beats) for a single shot, or (name, [parts]) for a group
# of shots cut on the beat; parts nest the same way. The third item, where
# there is one, is the transition in: beats the section before keeps drawing
# under it (see TRANSITIONS).
SECTIONS = [
    ('hook', [('hook-1', 2), ('hook-2', 2), ('hook-3', 2)]),
    ('title', 4),
    ('product', [('camera', 5), ('redrawn', 4), ('lumi', 8), ('voice', 5), ('diagram', 5)], 1),
    ('dashboard', 10, 1),
    ('styles', [('generated', [('gen-arcs', 3), ('gen-flow', 3), ('gen-tiles', 3)]),
                ('orbit', [('orbit-type', 3), ('orbit-device', 3), ('orbit-bleed', 4)]),
                ('light', [('light-wide', 5), ('light-close', 5)]),
                ('comic', [('comic-hq', 3), ('comic-close', 3), ('comic-launch', 3)]),
                ('pixel', [('pixel-run', 7), ('pixel-clear', 3)]),
                ('paper', [('paper-head', 3), ('paper-pad', 4), ('paper-stamp', 4)])]),
    ('closing', [('beats', [(f'beat-{i + 1}', 1) for i in range(4)]), ('every-format', 7)], 1),
    ('end', 13),
]
HOOK = 6     # beats of kinetic-type hook before the title hit


def _segments(parts, at):
    out = []
    for name, body, *overlap in parts:
        if isinstance(body, list):
            children = _segments(body, at)
            seg = vb.Segment(name, at, children[-1].until, children=children, overlap=overlap[0] if overlap else 0)
        else:
            seg = vb.Segment(name, at, at + body, overlap=overlap[0] if overlap else 0)
        out.append(seg)
        at = seg.until
    return out


def _timeline():
    segs = _segments(SECTIONS, 0)
    segs[-1].data = {'copy': list(END_COPY), 'copy_at': 0}
    return vb.Timeline(GRID, segs, end=segs[-1].until)


END_COPY = ('Made with videobuilder', 'Every shot here is a capability.', 'Tell the builder which one you want.')
TIMELINE = _timeline()
END = TIMELINE.end
END_CARD = TIMELINE.find('end').until - TIMELINE.find('end').at

# Each shot and the catalog capabilities it shows, named in its corner tag.
SHOTS = {
    'hook-1': ['kinetic-typography'], 'hook-2': ['kinetic-typography'], 'hook-3': ['kinetic-typography'],
    'title': ['pop-on-the-beat'],
    'camera': ['shape-morph', 'camera-on-a-screenshot'],
    'redrawn': ['redrawn-product-ui', 'eased-entrances'],
    'lumi': ['character-motion', 'staggered-reveals', 'springs-with-character'],
    'voice': ['footage-with-sound', 'word-timed-captions'],
    'diagram': ['drawn-on-diagram'],
    'dashboard': ['overlap-transitions', 'counting-numbers', 'gauges-and-rings', 'bar-charts', 'line-chart-callout'],
    **{n: ['generated-art'] for n in ('gen-arcs', 'gen-flow', 'gen-tiles')},
    **{n: ['orbit-3d', 'image-treatments'] for n in ('orbit-type', 'orbit-device', 'orbit-bleed')},
    **{n: ['hard-light-sweep'] for n in ('light-wide', 'light-close')},
    **{n: ['comic-halftone'] for n in ('comic-hq', 'comic-close', 'comic-launch')},
    **{n: ['pixel-art-layer'] for n in ('pixel-run', 'pixel-clear')},
    **{n: ['paper-collage'] for n in ('paper-head', 'paper-pad', 'paper-stamp')},
    **{f'beat-{i + 1}': ['beat-lock'] for i in range(4)},
    'every-format': ['every-format'],
    'end': ['seamless-loops'],
}
# Shorter names where a shot's tag would otherwise run past one line in 16:9.
SHORT = {'overlap-transitions': 'Overlap slide', 'counting-numbers': 'Counting numbers',
         'gauges-and-rings': 'Gauges', 'line-chart-callout': 'Line chart + callout',
         'springs-with-character': 'Springs', 'image-treatments': 'Image treatments'}
TAGS = {seg: [SHORT.get(cap, capabilities.get(cap)['title']) for cap in caps] for seg, caps in SHOTS.items()}

LOOP = True  # the end card comes to rest on the opening's first frame


# ---- music: the skill's make_track.py bed, retuned to the sections ----
# A thin hook building into the title hit; the full bed through the product
# and the numbers, then a second build into the looks, which go half-time to
# breathe; a hit on the paper rip into the closing block; a crash on the end card.
RATE = 48000


def _beat(name):
    return TIMELINE.find(name).at


def _music():
    marks = {k: _beat(k) for k in ('styles', 'closing', 'end')}
    args = dict(bpm=GRID.bpm, beats=int(END), hook=HOOK, v=4, **marks)
    key = hashlib.sha1(repr(sorted(args.items())).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-showcase-{key}.wav')
    if os.path.exists(path):
        return path
    sys.path.insert(0, str(HERE.parent / 'skill' / 'make-a-video' / 'scripts'))
    from make_track import synth
    spb = 60 / GRID.bpm
    styles, closing, end = marks['styles'], marks['closing'], marks['end']
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

    def build(at, beats, gain=1.0):
        """A snare roll that doubles up into beat `at`, over a rising noise wash."""
        start = at - beats
        for k in range(2 * start, 2 * at):   # eighths, then sixteenths for the last two beats
            step = 2 if k < 2 * (at - 2) else 4
            for j in range(step // 2):
                t = (k + j * 2 / step) * spb / 2
                add(t, 0.12, snare(gain * (0.18 + 0.32 * (t / spb - start) / beats)))
        rise = beats * spb
        add(start * spb, rise, lambda x, k: gain * 0.22 * (x / rise) ** 2 * noise[(k * 7) % len(noise)])

    def boom(at, crash=0.4, sub=0.5, length=2.2):
        """A hit: a sub drop and a long crash."""
        add(at * spb, 1.6, lambda x, k: sub * math.sin(2 * math.pi * (38 + 60 * math.exp(-x * 12)) * x)
            * math.exp(-x * 2.6))
        add(at * spb, length, lambda x, k: crash * noise[k % len(noise)] * math.exp(-x * 2.2))

    build(HOOK, HOOK - 2)
    boom(HOOK)
    # Punch: a snare on beats 2 and 4 of every bar, except in the looks, which go
    # half-time (a snare on 3 only) to breathe.
    for k in range(HOOK + 1, int(END)):
        if styles - 4 <= k < styles:
            continue   # the build has the snares here
        in_styles = styles <= k < closing
        if (in_styles and (k - styles) % 4 == 2) or (not in_styles and (k - HOOK) % 2 == 1):
            add(k * spb, 0.2, snare(0.42))
    build(styles, 4, 0.9)
    boom(styles, crash=0.36)
    # The rip: a tearing noise sweep into a hit on the downbeat of the closing block.
    add((closing - 0.5) * spb, 0.5 * spb,
        lambda x, k: 0.3 * (x / (0.5 * spb)) ** 1.5 * noise[(k * 3) % len(noise)] * (0.6 + 0.4 * math.sin(x * 900)))
    boom(closing, crash=0.42, sub=0.55)
    add(end * spb, 1.8, lambda x, k: 0.26 * noise[k % len(noise)] * math.exp(-x * 2.6))
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


# ---- the title: the hit, then the logo pops on each beat ----
def title_layout(st):
    """The logo's centre and radius, and where the wordmark and subtitle go."""
    word_f = kit.font(kit.pick(st, 168, 150), 850, tracking=-0.035)
    ww = vb.text.measure('Lumen', word_f)
    lh = vb.text.line_height(word_f)
    r = kit.pick(st, 74, 80)
    sub_f = kit.font(kit.pick(st, 38, 36), 500)
    sub_lines, (sw, sh) = kit.lines_of(SUBTITLE, sub_f, kit.pick(st, 900, 520))
    if st.wide:
        total = 2 * r + 36 + ww
        x0 = st.content.cx - total / 2
        cy = st.content.cy - 40
        return dict(logo=(x0 + r, cy, r), word=(x0 + 2 * r + 36, cy - lh / 2), sub=(sub_f, sub_lines, sw, sh, cy + lh / 2 + 28))
    block = 2 * r + 30 + lh + 30 + sh
    top = st.content.cy - block / 2
    wy = top + 2 * r + 30
    return dict(logo=(st.content.cx, top + r, r), word=(st.content.cx - ww / 2, wy), sub=(sub_f, sub_lines, sw, sh, wy + lh + 30))


SUBTITLE = 'One calm plan for your day.'


def title(cv, s, st):
    cv.fill(BG)
    L = title_layout(st)
    lx, ly, r = L['logo']
    hit = kit.prog(s.f, 0, 24)
    kit.glow(cv, st.content.cx, st.content.cy, kit.pick(st, 620, 560) * (0.6 + 0.4 * hit), ACCENT, 0.32 * (1 - 0.5 * hit))
    word_f = kit.font(kit.pick(st, 168, 150), 300 + 550 * kit.prog(s.f, 0, 18), tracking=-0.035)
    p = kit.spring(s.f, -2, kit.BOUNCY)
    # Pop on the beat: a punch and a ripple off the logo on beats 2, 3 and 4.
    beat = min(3, s.f // FPB)
    since = s.f - beat * FPB
    punch = 1 + 0.18 * (1 - vb.spring_at(since + 1, kit.FPS, **vb.damped(0.3, hz=3.2))) if beat else 1
    for k in range(1, beat + 1):
        age = s.f - k * FPB
        if 0 <= age < 22:
            cv.arc(lx, ly, r * 1.1 + age * 7, 0, 2 * math.pi, ACCENT, width=4, alpha=0.55 * (1 - age / 22))
    with kit.scaled(cv, lx, ly, max(0.0, p) * punch):
        kit.logo(cv, lx, ly, r, orb_spin(_frame_n(s)) + 2 * math.pi * (1 - p))
    q = kit.prog(s.f, 0, 12)
    wx, wy = L['word']
    with cv.layer(opacity=q, dy=(1 - q) * 30):
        box = vb.text.draw(cv, 'Lumen', word_f, wx, wy, INK)
    cv.mark('wordmark', *box)
    sub_f, sub_lines, sw, sh, sy = L['sub']
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
          **motion.SCENES, **data.SCENES, **imagery.SCENES, **looks.SCENES, **comic.SCENES, **pixel.SCENES,
          **paper.SCENES, **timing.SCENES, **voice.SCENES}


# ---- transitions between sections: the outgoing shot keeps drawing under the incoming one's first beat ----
PAGE = '#f1f2f4'


def morph_in(cv, out, inc, st):
    """Shape morph: the logo's sun grows into the screenshot's window."""
    t = kit.SMOOTH(vb.clamp01(inc.f / FPB))
    with cv.layer(opacity=1 - vb.clamp01(t * 1.6)):
        title(cv, out, st)
    lx, ly, r = title_layout(st)['logo']
    sun = [(lx + r * 0.42 * math.cos(2 * math.pi * i / 96), ly + r * 0.42 * math.sin(2 * math.pi * i / 96))
           for i in range(96)]
    w = st.content
    window = kit.rounded_points(w.x, w.y, w.w, w.h, 16, per_corner=12)
    shape = paths.morph(sun, window, t, closed=True, n=96)
    paths.draw(cv, shape, kit.mix(ACCENT, PAGE, vb.clamp01(t * 1.4)), fill=True)
    a = vb.clamp01((t - 0.45) / 0.5)
    if a > 0:
        ctx = cv.ctx
        ctx.save()
        kit.poly(ctx, shape)
        ctx.clip()
        with cv.layer(opacity=a):
            imagery.camera(cv, inc, st)
        ctx.restore()


def slide_in(cv, out, inc, st):
    """Overlap slide: the dashboard slides in over the diagram, which dims as it's covered."""
    SCENES[out.name](cv, out, st)
    frame = st.frame
    p = kit.prog(inc.f, 0, FPB, vb.ease_out_quint)
    cv.rect(*frame, (8, 9, 12, 0.55 * p))
    dx, dy = kit.pick(st, ((1 - p) * frame.w, 0), (0, (1 - p) * frame.h))
    with cv.layer(dx=dx, dy=dy):
        cv.shadow(*frame, radius=28, dx=kit.pick(st, -20, 0), dy=kit.pick(st, 0, -20), blur=50, color=(0, 0, 0, 0.6))
        with cv.clip(*frame, radius=28 * (1 - p)):
            data.dashboard(cv, inc, st)


def rip_in(cv, out, inc, st):
    """The paper rip: the wall tears open from the middle onto the next section."""
    SCENES[inc.name](cv, inc, st)
    paper.rip(cv, out, st)


TRANSITIONS = {'camera': morph_in, 'dashboard': slide_in, 'beat-1': rip_in}


def draw(n, cv):
    st = kit.stage(cv)
    live = TIMELINE.live(n)
    front = live[-1]
    if len(live) > 1:
        TRANSITIONS[front.name](cv, live[0], front, st)
    else:
        SCENES[front.name](cv, front, st)
    kit.tag(cv, st, TAGS[front.name], tag_alpha(front))


def tag_alpha(s):
    """The tag is up from a shot's first frame; the opening's comes up after
    the loop's seam, and the end card's goes before it."""
    if s.name == 'hook-1':
        return kit.prog(s.f, 10, 18)
    if s.name == 'end':
        return kit.prog(s.f, 6 * FPB, 6 * FPB + 8) * (1 - kit.prog(s.f, 10 * FPB, 11 * FPB, kit.SMOOTH))
    return 1.0


# Pairs drawn over each other by design (a callout inside its chart, a stamp slammed across the page,
# captions over the bottom of the footage).
OVERLAP_OK = {('chart', 'callout'), ('stamp', 'arrow'), ('stamp', 'notepad'), ('footage', 'caption')}

LAYOUTS = {name: {'safe': kit.SAFE[name]} for name in ('16x9', '9x16')}

FILM = vb.Film(
    draw=draw,
    timeline=TIMELINE,
    formats=(kit.F16, kit.F9),
    background=BG,
    audio=vb.Audio(_music(), fade_out_frames=round(2 * FPB), duck_db=-12),   # the music dips under the tester
    sounds=(vb.footage(TIMELINE, 'voice', start=0.0).sound(voice.CLIP_PATH),),
)

if __name__ == '__main__':
    vb.main(__file__)
