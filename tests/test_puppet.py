"""vb.Puppet: cut-out poses placed by their feet, downscaled once, held on a schedule."""
import unittest

from PIL import Image as PILImage, ImageDraw

import videobuilder as vb


def figure(dx=0, dy=0, mouth=False, size=200):
    """A cut-out: a 40x120 body standing with its feet at (100 + dx, 180 + dy)."""
    im = PILImage.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((80 + dx, 60 + dy, 119 + dx, 179 + dy), fill=(240, 120, 20, 255))
    if mouth:
        d.rectangle((95 + dx, 80 + dy, 104 + dx, 84 + dy), fill=(20, 20, 20, 255))
    return im


def alpha_bbox(cv):
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    im = PILImage.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
    return im.getchannel('A').point(lambda v: 255 if v >= 128 else 0).getbbox()


class Puppet(unittest.TestCase):
    def test_downscaled_once_to_the_height(self):
        p = vb.Puppet({'idle': figure()}, height=60)
        self.assertAlmostEqual(p.factor, 0.5)
        img = p._poses['idle'][0]
        self.assertEqual((img.w, img.h), (100, 100))
        b = p.box('idle')
        self.assertAlmostEqual(b.h, 60)
        self.assertAlmostEqual(b.y + b.h, 0)          # feet at the origin

    def test_poses_registered_differently_land_on_the_same_feet(self):
        p = vb.Puppet({'idle': figure(), 'moved': figure(dx=30, dy=-12)}, height=120)
        boxes = []
        for pose in ('idle', 'moved'):
            cv = vb.Canvas(300, 300)
            p.draw(cv, pose, 150, 250)
            boxes.append(alpha_bbox(cv))
        self.assertEqual(boxes[0], boxes[1])
        self.assertEqual(boxes[0][3], 250)            # bottom row on the ground line
        self.assertAlmostEqual((boxes[0][0] + boxes[0][2]) / 2, 150, delta=1)

    def test_a_mouth_only_pose_swaps_in_place(self):
        talk = figure(mouth=True)
        talk.putpixel((79, 179), (240, 120, 20, 200))   # an antialiasing pixel the idle pose doesn't have
        p = vb.Puppet({'idle': figure(), 'talk': talk}, height=120)
        self.assertEqual(p._poses['idle'][1], p._poses['talk'][1])   # snapped to the first pose's feet
        self.assertNotEqual(vb.Puppet({'idle': figure(), 'talk': talk}, height=120, snap=0)._poses['talk'][1],
                            p._poses['idle'][1])

    def test_squash_pivots_on_the_feet_and_marks_the_body(self):
        p = vb.Puppet({'idle': figure()}, height=120)
        cv = vb.Canvas(300, 300)
        box = p.draw(cv, 'idle', 150, 250, sx=1.5, sy=0.5, mark='fox')
        self.assertAlmostEqual(box.y + box.h, 250)
        self.assertAlmostEqual(box.h, 60)
        self.assertAlmostEqual(box.w, 60)
        self.assertEqual(cv.marks[0][0], 'fox')
        self.assertEqual(alpha_bbox(cv)[3], 250)

    def test_lean_moves_the_top_and_keeps_the_feet(self):
        p = vb.Puppet({'idle': figure()}, height=120)
        cv = vb.Canvas(300, 300)
        box = p.draw(cv, 'idle', 150, 250, lean=0.25, mark='fox')
        self.assertAlmostEqual(box.x, 150 - 20)       # the feet's left edge stays
        self.assertAlmostEqual(box.w, 40 + 30)        # the top moved 0.25 x 120 right

    def test_pose_at_holds_and_ages(self):
        holds = [(0, 'idle'), (10, 'talk'), (14, 'idle')]
        self.assertEqual(vb.Puppet.pose_at(0, holds), ('idle', 0))
        self.assertEqual(vb.Puppet.pose_at(9, holds), ('idle', 9))
        self.assertEqual(vb.Puppet.pose_at(10, holds), ('talk', 0))
        self.assertEqual(vb.Puppet.pose_at(13, holds), ('talk', 3))
        self.assertEqual(vb.Puppet.pose_at(99, holds), ('idle', 85))
        self.assertEqual(vb.Puppet.pose_at(2, [(5, 'a'), (8, 'b')]), ('a', 2))

    def test_breath_is_periodic(self):
        self.assertEqual(vb.Puppet.breath(0, 60), (1.0, 1.0))
        for a, b in zip(vb.Puppet.breath(60, 60), (1.0, 1.0)):
            self.assertAlmostEqual(a, b)
        sx, sy = vb.Puppet.breath(15, 60)
        self.assertGreater(sy, 1)
        self.assertLess(sx, 1)

    def test_a_pose_with_no_cut_out_is_refused(self):
        with self.assertRaises(ValueError):
            vb.Puppet({'idle': PILImage.new('RGB', (10, 10))}, height=10)


class Walk(unittest.TestCase):
    def test_down_and_squashed_on_contact_up_on_the_passing_position(self):
        p = vb.Puppet({'idle': figure()}, height=100)
        contact, passing = p.walk(0, 8), p.walk(4, 8)
        self.assertEqual(contact.lift, 0)
        self.assertGreater(contact.sx, 1)
        self.assertLess(contact.sy, 1)
        self.assertAlmostEqual(passing.lift, 0.035 * 100)
        self.assertAlmostEqual(passing.sx, 1)
        self.assertGreater(contact.lean, passing.lean)
        self.assertGreater(passing.lean, 0)

    def test_one_step_every_step_frames_from_start(self):
        p = vb.Puppet({'idle': figure()}, height=100)
        self.assertEqual(p.walk(3, 7.5, start=3), p.walk(3 + 15, 7.5, start=3))
        self.assertAlmostEqual(p.walk(3 + 3.75, 7.5, start=3).phase, 0.5)


if __name__ == '__main__':
    unittest.main()
