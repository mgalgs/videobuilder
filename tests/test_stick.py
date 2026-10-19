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

def flipped_pixels(cv):
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    return PILImage.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(),
                               1).transpose(PILImage.FLIP_LEFT_RIGHT)


class Moves(unittest.TestCase):
    def setUp(self):
        self.fig = vb.Stick(height=H)

    def test_a_blend_ends_exactly_on_its_poses(self):
        a, b = stick.POSES['stand'], stick.POSES['point']
        self.assertEqual(stick.blend(a, b, 0), a)
        self.assertEqual(stick.blend(a, b, 1), b)
        self.assertAlmostEqual(stick.blend(a, b, 0.5).front_arm, (a.front_arm + b.front_arm) / 2)

    def test_a_move_starts_and_ends_exactly_on_its_poses(self):
        for a, b in (('stand', 'point'), ('crouch', 'cheer'), ('sit', 'stand')):
            pa, pb = stick.POSES[a], stick.POSES[b]
            self.assertEqual(self.fig.move(pa, pb, 0), pa)
            self.assertEqual(self.fig.move(pa, pb, -3), pa)
            self.assertEqual(self.fig.move(pa, pb, 12 + 6 + 36), pb)
            self.assertNotEqual(self.fig.move(pa, pb, 6), pa)

    def test_overlap_the_arms_trail_the_body_and_the_head_settles_last(self):
        a, b = stick.POSES['stand'], stick.POSES['push']

        def share(p, name):
            return (getattr(p, name) - getattr(a, name)) / (getattr(b, name) - getattr(a, name))
        mid = self.fig.move(a, b, 6, frames=12, anticipate=False)
        self.assertGreater(share(mid, 'lean'), share(mid, 'front_arm') + 0.2)
        self.assertEqual(share(mid, 'nod'), 0)
        # the arms overshoot as they land (follow-through), the head is still settling after the body has
        late = [self.fig.move(a, b, age, frames=12, anticipate=False) for age in range(12, 40)]
        self.assertTrue(any(share(p, 'front_arm') > 1.0 for p in late))
        self.assertTrue(all(share(p, 'lean') == 1 for p in late))
        self.assertTrue(any(abs(share(p, 'nod') - 1) > 0.02 for p in late[10:]))

    def test_a_big_move_winds_up_the_other_way_first(self):
        a, b = stick.POSES['stand'], stick.POSES['push']
        early = [self.fig.move(a, b, age, frames=12) for age in range(1, 5)]
        self.assertTrue(any(p.lean < a.lean for p in early))       # back, before it leans in
        early = [self.fig.move(a, b, age, frames=12, anticipate=False) for age in range(1, 5)]
        self.assertTrue(all(p.lean >= a.lean for p in early))

    def test_act_holds_breathes_and_moves(self):
        keys = [(0, 'stand'), (30, 'point', 10), (90, 'shrug')]
        self.assertEqual(self.fig.act(10, keys, alive=False), stick.POSES['stand'])
        self.assertEqual(self.fig.act(30, keys, alive=False), stick.POSES['stand'])
        self.assertEqual(self.fig.act(85, keys, alive=False), stick.POSES['point'])
        self.assertNotEqual(self.fig.act(35, keys, alive=False), stick.POSES['point'])
        # alive: never frozen in a hold, and the move lands on the breathing pose
        self.assertNotEqual(self.fig.act(70, keys), self.fig.act(80, keys))
        self.assertEqual(self.fig.act(85, keys), self.fig.alive(stick.POSES['point'], 85))

    def test_act_keeps_a_cycle_going_while_it_holds(self):
        keys = [(0, 'stand'), (10, 'walk', 8)]
        self.assertEqual(self.fig.act(60, keys), self.fig.gait(60, 'walk').pose)
        self.assertNotEqual(self.fig.act(60, keys), self.fig.act(65, keys))

    def test_blinks_are_brief_and_seeded(self):
        b = [self.fig.blink(n) for n in range(600)]
        self.assertLessEqual(set(b), {1.0, 0.5, 0.0})
        self.assertGreater(b.count(1.0), 0.9 * len(b))
        self.assertIn(0.0, b)
        self.assertEqual(b, [vb.Stick(height=H).blink(n) for n in range(600)])
        self.assertNotEqual(b, [vb.Stick(height=H, seed=3).blink(n) for n in range(600)])


