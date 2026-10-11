"""Marked-box sampling and motion diagnostics shared by checks and the CLI."""
import math


def sample(film, fmt, frames, scale=0.05):
    return {n: {name: box for name, box in film.frame(n, fmt, scale=scale).marks}
            for n in sorted(set(frames))}


def speed(a, b):
    """Translation plus size change, in film pixels per frame."""
    return math.hypot(b.x - a.x, b.y - a.y) + math.hypot(b.w - a.w, b.h - a.h)


def motion_events(samples, min_speed=1.0):
    """Conservative mark motion: >=6 steady steps within 5%, or a full-speed one-frame edge."""
    events = []
    for name in {k for frame in samples for k in frame}:
        steps = []
        for prev, cur in zip(samples, samples[1:]):
            if name not in prev or name not in cur:
                steps.append(None)
            else:
                a, b = prev[name], cur[name]
                steps.append(tuple(y - x for x, y in zip(a, b)))
        speeds = [math.hypot(*v[:2]) + math.hypot(*v[2:]) if v is not None else 0 for v in steps]
        start = 0
        while start < len(steps):
            if speeds[start] < min_speed:
                start += 1
                continue
            end = start + 1
            while end < len(steps) and steps[end] is not None and speeds[end] >= min_speed:
                end += 1
            run = speeds[start:end]
            vectors = steps[start:end]
            straight = all(math.dist(v, vectors[0]) <= 0.05 * max(run) for v in vectors)
            if len(run) >= 6 and max(run) - min(run) <= 0.05 * max(run) and straight:
                events.append((name, 'constant rate', start, end))
            peak = max(run)
            easing_out = len(run) >= 3 and run[0] > run[1] > run[2] and run[2] <= 0.8 * run[0]
            easing_in = len(run) >= 3 and run[-3] < run[-2] < run[-1] and run[-3] <= 0.8 * run[-1]
            if start and speeds[start - 1] <= 0.2 * peak and run[0] >= 0.8 * peak and not easing_out:
                events.append((name, 'full-speed start', start, start + 1))
            if end < len(speeds) and speeds[end] <= 0.2 * peak and run[-1] >= 0.8 * peak and not easing_in:
                events.append((name, 'full-speed stop', end, end + 1))
            start = end
    return events
