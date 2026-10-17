"""Generated pictures (pictures.py and the /api/pictures routes), against a
fake artbox on a local port: nothing here touches the real network."""
import io
import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from PIL import Image

from http.server import ThreadingHTTPServer

from tests.fake_artbox import FakeArtbox, png
from videobuilder import pictures as pictures_module
from videobuilder.editor import Editor, make_handler
from videobuilder.pictures import Artbox, ArtboxError, check_base_url, valid_file_name, valid_job_id
from tests.test_project import TempProject

VIDEO = 'promo/film'


class Server(TempProject):
    """fixtures.API's editor and server, without inheriting its own tests."""

    def setUp(self):
        super().setUp()
        self.start()

    def start(self, **kw):
        self.editor = Editor(self.root, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(self.editor.pool.close)
        self.addCleanup(self.editor.renders.close)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.editor))
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            body = r.read()
            return json.loads(body) if r.headers.get('Content-Type') == 'application/json' else body

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())


class Base(Server):
    def setUp(self):
        self.fake = FakeArtbox()
        self.addCleanup(self.fake.close)
        self.clock = 0
        super().setUp()

    def start(self, **kw):
        kw.setdefault('artbox_url', self.fake.base)
        super().start(**kw)

    def make(self, prompt='a red teapot', n=2, cutout=False, **extra):
        return self.post('/api/pictures', {'video': VIDEO, 'prompt': prompt, 'n': n, 'cutout': cutout, **extra})

    def jobs(self):
        return self.get('/api/pictures?video=' + VIDEO)['jobs']

    def remote_id(self, local_id):
        return next(j for j in self.editor.pictures._load(VIDEO) if j['id'] == local_id)['remote']

    def poll(self):
        """One background tick, late enough that every job is due."""
        self.clock += 120
        with mock.patch('time.time', return_value=time.time() + self.clock):
            self.editor.pictures.tick()

    def status(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            with e:
                return e.code


class Flow(Base):
    def test_start_queued_done_files_fetched_and_added_to_a_note(self):
        code, job = self.make()
        self.assertEqual(code, 201, job)
        self.assertEqual((job['status'], job['prompt'], job['n'], job['cutout'], job['pictures']),
                         ('waiting', 'a red teapot', 2, False, []))
        sent = self.fake.submitted[-1]
        self.assertEqual((sent['prompt'], sent['n'], sent['size'], sent['matte']),
                         ('a red teapot', 2, '1024x1024', False))
        remote = self.remote_id(job['id'])

        self.poll()  # still queued
        self.assertEqual(self.jobs()[0]['status'], 'waiting')
        self.fake.jobs[remote]['state'] = 'running'
        self.poll()
        self.assertEqual(self.jobs()[0]['status'], 'making')
        self.fake.finish(remote)
        self.poll()
        [done] = self.jobs()
        self.assertEqual(done['status'], 'done')
        self.assertEqual(done['pictures'], [{'index': 0, 'cutout': False, 'posable': True},
                                            {'index': 1, 'cutout': False, 'posable': True}])

        with urllib.request.urlopen(f'{self.base}/api/pictures/{job["id"]}/0?video={VIDEO}', timeout=20) as r:
            self.assertEqual(r.headers['Content-Type'], 'image/webp')
            self.assertIn('max-age', r.headers['Cache-Control'])
            self.assertEqual(Image.open(io.BytesIO(r.read())).format, 'WEBP')
        full = self.get(f'/api/pictures/{job["id"]}/1?video={VIDEO}&full=1')
        self.assertTrue(full.startswith(b'\x89PNG'))
        self.assertEqual(self.status(f'/api/pictures/{job["id"]}/1?video={VIDEO}&cutout=1'), 404)
        self.assertEqual(self.status(f'/api/pictures/{job["id"]}/3?video={VIDEO}'), 404)

        code, record = self.post(f'/api/pictures/{job["id"]}/1/attach', {'video': VIDEO})
        self.assertEqual(code, 201, record)
        self.assertEqual((record['name'], record['type'], set(record)),
                         ('a-red-teapot-2.png', 'image/png', {'id', 'name', 'type', 'size'}))
        self.assertEqual(self.get('/api/attachments/' + record['id']), full)
        # It is an ordinary attachment: a note can carry it.
        self.editor.attachments.validate(VIDEO, [record['id']])

    def test_cutout_sends_a_grey_background_and_fetches_the_matte(self):
        code, job = self.make('steam rising from a cup', n=1, cutout=True)
        self.assertEqual(code, 201, job)
        self.assertEqual(job['prompt'], 'steam rising from a cup')
        sent = self.fake.submitted[-1]
        self.assertEqual(sent['prompt'], 'steam rising from a cup, on a plain mid-grey background')
        self.assertIs(sent['matte'], True)
        self.fake.finish(self.remote_id(job['id']))
        self.poll()
        [done] = self.jobs()
        self.assertEqual((done['prompt'], done['pictures']), ('steam rising from a cup', [{'index': 0, 'cutout': True, 'posable': True}]))
        thumb = Image.open(io.BytesIO(self.get(f'/api/pictures/{job["id"]}/0?video={VIDEO}&cutout=1')))
        self.assertEqual(thumb.mode, 'RGBA')
        self.assertEqual(thumb.getpixel((0, 0))[3], 0)
        code, record = self.post(f'/api/pictures/{job["id"]}/0/attach', {'video': VIDEO, 'cutout': True})
        self.assertEqual((code, record['name']), (201, 'steam-rising-from-a-cup-1-cutout.png'))
        code, record = self.post(f'/api/pictures/{job["id"]}/0/attach', {'video': VIDEO, 'cutout': False})
        self.assertEqual((code, record['name']), (201, 'steam-rising-from-a-cup-1.png'))

    def test_failed_job_shows_failed_and_retry_starts_it_again(self):
        _, job = self.make()
        self.fake.fail(self.remote_id(job['id']))
        self.poll()
        [failed] = self.jobs()
        self.assertEqual(failed['status'], 'failed')
        self.assertTrue(failed['message'])
        code, again = self.post(f'/api/pictures/{job["id"]}/retry', {'video': VIDEO})
        self.assertEqual((code, again['id'], again['status']), (200, job['id'], 'waiting'))
        self.assertEqual(len(self.fake.submitted), 2)
        self.fake.finish(self.remote_id(job['id']))
        self.poll()
        self.assertEqual(self.jobs()[0]['status'], 'done')
        code, result = self.post(f'/api/pictures/{job["id"]}/retry', {'video': VIDEO})
        self.assertEqual(code, 409, result)

    def test_a_job_waiting_over_twelve_hours_is_given_up(self):
        _, job = self.make()
        with mock.patch('time.time', return_value=time.time() + 12 * 3600 + 60):
            self.editor.pictures.tick()
        [failed] = self.jobs()
        self.assertEqual(failed['status'], 'failed')
        self.assertIn('waited too long', failed['message'])

    def test_a_job_the_service_has_forgotten_fails(self):
        _, job = self.make()
        del self.fake.jobs[self.remote_id(job['id'])]
        self.poll()
        self.assertEqual(self.jobs()[0]['status'], 'failed')

    def test_an_unreachable_service_leaves_jobs_waiting(self):
        _, job = self.make()
        self.fake.close()
        self.poll()
        [still] = self.jobs()
        self.assertEqual(still['status'], 'waiting')

    def test_resumes_pending_jobs_after_a_restart(self):
        _, job = self.make(n=1)
        self.editor.renders.close()
        self.editor.pool.close()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.fake.finish(self.remote_id(job['id']))
        self.start()  # a new Editor on the same state dir
        self.assertEqual(self.jobs()[0]['status'], 'waiting')
        self.poll()
        [done] = self.jobs()
        self.assertEqual((done['id'], done['status'], len(done['pictures'])), (job['id'], 'done', 1))

    def test_polls_back_off(self):
        _, job = self.make()
        delays = []
        now = time.time()
        for i in range(7):
            now += 60
            with mock.patch('time.time', return_value=now):
                self.editor.pictures.tick()
            record = self.editor.pictures._load(VIDEO)[0]
            delays.append(round(record['next_poll'] - now))
        self.assertEqual(delays, [10, 15, 20, 30, 30, 30, 30])

    def test_newest_first(self):
        self.make('first')
        self.make('second')
        self.assertEqual([j['prompt'] for j in self.jobs()], ['second', 'first'])

    def test_gpu_status(self):
        self.assertEqual(self.get('/api/pictures/gpu'), {'gpu': 'free'})
        self.editor.pictures.artbox._gpu = (0, 'unknown')
        self.fake.gpu = {'state': 'busy', 'queue': 3}
        self.assertEqual(self.get('/api/pictures/gpu'), {'gpu': 'busy'})
        self.editor.pictures.artbox._gpu = (0, 'unknown')
        self.fake.gpu = {'something': 'else'}
        self.assertEqual(self.get('/api/pictures/gpu'), {'gpu': 'unknown'})

    def test_service_down_when_starting_is_a_plain_502(self):
        self.fake.close()
        code, result = self.make()
        self.assertEqual(code, 502)
        self.assertIn("isn't answering", result['error'])
        self.assertEqual(self.jobs(), [])

    def test_store_over_its_cap_drops_the_oldest_sets(self):
        self.editor.pictures.video_max_bytes = 1
        ids = []
        for prompt in ('one', 'two'):
            _, job = self.make(prompt, n=1)
            ids.append(job['id'])
            self.fake.finish(self.remote_id(job['id']))
            self.poll()
        self.assertEqual([j['prompt'] for j in self.jobs()], ['two'])
        self.assertEqual(self.status(f'/api/pictures/{ids[0]}/0?video={VIDEO}'), 404)


class Limits(Base):
    def test_prompt_count_and_cutout_validation(self):
        for body, word in (({'prompt': ''}, 'Describe'), ({'prompt': '   '}, 'Describe'),
                           ({'prompt': 'x' * 1001}, 'too long'), ({'n': 0}, '1 to 4'), ({'n': 5}, '1 to 4'),
                           ({'n': '2'}, '1 to 4'), ({'n': True}, '1 to 4'), ({'cutout': 'yes'}, 'cutout')):
            code, result = self.post('/api/pictures', {'video': VIDEO, 'prompt': 'ok', 'n': 2, **body})
            self.assertEqual(code, 400, body)
            self.assertIn(word, result['error'], body)
        self.assertEqual(self.make('x' * 1000, n=4)[0], 201)
        self.assertEqual(self.fake.submitted[-1]['n'], 4)

    def test_at_most_two_pending_per_video(self):
        self.assertEqual(self.make()[0], 201)
        self.assertEqual(self.make()[0], 201)
        code, result = self.make()
        self.assertEqual(code, 429)
        self.assertIn('already on the way', result['error'])
        self.assertEqual(len(self.fake.submitted), 2)

    def test_retry_also_counts_toward_the_pending_limit(self):
        _, first = self.make()
        self.fake.fail(self.remote_id(first['id']))
        self.poll()
        self.make()
        self.make()
        code, _ = self.post(f'/api/pictures/{first["id"]}/retry', {'video': VIDEO})
        self.assertEqual(code, 429)

    def test_daily_picture_cap(self):
        self.editor.pictures.daily_cap = 5
        _, job = self.make(n=4)
        self.fake.finish(self.remote_id(job['id']))
        self.poll()
        code, result = self.make(n=2)
        self.assertEqual(code, 429)
        self.assertIn('1 picture left', result['error'])
        self.assertEqual(self.make(n=1)[0], 201)
        code, result = self.make(n=1)
        self.assertEqual(code, 429)
        self.assertIn("today's limit of 5 pictures", result['error'])
        # A day later the window has moved on.
        with mock.patch('time.time', return_value=time.time() + 24 * 3600 + 5):
            self.editor.pictures.check_daily_cap('anonymous', False, 4)

    def test_daily_cap_is_per_author_and_never_binds_an_admin(self):
        pics = self.editor.pictures
        pics.daily_cap = 2
        self.make(n=2)
        with self.assertRaises(pictures_module.PictureError):
            pics.check_daily_cap('anonymous', False, 1)
        pics.check_daily_cap('someone else', False, 2)
        pics.check_daily_cap('anonymous', True, 4)

    def test_an_unlimited_account_is_not_held_to_the_cap(self):
        pics = self.editor.pictures
        pics.daily_cap = 2
        self.make(n=2)
        limits = {'anonymous': {'kind': 'unlimited'}, 'someone': {'kind': 'custom', 'notes': 9, 'cost_usd': None}}
        accounts = mock.Mock(get_limit=lambda name: limits.get(name, {'kind': 'default'}))
        library = mock.Mock(accounts=accounts, picture_dirs=lambda: [pics.root])
        with mock.patch.object(self.editor, 'library', library):
            pics.check_daily_cap('anonymous', False, 2)
            pics.check_daily_cap('someone', False, 2)
            with self.assertRaises(pictures_module.PictureError):
                pics.check_daily_cap('someone', False, 3)

    def test_the_cap_comes_from_config_or_the_flag(self):
        self.assertEqual(self.editor.pictures.daily_cap, 40)
        editor = Editor(self.root, artbox_url=self.fake.base, account_daily_picture_cap=7)
        self.addCleanup(editor.renders.close)
        self.addCleanup(editor.pool.close)
        self.assertEqual(editor.pictures.daily_cap, 7)
        with self.assertRaises(ValueError):
            Editor(self.root, artbox_url=self.fake.base, account_daily_picture_cap=0)


class Poses(Base):
    def done_set(self, prompt='a cartoon fox, flat colours, thick outlines, on a white background', n=2, cutout=True):
        _, job = self.make(prompt, n=n, cutout=cutout)
        self.fake.finish(self.remote_id(job['id']))
        self.poll()
        return job

    def pose(self, job_id, index=1, pose='waving, arm raised to the right', video=VIDEO):
        return self.post(f'/api/pictures/{job_id}/{index}/pose', {'video': video, 'pose': pose})

    def test_another_pose_redraws_that_picture_from_its_seed(self):
        base = self.done_set()
        remote = self.remote_id(base['id'])
        name = self.fake.jobs[remote]['images'][1]['name']
        code, job = self.pose(base['id'])
        self.assertEqual(code, 201, job)
        self.assertEqual((job['prompt'], job['n'], job['cutout'], job['status']),
                         ('waving, arm raised to the right', 2, True, 'waiting'))
        self.assertEqual(job['poseOf'], {'id': base['id'], 'index': 1, 'cutout': True,
                                         'prompt': 'a cartoon fox, flat colours, thick outlines, on a white background'})
        sent = self.fake.submitted[-1]
        self.assertEqual((sent['refMode'], sent['refs'], sent['seed'], sent['n'], sent['matte']),
                         ('KI', [f'{remote}/{name}'], 4, 2, True))
        self.assertEqual(sent['prompt'],
                         'the same cartoon fox from image 1, now waving, arm raised towards the right edge of the '
                         'image. Keep the same face, colours, proportions and outline weight. a cartoon fox, flat '
                         'colours, thick outlines, on a plain mid-grey background')
        # It is an ordinary set from here on: polled, fetched, and itself a source for more poses.
        self.fake.finish(self.remote_id(job['id']))
        self.poll()
        done = next(j for j in self.jobs() if j['id'] == job['id'])
        self.assertEqual((done['status'], len(done['pictures']), done['pictures'][0]['posable']), ('done', 2, True))
        code, again = self.pose(job['id'], 0, 'sitting')
        self.assertEqual(code, 201, again)
        self.assertEqual(again['poseOf']['prompt'], 'waving, arm raised to the right')
        sent = self.fake.submitted[-1]
        self.assertEqual(sent['refs'], [f"{self.remote_id(job['id'])}/"
                                        f"{self.fake.jobs[self.remote_id(job['id'])]['images'][0]['name']}"])
        # Still the fox of the first description, not "waving" of the last pose.
        self.assertTrue(sent['prompt'].startswith('the same cartoon fox from image 1, now sitting. '), sent['prompt'])
        self.assertIn('a cartoon fox, flat colours, thick outlines, on a plain', sent['prompt'])

    def test_matte_follows_the_source_and_a_retry_resends_the_reference(self):
        base = self.done_set('a teapot', n=1, cutout=False)
        code, job = self.pose(base['id'], 0, 'tipped over')
        self.assertEqual(code, 201, job)
        first = self.fake.submitted[-1]
        self.assertIs(first['matte'], False)
        self.assertTrue(first['prompt'].startswith('the same teapot from image 1, now tipped over. '))
        self.assertTrue(first['prompt'].endswith('a teapot, on a plain mid-grey background'))
        self.fake.fail(self.remote_id(job['id']))
        self.poll()
        self.assertEqual(self.post(f'/api/pictures/{job["id"]}/retry', {'video': VIDEO})[0], 200)
        again = self.fake.submitted[-1]
        self.assertEqual(again, first)

    def test_the_seed_is_read_from_the_name_or_left_out(self):
        _, job = self.make('a fox', n=1)
        remote = self.remote_id(job['id'])
        self.fake.finish(remote)
        del self.fake.jobs[remote]['images'][0]['seed']
        self.poll()
        self.pose(job['id'], 0)
        self.assertEqual(self.fake.submitted[-1]['seed'], 3)  # from "..._seed3_..."
        _, job = self.make('a fox', n=1)
        remote = self.remote_id(job['id'])
        self.fake.finish(remote)
        image = self.fake.jobs[remote]['images'][0]
        del image['seed']
        self.fake.files[f'/files/{remote}/fox.png'] = self.fake.files.pop(f'/files/{remote}/{image["name"]}')
        image['name'] = 'fox.png'
        self.poll()
        self.assertEqual(self.pose(job['id'], 0)[0], 201)
        self.assertNotIn('seed', self.fake.submitted[-1])
        self.assertEqual(self.fake.submitted[-1]['refs'], [f'{remote}/fox.png'])

    def test_refused_sources(self):
        _, pending = self.make('a fox')
        code, result = self.pose(pending['id'], 0)
        self.assertEqual(code, 409, result)
        self.fake.fail(self.remote_id(pending['id']))
        self.poll()
        self.assertEqual(self.pose(pending['id'], 0)[0], 409)
        base = self.done_set(n=1)
        self.assertEqual(self.pose(base['id'], 1)[0], 404)  # no second picture
        self.assertEqual(self.pose('0' * 16, 0)[0], 404)
        self.assertEqual(self.pose(base['id'], 0, '   ')[0], 400)
        self.assertEqual(self.pose(base['id'], 0, 'x' * 301)[0], 400)
        self.assertEqual(self.pose(base['id'], 0, None)[0], 400)
        # The same set, asked for from another video, is not there.
        other = 'promo/other'
        (self.root / 'promo' / 'other.py').write_text(self.film.read_text())
        self.assertIn(other, [v.id for v in self.editor.project.videos()])
        code, result = self.pose(base['id'], 0, video=other)
        self.assertEqual(code, 404, result)
        # A client can't name its own reference: anything but the pose is ignored.
        sent = len(self.fake.submitted)
        code, job = self.post(f'/api/pictures/{base["id"]}/0/pose',
                              {'video': VIDEO, 'pose': 'sitting', 'refs': ['evil/x.png'], 'seed': 1, 'n': 4})
        self.assertEqual(code, 201, job)
        self.assertEqual(len(self.fake.submitted), sent + 1)
        self.assertEqual(self.fake.submitted[-1]['refs'], [f'{self.remote_id(base["id"])}/'
                                                           f'{self.fake.jobs[self.remote_id(base["id"])]["images"][0]["name"]}'])
        self.assertEqual(job['n'], 2)

    def test_a_picture_from_before_poses_is_not_posable(self):
        base = self.done_set(n=1)
        jobs = self.editor.pictures._load(VIDEO)
        del jobs[0]['pictures'][0]['name']
        self.editor.pictures._save(VIDEO, jobs)
        self.assertIs(self.jobs()[0]['pictures'][0]['posable'], False)
        self.assertEqual(self.pose(base['id'], 0)[0], 409)

    def test_poses_count_toward_the_daily_cap_and_the_pending_limit(self):
        base = self.done_set(n=2)
        self.editor.pictures.daily_cap = 3
        code, result = self.pose(base['id'], 0)
        self.assertEqual(code, 429, result)
        self.assertIn('1 picture left', result['error'])
        self.editor.pictures.daily_cap = 40
        self.assertEqual(self.pose(base['id'], 0)[0], 201)
        self.assertEqual(self.pose(base['id'], 1)[0], 201)
        code, result = self.pose(base['id'], 0)
        self.assertEqual(code, 429, result)
        self.assertIn('already on the way', result['error'])


class PosePrompt(unittest.TestCase):
    def test_subject_and_style(self):
        pose_prompt = pictures_module.pose_prompt
        self.assertEqual(pictures_module._subject('A small orange fox standing on a rock, cartoon'), 'small orange fox')
        self.assertEqual(pictures_module._subject('the robot with a red scarf, waving'), 'robot with a red scarf')
        self.assertEqual(pictures_module._subject('...'), 'character')
        self.assertEqual(pictures_module._style('a fox, flat colours, on a white background.'), 'a fox, flat colours')
        out = pose_prompt('a fox', 'pointing to the left.')
        self.assertIn('now pointing towards the left edge of the image. Keep', out)
        # Already said about the picture, or about a hand: left alone.
        self.assertIn('now pointing towards the left edge of the image. Keep',
                      pose_prompt('a fox', 'pointing towards the left edge of the image'))
        self.assertIn('raising its left paw', pose_prompt('a fox', 'raising its left paw'))
        # The character's own side is not the image's: rewriting it would mirror the pose.
        self.assertIn('now pointing to his left. Keep', pose_prompt('a fox', 'pointing to his left'))
        self.assertIn('now looking towards their right. Keep', pose_prompt('a fox', 'looking towards their right'))
        # Nouns that end in -ing are part of the subject, not what it is doing.
        self.assertEqual(pictures_module._subject('a cartoon viking with a beard'), 'cartoon viking with a beard')
        self.assertEqual(pictures_module._subject('a cute duckling'), 'cute duckling')
        self.assertEqual(pictures_module._subject('A watercolour painting of a fox'), 'watercolour painting of a fox')
        self.assertEqual(pictures_module._subject('a duckling swimming in a pond'), 'duckling')


class NetworkSafety(Base):
    def test_validators(self):
        for good in ('20261016-142016', 'abc_DEF-1'):
            self.assertTrue(valid_job_id(good), good)
        for bad in ('', '../x', 'a/b', '.hidden', 'a b', 'a' * 65, 'x%2f', None, 3, 'http://evil'):
            self.assertFalse(valid_job_id(bad), bad)
        for good in ('2026-10-16-14h20m43s_seed3_isolated red teapot.png', "a cat's hat (blue), 2+2.png",
                     'café.png', 'What a day!.png', 'a cat: asleep?.png', '50% "off"; #1 — now.png',
                     'x%2f.png', 'a' * 1100 + '.png'):
            self.assertTrue(valid_file_name(good), good)
        for bad in ('../x.png', 'a/b.png', 'a\\b.png', '.x.png', 'x..png', 'http://evil.example/x.png',
                    '/etc/passwd.png', 'x.png?y', 'x.jpg', 'x\n.png', 'x\x00.png', 'a' * 2100 + '.png', '', None):
            self.assertFalse(valid_file_name(bad), bad)
        for bad in ('ftp://x', 'http://', 'http://u:p@host', 'http://host/?q=1', 'http://host/#f', 'host:80'):
            with self.assertRaises(ValueError):
                check_base_url(bad)
        self.assertEqual(check_base_url('https://art.example/base/'), 'https://art.example/base')

    def test_hostile_names_and_absolute_urls_are_refused(self):
        good = '2026-10-16-14h20m40s_seed3_ok.png'
        images = [{'name': '../../etc/passwd.png', 'seed': 1},
                  {'name': self.fake.base + '/files/evil.png', 'seed': 2},
                  {'name': good, 'seed': 3, 'matte': 'http://127.0.0.1:1/steal_matte.png'}]
        _, job = self.make(n=3, cutout=True)
        remote = self.remote_id(job['id'])
        self.fake.files[f'/files/{remote}/{good}'] = png((1, 2, 3))
        self.fake.overrides[remote] = {'id': remote, 'state': 'done', 'images': images}
        self.poll()
        [done] = self.jobs()
        self.assertEqual(done['pictures'], [{'index': 0, 'cutout': False, 'posable': True}])
        fetched = [p for m, p in self.fake.requests if p.startswith('/files/')]
        self.assertEqual(fetched, [f'/files/{remote}/{good}'])

    def test_a_done_job_with_only_hostile_names_fails(self):
        _, job = self.make(n=1)
        remote = self.remote_id(job['id'])
        self.fake.overrides[remote] = {'id': remote, 'state': 'done',
                                       'images': [{'name': 'https://elsewhere.example/a.png'}]}
        self.poll()
        self.assertEqual(self.jobs()[0]['status'], 'failed')

    def test_prompts_with_punctuation_come_back(self):
        for prompt in ('What a day!', 'a cat: asleep?', '50% "off"; #1 — now', 'a/b'):
            _, job = self.make(prompt=prompt, n=1)
            self.fake.finish(self.remote_id(job['id']))
            self.poll()
            [done] = [j for j in self.jobs() if j['id'] == job['id']]
            if prompt == 'a/b':
                self.assertEqual(done['status'], 'failed')
            else:
                self.assertEqual(done['status'], 'done', prompt)
                self.assertEqual(self.status(f'/api/pictures/{job["id"]}/0?video={VIDEO}'), 200)

    def test_a_job_whose_names_cant_be_used_offers_no_retry(self):
        _, job = self.make(n=1)
        remote = self.remote_id(job['id'])
        self.fake.overrides[remote] = {'id': remote, 'state': 'done', 'images': [{'name': 'a/b.png'}]}
        self.poll()
        [failed] = self.jobs()
        self.assertEqual(failed['status'], 'failed')
        self.assertFalse(failed['retryable'])
        self.assertIn("can't use", failed['message'])
        code, result = self.post(f'/api/pictures/{job["id"]}/retry', {'video': VIDEO})
        self.assertEqual(code, 409)
        self.assertIn("can't use", result['error'])

    def test_a_hostile_job_id_from_the_service_is_refused(self):
        with mock.patch.object(Artbox, '_json', return_value={'id': '../../admin', 'state': 'queued'}):
            code, result = self.make()
        self.assertEqual(code, 502, result)
        self.assertEqual(self.jobs(), [])

    def test_redirects_are_not_followed(self):
        other = FakeArtbox()
        self.addCleanup(other.close)
        self.fake.redirect = other.base + '/api/gpu'
        artbox = Artbox(self.fake.base)
        with self.assertRaises(ArtboxError) as e:
            artbox.job('20261016-142000')
        self.assertEqual(e.exception.status, 302)
        self.assertEqual(other.requests, [])

    def test_oversized_and_non_png_files_are_skipped(self):
        _, job = self.make(n=2)
        remote = self.remote_id(job['id'])
        self.fake.finish(remote)
        names = [i['name'] for i in self.fake.jobs[remote]['images']]
        self.fake.files[f'/files/{remote}/{names[0]}'] = b'<html>not a png</html>'
        with mock.patch.object(pictures_module, 'FILE_MAX_BYTES', 10 ** 6):
            self.fake.files[f'/files/{remote}/{names[1]}'] = b'\x89PNG\r\n\x1a\n' + b'0' * (10 ** 6 + 10)
            self.poll()
        record = self.editor.pictures._load(VIDEO)[0]
        # The oversized read is a fetch failure (retried later), the HTML a skipped picture.
        self.assertEqual(record['status'], 'making')
        self.assertEqual(record['fetch_failures'], 1)

    def test_bad_ids_in_routes(self):
        _, job = self.make()
        self.assertEqual(self.status(f'/api/pictures/../0?video={VIDEO}'), 404)
        self.assertEqual(self.status(f'/api/pictures/{"0" * 16}/0?video={VIDEO}'), 404)
        self.assertEqual(self.post(f'/api/pictures/{"0" * 16}/retry', {'video': VIDEO})[0], 404)
        self.assertEqual(self.post(f'/api/pictures/{job["id"]}/0/attach', {'video': VIDEO})[0], 404)


class NotConfigured(Server):
    def test_every_route_is_404_and_the_page_hides_the_button(self):
        self.assertIsNone(self.editor.pictures)
        for path in ('/api/pictures?video=' + VIDEO, '/api/pictures/gpu', f'/api/pictures/{"0" * 16}/0?video={VIDEO}'):
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.get(path)
            e.exception.close()
            self.assertEqual(e.exception.code, 404, path)
        for path, body in (('/api/pictures', {'video': VIDEO, 'prompt': 'x', 'n': 1}),
                           (f'/api/pictures/{"0" * 16}/retry', {'video': VIDEO}),
                           (f'/api/pictures/{"0" * 16}/0/attach', {'video': VIDEO})):
            self.assertEqual(self.post(path, body)[0], 404, path)
        html = self.get('/')
        self.assertIn(b'id="pictures-button"', html)
        self.assertIn(b'hidden', html.split(b'id="pictures-button"', 1)[1].split(b'>', 1)[0])


if __name__ == '__main__':
    unittest.main()
