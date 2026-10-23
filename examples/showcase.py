"""The showcase: videobuilder's product film. Everything it can do, in one
quick cut on the beat of a generated music bed: every capability counted and
on a wall, a beat for every family with its demos playing, and then a
launch film for a made-up app, Lumen, cut from the hand-written ones.

    python -m videobuilder preview examples/showcase.py
    python -m videobuilder render examples/showcase.py --format all

Sections: the count rolling up from the wordmark; the wall of every
capability, the camera pulling back until all of them are in frame; one beat
per family, as the /capabilities page files them, each coming in on a wipe
with its size counting up and four of its demos playing; "ask by name, or
describe it"; then Lumen: the title hit, the product (camera, UI, Lumi
checking off the day, a tester on camera, the release in a terminal, a
diagram), the launch numbers on one dashboard, the looks (generated art, 3D,
hard light, one scene in three named looks, comic, pixel art, a cut-out fox,
the fox walking into a hit, a stick figure running into a wall, two named
type styles, paper collage), and the timing and formats block; then the end
card with the gallery's address.

Every count, family and family size, and every tile on the wall, is read
from the capabilities API when the film loads (showcase_scenes/everything.py):
a capability or a family that lands changes the film with no edit to it.

A shot can show several capabilities at once: its tag names them all
(SHOTS), so a viewer can find on the /capabilities page what they just saw.
Three capabilities are properties of the whole film as well as a shot: every
cut is on the beat (beat-lock), it renders in two shapes laid out separately
(every-format), and the end card comes to rest exactly where the opening
starts (seamless-loops).

The shots live in examples/showcase_scenes/; this file holds the timeline,
the transitions, the music, the end card and the tag.
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
from showcase_scenes import art, comic, data, everything, fox, imagery, kit, looks, motion, paper, pixel, stick, terminal, timing, typeset, voice, walk  # noqa: E402
from showcase_scenes.kit import ACCENT, BG, INK, MUTED  # noqa: E402

GRID = kit.GRID
FPB = kit.FPB
TOTAL = everything.TOTAL


def _read_beats(words):
    """Beats a shot needs to read `words` words (1 s plus 3 words a second), to the half beat."""
    return math.ceil(2 * (1 + words / 3) * GRID.bpm / 60) / 2


def _family_beats(beat):
    return max(everything.FAMILY_BEATS, _read_beats(len(beat.family.title.split()))) + (1 if beat.sounding else 0)


# ---- the timeline: beats at 120 bpm, 15 frames each ----
# A section is (name, beats) for a single shot, or (name, [parts]) for a group
# of shots cut on the beat; parts nest the same way. The third item, where
# there is one, is the transition in: beats the section before keeps drawing
# under it (see TRANSITIONS). A fourth is the shot's data (its copy).
SECTIONS = [
    ('open', 4, 0, {'copy': [everything.WORDMARK, str(TOTAL), 'capabilities']}),
    ('wall', 6, 0, {'copy': list(everything.PLAQUE)}),
    *[(b.name, _family_beats(b), 1, {'copy': [b.family.title]}) for b in everything.BEATS],
    ('ask', 7, 0, {'copy': [everything.ASK]}),
    ('title', 4),
    ('product', [('camera', 4), ('redrawn', 4), ('lumi', 8), ('voice', 5), ('terminal', 4), ('diagram', 5)], 1),
    ('dashboard', 7, 1),
    ('styles', [('generated', [('gen-arcs', 3), ('gen-flow', 3)]),
                ('orbit', [('orbit-type', 3), ('orbit-bleed', 3)]),
                ('light-close', 3),
                ('art', [('art-swirl', 2), ('art-woodblock', 2), ('art-pop', 2)]),
                ('comic', [('comic-hq', 3), ('comic-close', 3)]),
                ('pixel', [('pixel-run', 3), ('pixel-clear', 2)]),
                ('fox', 5),
                ('walk', 5),
                ('stick', 5),
                ('typeset', [('type-flap', 4), ('type-rubber', 4)]),
                ('paper', [('paper-head', 3), ('paper-pad', 4), ('paper-stamp', 4)])]),
    ('closing', [('beats', [(f'beat-{i + 1}', 1) for i in range(4)]), ('every-format', 5)], 1),
    ('end', 10),
]


def _segments(parts, at):
    out = []
    for name, body, *more in parts:
        overlap = more[0] if more else 0
        data_ = more[1] if len(more) > 1 else {}
        if isinstance(body, list):
            children = _segments(body, at)
            seg = vb.Segment(name, at, children[-1].until, dict(data_), children=children, overlap=overlap)
        else:
            seg = vb.Segment(name, at, at + body, dict(data_), overlap=overlap)
        out.append(seg)
        at = seg.until
    return out


def _title_hit():
    """The hit on the title, when the sound-effects pack is installed
    (`python -m videobuilder sfx fetch`); without it, the film has none."""
    try:
        return (vb.sfx.sound('pro_impact/short', at=TIMELINE.span('title')[0], fps=GRID.fps, gain_db=-8),)
    except vb.sfx.SfxUnavailable:
        return ()


def _timeline():
    segs = _segments(SECTIONS, 0)
    segs[-1].data = {'copy': list(END_COPY), 'copy_at': 0}
    return vb.Timeline(GRID, segs, end=segs[-1].until)


END_COPY = (everything.WORDMARK, f'See all {TOTAL}: {everything.URL}', 'Sound effects: earshot by Leon Lin (MIT)')
TIMELINE = _timeline()
END = TIMELINE.end
END_CARD = TIMELINE.find('end').until - TIMELINE.find('end').at

# Each shot and the capabilities it shows, named in its tag: every catalog
# capability in some Lumen shot's, and in each family beat the demos it plays
# and the wipe it comes in on.
SHOTS = {
    'open': ['kinetic-typography', 'odometer-roll'],
    'wall': ['optical-zoom', 'center-out-stagger'],
    **{b.name: b.tag for b in everything.BEATS},
    'ask': everything.ASK_TAG,
    'title': ['pop-on-the-beat', 'sound-effects'],
    'camera': ['outline-morph', 'camera-on-a-screenshot'],
    'redrawn': ['redrawn-product-ui', 'eased-entrances'],
    'lumi': ['character-motion', 'staggered-reveals', 'springs-with-character'],
    'voice': ['footage-with-sound', 'word-timed-captions'],
    'terminal': ['terminal-log'],
    'diagram': ['drawn-on-diagram'],
    'dashboard': ['overlap-transitions', 'counting-numbers', 'gauges-and-rings', 'bar-charts', 'line-chart-callout'],
    **{n: ['generated-art'] for n in ('gen-arcs', 'gen-flow')},
    **{n: ['orbit-3d', 'image-treatments'] for n in ('orbit-type', 'orbit-bleed')},
    'light-close': ['hard-light-sweep'],
    **{n: ['looks'] for n in ('art-swirl', 'art-woodblock', 'art-pop')},
    **{n: ['look-filter-pop-art'] for n in ('comic-hq', 'comic-close')},     # once comic-halftone
    **{n: ['look-filter-pixel'] for n in ('pixel-run', 'pixel-clear')},      # once pixel-art-layer
    'fox': ['puppet-motion', 'pose-swaps', 'narration'],
    'walk': ['walk-in-place', 'parallax-scene', 'impact-frame'],
    'stick': ['stick-figure'],
    **{n: ['paper-collage'] for n in ('paper-head', 'paper-pad', 'paper-stamp')},
    'type-flap': ['type', 'type-split-flap'], 'type-rubber': ['type', 'type-rubber'],
    **{f'beat-{i + 1}': ['beat-lock'] for i in range(4)},
    'every-format': ['every-format'],
    'end': ['seamless-loops'],
}
# Shorter names where a shot's tag would otherwise run past one line in 16:9.
SHORT = {'overlap-transitions': 'Overlap slide', 'counting-numbers': 'Counting numbers',
         'gauges-and-rings': 'Gauges', 'line-chart-callout': 'Line chart + callout',
         'springs-with-character': 'Springs', 'image-treatments': 'Image treatments'}
TAGS = {seg: [SHORT.get(cap, everything.NAMES[cap]) for cap in caps] for seg, caps in SHOTS.items()}

LOOP = True  # the end card comes to rest on the opening's first frame


# ---- music: the skill's make_track.py bed, retuned to the sections ----
# A thin opening building into the wall; the full bed under the families;
# thin again under the ask, building into Lumen's title hit; the full bed
# through the product and the numbers, then a build into the looks, which go
# half-time to breathe; a hit on the paper rip into the closing block; a
# crash on the end card.
RATE = 48000


def _beat(name):
    return TIMELINE.find(name).at


def _music():
    marks = {k: _beat(k) for k in ('wall', 'ask', 'title', 'styles', 'closing', 'end')}
    args = dict(bpm=GRID.bpm, beats=END, v=5, **marks)
    key = hashlib.sha1(repr(sorted(args.items())).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-showcase-{key}.wav')
    if os.path.exists(path):
        return path
    sys.path.insert(0, str(HERE.parent / 'skill' / 'make-a-video' / 'scripts'))
    from make_track import synth
    spb = 60 / GRID.bpm
    wall_, ask_, title_ = marks['wall'], marks['ask'], marks['title']
    styles, closing, end = marks['styles'], marks['closing'], marks['end']
    beats = math.ceil(END)
    full = synth(GRID.bpm, beats, rate=RATE, loop='minor', tail=1.0)
    thin = synth(GRID.bpm, beats, rate=RATE, loop='minor', voices=('kick', 'pad'), tail=1.0)
    n = len(full)
    thin_spans = [(0, int(wall_ * spb * RATE)), (int(ask_ * spb * RATE), int(title_ * spb * RATE))]
    out = [(thin[i] if any(a <= i < b for a, b in thin_spans) else full[i]) / 32767 for i in range(n)]
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
        for k in range(int(2 * start), int(2 * at)):   # eighths, then sixteenths for the last two beats
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

    build(wall_, wall_ - 1)
    boom(wall_)
    # Punch: a snare on beats 2 and 4 of every bar where the bed is full, except
    # in the looks, which go half-time (a snare on 3 only) to breathe.
    for k in range(int(wall_) + 1, beats):
        if ask_ <= k < title_ or styles - 4 <= k < styles:
            continue   # thin under the ask; the build has the snares before the looks
        in_styles = styles <= k < closing
        if (in_styles and (k - styles) % 4 == 2) or (not in_styles and (k - wall_) % 2 == 1):
            add(k * spb, 0.2, snare(0.42))
    build(title_, 3, 0.8)
    boom(title_, crash=0.38)
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
    data_ = array.array('h', (int(v / peak * 0.9 * 32767) for v in out))
    tmp = f'{path}.{os.getpid()}.tmp'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data_.tobytes())
    os.replace(tmp, path)
    return path


# ---- the Lumen logo's moon turns with the film ----
ORBIT = 75  # frames per turn of the logo's moon


def orb_spin(n):
    return 2 * math.pi * (n % ORBIT) / ORBIT


def _frame_n(s):
    return TIMELINE.start(s.segment) + s.f


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


# ---- the end card: the gallery's address, then the wordmark comes to rest where the opening starts ----
def end(cv, s, st):
    f = s.f
    cv.fill(BG)
    leave = kit.prog(f, s.length - 2 * FPB - 6, s.length - FPB, kit.SMOOTH)   # copy goes, the wordmark glides home
    land = kit.prog(f, s.length - 2 * FPB, s.length - 6, kit.SMOOTH)
    everything.far_wall(cv, st, _frame_n(s), 0.2 * kit.prog(f, 0, 12) * (1 - land))
    word, url, credit = END_COPY
    c = st.content
    rest = everything.wordmark_rest(st)
    big = rest.scaled(1.25)
    url_f = everything.fit(url, 800, kit.pick(st, 50, 44), 24, c.w - 60, tracking=-0.01)
    if vb.text.measure(url, url_f) > c.w - 60:
        url_f = everything.fit(url, 800, 40, 20, c.w - 60, tracking=-0.01)
    ub_w = vb.text.measure(url, url_f) + 60
    ub_h = vb.text.line_height(url_f) + 36
    block = big.h + 40 + ub_h
    top = c.cy - block / 2
    home = vb.Box(c.cx - big.w / 2, top, big.w, big.h)
    p = kit.spring(f, -3)
    wb = vb.Box(kit.lerp(home.x, rest.x, land), kit.lerp(home.y, rest.y, land), kit.lerp(home.w, rest.w, land),
                kit.lerp(home.h, rest.h, land))
    everything.wordmark(cv, st, wb, alpha=min(1.0, max(0.0, p)) if land == 0 else 1.0)
    a = kit.prog(f, FPB, FPB + 12)
    ub = vb.Box(c.cx - ub_w / 2, home.bottom + 40, ub_w, ub_h)
    if a * (1 - leave) > 0.003:
        with cv.layer(opacity=a * (1 - leave), dy=(1 - a) * 24):
            cv.rect(*ub, everything.SUN, radius=ub_h / 2)
            vb.text.draw(cv, url, url_f, ub.x + 30, ub.y + 18, BG)
        cv.mark('url', *ub)
    cf = everything.fit(credit, 600, kit.pick(st, 26, 24), 16, c.w)
    cw = vb.text.measure(credit, cf)
    b = kit.prog(f, 3 * FPB, 3 * FPB + 12)
    if b * (1 - leave) > 0.003:
        cy = c.bottom - vb.text.line_height(cf)
        with cv.layer(opacity=b * (1 - leave)):
            vb.text.draw(cv, credit, cf, c.cx - cw / 2, cy, MUTED)
        cv.mark('credit', c.cx - cw / 2, cy, cw, vb.text.line_height(cf))


SCENES = {'title': title, 'end': end, **everything.SCENES,
          **motion.SCENES, **data.SCENES, **imagery.SCENES, **looks.SCENES, **art.SCENES, **comic.SCENES, **pixel.SCENES, **fox.SCENES, **walk.SCENES, **stick.SCENES,
          **paper.SCENES, **typeset.SCENES, **timing.SCENES, **voice.SCENES, **terminal.SCENES}


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


def wipe_in(cv, out, inc, st):
    """A family beat comes in on a wipe (a capability of the Transitions family, named in its tag)."""
    _, fn = everything.BEAT[inc.name].wipe
    fn(cv, lambda c: SCENES[out.name](c, out, st), lambda c: SCENES[inc.name](c, inc, st), vb.clamp01((inc.f + 1) / FPB))


TRANSITIONS = {'camera': morph_in, 'dashboard': slide_in, 'beat-1': rip_in,
               **{b.name: wipe_in for b in everything.BEATS if b.wipe}}


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
    if s.name == 'open':
        return kit.prog(s.f, 10, 18)
    if s.name == 'end':
        return kit.prog(s.f, 4 * FPB, 4 * FPB + 8) * (1 - kit.prog(s.f, s.length - 2 * FPB - 6, s.length - FPB, kit.SMOOTH))
    return 1.0


# Pairs drawn over each other by design (a callout inside its chart, a stamp slammed across the page,
# captions over the bottom of the footage).
OVERLAP_OK = {('chart', 'callout'), ('stamp', 'arrow'), ('stamp', 'notepad'), ('footage', 'caption')}

LAYOUTS = {name: {'safe': kit.SAFE[name]} for name in ('16x9', '9x16')}


def _sounds():
    out = [vb.footage(TIMELINE, 'voice', start=0.0).sound(voice.CLIP_PATH),
           fox.VOICE.sound(at=TIMELINE.span('fox')[0], fps=GRID.fps)]
    for b in everything.BEATS:
        out += everything.family_sounds(b, TIMELINE.span(b.name)[0])
    return tuple(out) + _title_hit()


def use_clips(directory):
    """Tile the wall with the posters `capabilities build` wrote to `directory`."""
    everything.use_clips(directory)


# The poster: the wall, every capability in frame, under its plaque.
POSTER = TIMELINE.start('wall') + 5 * FPB

FILM = vb.Film(
    draw=draw,
    timeline=TIMELINE,
    formats=(kit.F16, kit.F9),
    background=BG,
    audio=vb.Audio(_music(), fade_out_frames=round(2 * FPB), duck_db=-12),   # the music dips under the voices
    sounds=_sounds(),
)

if __name__ == '__main__':
    vb.main(__file__)
