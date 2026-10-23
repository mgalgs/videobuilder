"""Letter Sort Animation: the letters of a word stand in a jumbled order,
then each one travels along a little arc to its own place until they spell
the word."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type import kit as type_kit


def shuffled(text, seed=0):
    """`text` with its non-space letters in a jumbled order (spaces keep their
    places), never the original order when the letters allow another. The
    same `seed` gives the same jumble."""
    slots = [i for i, ch in enumerate(text) if not ch.isspace()]
    letters = [text[i] for i in slots]
    rnd = random.Random(seed)
    order = letters[:]
    for _ in range(50):
        rnd.shuffle(order)
        if order != letters:
            break
    out = list(text)
    for i, ch in zip(slots, order):
        out[i] = ch
    return ''.join(out)


def _sources(text, scrambled):
    """For each character of `text`, the index in `scrambled` it starts from:
    equal letters are matched first to first, so twin letters don't cross."""
    if sorted(text) != sorted(scrambled):
        raise ValueError(f'{scrambled!r} is not a reordering of {text!r}')
    free = {}
    for j, ch in enumerate(scrambled):
        free.setdefault(ch, []).append(j)
    return [free[ch].pop(0) for ch in text]


def _overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def _lanes(moves):
    """A lane (0, 1, ...) and a flock number for each `(from, to, lo, hi)` move
    on one side of the line (left edges, then the x-span the letter sweeps).
    Moves whose spans overlap share a flock, which flies in step; within it a
    letter that overtakes another rides a lane outside it, so the arcs nest
    and no letter passes through another or rises through one already up."""
    lanes, flock = [0] * len(moves), list(range(len(moves)))
    done = []
    for i in sorted(range(len(moves)), key=lambda i: (abs(moves[i][1] - moves[i][0]), i)):
        a, b, lo, hi = moves[i]
        near = [j for j in done if _overlaps((lo, hi), moves[j][2:])]
        lanes[i] = max([lanes[j] + 1 for j in near if (a - moves[j][0]) * (b - moves[j][1]) < 0], default=0)
        for j in near:
            old = flock[j]
            flock = [flock[i] if f == old else f for f in flock]
        done.append(i)
    return lanes, flock


def _departures(movers):
    """The order movers set off in, each given as `(source span, target span)`:
    a letter goes once the fewest letters still waiting stand where it lands,
    so slots are vacated before they are filled (ties go left to right)."""
    waiting, order = list(range(len(movers))), []
    while waiting:
        def blocked(i):
            return sum(_overlaps(movers[i][1], movers[j][0]) for j in waiting if j != i)
        i = min(waiting, key=lambda i: (blocked(i), movers[i][0][0]))
        waiting.remove(i)
        order.append(i)
    return order


