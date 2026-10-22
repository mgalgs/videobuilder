"""Ragdoll: a jointed figure stands on a ledge; the ledge drops away and the
figure falls limp, tumbling onto the floor and folding up where it lands."""
import functools
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# The rig, standing: joint -> (x, y) as shares of its height, feet at (0, 0), y down.
STANDING = {
    'head': (0.0, -0.92), 'neck': (0.0, -0.81),
    'l_shoulder': (-0.11, -0.78), 'r_shoulder': (0.11, -0.78),
    'l_elbow': (-0.17, -0.63), 'r_elbow': (0.17, -0.63),
    'l_hand': (-0.20, -0.48), 'r_hand': (0.20, -0.48),
    'l_hip': (-0.07, -0.50), 'r_hip': (0.07, -0.50),
    'l_knee': (-0.08, -0.25), 'r_knee': (0.08, -0.25),
    'l_foot': (-0.09, 0.0), 'r_foot': (0.09, 0.0),
}
TORSO = ('l_shoulder', 'r_shoulder', 'r_hip', 'l_hip')
LIMBS = (('neck', 'head'),
         ('l_shoulder', 'l_elbow'), ('l_elbow', 'l_hand'), ('r_shoulder', 'r_elbow'), ('r_elbow', 'r_hand'),
         ('l_hip', 'l_knee'), ('l_knee', 'l_foot'), ('r_hip', 'r_knee'), ('r_knee', 'r_foot'))
# Rigid links: the drawn limbs, plus the torso box braced so it can't shear.
_STIFF = LIMBS + (('l_shoulder', 'r_shoulder'), ('r_shoulder', 'r_hip'), ('r_hip', 'l_hip'),
                  ('l_hip', 'l_shoulder'), ('l_shoulder', 'r_hip'), ('r_shoulder', 'l_hip'),
                  ('neck', 'l_shoulder'), ('neck', 'r_shoulder'))
# Joint limits, loosely: these pairs may come closer than standing only down to a share of it,
# so elbows and knees bend but don't fold flat, and the head can loll but not sink into the chest.
_LIMITS = (('l_shoulder', 'l_hand', 0.45), ('r_shoulder', 'r_hand', 0.45),
           ('l_hip', 'l_foot', 0.55), ('r_hip', 'r_foot', 0.55),
           ('head', 'l_shoulder', 0.8), ('head', 'r_shoulder', 0.8),
           ('l_knee', 'r_knee', 0.5), ('l_elbow', 'l_hip', 0.4), ('r_elbow', 'r_hip', 0.4))


def standing_pose(x, foot_y, height):
    """The rig standing upright with its feet centred on (x, foot_y), `height`
    px tall: a dict joint name -> (x, y), ready for `ragdoll`."""
    return {k: (x + u * height, foot_y + v * height) for k, (u, v) in STANDING.items()}


@functools.lru_cache(maxsize=8)
def _track(pose, floor, release, seconds, push, spin, gravity, drag, friction, bounce, hz, iterations):
    names = [k for k, _ in pose]
    at = {k: i for i, k in enumerate(names)}
    rest = [list(p) for _, p in pose]
    size = max(p[1] for p in rest) - min(p[1] for p in rest)
    dist = lambda a, b: math.dist(rest[at[a]], rest[at[b]])  # noqa: E731
    stiff = [(at[a], at[b], dist(a, b)) for a, b in _STIFF if a in at and b in at]
    limits = [(at[a], at[b], dist(a, b) * k) for a, b, k in _LIMITS if a in at and b in at]
    radius = [size * (0.07 if k == 'head' else 0.02) for k in names]
    dt = 1.0 / hz
    keep = math.exp(-drag * dt)
    pts = [p[:] for p in rest]
    base = max(p[1] for p in rest)
    # The push at release: a sideways shove plus a tip about the feet (`spin` rad/s), so it topples.
    prev = [[x - (push[0] + spin * (base - y)) * dt, y - push[1] * dt] for x, y in pts]
    out = []
    for k in range(round(seconds * hz) + 1):
        out.append(tuple(tuple(p) for p in pts))
        if (k + 1) * dt <= release:
            continue
        for i, (x, y) in enumerate(pts):
            px, py = prev[i]
            prev[i] = [x, y]
            pts[i] = [x + (x - px) * keep, y + (y - py) * keep + gravity * dt * dt]
        for _ in range(iterations):
            for i, j, length in stiff:
                _solve(pts, i, j, length, exact=True)
            for i, j, least in limits:
                _solve(pts, i, j, least, exact=False)
            for i, p in enumerate(pts):
                ground = floor - radius[i]
                if p[1] > ground:
                    vx, vy = p[0] - prev[i][0], p[1] - prev[i][1]
                    p[1] = ground
                    prev[i][0] = p[0] - vx * (1 - friction)
                    prev[i][1] = ground + max(vy, 0) * bounce
    return names, out


def _solve(pts, i, j, length, exact):
    (x0, y0), (x1, y1) = pts[i], pts[j]
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy) or 1e-9
    if not exact and d >= length:
        return
    s = (d - length) / d / 2
    pts[i] = [x0 + dx * s, y0 + dy * s]
    pts[j] = [x1 - dx * s, y1 - dy * s]


