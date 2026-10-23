"""Everything videobuilder can do, read from the capabilities API when the
film loads: the count, the wall of every capability, one beat per family
with a few of its demos playing, and "ask by name, or describe it". No
count, family or family size here is written by hand: a capability or a
family that lands changes these shots with no edit to them.

The families are the registry's (videobuilder/capabilities/<family>/), in
the order the /capabilities page files them: category by category, as the
catalog lists its categories. The hand-written catalog capabilities are the
Lumen film's own shots, so they count here and tile the wall but get no
family beat of their own.

The wall is one picture per format, built once: each tile is the poster
`capabilities build` has just written beside the clips (`use_clips`, which
`build_showcase` calls, or $VIDEOBUILDER_CAPABILITIES_DIR), decoded small. A
capability with no poster gets a plain tile in its family's colour, so the
film renders anywhere. The clips that play (the wall's middle, the family
and ask beats) are the demos themselves, drawn live at the size they are
seen (`play`): they need no files, and no video is decoded.
"""
import hashlib
import inspect
import math
import os
import random
from dataclasses import dataclass

from PIL import Image as PILImage
from PIL import ImageDraw, ImageOps

import videobuilder as vb
from videobuilder import Box, capabilities, text
from videobuilder.capabilities import registry, schema
from videobuilder.capabilities.typography.odometer_roll import draw_odometer

from . import kit
from .kit import BG, CARD, CARD_HI, FPB, INK, LINE, MUTED, TEAL

SUN, LILAC, SKY = '#f2b84b', '#a593ff', '#6fb5ff'
ACCENTS = (kit.ACCENT, TEAL, SUN, LILAC, SKY)
URL = 'mgalgs.io/videobuilder'
WORDMARK = 'videobuilder'

# ---- what there is ----
CATALOG = capabilities.entries()   # the hand-written capabilities, families' members included
REGISTRY = registry.catalog()      # the one-file capabilities
TOTAL = len(CATALOG) + len(REGISTRY)
NAMES = {**{t.id: t.name for t in REGISTRY}, **{e['id']: e['title'] for e in CATALOG}}
_BY_ID = {t.id: t for t in REGISTRY}


@dataclass(frozen=True)
class Family:
    slug: str
    title: str
    category: str
    members: tuple


def _families():
    """The registry's families as the /capabilities page files them: the
    catalog's categories in order, each category's families in registry order."""
    cats = list(capabilities.categories())

    def where(slug):
        cat = capabilities.FAMILY_CATEGORY.get(slug)
        return cats.index(cat) if cat in cats else len(cats)

    out = []
    for slug in sorted(schema.FAMILIES, key=where):
        members = tuple(t for t in REGISTRY if t.family == slug)
        if members:
            title = capabilities.REGISTRY_FAMILIES.get(slug, (slug.capitalize(),))[0]
            out.append(Family(slug, title, capabilities.FAMILY_CATEGORY.get(slug, ''), members))
    return tuple(out)


FAMILIES = _families()

# Demos that read well small and draw fast, picked first where a family has
# them; a family with none of these (a new one, say) picks its own, one
# group at a time. The film never depends on any of them being there.
FAVOURITES = (
    'fireworks', 'mandelbrot-zoom', 'phyllotaxis', 'cyclic-cellular-automaton', 'like-heart-burst',
    'coverflow-carousel', 'progress-ring', 'toggle-switch-slide', 'neon-flicker', 'liquid-melt',
    'split-flap-display', 'odometer-roll', 'bar-chart-race', 'globe-spin', 'breaking-news-banner-slam',
    'sunburst-build', 'walk-cycle', 'squash-and-stretch', 'radial-stagger', 'pendulum-swing', 'x-ray',
    'halation', 'synthwave-sun', 'chromatic-dispersion', 'pixel-build', 'bauhaus-geometric-shuffle',
    'spiral-bloom', 'hexagon-tile-reveal', 'smash-cut', 'cube-rotate', 'drip-wipe', 'shatter', 'fly-through',
    'voxel-build', 'drone-flyover', 'thin-film-iridescence', 'impact-hit', 'whoosh', 'success-chime',
    'sub-drop', 'star-rating-fill', 'gauge-needle-sweep', 'angled-lower-third', 'long-shadow-growth',
    'swirl', 'color-cycling', 'ink-bleed', 'halftone',
)
# The wipes the family beats come in on, in this order where they exist;
# then any other capability in the Transitions family's Wipes group.
WIPES_FIRST = ('iris-wipe', 'checkerboard-wipe', 'clock-wipe', 'diagonal-wipe', 'star-wipe', 'barn-door-wipe',
               'venetian-blinds-wipe', 'box-wipe', 'diamond-wipe', 'zigzag-wipe')

