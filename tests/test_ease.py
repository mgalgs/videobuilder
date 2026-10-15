import math
import unittest

from videobuilder import ease
from videobuilder.ease import bezier, critical, interpolate, log_lerp, spring, spring_at


def step_response(t, stiffness=100.0, damping=10.0, mass=1.0):
    """The textbook step response of a damped harmonic oscillator released
    from rest at 0 toward 1: m x'' + c x' + k (x - 1) = 0, x(0) = x'(0) = 0."""
    if t <= 0:
        return 0.0
    w0 = math.sqrt(stiffness / mass)
    zeta = damping / (2 * math.sqrt(stiffness * mass))
    if zeta < 1:
        w1 = w0 * math.sqrt(1 - zeta ** 2)
        return 1 - math.exp(-zeta * w0 * t) * (math.cos(w1 * t) + zeta * w0 / w1 * math.sin(w1 * t))
    if zeta == 1:
        return 1 - math.exp(-w0 * t) * (1 + w0 * t)
    r = w0 * math.sqrt(zeta ** 2 - 1)
    r1, r2 = -zeta * w0 + r, -zeta * w0 - r
    return 1 - (r2 * math.exp(r1 * t) - r1 * math.exp(r2 * t)) / (r2 - r1)


class SpringPhysics(unittest.TestCase):
    CONFIGS = [
        {},  # the defaults: stiffness 100, damping 10, mass 1
        dict(stiffness=170, damping=12),
        dict(stiffness=200, damping=26, mass=1.0),
        dict(stiffness=80, damping=8, mass=0.6),
        dict(stiffness=300, damping=20, mass=2.0),
    ]

    def test_under_damped_is_the_step_response(self):
        for fps in (24, 30, 60):
            for cfg in self.CONFIGS:
                for n in range(0, 3 * fps):
                    with self.subTest(fps=fps, cfg=cfg, n=n):
                        self.assertAlmostEqual(spring_at(n, fps, **cfg), step_response(n / fps, **cfg), delta=1e-9)

    def test_critical_is_the_critically_damped_response(self):
        for k, m in ((100, 1), (120, 1), (200, 0.5), (60, 3)):
            for n in range(0, 90):
                with self.subTest(k=k, m=m, n=n):
                    ours = spring_at(n, 30, **critical(k, m))
                    physics = step_response(n / 30, stiffness=k, damping=2 * math.sqrt(k * m), mass=m)
                    self.assertAlmostEqual(ours, physics, delta=1e-9)

    def test_over_damped_crawls_behind_critical(self):
        cfg = dict(stiffness=100, damping=60)
        self.assertAlmostEqual(spring_at(15, 30, **cfg), step_response(0.5, **cfg), delta=1e-9)
        self.assertLess(spring_at(15, 30, **cfg), spring_at(15, 30, **critical(100)) - 0.1)

    def test_critical_params(self):
        p = critical(144, mass=2)
        self.assertEqual(p['stiffness'], 144)
        self.assertEqual(p['mass'], 2)
        self.assertAlmostEqual(p['damping'] / (2 * math.sqrt(144 * 2)), 1.0, places=12)
        self.assertEqual(critical(100)['mass'], 1.0)

    def test_critical_never_overshoots(self):
        cfg = critical(150)
        values = [spring(i / 120, **cfg) for i in range(600)]
        self.assertTrue(all(b >= a for a, b in zip(values, values[1:])))
        self.assertLessEqual(max(values), 1.0)
        self.assertGreater(values[-1], 0.999)

    def test_rest_and_limits(self):
        self.assertEqual(spring(0), 0.0)
        self.assertEqual(spring(-1), 0.0)
        self.assertAlmostEqual(spring(20), 1.0, places=9)
        self.assertGreater(max(spring(i / 60) for i in range(120)), 1.0)  # default bounces


