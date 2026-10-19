"""vb.Stick: a stick figure drawn in code, its rig, faces, poses, motion, talking and props."""
import math
import unittest

from PIL import Image as PILImage

import videobuilder as vb
from videobuilder import stick

H = 300
GROUND = 400
LIMBS = (('shoulder', 'front_elbow', stick.UPPER_ARM), ('front_elbow', 'front_hand', stick.FOREARM),
         ('shoulder', 'back_elbow', stick.UPPER_ARM), ('back_elbow', 'back_hand', stick.FOREARM),
         ('hip', 'front_knee', stick.THIGH), ('front_knee', 'front_ankle', stick.SHIN),
         ('hip', 'back_knee', stick.THIGH), ('back_knee', 'back_ankle', stick.SHIN),
         ('hip', 'neck', stick.TORSO))


def ink_bbox(cv, threshold=128):
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    im = PILImage.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
    return im.getchannel('A').point(lambda v: 255 if v >= threshold else 0).getbbox()


def soles(fig, pose, x=200, y=GROUND, facing=1, lift=0.0):
    """The bottom edge of each foot's stroke on the canvas."""
    j = fig.joints(pose, x, y, facing=facing, lift=lift)
    half = 0.6 * fig.weight * fig.height
    return j['front_ankle'][1] + half, j['back_ankle'][1] + half


class Rig(unittest.TestCase):
    def setUp(self):
        self.fig = vb.Stick(height=H)

    def assertLimbsKeepTheirLength(self, pose, msg=None):
        j = self.fig.joints(pose, 200, GROUND)
        for a, b, share in LIMBS:
            self.assertAlmostEqual(math.dist(j[a], j[b]), share * H, places=6, msg=f'{a}-{b} {msg or ""}')

    def test_height_is_one_number_soles_to_crown(self):
        fig = vb.Stick(height=H)
        straight = stick.Pose()                        # every angle 0: legs and body plumb
        cv = vb.Canvas(400, 500)
        fig.draw(cv, straight, 200, GROUND)
        x0, y0, x1, y1 = ink_bbox(cv, threshold=1)
        self.assertEqual(y1, GROUND)
        self.assertAlmostEqual(GROUND - y0, H, delta=1.5)
        self.assertAlmostEqual(fig.box(straight, 200, GROUND).h, H, delta=1.5)

    def test_limb_lengths_stay_fixed_in_every_pose(self):
        for name in stick.names():
            with self.subTest(pose=name):
                for n in (0, 7, 13, 22):
                    self.assertLimbsKeepTheirLength(self.fig.pose(name, n), f'frame {n}')

    def test_limb_lengths_stay_fixed_through_a_blend_and_a_move(self):
        a, b = stick.POSES['crouch'], stick.POSES['cheer']
        for t in (0.1, 0.37, 0.5, 0.81, 1.2):
            self.assertLimbsKeepTheirLength(stick.blend(a, b, t), f't={t}')
        for age in range(0, 60, 3):
            self.assertLimbsKeepTheirLength(self.fig.move(a, b, age, frames=12), f'age={age}')

    def test_every_pose_stands_on_its_lowest_foot(self):
        for name in stick.names():
            with self.subTest(pose=name):
                self.assertAlmostEqual(max(soles(self.fig, self.fig.pose(name, 4))), GROUND, places=6)

    def test_both_feet_on_the_ground_in_stand_and_its_breathing(self):
        for n in (0, 20, 45, 101, 160):
            for pose in (stick.POSES['stand'], self.fig.alive(stick.POSES['stand'], n)):
                front, back = soles(self.fig, pose)
                self.assertAlmostEqual(front, GROUND, delta=0.5)
                self.assertAlmostEqual(back, GROUND, delta=0.5)

    def test_standing_poses_put_both_feet_down(self):
        for name in ('stand', 'point', 'wave', 'shrug', 'think', 'push', 'sit', 'crouch', 'hold', 'read', 'cheer',
                     'slump'):
            with self.subTest(pose=name):
                front, back = soles(self.fig, name)
                self.assertAlmostEqual(front, back, delta=0.5)

    def test_the_drawing_sits_on_the_ground(self):
        for name in ('stand', 'push', 'sit', 'crouch'):
            with self.subTest(pose=name):
                cv = vb.Canvas(400, 500)
                self.fig.draw(cv, name, 200, GROUND)
                self.assertEqual(ink_bbox(cv)[3], GROUND)

    def test_think_puts_the_hand_at_the_chin_and_point_reaches_ahead(self):
        j = self.fig.joints('think', 0, 0)
        r = self.fig.r * H
        self.assertLess(math.dist(j['front_hand'], j['head']), 1.35 * r)
        self.assertGreater(j['front_hand'][1], j['head'][1])           # below the middle of the head
        j = self.fig.joints('point', 0, 0)
        self.assertGreater(j['front_hand'][0] - j['shoulder'][0], 0.25 * H)
        self.assertAlmostEqual(j['front_hand'][1], j['shoulder'][1], delta=0.06 * H)

    def test_line_body_and_colours(self):
        fig = vb.Stick(height=H, ink='#0000ff', fill='#ffff00', body='line')
        cv = vb.Canvas(400, 500)
        fig.draw(cv, 'stand', 200, GROUND)
        cv.surface.flush()
        im = PILImage.frombuffer('RGBA', (400, 500), bytes(cv.surface.get_data()), 'raw', 'BGRA',
                                 cv.surface.get_stride(), 1).convert('RGB')
        colours = {c for _, c in im.getcolors(1 << 20)}
        self.assertIn((0, 0, 255), colours)
        self.assertIn((255, 255, 0), colours)
        with self.assertRaises(ValueError):
            vb.Stick(body='blob')

    def test_mark_names_the_figure_box(self):
        cv = vb.Canvas(400, 500)
        drawn = self.fig.draw(cv, 'stand', 200, GROUND, mark='hero')
        self.assertEqual(cv.marks[0][0], 'hero')
        for a, b in zip(cv.marks[0][1], drawn.box):
            self.assertAlmostEqual(a, b, places=6)
        self.assertAlmostEqual(drawn.box.y + drawn.box.h, GROUND, delta=0.6 * self.fig.weight * H + 0.01)
        x0, y0, x1, y1 = ink_bbox(cv, threshold=1)
        self.assertLessEqual(drawn.box.x, x0 + 0.5)
        self.assertGreaterEqual(drawn.box.x + drawn.box.w, x1 - 0.5)


