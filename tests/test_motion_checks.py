"""Synthetic signals for the optional motion and decoded-picture warnings."""
import importlib.util
import math
import unittest
from pathlib import Path

import videobuilder as vb

SCRIPT = Path(__file__).resolve().parent.parent / 'skill/make-a-video/scripts/check.py'
spec = importlib.util.spec_from_file_location('video_check', SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class MotionChecks(unittest.TestCase):
    def test_flashes_need_large_opposing_changes(self):
        frames = [bytes([v] * 16) for v in (0, 255, 0, 255, 0, 255, 0, 255, 0)]
        self.assertEqual(check.flash_frames(frames[:7], fps=10), [])  # three complete flashes
        self.assertEqual(check.flash_frames(frames, fps=10), [8])
        small = [bytes([v] + [0] * 15) for v in (0, 255, 0, 255, 0, 255, 0, 255, 0)]
        self.assertEqual(check.flash_frames(small, fps=10), [])

    def test_flashes_with_held_states(self):
        for hold in (2, 3):
            frames = [bytes([v] * 16) for v in ([0] * hold + [255] * hold) * 7]
            self.assertTrue(check.flash_frames(frames, fps=30), f'{hold}-frame holds')

    def test_loop_seam(self):
        good = [bytes([v] * 8) for v in (0, 10, 20, 10)]
        bad = [bytes([v] * 8) for v in (0, 1, 2, 100)]
        self.assertLess(check.seam_ratio(good), 3)
        self.assertGreater(check.seam_ratio(bad), 3)
        duplicate = [bytes([round(128 + 100 * math.sin(2 * math.pi * n / 15))] * 8)
                     for n in range(16)]
        self.assertLess(check.seam_ratio(duplicate), 1 / 3)
        report = check.Report()
        check.picture_safety('loop.mp4', type('Film', (), {'fps': 30})(), report,
                             loop=True, frames=duplicate)
        self.assertEqual(report.warned, 1)

    def test_motion_warns_on_linear_run_and_hard_edges(self):
        samples = [{'hero': (min(max(n - 2, 0), 8) * 3, 0, 10, 10)} for n in range(14)]
        events = check.motion_events(samples)
        self.assertTrue(any(kind == 'constant rate' for _, kind, _, _ in events))
        self.assertTrue(any(kind == 'full-speed start' for _, kind, _, _ in events))
        self.assertTrue(any(kind == 'full-speed stop' for _, kind, _, _ in events))
        still = [{'hero': (0, 0, 10, 10)} for _ in range(14)]
        self.assertEqual(check.motion_events(still), [])

    def test_motion_allows_recommended_entrance_and_exit_curves(self):
        for curve in (vb.ease_out_expo, vb.ease_out_quint, vb.ease_in_expo):
            positions = [0] * 5 + [400 * curve(n / 18) for n in range(1, 19)] + [400] * 3
            samples = [{'hero': (x, 0, 10, 10)} for x in positions]
            self.assertFalse(any(kind.startswith('full-speed') for _, kind, _, _ in
                                 check.motion_events(samples)), curve)


if __name__ == '__main__':
    unittest.main()