def ragdoll(pose, t, floor, release=0.0, push=(60.0, 0.0), spin=0.6, gravity=2400.0, drag=0.6,
            friction=0.35, bounce=0.15, hz=120, iterations=10):
    """The figure's joints at `t` seconds: a dict joint name -> (x, y).

    `pose` (e.g. `standing_pose(...)`) is held still until `release` seconds,
    when its support goes and it falls limp under `gravity` (px/s^2), with
    rigid bones, loose joint limits and nothing holding it up, onto the
    ground line at y = `floor`, where it slides to a stop (`friction`, 0..1
    per contact step) and folds up. At release it gets `push` (px/s) and a
    tip of `spin` (rad/s about its feet) so it topples rather than dropping
    straight. Stepped (Verlet, fixed `hz`) and cached, so the same `t` always
    gives the same pose and frames can render in any order. Joints not named
    in `STANDING` are carried along as loose points."""
    end = max(t, release) + 1.0 / hz
    seconds = math.ceil(end * 2) / 2   # simulate in half-second blocks so neighbouring frames share a track
    names, track = _track(tuple(pose.items()), floor, release, seconds, tuple(push), spin, gravity, drag,
                          friction, bounce, hz, iterations)
    return dict(zip(names, track[min(len(track) - 1, max(0, round(t * hz)))]))


def draw_ragdoll(cv, pts, height, color=demo.TEAL, head=demo.ACCENT, joints=demo.INK, body=None):
    """Draw a `ragdoll` pose: round-capped limbs, a filled torso, a round head
    and a dot at each joint, sized for a figure `height` px tall."""
    w = height * 0.035
    c = cv.ctx
    c.save()
    c.set_line_cap(1)   # round
    c.set_line_join(1)
    c.move_to(*pts[TORSO[0]])
    for k in TORSO[1:]:
        c.line_to(*pts[k])
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(body or demo.BG, 1.0))
    c.fill_preserve()
    c.set_source_rgba(*vb.canvas.rgba(color, 1.0))
    c.set_line_width(w)
    c.stroke()
    for a, b in LIMBS:
        c.move_to(*pts[a])
        c.line_to(*pts[b])
    c.stroke()
    c.restore()
    hx, hy = pts['head']
    demo.dot(cv, hx, hy, height * 0.07, head)
    for k, (x, y) in pts.items():
        if k not in ('head', 'neck'):
            demo.dot(cv, x, y, w * 0.32, joints)


FLOOR = demo.H - 80
LEDGE_Y = 270
FIG_H = 190
GRAVITY = 1600.0
RELEASE = 0.7
FIG_X = demo.W / 2 - 40
DOOR = 60   # each trapdoor half's length
POSE = standing_pose(FIG_X, LEDGE_Y, FIG_H)


def _doors(cv, t):
    """The ledge: two trapdoor halves hinged at its ends, swinging down out
    from under the feet a little faster than the figure falls."""
    fall = 0.5 * GRAVITY * max(0.0, t - RELEASE) ** 2
    angle = math.asin(min(1.0, 1.6 * fall / DOOR))
    for side in (-1, 1):
        hx = FIG_X + side * DOOR
        cv.line(hx, LEDGE_Y, hx - side * DOOR * math.cos(angle), LEDGE_Y + DOOR * math.sin(angle),
                demo.MUTED, width=6)
        demo.dot(cv, hx, LEDGE_Y, 5, demo.LINE)
    cv.line(FIG_X - DOOR - 40, LEDGE_Y, FIG_X - DOOR, LEDGE_Y, demo.MUTED, width=6)
    cv.line(FIG_X + DOOR, LEDGE_Y, FIG_X + DOOR + 40, LEDGE_Y, demo.MUTED, width=6)


def draw(n, cv):
    t = n / demo.FPS
    demo.floor(cv, FLOOR)
    _doors(cv, t)
    pts = ragdoll(POSE, t, FLOOR, release=RELEASE, push=(20.0, 0.0), spin=2.4, gravity=GRAVITY)
    draw_ragdoll(cv, pts, FIG_H)
    xs, ys = [p[0] for p in pts.values()], [p[1] for p in pts.values()]
    cv.mark('ragdoll', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='ragdoll',
    name='Ragdoll',
    family='particles',
    group='Soft bodies & cloth',
    aliases=('physics ragdoll', 'limp body physics', 'ragdoll physics'),
    definition='A figure made of stiff limbs on loose joints loses whatever was holding it up and drops '
               'like a puppet with its strings cut, tumbling and folding into a heap where it lands.',
    phrasings=('a stick figure that goes limp and collapses when the floor opens under it',
               'make the character fall over floppy, like a rag doll',
               'a jointed body that crumples to the ground with real physics'),
    related=('rigid-body-pile', 'bounce-ease-out', 'physics-letter-drop', 'bounce-ease-in', 'gravity-drop',
             'newton-s-cradle'),
    api=('videobuilder.techniques.particles.ragdoll.ragdoll',
         'videobuilder.techniques.particles.ragdoll.standing_pose',
         'videobuilder.techniques.particles.ragdoll.draw_ragdoll'),
    demo=lambda: demo.film(draw),
)