class Bezier(unittest.TestCase):
    def test_presets(self):
        for name in ('ease_out_expo', 'ease_out_quint', 'ease_in_out_quart', 'ease_in_expo', 'ease_out_back'):
            curve = getattr(ease, name)
            self.assertEqual((curve(0), curve(1)), (0, 1))
        self.assertGreater(max(ease.ease_out_back(i / 100) for i in range(101)), 1)

    def test_linear(self):
        f = bezier(0, 0, 1, 1)
        for x in (0, 0.1, 0.25, 0.5, 0.9, 1):
            self.assertAlmostEqual(f(x), x, places=9)

    def test_css_ease(self):
        # CSS `ease` is cubic-bezier(0.25, 0.1, 0.25, 1).
        f = bezier(0.25, 0.1, 0.25, 1)
        self.assertAlmostEqual(f(0.5), 0.8024033877399112, places=6)

    def test_against_bisection(self):
        def reference(x1, y1, x2, y2, x):
            bx = lambda t: 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3
            by = lambda t: 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3
            lo, hi = 0.0, 1.0
            for _ in range(200):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if bx(mid) < x else (lo, mid)
            return by((lo + hi) / 2)
        for curve in ((0.25, 0.1, 0.25, 1), (0.16, 1, 0.3, 1), (0.65, 0, 0.35, 1), (0, 0, 0.58, 1), (0.9, 0, 0.1, 1)):
            f = bezier(*curve)
            for i in range(1, 100):
                with self.subTest(curve=curve, x=i / 100):
                    self.assertAlmostEqual(f(i / 100), reference(*curve, i / 100), delta=1e-7)

    def test_ends_and_clamp(self):
        f = bezier(0.65, 0, 0.35, 1)
        self.assertEqual(f(0), 0)
        self.assertEqual(f(1), 1)
        self.assertEqual(f(-3), 0)
        self.assertEqual(f(7), 1)
        self.assertAlmostEqual(f(0.5), 0.5, places=9)  # symmetric curve

    def test_overshoot_y_allowed_x_not(self):
        f = bezier(0.34, 1.56, 0.64, 1)
        self.assertGreater(max(f(i / 100) for i in range(101)), 1.0)
        with self.assertRaises(ValueError):
            bezier(1.2, 0, 0.5, 1)

    def test_monotonic_in_x(self):
        f = bezier(0.16, 1, 0.3, 1)
        ys = [f(i / 400) for i in range(401)]
        self.assertTrue(all(b >= a - 1e-12 for a, b in zip(ys, ys[1:])))


class Interpolate(unittest.TestCase):
    def test_damped_ratio(self):
        import math
        for ratio in (0.4, 0.7, 1.0):
            p = ease.damped(ratio, hz=2, mass=1.5)
            self.assertAlmostEqual(p['damping'] / (2 * math.sqrt(p['stiffness'] * p['mass'])), ratio)
            if ratio == 1:
                self.assertEqual(p, ease.critical(p['stiffness'], p['mass']))

    def test_pieces_and_clamp(self):
        self.assertEqual(interpolate(5, [0, 10], [0, 100]), 50)
        self.assertEqual(interpolate(-5, [0, 10], [0, 100]), 0)
        self.assertEqual(interpolate(15, [0, 10], [0, 100]), 100)
        self.assertEqual(interpolate(15, [0, 10], [0, 100], clamp=False), 150)
        self.assertEqual(interpolate(15, [0, 10, 20], [0, 100, 0]), 50)

    def test_eased(self):
        self.assertAlmostEqual(interpolate(5, [0, 10], [0, 1], ease=lambda p: p * p), 0.25)

    def test_bad_keyframes(self):
        with self.assertRaises(ValueError):
            interpolate(0, [0], [0])
        with self.assertRaises(ValueError):
            interpolate(0, [0, 1], [0])

    def test_log_lerp(self):
        self.assertAlmostEqual(log_lerp(1, 4, 0.5), 2)
        self.assertAlmostEqual(log_lerp(2, 8, 0), 2)
        self.assertAlmostEqual(log_lerp(2, 8, 1), 8)

    def test_clamp01(self):
        self.assertEqual([ease.clamp01(x) for x in (-1, 0.5, 2)], [0, 0.5, 1])


if __name__ == '__main__':
    unittest.main()