def letter_sort(text, font, p, scrambled=None, seed=0, stagger=0.35, lift=0.6, tilt=14.0):
    """Where each letter of `text` stands at progress `p` (0 -> 1) as it sorts
    from `scrambled` (default `shuffled(text, seed)`) into order: a list of
    `(char, x, dy, angle)`, `x` the letter's left edge from the line's start,
    `dy` its lift off the baseline (negative is up) and `angle` its tilt in
    degrees. Letters set off in flocks across the first `stagger` of the move,
    those whose landing spots are still occupied going last. Each one
    lifts clear of the line before it slides and drops in after: letters
    moving right arc over the line, letters moving left dip under it, so two
    that swap pass on opposite sides, and a long path rides outside any
    shorter one on its side (each lane `lift` line-heights deep), flying with
    it, so no two letters in flight meet. Letters tilt up to `tilt` degrees mid-flight;
    letters already in place stay put."""
    scrambled = shuffled(text, seed) if scrambled is None else scrambled
    src = _sources(text, scrambled)
    xs_to, _ = type_kit.advances(text, font)
    xs_from, _ = type_kit.advances(scrambled, font)
    lh = vb.text.line_height(font)
    moving = [i for i in range(len(text)) if xs_from[src[i]] != xs_to[i] and not text[i].isspace()]
    spans = {}
    for i in moving:
        w = vb.text.measure(text[i], font)
        a, b = xs_from[src[i]], xs_to[i]
        spans[i] = ((a, a + w), (b, b + w))
    lane, flock = {}, {}
    for side in (-1, 1):   # -1: moving right, over the line; 1: moving left, under it
        group = [i for i in moving if (xs_to[i] < xs_from[src[i]]) == (side > 0)]
        lanes, flocks = _lanes([(spans[i][0][0], spans[i][1][0], min(spans[i][0][0], spans[i][1][0]),
                                 max(spans[i][0][1], spans[i][1][1])) for i in group])
        lane.update(zip(group, lanes))
        flock.update((i, (side, f)) for i, f in zip(group, flocks))
    flights = []   # flocks in the order they set off: whichever has a letter go first goes first
    for k in _departures([spans[i] for i in moving]):
        if flock[moving[k]] not in flights:
            flights.append(flock[moving[k]])
    rank = {i: flights.index(flock[i]) for i in moving}
    out = []
    for i, ch in enumerate(text):
        a, b = xs_from[src[i]], xs_to[i]
        if i not in rank:
            out.append((ch, b, 0.0, 0.0))
            continue
        start = stagger * rank[i] / max(1, len(flights) - 1)
        t = vb.clamp01((p - start) / (1 - stagger))
        q = vb.ease_in_out_quart(t)   # slides mostly mid-flight...
        hop = math.sin(math.pi * t) ** 0.5 if 0 < t < 1 else 0.0   # ...while it is already up off the line
        side = -1 if b > a else 1
        depth = lift * lh * (1 + 0.9 * lane[i])
        out.append((ch, a + (b - a) * q, side * depth * hop, side * tilt * math.sin(math.pi * q)))
    return out


def draw_letter_sort(cv, text, font, x, y, p, color, moving=None, **kw):
    """Draw `text` sorting itself at progress `p` from its top-left (x, y);
    letters in flight are drawn in `moving` (default `color`). `kw` goes to
    `letter_sort`. Returns the Box of the finished line."""
    lh = vb.text.line_height(font)
    for ch, lx, dy, angle in letter_sort(text, font, p, **kw):
        if ch.isspace():
            continue
        gw = vb.text.measure(ch, font)
        ctx = cv.ctx
        ctx.save()
        ctx.translate(x + lx + gw / 2, y + dy + lh / 2)
        ctx.rotate(math.radians(angle))
        type_kit.glyphs(cv, ch, font, -gw / 2, -lh / 2, moving if (moving and dy) else color)
        ctx.restore()
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(120, 800)
    text = 'SORTED'
    w, h = vb.text.block_size([text], f)
    box = draw_letter_sort(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.4, 2.3),
                           demo.INK, moving=demo.ACCENT, scrambled='DTOESR')
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='letter-sort-animation',
    name='Letter sort animation',
    family='typography',
    group='Wave and motion',
    aliases=('unscramble word', 'letter reorder', 'anagram sort'),
    definition='A word starts with its letters in the wrong order, and each letter glides along '
               'a small arc to its proper spot until the word reads correctly.',
    phrasings=('the jumbled letters rearrange themselves into the word',
               'start with an anagram and have the letters swap places to spell the title',
               'letters shuffle around and settle into the right order'),
    related=('letter-roll', 'grid-reflow-shuffle', 'random-order-character-reveal', 'character-slide-in',
             'pixel-sort-text', 'character-rotate-in'),
    api=('videobuilder.capabilities.typography.letter_sort_animation.draw_letter_sort',
         'videobuilder.capabilities.typography.letter_sort_animation.letter_sort',
         'videobuilder.capabilities.typography.letter_sort_animation.shuffled'),
    demo=lambda: demo.film(draw),
)