class Gait(unittest.TestCase):
    def setUp(self):
        self.fig = vb.Stick(height=H)

    def test_the_walk_moves_at_a_steady_speed(self):
        xs = [self.fig.gait(n, 'walk').x for n in range(90)]
        steps = {round(b - a, 9) for a, b in zip(xs, xs[1:])}
        self.assertEqual(len(steps), 1)
        self.assertAlmostEqual(steps.pop(), self.fig.speed('walk'))

    def test_a_planted_foot_stays_put_on_the_ground_while_the_body_passes(self):
        for kind in ('walk', 'run'):
            planted = {'front': [], 'back': []}
            for n in range(60):
                st = self.fig.gait(n, kind)
                j = self.fig.joints(st.pose, 100 + st.x, GROUND, lift=st.lift)
                for side in ('front', 'back'):
                    if st.contact in (side, 'both'):
                        half = 0.6 * self.fig.weight * H
                        self.assertAlmostEqual(j[f'{side}_ankle'][1] + half, GROUND, places=6)
                        planted[side].append((n, j[f'{side}_ankle'][0]))
            for side, run in planted.items():
                # consecutive frames on one contact: the same x
                for (n0, x0), (n1, x1) in zip(run, run[1:]):
                    if n1 == n0 + 1:
                        self.assertAlmostEqual(x0, x1, places=6, msg=f'{kind} {side} slid at frame {n1}')

    def test_the_walk_always_has_a_foot_down_and_the_run_flies(self):
        walk = [self.fig.gait(n, 'walk') for n in range(30)]
        self.assertTrue(all(s.contact and s.lift == 0 for s in walk))
        self.assertIn('both', [s.contact for s in walk])
        run = [self.fig.gait(n, 'run') for n in range(60)]
        flying = [s for s in run if s.contact is None]
        self.assertTrue(flying)
        self.assertTrue(all(s.lift > 0 for s in flying))

    def test_the_cycle_repeats_every_period(self):
        for n in (0, 4, 17):
            a, b = self.fig.gait(n, 'walk').pose, self.fig.gait(n + 30, 'walk').pose
            for f in stick.fields(stick.Pose):
                self.assertAlmostEqual(getattr(a, f.name), getattr(b, f.name), places=9)
            self.assertAlmostEqual(self.fig.gait(n, 'walk').phase, n / 30)

    def test_a_cycle_in_place_is_the_same_pose_whatever_the_ground_does(self):
        st = self.fig.gait(12, 'walk')
        a = self.fig.joints(st.pose, 300, GROUND)
        b = self.fig.joints(st.pose, 300 + st.x, GROUND)
        self.assertAlmostEqual(b['hip'][0] - a['hip'][0], st.x)


class Talking(unittest.TestCase):
    WORDS = [('Working', 1.0, 1.5), ('harder', 1.6, 2.0), ('is', 2.5, 2.7)]

    def test_shut_between_words_open_inside_them(self):
        self.assertEqual(stick.mouth(self.WORDS, 0.5), 0)
        self.assertEqual(stick.mouth(self.WORDS, 1.55), 0)
        self.assertEqual(stick.mouth(self.WORDS, 3.0), 0)
        self.assertGreater(stick.mouth(self.WORDS, 2.6), 0.9)

    def test_one_flap_a_syllable(self):
        def flaps(a, z, fps=240):
            opened = [stick.mouth(self.WORDS, a + (z - a) * k / fps) > 0.5 for k in range(fps)]
            return sum(1 for x, y in zip([False] + opened, opened) if y and not x)
        self.assertEqual(stick.syllables('Working'), 2)
        self.assertEqual(stick.syllables('harder'), 2)
        self.assertEqual(stick.syllables('is'), 1)
        self.assertEqual(flaps(1.0, 1.5), 2)
        self.assertEqual(flaps(1.6, 2.0), 2)
        self.assertEqual(flaps(2.5, 2.7), 1)

    def test_a_caption_track_or_a_narration_gives_the_timings(self):
        track = vb.captions.Track([vb.captions.Word(t, a, z) for t, a, z in self.WORDS])
        self.assertEqual(stick.mouth(track, 2.6), stick.mouth(self.WORDS, 2.6))

        class Narration:
            pass
        n = Narration()
        n.track = track
        self.assertEqual(stick.mouth(n, 1.2), stick.mouth(self.WORDS, 1.2))

    def test_talking_opens_the_drawn_mouth(self):
        fig = vb.Stick(height=200)
        a, b = vb.Canvas(300, 300), vb.Canvas(300, 300)
        fig.draw(a, 'stand', 150, 280, talk=0)
        fig.draw(b, 'stand', 150, 280, talk=1)
        self.assertNotEqual(bytes(a.surface.get_data()), bytes(b.surface.get_data()))