_FILMS = {}


def demo(id):
    """The demo film of registry capability `id`, built once; None when it
    can't be built here (a sound demo without the sound-effects pack)."""
    if id not in _FILMS:
        try:
            _FILMS[id] = _BY_ID[id].demo()
        except vb.sfx.SfxUnavailable:
            _FILMS[id] = None
    return _FILMS[id]


def tag_fits(names):
    """Whether a tag naming `names` fits the room kept for it in both formats."""
    return all(len(kit.tag_lines(names, kit.SAFE[f][2] - 2 * kit.TAG_PAD[0])) <= kit.TAG_LINES[f]
               for f in kit.SAFE)


def _candidates(members):
    """`members`, favourites first, then one from each group in turn."""
    first = [_BY_ID[i] for i in FAVOURITES if i in _BY_ID and _BY_ID[i] in members]
    groups = {}
    for t in members:
        groups.setdefault(t.group, []).append(t)
    rest, queues = [], sorted(groups.values(), key=len, reverse=True)
    while any(queues):
        for q in queues:
            if q:
                rest.append(q.pop(0))
    return first + [t for t in rest if t not in first]


def pick(members, k, also=()):
    """Up to `k` of `members` whose demos build, their names and `also` fitting one tag."""
    out = []
    for t in _candidates(members):
        if len(out) == k:
            break
        if demo(t.id) is not None and tag_fits([x.name for x in out] + [t.name] + list(also)):
            out.append(t)
    return out


def _wipes():
    """(id, function) for every wipe there is: WIPES_FIRST, then the rest."""
    trans = [t for t in REGISTRY if t.family == 'transitions' and t.group == 'Wipes']
    order = [_BY_ID[i] for i in WIPES_FIRST if i in _BY_ID] + [t for t in trans if t.id not in WIPES_FIRST]
    out = []
    for t in order:
        fn = t.resolve_api()[0]
        if callable(fn) and list(inspect.signature(fn).parameters)[:4] == ['cv', 'a', 'b', 'p']:
            out.append((t.id, fn))
    return out


WIPES = _wipes()


# ---- the beats: one per family, then the ask ----
FAMILY_BEATS = 4   # one of them under the wipe in; a family whose clips sound gets one more, a beat per sound


@dataclass(frozen=True)
class Beat:
    """One family's beat: its family, the clips it plays, the wipe it comes in on."""
    name: str
    family: Family
    index: int
    clips: tuple
    wipe: tuple
    sounding: bool

    @property
    def beats(self):
        return FAMILY_BEATS + (1 if self.sounding else 0)

    @property
    def tag(self):
        return [t.id for t in self.clips] + ([self.wipe[0]] if self.wipe else [])


def _beats():
    out = []
    for k, fam in enumerate(FAMILIES):
        wipe = WIPES[k % len(WIPES)] if WIPES else None
        also = [NAMES[wipe[0]]] if wipe else []
        clips = tuple(pick(fam.members, 4, also))
        sounding = bool(clips) and all(demo(t.id).sounds for t in clips)
        if sounding:   # heard one at a time, a beat each: three of them
            clips = tuple(pick(fam.members, 3, also))
        out.append(Beat(f'fam-{fam.slug}', fam, k, clips, wipe, sounding))
    return tuple(out)


BEATS = _beats()
BEAT = {b.name: b for b in BEATS}

# The ask: a note typed in plain words and the capability it finds, then a search by name.
NOTE = 'make the total roll up like an old car meter'
NOTE_FINDS = 'odometer-roll'
SEARCH = 'wipe'


def _search(word):
    """[(family title, [ids])] for every capability whose name has `word`,
    biggest family first: the registry by family, the catalog by category."""
    hits = {}
    for t in REGISTRY:
        if word in t.name.lower():
            hits.setdefault(capabilities.REGISTRY_FAMILIES.get(t.family, (t.family,))[0], []).append(t.id)
    for e in CATALOG:
        if word in e['title'].lower():
            hits.setdefault(e['category'], []).append(e['id'])
    return sorted(hits.items(), key=lambda kv: -len(kv[1]))


SEARCH_ROWS = _search(SEARCH)
_open = SEARCH_ROWS[0][1] if SEARCH_ROWS else []
SEARCH_CLIPS = [t.id for t in pick([_BY_ID[i] for i in _open if i in _BY_ID], 3,
                                   also=[NAMES[NOTE_FINDS]] if NOTE_FINDS in _BY_ID else [])]
