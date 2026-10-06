"""Easing curves, interpolation and springs: pure functions of time, no state."""
import math


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def linear(x):
    return x


def bezier(x1, y1, x2, y2):
    """CSS cubic-bezier(x1, y1, x2, y2) as a function of progress in [0, 1]."""
    if not (0 <= x1 <= 1 and 0 <= x2 <= 1):
        raise ValueError('bezier x values must be in [0, 1]')
    cx, bx = 3 * x1, 3 * (x2 - x1) - 3 * x1
    ax = 1 - cx - bx
    cy, by = 3 * y1, 3 * (y2 - y1) - 3 * y1
    ay = 1 - cy - by

    def x_of(t):
        return ((ax * t + bx) * t + cx) * t

    def solve(x):
        # Newton from t = x, then bisection if the slope is too flat to trust.
        t = x
        for _ in range(8):
            err = x_of(t) - x
            if abs(err) < 1e-9:
                return t
            slope = (3 * ax * t + 2 * bx) * t + cx
            if abs(slope) < 1e-6:
                break
            t -= err / slope
        lo, hi, t = 0.0, 1.0, x
        for _ in range(60):
            if x_of(t) < x:
                lo = t
            else:
                hi = t
            t = (lo + hi) / 2
        return t

    def ease(x):
        x = clamp01(x)
        if x in (0.0, 1.0):
            return x
        t = solve(x)
        return ((ay * t + by) * t + cy) * t
    return ease


def interpolate(x, xs, ys, ease=linear, clamp=True):
    """Piecewise map of `x` over keyframes `xs` -> `ys`, eased per piece."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError('need matching keyframes, at least two')
    k = 0
    while k < len(xs) - 2 and x > xs[k + 1]:
        k += 1
    x0, x1, y0, y1 = xs[k], xs[k + 1], ys[k], ys[k + 1]
    p = (x - x0) / (x1 - x0)
    if clamp:
        p = clamp01(p)
    return y0 + (y1 - y0) * ease(p)


def spring(t, stiffness=100.0, damping=10.0, mass=1.0):
    """Unit step response of a damped spring at `t` seconds: 0 at rest, -> 1.

    Closed form, so any frame evaluates alone. All three regimes are real
    physics: under-damped bounces, critical settles fastest without overshoot,
    over-damped crawls. (Remotion treats every damping ratio >= 1 as critical;
    see `critical()` for the same feel.)
    """
    if t <= 0:
        return 0.0
    w0 = math.sqrt(stiffness / mass)
    zeta = damping / (2 * math.sqrt(stiffness * mass))
    if zeta < 1:
        wd = w0 * math.sqrt(1 - zeta * zeta)
        env = math.exp(-zeta * w0 * t)
        return 1 - env * (math.cos(wd * t) + zeta * w0 / wd * math.sin(wd * t))
    if zeta == 1:
        return 1 - math.exp(-w0 * t) * (1 + w0 * t)
    r = math.sqrt(zeta * zeta - 1)
    s1, s2 = -w0 * (zeta - r), -w0 * (zeta + r)
    return 1 - (s2 * math.exp(s1 * t) - s1 * math.exp(s2 * t)) / (s2 - s1)


def critical(stiffness, mass=1.0):
    """Spring params with damping ratio exactly 1: fastest settle, no overshoot."""
    return {'stiffness': stiffness, 'mass': mass, 'damping': 2 * math.sqrt(stiffness * mass)}


def spring_at(frame, fps, **params):
    """`spring` for a frame offset (frames since the spring started)."""
    return spring(frame / fps, **params)


def log_lerp(a, b, p):
    """Lerp in log space: even-feeling zoom between two scales."""
    return math.exp(math.log(a) + (math.log(b) - math.log(a)) * p)