class Facing(unittest.TestCase):
    def test_facing_left_mirrors_the_joints(self):
        fig = vb.Stick(height=H)
        for name in ('point', 'push', 'walk'):
            right = fig.joints(name, 200, GROUND, facing=1)
            left = fig.joints(name, 200, GROUND, facing=-1)
            for k in right:
                self.assertAlmostEqual(right[k][0] - 200, 200 - left[k][0], places=6)
                self.assertAlmostEqual(right[k][1], left[k][1], places=6)

    def test_facing_left_draws_the_mirror_image(self):
        fig = vb.Stick(height=200)
        right, left = vb.Canvas(300, 300), vb.Canvas(300, 300)
        fig.draw(right, 'point', 150, 280, face='happy', prop='mug')
        fig.draw(left, 'point', 150, 280, face='happy', prop='mug', facing=-1)
        a = flipped_pixels(right).getchannel('A')
        b = flipped_pixels(left).transpose(PILImage.FLIP_LEFT_RIGHT).getchannel('A')
        diff = sum(abs(x - y) for x, y in zip(a.tobytes(), b.tobytes())) / (300 * 300)
        self.assertLess(diff, 0.5)

    def test_a_turn_squashes_through_the_side_view(self):
        fig = vb.Stick()
        self.assertEqual(fig.turn(10, 10), 1)
        self.assertEqual(fig.turn(16, 10), -1)
        self.assertLess(abs(fig.turn(13, 10)), 0.05)
        box = fig.box('stand', 0, 0, facing=fig.turn(13, 10))
        self.assertLess(box.w, 0.5 * fig.box('stand', 0, 0).w)
        fig.draw(vb.Canvas(300, 300), 'stand', 150, 280, facing=fig.turn(13, 10))


class Props(unittest.TestCase):
    def test_a_held_prop_stays_at_the_hand(self):
        fig = vb.Stick(height=H)
        a, b = stick.POSES['hold'], stick.POSES['cheer']
        for kind in ('mug', 'phone', 'pencil', 'sign'):
            for age in (0, 4, 9, 30, 80):
                pose = fig.move(a, b, age)
                bare, held = vb.Canvas(500, 500), vb.Canvas(500, 500)
                fig.draw(bare, pose, 250, 450)
                drawn = fig.draw(held, pose, 250, 450, prop=kind)
                self.assertEqual(drawn.prop, drawn.joints['front_hand'])
                # the prop's own pixels: ink that the bare figure doesn't have, touching the hand
                x, y = drawn.prop
                pa, pb = bare.surface.get_data(), held.surface.get_data()
                stride = held.surface.get_stride()
                near = 0.08 * H
                touched = any(pa[yy * stride + 4 * xx + 3] != pb[yy * stride + 4 * xx + 3]
                              for yy in range(int(y - near), int(y + near))
                              for xx in range(int(x - near), int(x + near)))
                self.assertTrue(touched, f'{kind} at age {age}')

    def test_a_prop_in_the_back_hand_and_a_two_handed_sheet(self):
        fig = vb.Stick(height=H)
        drawn = fig.draw(vb.Canvas(500, 500), 'walk', 250, 450, prop=stick.prop('mug', hand='back'))
        self.assertEqual(drawn.prop, drawn.joints['back_hand'])
        drawn = fig.draw(vb.Canvas(500, 500), 'read', 250, 450, prop='map')
        self.assertEqual(drawn.prop, drawn.joints['front_hand'])
        with self.assertRaises(ValueError):
            stick.prop('mug', hand='left')

    def test_a_signs_words_read_the_right_way_whichever_way_it_faces(self):
        fig = vb.Stick(height=H)
        sign = stick.prop('sign', text='EXIT')
        right, left = vb.Canvas(500, 500), vb.Canvas(500, 500)
        fig.draw(right, 'hold', 250, 450, prop=sign)
        fig.draw(left, 'hold', 250, 450, prop=sign, facing=-1)
        # mirrored whole, the left one's board matches the right one's except for the words
        a = flipped_pixels(right).getchannel('A').tobytes()
        b = flipped_pixels(left).transpose(PILImage.FLIP_LEFT_RIGHT).getchannel('A').tobytes()
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()