class Names(unittest.TestCase):
    def test_every_named_pose_exists_and_draws(self):
        fig = vb.Stick(height=200)
        for name in ('stand', 'walk', 'run', 'point', 'wave', 'shrug', 'think', 'push', 'sit', 'crouch', 'hold',
                     'read', 'cheer', 'slump'):
            with self.subTest(pose=name):
                self.assertIn(name, stick.names())
                cv = vb.Canvas(300, 300)
                fig.draw(cv, name, 150, 280)
                self.assertIsNotNone(ink_bbox(cv))

    def test_every_expression_exists_and_draws_its_own_face(self):
        fig = vb.Stick(height=200)
        seen = set()
        for name in ('neutral', 'happy', 'worried', 'determined', 'surprised', 'thinking', 'sleepy', 'content',
                     'annoyed'):
            with self.subTest(expression=name):
                self.assertIn(name, stick.expressions())
                cv = vb.Canvas(300, 300)
                fig.draw(cv, 'stand', 150, 280, face=name)
                seen.add(bytes(cv.surface.get_data()))
        self.assertEqual(len(seen), 9)

    def test_every_mouth_and_prop_draws(self):
        fig = vb.Stick(height=200)
        for m in ('smile', 'flat', 'frown', 'open', 'o', 'gritted'):
            fig.draw(vb.Canvas(300, 300), 'stand', 150, 280, face=stick.face('neutral', mouth=m))
        for p in stick.PROPS:
            fig.draw(vb.Canvas(300, 300), 'hold', 150, 280, prop=stick.prop(p, text='THIS WAY'))

    def test_an_unknown_name_is_one_clear_error_listing_the_names(self):
        fig = vb.Stick()
        for call, kind, some in ((lambda: fig.pose('moonwalk'), 'pose', 'stand, point'),
                                 (lambda: stick.face('smug'), 'expression', 'neutral, happy'),
                                 (lambda: stick.face('happy', mouth='pout'), 'mouth', 'smile, flat'),
                                 (lambda: stick.prop('umbrella'), 'prop', 'sheet, map, mug'),
                                 (lambda: fig.gait(0, 'skip'), 'gait', 'walk, run'),
                                 (lambda: fig.draw(vb.Canvas(10, 10), 'moonwalk', 0, 0), 'pose', 'walk, run')):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError) as e:
                    call()
                self.assertIn(f'no {kind}', str(e.exception))
                self.assertIn(some, str(e.exception))

    def test_a_face_takes_its_fields_by_keyword(self):
        f = stick.face('happy', gaze_x=-1)
        self.assertEqual((f.gaze_x, f.curve), (-1, stick.FACES['happy'].curve))
        self.assertIs(stick.face(f), f)


class Faces(unittest.TestCase):
    def test_blend_endpoints_and_middle(self):
        a, b = stick.FACES['neutral'], stick.FACES['surprised']
        self.assertEqual(stick.blend_faces(a, b, 0), a)
        self.assertEqual(stick.blend_faces(a, b, 1), b)
        self.assertAlmostEqual(stick.blend_faces(a, b, 0.5).eyes, (a.eyes + b.eyes) / 2)

    def test_face_at_eases_from_one_expression_to_the_next(self):
        fig = vb.Stick()
        keys = [(0, 'neutral'), (10, 'happy', 6)]
        self.assertEqual(fig.face_at(5, keys), stick.FACES['neutral'])
        self.assertEqual(fig.face_at(16, keys), stick.FACES['happy'])
        mid = fig.face_at(13, keys).curve
        self.assertTrue(stick.FACES['neutral'].curve < mid < stick.FACES['happy'].curve)

    def test_the_face_turns_with_the_head(self):
        fig = vb.Stick(height=200)
        middles = []
        for turn in (0.0, 0.8):
            cv = vb.Canvas(300, 300)
            fig.draw(cv, stick.Pose(), 150, 280, turn=turn)
            cv.surface.flush()
            im = PILImage.frombuffer('RGBA', (300, 300), bytes(cv.surface.get_data()), 'raw', 'BGRA',
                                     cv.surface.get_stride(), 1).convert('L')
            hx, hy = fig.joints(stick.Pose(), 150, 280)['head']
            r = 0.85 * fig.r * 200                        # inside the head's outline: just the features
            xs = [x for x in range(round(hx - r), round(hx + r)) for y in range(round(hy - r), round(hy + r))
                  if math.hypot(x - hx, y - hy) < r and im.getpixel((x, y)) < 100]
            middles.append(sum(xs) / len(xs))
        self.assertGreater(middles[1], middles[0] + 0.25 * fig.r * 200)

if __name__ == '__main__':
    unittest.main()