ASK_TAG = ([NOTE_FINDS] if NOTE_FINDS in _BY_ID else []) + SEARCH_CLIPS


# ---- drawing helpers ----
EASE_IO = vb.ease_in_out_quart


def fit(copy, weight, hi, lo, width, mono=False, **kw):
    """The biggest font from `hi` down to `lo` that sets `copy` on one line in `width`."""
    make = kit.mono if mono else kit.font
    for size in range(hi, lo - 1, -2):
        f = make(size, weight, **kw)
        if text.measure(copy, f) <= width:
            return f
    return make(lo, weight, **kw)


def appear(f, delay=0):
    return kit.spring(f, delay, kit.BOUNCY)


def chip(cv, label, x, bottom, size=18):
    """A capability's name on a dark pill, its foot at `bottom`."""
    f = kit.font(size, 700)
    w, h = text.measure(label, f) + 2 * size * 0.6, text.line_height(f) + size * 0.5
    cv.rect(x, bottom - h, w, h, BG, radius=h / 2, alpha=0.82)
    text.draw(cv, label, f, x + size * 0.6, bottom - h + size * 0.25, INK)


def play(cv, id, box, n, radius=12, alpha=1.0, outline=LINE):
    """Registry capability `id`'s demo at its frame `n` (looping), drawn live into `box`."""
    film = demo(id)
    if film is None:
        return
    fmt = film.formats[0]
    k = box.w * cv.scale_factor() / fmt.width
    if k * fmt.width < 4:
        return
    sub = film.frame(int(n) % film.frames, fmt, scale=k)
    surf = sub.surface
    surf.flush()
    ctx = cv.ctx
    with cv.layer(opacity=alpha):
        with cv.clip(*box, radius=radius):
            ctx.save()
            ctx.translate(box.x, box.y)
            ctx.scale(box.w / surf.get_width(), box.h / surf.get_height())
            ctx.set_source_surface(surf, 0, 0)
            ctx.paint()
            ctx.restore()
        if outline:
            cv.outline(*box, outline, width=2, radius=radius)


def tile(cv, id, box, n, label=True, radius=12, alpha=1.0, size=18, outline=LINE):
    play(cv, id, box, n, radius, alpha, outline)
    if label and alpha > 0.05:
        with cv.layer(opacity=alpha):
            chip(cv, NAMES[id], box.x + size * 0.6, box.bottom - size * 0.6, size)


# ---- the wall: every capability, a tile each ----
TW, TH, GAP = 80, 45, 6           # a tile in the wall picture, and the gap around it
PW, PH = TW + GAP, TH + GAP       # its pitch
HERO = {'16x9': (6, 6), '9x16': (4, 12)}   # the block in the middle that plays live, filling the frame at first
CLIPS = os.environ.get('VIDEOBUILDER_CAPABILITIES_DIR')
_WALLS = {}


def use_clips(directory):
    """Tile the wall with the posters in `directory` (a `capabilities build`
    output), building both formats' walls now, before any render forks."""
    global CLIPS
    CLIPS = directory
    _WALLS.clear()
    for name in HERO:
        wall(name)


def _colour(id):
    """A capability's tile colour: its family's, or its catalog category's."""
    t = _BY_ID.get(id)
    keys = [f.slug for f in FAMILIES] + list(capabilities.categories())
    key = t.family if t else capabilities.get(id)['category']
    return ACCENTS[keys.index(key) % len(ACCENTS)] if key in keys else MUTED


def _plain(id, w, h):
    """A tile for a capability with no poster: a card in its colour with a mark on it."""
    rnd = random.Random(hashlib.sha1(id.encode()).digest())
    base = kit.mix(CARD_HI, _colour(id), 0.28)
    im = PILImage.new('RGB', (w, h), tuple(int(c) for c in base))
    d = ImageDraw.Draw(im)
    hi = tuple(int(c) for c in kit.mix(_colour(id), INK, 0.2))
    r = h * rnd.uniform(0.16, 0.3)
    cx, cy = w * rnd.uniform(0.25, 0.75), h * rnd.uniform(0.35, 0.65)
    if rnd.random() < 0.5:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hi)
    else:
        d.rounded_rectangle((cx - 1.6 * r, cy - r * 0.7, cx + 1.6 * r, cy + r * 0.7), radius=r * 0.3, fill=hi)
    return im


def _poster(id, w, h):
    """`id`'s poster from the clips directory at w x h, or None."""
    path = os.path.join(CLIPS, f'{id}.jpg') if CLIPS else None
    if not path or not os.path.exists(path):
        return None
    im = PILImage.open(path)
    im.draft('RGB', (w * 2, h * 2))   # a JPEG decodes straight to near the size it's needed
    return ImageOps.fit(im.convert('RGB'), (w, h), PILImage.BILINEAR)


