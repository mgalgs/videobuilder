"""L-system plant: a short rewriting rule is applied to a string over and over,
and a turtle reads the result as draw-forward, turn and branch commands, so a
whole branching plant grows up from one stem, tips budding as they arrive."""
import math
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PLANT_AXIOM = 'X'
PLANT_RULES = {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'}


def rewrite(axiom, rules, generations):
    """`axiom` with every symbol replaced by `rules[symbol]` (or kept, when it
    has no rule), all at once, `generations` times over."""
    s = axiom
    for _ in range(generations):
        s = ''.join(rules.get(ch, ch) for ch in s)
    return s


def turtle(commands, angle=25.0, step=1.0, heading=-90.0, jitter=0.0, seed=0, draw='F'):
    """Read `commands` as turtle moves from (0, 0) facing `heading` degrees
    (-90 is straight up on a canvas): a symbol in `draw` steps forward
    `step` drawing a segment, `+`/`-` turn by `angle` degrees, `[` saves the
    turtle and `]` returns to it. `jitter` adds up to that many degrees of
    seeded random wobble to each turn. Returns `(segments, tips)`: segments
    as `(x0, y0, x1, y1, depth, reach)`, where `depth` is the branch nesting
    and `reach` the path length from the root to the segment's start (the
    order a growing plant reaches it); tips as `(x, y, reach)`, the ends of
    branches."""
    rnd = random.Random(seed)
    x = y = reach = 0.0
    a = heading
    depth = 0
    stack, segments, tips = [], [], []
    moved = False
    for ch in commands:
        if ch in draw:
            r = math.radians(a)
            nx, ny = x + step * math.cos(r), y + step * math.sin(r)
            segments.append((x, y, nx, ny, depth, reach))
            x, y, reach = nx, ny, reach + step
            moved = True
        elif ch in '+-':
            a += (angle if ch == '+' else -angle) + (rnd.uniform(-jitter, jitter) if jitter else 0.0)
        elif ch == '[':
            stack.append((x, y, a, reach, depth))
            depth += 1
            moved = False
        elif ch == ']':
            if moved:
                tips.append((x, y, reach))
            x, y, a, reach, depth = stack.pop()
            moved = False
    if moved:
        tips.append((x, y, reach))
    return segments, tips


def l_system_plant(generations=5, axiom=PLANT_AXIOM, rules=PLANT_RULES, **kw):
    """The plant as `turtle` returns it, for `axiom` rewritten by `rules`
    `generations` times. `kw` goes to `turtle`."""
    return turtle(rewrite(axiom, rules, generations), **kw)


def draw_l_system_plant(cv, x, y, p, height=440, generations=5, color=demo.TEAL, bud=demo.ACCENT,
                        width=7.0, taper=0.7, plant=None, **kw):
    """Draw an L-system plant rooted at (x, y), `height` px tall when grown,
    at growth progress `p` (0 -> 1): each segment draws on once the growth
    front, sweeping out along every branch from the root at once, reaches
    it, and each branch tip buds in `bud` as the front arrives. Stems start
    `width` px wide and narrow by `taper` per level of branching. `plant` is
    a ready `(segments, tips)` (else built by `l_system_plant(generations,
    **kw)`). Returns the Box of the grown plant."""
    segments, tips = plant or l_system_plant(generations, **kw)
    xs = [c for s in segments for c in (s[0], s[2])]
    ys = [c for s in segments for c in (s[1], s[3])]
    k = height / max(max(ys) - min(ys), 1e-9)
    step = math.hypot(segments[0][2] - segments[0][0], segments[0][3] - segments[0][1])
    total = max(max(s[5] for s in segments) + step, 1e-9)
    front = vb.clamp01(p) * total
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_cap(1)  # round, so segments join without gaps
    for x0, y0, x1, y1, depth, reach in segments:
        q = vb.clamp01((front - reach) / step)
        if q <= 0:
            continue
        cv.line(x + x0 * k, y + y0 * k, x + (x0 + (x1 - x0) * q) * k, y + (y0 + (y1 - y0) * q) * k,
                color, width=max(width * taper ** depth, 1.2))
    ctx.restore()
    for tx, ty, reach in tips:
        q = vb.clamp01((front - reach) / (step * 6))
        if q > 0:
            demo.dot(cv, x + tx * k, y + ty * k, r=2.6 * vb.ease_out_back(q), color=bud, alpha=0.95)
    return vb.Box(x + min(xs) * k, y + min(ys) * k, (max(xs) - min(xs)) * k, height)


@lru_cache(maxsize=None)
def _demo_plant():
    return l_system_plant(5, jitter=4, seed=3)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.6))
    demo.floor(cv, 490, demo.LINE)
    plant = _demo_plant()
    segs = plant[0]
    xs = [c for s in segs for c in (s[0], s[2])]
    ys = [c for s in segs for c in (s[1], s[3])]
    lean = (min(xs) + max(xs)) / 2 * 430 / (max(ys) - min(ys))  # centre the crown, not the root
    box = draw_l_system_plant(cv, demo.W / 2 - lean, 490, p, height=430, plant=plant)
    cv.mark('plant', *box)
    f = demo.mono(17, 500)
    vb.text.draw(cv, ['X -> F+[[X]-X]-F[-FX]+X', 'F -> FF'], f, 40, 36, demo.MUTED)


CAPABILITY = Capability(
    id='l-system-plant',
    name='L-system plant',
    family='particles',
    group='Growth & L-systems',
    aliases=('Lindenmayer system', 'string rewriting plant', 'turtle graphics plant', 'fractal plant'),
    definition='A plant made of branching lines grows up from a single stem, splitting again and again '
               'by a simple repeated rule until it fans out into a full, budding shrub.',
    phrasings=('a fractal plant that grows branch by branch from a seed',
               'draw a procedural tree growing up out of the ground',
               'a generative fern sprouting and branching on screen'),
    related=('langton-s-ant', 'space-colonization', 'physarum-slime-mold', 'lenia',
             'diffusion-limited-aggregation', 'springs-network'),
    api=('videobuilder.capabilities.particles.l_system_plant.draw_l_system_plant',
         'videobuilder.capabilities.particles.l_system_plant.l_system_plant',
         'videobuilder.capabilities.particles.l_system_plant.rewrite',
         'videobuilder.capabilities.particles.l_system_plant.turtle'),
    demo=lambda: demo.film(draw),
)