def wall(fmt):
    """The wall for format `fmt` ('16x9' or '9x16'): {'cols', 'rows', 'hero':
    (c0, r0, hc, hr), 'cells': [id or None, row by row], 'image', 'w', 'h'}."""
    if fmt in _WALLS:
        return _WALLS[fmt]
    W, H = (kit.F16 if fmt == '16x9' else kit.F9).width, (kit.F16 if fmt == '16x9' else kit.F9).height
    hc, hr = HERO[fmt]
    cols = max(hc, round(math.sqrt(TOTAL * (W / H) * PH / PW)))
    rows = max(hr, math.ceil(TOTAL / cols))
    c0, r0 = (cols - hc) // 2, (rows - hr) // 2
    live = [i for i in FAVOURITES if i in _BY_ID and demo(i) is not None][:hc * hr]
    rest = [e['id'] for e in CATALOG] + [t.id for t in REGISTRY if t.id not in live]
    random.Random(979).shuffle(rest)
    cells, k, h = [], 0, 0
    in_hero = [(c0 <= c < c0 + hc and r0 <= r < r0 + hr) for r in range(rows) for c in range(cols)]
    hero_cells = sum(in_hero)
    ids = live + rest[:hero_cells - len(live)] if len(live) < hero_cells else live
    rest = [i for i in rest if i not in ids]
    for inside in in_hero:
        if inside:
            cells.append(ids[h] if h < len(ids) else None)
            h += 1
        else:
            cells.append(rest[k] if k < len(rest) else None)
            k += 1
    im = PILImage.new('RGB', (cols * PW, rows * PH), BG)
    mask = PILImage.new('L', (TW, TH), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, TW - 1, TH - 1), radius=6, fill=255)
    for i, cid in enumerate(cells):
        if cid is None:
            continue
        r, c = divmod(i, cols)
        im.paste(_poster(cid, TW, TH) or _plain(cid, TW, TH), (c * PW + GAP // 2, r * PH + GAP // 2), mask)
    out = _WALLS[fmt] = dict(cols=cols, rows=rows, hero=(c0, r0, hc, hr), cells=cells, live=set(live),
                             image=vb.Image.from_pil(im), w=cols * PW, h=rows * PH)
    return out


def mosaic(cv, st, cx, cy, s, alpha=1.0):
    """The wall, its point (cx, cy) at the frame's centre, `s` canvas px per wall px.
    Returns where the wall's top left lands."""
    W = wall(st.name)
    fr = st.frame
    x, y = fr.cx - cx * s, fr.cy - cy * s
    if alpha > 0.003:
        with cv.layer(opacity=alpha), cv.clip(*fr):
            cv.image(W['image'], x, y, W['w'] * s, W['h'] * s)
    return x, y


def far_wall(cv, st, n, alpha):
    """The whole wall far behind and dim, drifting: the opening's and the end card's ground."""
    W = wall(st.name)
    s = min(st.frame.w / W['w'], st.frame.h / W['h']) * 1.5
    mosaic(cv, st, W['w'] * (0.5 + 0.04 * math.sin(n / 90)), W['h'] * 0.5, s, alpha)


# ---- the opening: the wordmark leaves its resting place, the count rolls up ----
def wordmark_font(st):
    return kit.font(kit.pick(st, 96, 84), 850, tracking=-0.035)


def wordmark_rest(st):
    """The wordmark alone, centred: where the film starts and the end card comes to rest."""
    f = wordmark_font(st)
    w, h = text.measure(WORDMARK, f), text.line_height(f)
    return Box(st.content.cx - w / 2, st.content.cy - h / 2, w, h)


def wordmark(cv, st, box, alpha=1.0):
    """The wordmark drawn into `box` (the resting box, moved and scaled)."""
    rest = wordmark_rest(st)
    s = box.w / rest.w
    with cv.layer(opacity=alpha, dx=box.x - rest.x * s, dy=box.y - rest.y * s, scale=s):
        text.draw(cv, WORDMARK, wordmark_font(st), rest.x, rest.y, INK)
        cv.mark('wordmark', *rest)


def _open_layout(st):
    c = st.content
    places = len(str(TOTAL))
    cw = min(kit.pick(st, 150, 140), (c.w - (places - 1) * 16) / places)
    ch = cw * 1.32
    odo_w = places * cw + (places - 1) * 16
    kick = wordmark_rest(st).scaled(0.6)
    tail_f = kit.font(kit.pick(st, 88, 84), 850, tracking=-0.02)
    tail_h = text.line_height(tail_f)
    block = kick.h + 28 + ch + 28 + tail_h
    top = c.cy - block / 2
    kick = Box(c.cx - kick.w / 2, top, kick.w, kick.h)
    odo = Box(c.cx - odo_w / 2, kick.bottom + 28, odo_w, ch)
    return kick, odo, (cw, ch), tail_f, odo.bottom + 28


def opening(cv, s, st):
    f = s.f
    cv.fill(BG)
    far_wall(cv, st, s.f, 0.16 * kit.prog(f, 6, 30, kit.SMOOTH))
    kick, odo, cell, tail_f, tail_y = _open_layout(st)
    rest = wordmark_rest(st)
    p = kit.prog(f, 4, 18, kit.SMOOTH)
    wordmark(cv, st, Box(kit.lerp(rest.x, kick.x, p), kit.lerp(rest.y, kick.y, p), kit.lerp(rest.w, kick.w, p),
                         kit.lerp(rest.h, kick.h, p)))
    # The count, on an odometer: every capability there is, rolled up from zero.
    e = appear(f, 10)
    if e > 0.01:
        value = TOTAL * EASE_IO(vb.clamp01((f - 14) / 34))
        digits = kit.mono(cell[1] * 0.72, 700)
        with cv.layer(opacity=vb.clamp01(e), dy=(1 - min(1, e)) * 50):
            box = draw_odometer(cv, value, len(str(TOTAL)), digits, odo.x, odo.y, INK, cell=cell, face=CARD_HI,
                                gap=16)
        cv.mark('odometer', *box)
    # "capabilities", in kinetic type: each letter drops in on a spring as the count lands.
    word = 'capabilities'
    tw = text.measure(word, tail_f)
    x0 = st.content.cx - tw / 2
    lh = text.line_height(tail_f)
    shown = False
    for i, ch in enumerate(word):
        q = kit.spring(f, 44 + i * 1.2, kit.BOUNCY)
        if q <= 0.01:
            continue
        shown = True
        x, w = x0 + (text.measure(word[:i], tail_f) if i else 0), text.measure(ch, tail_f)
        with kit.scaled(cv, x + w / 2, tail_y + lh, min(1.0, q) ** 0.5), \
                cv.layer(opacity=vb.clamp01(q), dy=(1 - q) * -40):
            text.draw(cv, ch, tail_f, x, tail_y, kit.ACCENT)
    if shown:
        cv.mark('tail', st.content.cx - tw / 2, tail_y, tw, lh)


# ---- the wall: the camera pulls back from the middle until every tile is in frame ----
PLAQUE = (f'{TOTAL} capabilities', 'One short demo each')


def wall_scene(cv, s, st):
    f = s.f
    cv.fill(BG)
    W = wall(st.name)
    fr = st.frame
    c0, r0, hc, hr = W['hero']
    hero_c = ((c0 + hc / 2) * PW, (r0 + hr / 2) * PH)
    s0 = fr.w / (hc * PW)
    s1 = min(fr.w / W['w'], fr.h / W['h'])
    z0, z1 = 8, 62
    p = EASE_IO(vb.clamp01((f - z0) / (z1 - z0)))
    k = vb.log_lerp(s0, s1, p) * (1 + 0.03 * vb.clamp01((f - z1) / 30))
    cx, cy = kit.lerp(hero_c[0], W['w'] / 2, p), kit.lerp(hero_c[1], W['h'] / 2, p)
    x, y = mosaic(cv, st, cx, cy, k, alpha=EASE_IO(vb.clamp01(p / 0.4)))
    # The middle plays: a centre-out stagger of live demos, sharp while they're big enough to see.
    tw = TW * k
    live_a = vb.clamp01((tw - 50) / 60)
    if live_a > 0.01:
        for i in range(hc * hr):
            r, c = divmod(i, hc)
            cid = W['cells'][(r0 + r) * W['cols'] + c0 + c]
            if cid not in W['live']:
                continue
            d = math.hypot(c - (hc - 1) / 2, r - (hr - 1) / 2)
            e = vb.clamp01((f + 3 - d * 1.1) / 5)
            if e <= 0:
                continue
            bx = Box(x + ((c0 + c) * PW + GAP / 2) * k, y + ((r0 + r) * PH + GAP / 2) * k, tw, TH * k)
            if bx.right < 0 or bx.x > fr.w or bx.bottom < 0 or bx.y > fr.h:
                continue
            with cv.layer(opacity=e * live_a):
                cv.rect(*bx, BG, radius=6 * k)
                play(cv, cid, bx, 24 + f + 7 * i, radius=6 * k, outline=None)
    # The plaque, once the whole wall is out.
    q = appear(f, z1 - 8)
    if q <= 0.01:
        cv.mark('wall', *st.content)
        return
    head_f = fit(PLAQUE[0], 900, kit.pick(st, 96, 80), 48, st.content.w - 120, tracking=-0.03)
    line_f = fit(PLAQUE[1], 650, kit.pick(st, 44, 40), 28, st.content.w - 120)
    hw, lw = text.measure(PLAQUE[0], head_f), text.measure(PLAQUE[1], line_f)
    hh, lh = text.line_height(head_f), text.line_height(line_f)
    bw, bh = max(hw, lw) + 90, hh + lh + 70
    pb = Box(st.content.cx - bw / 2, st.content.cy - bh / 2, bw, bh)
    with cv.layer(opacity=vb.clamp01(q), dy=(1 - min(1, q)) * 40):
        cv.shadow(*pb, radius=28, dy=12, blur=44, color=(0, 0, 0, 0.6))
        cv.rect(*pb, BG, radius=28, alpha=0.94)
        cv.outline(*pb, SUN, width=4, radius=28)
        text.draw(cv, PLAQUE[0], head_f, pb.cx - hw / 2, pb.y + 32, SUN)
        text.draw(cv, PLAQUE[1], line_f, pb.cx - lw / 2, pb.y + 38 + hh, MUTED)
    cv.mark('plaque', *pb)


# ---- one family: where the page files it, its size, its name, four of its demos ----
def _family_layout(st, n):
    """(head box, tile boxes) for `n` 16:9 tiles."""
    c = st.content
    g = 22
    if st.wide:
        head = Box(c.x, c.y, 400, c.h)
        area = Box(head.right + 40, c.y, c.right - head.right - 40, c.h)
    else:
        head = Box(c.x, c.y, c.w, 330)
        area = Box(c.x, head.bottom + 30, c.w, c.bottom - head.bottom - 30)
    cols = 2 if n > 1 else 1
    rows = math.ceil(n / cols)
    tw = min((area.w - g * (cols - 1)) / cols, ((area.h - g * (rows - 1)) / rows) * 16 / 9)
    th = tw * 9 / 16
    x0 = area.x + (area.w - cols * tw - (cols - 1) * g) / 2
    y0 = area.y + (area.h - rows * th - (rows - 1) * g) / 2
    return head, [Box(x0 + (i % cols) * (tw + g), y0 + (i // cols) * (th + g), tw, th) for i in range(n)]


def sound_window(beat, i):
    """(first frame into the beat, frames) clip `i` of a sounding beat is heard for."""
    return FPB * (1 + i), FPB


def sound_from(id):
    """The demo frame clip `id` starts playing from when it's heard: just before its first sound."""
    film = demo(id)
    return max(0, min(s.at for s in film.sounds) - 4) if film.sounds else 20


def family(cv, s, st):
    f = s.f
    beat = BEAT[s.name]
    fam = beat.family
    accent = ACCENTS[beat.index % len(ACCENTS)]
    cv.fill(BG)
    head, slots = _family_layout(st, len(beat.clips))
    # Where the page files it, and which of the families this is.
    kick = f'{fam.category} · {beat.index + 1} of {len(BEATS)}'.upper()
    kf = fit(kick, 700, 24, 15, head.w, mono=True, tracking=0.06)
    e = vb.clamp01(appear(f, 0))
    with cv.layer(opacity=e, dx=(1 - e) * -30):
        box = text.draw(cv, kick, kf, head.x, head.y, accent)
    cv.mark('kicker', *box)
    y = box.bottom + 8
    # The size, counting up; the name under it.
    count = str(len(fam.members))
    cf = kit.font(kit.pick(st, 150, 140), 900, tracking=-0.04)
    shown = str(round(len(fam.members) * kit.prog(f, 2, 16)))
    p = appear(f, 1)
    if p > 0.01:
        with cv.layer(opacity=vb.clamp01(p), dy=(1 - min(1, p)) * 30):
            text.draw(cv, shown, cf, head.x - 6, y, accent)
        cv.mark('count', head.x, y, text.measure(count, cf), text.line_height(cf) * 0.9)
    y += text.line_height(cf) * 0.9
    nf = kit.font(kit.pick(st, 64, 64), 850, tracking=-0.025, line_height=1.02)
    while len(text.wrap(fam.title, nf, head.w)) > 2 and nf.size > 36:
        nf = kit.font(nf.size - 4, 850, tracking=-0.025, line_height=1.02)
    lines = text.wrap(fam.title, nf, head.w, balance=True)
    q = appear(f, 4)
    if q > 0.01:
        with cv.layer(opacity=vb.clamp01(q), dy=(1 - min(1, q)) * 30):
            box = text.draw(cv, lines, nf, head.x, y, INK)
        cv.mark('name', *box)
    # Its demos, playing; in a family that sounds, each lights up while it's heard.
    chip_size = kit.pick(st, 18, 16)
    for i, (t, slot) in enumerate(zip(beat.clips, slots)):
        a = appear(f, 3 + 3 * i)
        if a <= 0.01:
            continue
        n, lit = 20 + f, False
        if beat.sounding:
            w0, wl = sound_window(beat, i)
            n = sound_from(t.id) + max(0, f - w0)
            lit = w0 <= f < w0 + wl
        with cv.layer(opacity=vb.clamp01(a), dy=(1 - min(1, a)) * 40):
            tile(cv, t.id, slot, n, size=chip_size, outline=accent if lit else LINE)
            if lit:
                cv.outline(*slot.pad(-4), accent, width=4, radius=16)
        cv.mark(f'clip-{i}', *slot)


def family_sounds(beat, at):
    """The sounds of a sounding beat's clips, each in its window; `at` is the beat's first frame."""
    out = []
    if not beat.sounding:
        return out
    for i, t in enumerate(beat.clips):
        w0, wl = sound_window(beat, i)
        d0 = sound_from(t.id)
        for snd in demo(t.id).sounds:
            if d0 <= snd.at < d0 + wl:
                out.append(vb.Sound(snd.path, at=at + w0 + snd.at - d0, start=snd.start,
                                    frames=min(snd.frames, wl + 10), gain_db=snd.gain_db - 2,
                                    fade_in_frames=snd.fade_in_frames, fade_out_frames=4, ducks=False))
    return out


# ---- ask by name, or describe it ----
ASK = 'Ask by name, or describe it'
SWAP = 52   # frames in: the note gives way to the search


def _typed(s, f, a, cps):
    return s[:max(0, min(len(s), int((f - a) * cps / kit.FPS)))]


def _caret(cv, x, y, h, f, colour):
    if (f // 8) % 2 == 0:
        cv.rect(x + 2, y + 4, 3, h - 8, colour)


def _panel(cv, box, fill=CARD, radius=22):
    cv.shadow(*box, radius=radius, dy=10, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(*box, fill, radius=radius)
    cv.outline(*box, LINE, width=2, radius=radius)


def ask(cv, s, st):
    f = s.f
    cv.fill(BG)
    c = st.content
    if st.wide:
        col = Box(c.x, c.y, 380, c.h)
        stage = Box(col.right + 40, c.y, c.right - col.right - 40, c.h)
    else:
        col = Box(c.x, c.y, c.w, 150)
        stage = Box(c.x, col.bottom + 20, c.w, c.bottom - col.bottom - 20)
    hf = kit.font(kit.pick(st, 64, 62), 850, tracking=-0.025, line_height=1.04)
    lines = text.wrap(ASK, hf, col.w, balance=True)
    q = appear(f, 0)
    with cv.layer(opacity=vb.clamp01(q), dy=(1 - min(1, q)) * 30):
        box = text.draw(cv, lines, hf, col.x, col.y, INK)
    cv.mark('headline', *box)
    if f < SWAP + 8:
        u = kit.prog(f, SWAP, SWAP + 8, EASE_IO)
        with cv.layer(opacity=1 - u, dx=-60 * u):
            _note(cv, f, stage)
    if f >= SWAP:
        u = appear(f, SWAP + 2)
        with cv.layer(opacity=vb.clamp01(u), dx=(1 - min(1, u)) * 60):
            _search_panel(cv, f - SWAP, stage)
    cv.mark('stage', *stage)


def _note(cv, f, stage):
    nf = kit.font(30, 600)
    lab = kit.mono(20, 700, tracking=0.06)
    width = stage.w - 60
    full = text.wrap(NOTE, nf, width)
    nb = Box(stage.x, stage.y, stage.w, 64 + text.line_height(nf) * len(full) + 24)
    _panel(cv, nb)
    text.draw(cv, 'YOUR NOTE', lab, nb.x + 30, nb.y + 20, MUTED)
    cur = _typed(NOTE, f, 3, 40)
    cl = text.wrap(cur, nf, width) if cur else ['']
    text.draw(cv, cl, nf, nb.x + 30, nb.y + 56, INK)
    if len(cur) < len(NOTE):
        _caret(cv, nb.x + 30 + text.measure(cl[-1], nf), nb.y + 56 + text.line_height(nf) * (len(cl) - 1),
               text.line_height(nf), f, LILAC)
        return
    if NOTE_FINDS not in _BY_ID:
        return
    done = 3 + len(NOTE) * kit.FPS / 40
    q = appear(f, done + 2)
    if q <= 0.01:
        return
    t = _BY_ID[NOTE_FINDS]
    cb = Box(stage.x, nb.bottom + 24, stage.w, min(stage.bottom - nb.bottom - 24, 230))
    with cv.layer(opacity=vb.clamp01(q), dy=(1 - min(1, q)) * 40):
        _panel(cv, cb, CARD_HI)
        cv.outline(*cb, LILAC, width=4, radius=22)
        th = cb.h - 40
        tw = min(th * 16 / 9, cb.w * 0.45)
        th = tw * 9 / 16
        tb = Box(cb.x + 20, cb.cy - th / 2, tw, th)
        play(cv, t.id, tb, 30 + f)
        tx = tb.right + 24
        room = cb.right - tx - 20
        name_f = fit(t.name, 800, 34, 24, room)
        text.draw(cv, t.name, name_f, tx, cb.y + 22, INK)
        df = kit.font(22, 500, line_height=1.25)
        dl = text.wrap(t.definition, df, room)
        fits = max(1, int((cb.bottom - 20 - (cb.y + 30 + text.line_height(name_f))) / text.line_height(df)))
        if len(dl) > fits:
            dl = dl[:fits]
            dl[-1] = dl[-1].rstrip(' ,.;') + '…'
        text.draw(cv, dl, df, tx, cb.y + 30 + text.line_height(name_f), MUTED)


def _search_panel(cv, f, pb):
    _panel(cv, pb)
    lab = kit.mono(20, 700, tracking=0.06)
    text.draw(cv, f'SEARCH ALL {TOTAL} CAPABILITIES', lab, pb.x + 26, pb.y + 20, MUTED)
    sb = Box(pb.x + 22, pb.y + 56, pb.w - 44, 60)
    cv.rect(*sb, BG, radius=30)
    cv.outline(*sb, LILAC, width=3, radius=30)
    sf = kit.font(30, 600)
    cx, cy = sb.x + 34, sb.cy
    cv.arc(cx - 3, cy - 3, 10, 0, 2 * math.pi, MUTED, width=3.5)
    cv.line(cx + 4, cy + 4, cx + 12, cy + 12, MUTED, width=3.5)
    typed = _typed(SEARCH, f, 2, 12)
    ty = sb.cy - text.line_height(sf) / 2
    text.draw(cv, typed, sf, sb.x + 62, ty, INK)
    _caret(cv, sb.x + 62 + text.measure(typed, sf), ty, text.line_height(sf), f, LILAC)
    if len(typed) < len(SEARCH):
        return
    t0 = 2 + len(SEARCH) * kit.FPS / 12 + 2
    y = sb.bottom + 16
    rf = kit.font(26, 750)
    nf = kit.mono(24, 700)
    rh = 50
    for i, (fam, ids) in enumerate(SEARCH_ROWS):
        if y + rh > pb.bottom - 14:
            break
        e = appear(f, t0 + 2 * i)
        rb = Box(pb.x + 22, y, pb.w - 44, rh)
        if e > 0.01:
            with cv.layer(opacity=vb.clamp01(e), dx=(1 - min(1, e)) * 30):
                cv.rect(*rb, CARD_HI if i == 0 else BG, radius=14)
                text.draw(cv, fam, rf, rb.x + 20, rb.cy - text.line_height(rf) / 2, INK)
                cs = str(len(ids))
                text.draw(cv, cs, nf, rb.right - 20 - text.measure(cs, nf), rb.cy - text.line_height(nf) / 2, LILAC)
        y += rh + 10
        if i == 0 and SEARCH_CLIPS:
            n = len(SEARCH_CLIPS)
            g = 14
            tw = (rb.w - g * (n - 1)) / n
            th = tw * 9 / 16
            if y + th > pb.bottom - 14:
                continue
            for j, cid in enumerate(SEARCH_CLIPS):
                q = appear(f, t0 + 3 + 3 * j)
                if q > 0.01:
                    tb = Box(rb.x + j * (tw + g), y, tw, th)
                    with cv.layer(opacity=vb.clamp01(q), dy=(1 - min(1, q)) * 24):
                        tile(cv, cid, tb, 22 + (f + 9 * j) % 50, size=15)
            y += th + 14


SCENES = {'open': opening, 'wall': wall_scene, 'ask': ask, **{b.name: family for b in BEATS}}
