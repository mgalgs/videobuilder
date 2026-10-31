"""Pre-production: the bible's phase, option sets, scenes and script, and
the board API (preprod.py, preprod_api.py, fountain.py)."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from tests.fake_artbox import png
from tests.fixtures import settle
from tests.test_project import TempProject
from videobuilder import fountain
from videobuilder.editor import Editor, make_handler
from videobuilder.gitutil import git

VIDEO = 'promo/film'


class Server(TempProject):
    """fixtures.API's editor and server, without inheriting its own tests --
    tearDown order matters: renders/pool must stop *before* the tmp dir goes
    (TempProject.tearDown), not merely by addCleanup, which runs after it."""

    def setUp(self):
        super().setUp()
        git(self.root, 'branch', '-M', 'main')
        self.directory = self.root / 'promo'
        self.start(auto_land=False)

    def start(self, **kw):
        self.editor = Editor(self.root, unsandboxed_previews=True, **kw)
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.editor))
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def restart(self, **kw):
        self.stop()
        self.start(**kw)

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.editor.renders.close()
        self.editor.pool.close()

    def tearDown(self):
        self.stop()
        super().tearDown()

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

    def board(self):
        return self.get('/api/preprod?video=' + VIDEO)

    def commit_main(self):
        return git(self.root, 'rev-parse', 'main')


LOOK_SET = {
    'topic': 'look', 'id': 'look', 'question': 'Which look?',
    'options': [
        {'key': 'A', 'label': 'Moody', 'text': 'Low-key lighting, long shadows.',
         'swatches': ['#101418', '#5a4632']},
        {'key': 'B', 'label': 'Bright', 'text': 'High-key, saturated colour.'},
    ],
}


class Board(Server):
    def test_a_video_with_no_preproduction_files_shows_an_empty_board(self):
        body = self.board()
        self.assertEqual(body['phase'], 'production')
        self.assertEqual(body['sets'], [])
        self.assertEqual(body['characters'], [])
        self.assertEqual(body['script'], {'exists': False, 'draft': None, 'title': None, 'scenes': 0})
        self.assertEqual(body['scenes'], {'songs': [], 'scenes': [], 'seconds': 0, 'length': '0:00'})
        self.assertEqual(len(body['checklist']), 5)
        self.assertTrue(all(not item['settled'] for item in body['checklist']))
        self.assertEqual(body['problems'], [])


class Sets(Server):
    def test_look_set_round_trips_with_swatches(self):
        code, body = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        self.assertEqual(code, 200)
        self.assertTrue(body['changed'])
        got = next(s for s in self.board()['sets'] if s['id'] == 'look')
        self.assertEqual(got['options'][0]['swatches'], ['#101418', '#5a4632'])
        self.assertEqual(got['pick'], None)
        log = git(self.root, 'log', '-1', '--format=%s', '--', 'promo/bible/options/look.json')
        self.assertIn('look', log.lower())

    def test_character_set_round_trips(self):
        cset = {'topic': 'character', 'id': 'character-ana', 'character': 'ana', 'question': 'Which Ana?',
               'options': [{'key': 'A', 'label': 'Scrappy', 'text': 'Wiry, quick to smile.'},
                          {'key': 'B', 'label': 'Steady', 'text': 'Calm, watchful.'}]}
        code, body = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': cset})
        self.assertEqual(code, 200)
        got = next(s for s in self.board()['sets'] if s['id'] == 'character-ana')
        self.assertEqual(got['character'], 'ana')

    def test_scene_set_round_trips(self):
        sset = {'topic': 'scene', 'id': 'scene-opening', 'scene': 'opening', 'question': 'How does it open?',
               'options': [{'key': 'A', 'label': 'Quiet', 'text': 'A slow dawn over the lighthouse.'},
                          {'key': 'B', 'label': 'Storm', 'text': 'Straight into the storm.'}]}
        code, body = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': sset})
        self.assertEqual(code, 200)
        got = next(s for s in self.board()['sets'] if s['id'] == 'scene-opening')
        self.assertEqual(got['scene'], 'opening')

    def test_wrong_id_for_topic_is_rejected(self):
        bad = {**LOOK_SET, 'id': 'not-look'}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': bad})
        self.assertEqual(code, 400)

    def test_one_option_is_rejected(self):
        bad = {**LOOK_SET, 'options': LOOK_SET['options'][:1]}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': bad})
        self.assertEqual(code, 400)

    def test_five_options_is_rejected(self):
        five = [{'key': k, 'label': k, 'text': 'x'} for k in ('A', 'B', 'C', 'D')]
        five.append({'key': 'A', 'label': 'dup', 'text': 'y'})
        bad = {**LOOK_SET, 'options': five}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': bad})
        self.assertEqual(code, 400)

    def test_duplicate_keys_is_rejected(self):
        bad = {**LOOK_SET, 'options': [{'key': 'A', 'label': 'x', 'text': 'x'},
                                       {'key': 'A', 'label': 'y', 'text': 'y'}]}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': bad})
        self.assertEqual(code, 400)

    def test_bad_image_path_is_rejected(self):
        bad = {**LOOK_SET, 'options': [{'key': 'A', 'label': 'x', 'text': 'x',
                                        'image': '../etc/passwd', 'kind': 'vb'},
                                       LOOK_SET['options'][1]]}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': bad})
        self.assertEqual(code, 400)

    def test_image_without_kind_is_rejected(self):
        bad = {**LOOK_SET, 'options': [{'key': 'A', 'label': 'x', 'text': 'x',
                                        'image': 'bible/options/look/a.png'},
                                       LOOK_SET['options'][1]]}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': bad})
        self.assertEqual(code, 400)

    def test_upload_copies_the_attachment_in_as_kind_yours(self):
        att = self.editor.attachments.upload(VIDEO, 'ref.png', 'image/png', png((200, 50, 50)))
        cset = {'topic': 'character', 'id': 'character-ana', 'character': 'ana', 'question': 'Which Ana?',
               'options': [{'key': 'A', 'label': 'Scrappy', 'text': 'x', 'upload': att['id']},
                          {'key': 'B', 'label': 'Steady', 'text': 'y'}]}
        code, body = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': cset})
        self.assertEqual(code, 200)
        got = next(s for s in self.board()['sets'] if s['id'] == 'character-ana')
        self.assertEqual(got['options'][0]['kind'], 'yours')
        self.assertTrue(got['options'][0]['image'].endswith('.png'))
        self.assertTrue((self.directory / got['options'][0]['image']).is_file())

    def test_svg_upload_is_rejected(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        att = self.editor.attachments.upload(VIDEO, 'ref.svg', 'image/svg+xml', svg)
        cset = {'topic': 'character', 'id': 'character-ana', 'character': 'ana', 'question': 'Which Ana?',
               'options': [{'key': 'A', 'label': 'Scrappy', 'text': 'x', 'upload': att['id']},
                          {'key': 'B', 'label': 'Steady', 'text': 'y'}]}
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': cset})
        self.assertEqual(code, 400)

    def test_stale_base_is_refused(self):
        base = self.commit_main()
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': base, 'set': LOOK_SET})
        code, _ = self.post('/api/preprod/sets', {'video': VIDEO, 'base': base,
                                                   'set': {**LOOK_SET, 'question': 'Changed'}})
        self.assertEqual(code, 409)

    def test_delete_removes_the_file_and_its_images(self):
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        self.assertTrue((self.directory / 'bible/options/look.json').is_file())
        code, body = self.post('/api/preprod/sets/delete', {'video': VIDEO, 'id': 'look'})
        self.assertEqual(code, 200)
        self.assertFalse((self.directory / 'bible/options/look.json').is_file())
        self.assertEqual(self.board()['sets'], [])

    def test_delete_unknown_set_is_404(self):
        code, _ = self.post('/api/preprod/sets/delete', {'video': VIDEO, 'id': 'nope'})
        self.assertEqual(code, 404)


class Picks(Server):
    def setUp(self):
        super().setUp()
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})

    def test_pick_is_committed_and_shown(self):
        code, body = self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'B'})
        self.assertEqual(code, 200)
        got = next(s for s in self.board()['sets'] if s['id'] == 'look')
        self.assertEqual(got['pick'], 'B')
        log = git(self.root, 'log', '-1', '--format=%s')
        self.assertEqual(log, 'Pick: look B')

    def test_clearing_a_pick(self):
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'B'})
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': None})
        got = next(s for s in self.board()['sets'] if s['id'] == 'look')
        self.assertIsNone(got['pick'])

    def test_unknown_set_is_404(self):
        code, _ = self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'nope', 'key': 'A'})
        self.assertEqual(code, 404)

    def test_unknown_key_is_400(self):
        code, _ = self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'Z'})
        self.assertEqual(code, 400)


SCRIPT_V1 = (
    'Title: The Lighthouse Keeper\n'
    'Draft: 1\n'
    '\n'
    'INT. LIGHTHOUSE - NIGHT #1#\n'
    '\n'
    'Rain lashes the windows.\n'
    '\n'
    'ANA\n'
    "(whispering)\n"
    "It's coming.\n"
    '\n'
    'EXT. CLIFF - DAY\n'
    '\n'
    'CUT TO:\n'
)


class Script(Server):
    def test_script_round_trips_with_draft_and_numbered_scenes(self):
        code, body = self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(),
                                                        'text': SCRIPT_V1})
        self.assertEqual(code, 200)
        self.assertEqual(body['draft'], 1)
        self.assertEqual(body['title'], 'The Lighthouse Keeper')
        self.assertEqual([s['number'] for s in body['scenes']], [1, 2])
        types = [e['type'] for e in body['elements']]
        self.assertIn('character', types)
        self.assertIn('dialogue', types)
        self.assertIn('parenthetical', types)
        self.assertIn('transition', types)
        got = self.get('/api/preprod/script?video=' + VIDEO)
        self.assertEqual(got['text'], SCRIPT_V1)

    def test_drafts_list_grows_and_old_draft_is_readable(self):
        self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(), 'text': SCRIPT_V1})
        v2 = SCRIPT_V1.replace('Draft: 1', 'Draft: 2').replace('Ana', 'Ana')
        self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(), 'text': v2})
        got = self.get('/api/preprod/script?video=' + VIDEO)
        self.assertEqual({d['n'] for d in got['drafts']}, {1, 2})
        first = self.get(f'/api/preprod/script?video={VIDEO}&draft=1')
        self.assertEqual(first['draft'], 1)
        self.assertEqual(first['text'], SCRIPT_V1)

    def test_unknown_draft_is_404(self):
        self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(), 'text': SCRIPT_V1})
        try:
            self.get(f'/api/preprod/script?video={VIDEO}&draft=9')
            self.fail('expected 404')
        except urllib.error.HTTPError as e:
            with e:
                self.assertEqual(e.code, 404)

    def test_no_script_is_404(self):
        try:
            self.get('/api/preprod/script?video=' + VIDEO)
            self.fail('expected 404')
        except urllib.error.HTTPError as e:
            with e:
                self.assertEqual(e.code, 404)


class FountainParsing(unittest.TestCase):
    def test_forced_heading_section_and_transition(self):
        text = '.A FORCED HEADING\n\n# Act One\n\n>FORCED TRANSITION\n'
        parsed = fountain.parse(text)
        types = {e['text']: e['type'] for e in parsed['elements']}
        self.assertEqual(types['A FORCED HEADING'], 'heading')
        self.assertEqual(types['Act One'], 'section')
        self.assertEqual(types['FORCED TRANSITION'], 'transition')

    def test_scene_number_suffix_and_positional_fallback(self):
        text = 'INT. ROOM - DAY #5#\n\naction here\n\nEXT. YARD - DAY\n'
        parsed = fountain.parse(text)
        self.assertEqual([s['number'] for s in parsed['scenes']], [5, 2])

    def test_title_page_is_parsed_and_stripped(self):
        title, draft, body = fountain.parse_title_page('Title: X\nDraft: 3\n\nINT. ROOM - DAY\n')
        self.assertEqual((title, draft), ('X', 3))
        self.assertEqual(body, 'INT. ROOM - DAY\n')

    def test_no_title_page(self):
        title, draft, body = fountain.parse_title_page('INT. ROOM - DAY\n')
        self.assertEqual((title, draft), (None, None))


SCENES_BODY = {
    'songs': [{'id': 'song-1', 'name': 'Opening', 'file': 'opening.mp3', 'duration': 180, 'bpm': 90,
              'mood': 'tense', 'sections': [{'name': 'intro', 'start': 0, 'end': 20, 'text': ''}]}],
    'scenes': [{'id': 'opening', 'slugline': 'INT. LIGHTHOUSE - NIGHT', 'summary': 'Ana waits out the storm.',
               'seconds': 28, 'song': 'song-1', 'section': 'intro', 'from': 52, 'to': 80, 'look': None}],
}


class Scenes(Server):
    def test_scenes_round_trip_with_number_and_clocks(self):
        code, body = self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **SCENES_BODY})
        self.assertEqual(code, 200)
        scene = body['scenes']['scenes'][0]
        self.assertEqual(scene['number'], 1)
        self.assertEqual(scene['length'], '0:28')
        self.assertEqual(scene['from_clock'], '0:52')
        self.assertEqual(scene['to_clock'], '1:20')

    def test_reordering_renumbers(self):
        two = {'songs': SCENES_BODY['songs'],
              'scenes': [{**SCENES_BODY['scenes'][0], 'id': 'a'}, {**SCENES_BODY['scenes'][0], 'id': 'b'}]}
        self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **two})
        swapped = {'songs': two['songs'], 'scenes': list(reversed(two['scenes']))}
        code, body = self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **swapped})
        self.assertEqual([s['id'] for s in body['scenes']['scenes']], ['b', 'a'])
        self.assertEqual([s['number'] for s in body['scenes']['scenes']], [1, 2])

    def test_bad_scene_id_is_rejected(self):
        bad = {'songs': [], 'scenes': [{**SCENES_BODY['scenes'][0], 'id': 'Not Valid', 'song': None,
                                        'section': None, 'from': None, 'to': None}]}
        code, _ = self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **bad})
        self.assertEqual(code, 400)

    def test_to_before_from_is_rejected(self):
        bad = {'songs': SCENES_BODY['songs'],
              'scenes': [{**SCENES_BODY['scenes'][0], 'from': 80, 'to': 52}]}
        code, _ = self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **bad})
        self.assertEqual(code, 400)

    def test_unknown_song_id_is_rejected(self):
        bad = {'songs': [], 'scenes': [SCENES_BODY['scenes'][0]]}
        code, _ = self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **bad})
        self.assertEqual(code, 400)

    def test_duplicate_scene_ids_is_rejected(self):
        bad = {'songs': SCENES_BODY['songs'],
              'scenes': [SCENES_BODY['scenes'][0], SCENES_BODY['scenes'][0]]}
        code, _ = self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **bad})
        self.assertEqual(code, 400)


class Checklist(Server):
    def _item(self, id_):
        return next(i for i in self.board()['checklist'] if i['id'] == id_)

    def test_logline_settles_once_written(self):
        self.assertFalse(self._item('logline')['settled'])
        (self.directory / 'bible').mkdir(exist_ok=True)
        (self.directory / 'bible/bible.md').write_text('## Logline\n\nA keeper against a storm.\n')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'logline')
        self.assertTrue(self._item('logline')['settled'])

    def test_script_settles_once_a_scene_exists(self):
        self.assertFalse(self._item('script')['settled'])
        self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(), 'text': SCRIPT_V1})
        self.assertTrue(self._item('script')['settled'])

    def test_look_settles_once_its_set_is_picked(self):
        self.assertFalse(self._item('look')['settled'])
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        self.assertFalse(self._item('look')['settled'])
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'A'})
        self.assertTrue(self._item('look')['settled'])

    def test_cast_settles_once_every_character_set_is_picked(self):
        self.assertFalse(self._item('cast')['settled'])
        self.post('/api/film', {'video': VIDEO, 'base': self.commit_main(),
                                'characters': [{'name': 'Ana', 'description': 'The keeper'}]})
        self.assertTrue(self._item('cast')['settled'])  # a character with no alternatives set is settled already
        cset = {'topic': 'character', 'id': 'character-ana', 'character': 'ana', 'question': 'Which Ana?',
               'options': [{'key': 'A', 'label': 'Scrappy', 'text': 'x'},
                          {'key': 'B', 'label': 'Steady', 'text': 'y'}]}
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': cset})
        self.assertFalse(self._item('cast')['settled'])
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'character-ana', 'key': 'A'})
        self.assertTrue(self._item('cast')['settled'])

    def test_scenes_settle_once_every_scene_set_is_picked(self):
        self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(), **SCENES_BODY})
        self.assertTrue(self._item('scenes')['settled'])  # a scene with no alternatives set is already settled
        sset = {'topic': 'scene', 'id': 'scene-opening', 'scene': 'opening', 'question': 'How does it open?',
               'options': [{'key': 'A', 'label': 'Quiet', 'text': 'x'},
                          {'key': 'B', 'label': 'Storm', 'text': 'y'}]}
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': sset})
        self.assertFalse(self._item('scenes')['settled'])
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'scene-opening', 'key': 'A'})
        self.assertTrue(self._item('scenes')['settled'])


class MalformedFiles(Server):
    def test_a_malformed_set_is_skipped_and_reported(self):
        (self.directory / 'bible/options').mkdir(parents=True)
        (self.directory / 'bible/options/look.json').write_text('not json')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'bad set')
        body = self.board()
        self.assertEqual(body['sets'], [])
        self.assertEqual(len(body['problems']), 1)
        self.assertIn('options/look.json', body['problems'][0]['file'])


    def test_a_parseable_file_of_the_wrong_shape_is_skipped_and_reported(self):
        (self.directory / 'bible/options').mkdir(parents=True)
        (self.directory / 'bible/options/look.json').write_text(json.dumps(
            {'id': 'look', 'pick': 'A', 'choices': [{'key': 'A'}, {'key': 'B'}]}))
        (self.directory / 'bible/scenes.json').write_text(json.dumps(
            {'scenes': [{'id': 'opening', 'slugline': 'EXT. CLIFF - DUSK', 'summary': 'x'}]}))
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'hand-written bible files')
        body = self.board()
        self.assertEqual(body['sets'], [])
        self.assertEqual(body['scenes']['scenes'], [])
        self.assertEqual({p['file'] for p in body['problems']}, {'bible/options/look.json', 'bible/scenes.json'})
        self.assertFalse(next(c for c in body['checklist'] if c['id'] == 'look')['settled'])


class Image(Server):
    def test_committed_picture_is_served_and_traversal_is_refused(self):
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        att = self.editor.attachments.upload(VIDEO, 'ref.png', 'image/png', png((10, 20, 30)))
        cset = {'topic': 'character', 'id': 'character-ana', 'character': 'ana', 'question': 'Which Ana?',
               'options': [{'key': 'A', 'label': 'Scrappy', 'text': 'x', 'upload': att['id']},
                          {'key': 'B', 'label': 'Steady', 'text': 'y'}]}
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': cset})
        path = next(s for s in self.board()['sets'] if s['id'] == 'character-ana')['options'][0]['image']
        data = self.get(f'/api/preprod/image?video={VIDEO}&path={path}')
        self.assertTrue(data.startswith(b'\x89PNG'))
        for bad in ('../film.py', 'film.py', 'bible/options/nope.png'):
            try:
                self.get(f'/api/preprod/image?video={VIDEO}&path={bad}')
                self.fail(f'expected 404 for {bad}')
            except urllib.error.HTTPError as e:
                with e:
                    self.assertEqual(e.code, 404)


class PhaseFlip(Server):
    def test_setting_pre_production_commits_only_the_phase_file(self):
        before = self.commit_main()
        code, body = self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.assertEqual(code, 200)
        self.assertTrue(body['changed'])
        self.assertIsNone(body['note'])
        self.assertEqual(self.board()['phase'], 'pre-production')
        files = git(self.root, 'diff', '--name-only', before, 'main')
        self.assertEqual(files, 'promo/bible/phase.json')

    def test_asking_again_is_a_no_op(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        before = self.commit_main()
        code, body = self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.assertEqual(code, 200)
        self.assertFalse(body['changed'])
        self.assertEqual(self.commit_main(), before)


class RenderGate(Server):
    def test_no_render_is_requested_for_a_commit_in_pre_production(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        with mock.patch.object(self.editor.renders, 'request') as req:
            code, _ = self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(),
                                                         'text': SCRIPT_V1})
            self.assertEqual(code, 200)
            req.assert_not_called()
        self.post('/api/phase', {'video': VIDEO, 'phase': 'production'})
        with mock.patch.object(self.editor.renders, 'request') as req:
            v2 = SCRIPT_V1.replace('Draft: 1', 'Draft: 2')
            code, _ = self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(), 'text': v2})
            self.assertEqual(code, 200)
            req.assert_called_once()

    def test_main_moved_does_not_render_in_pre_production(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.editor._seen_main = None
        (self.directory / 'README.md').write_text('changed\n')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'external change')
        with mock.patch.object(self.editor.renders, 'request') as req:
            self.editor.main_moved()
            req.assert_not_called()

    def test_an_auto_landed_note_does_not_render_in_pre_production(self):
        from videobuilder.agents import FakeBackend
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.restart(auto_land=True, backend=FakeBackend(delay=0))
        with mock.patch.object(self.editor.renders, 'request') as req:
            code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'tweak it'})
            self.assertEqual(code, 200)
            settle(self.editor)
            landed = self.editor.notes.current(note['id'])
            self.assertEqual(landed['state'], 'landed')
            req.assert_not_called()

    def test_explicit_render_requests_refuse_409(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        for path in (f'/api/video?video={VIDEO}', f'/api/clip?video={VIDEO}&clip=x'):
            try:
                self.get(path)
                self.fail(f'expected 409 for {path}')
            except urllib.error.HTTPError as e:
                with e:
                    self.assertEqual(e.code, 409)
        code, body = self.post('/api/video/retry', {'video': VIDEO, 'commit': self.commit_main(), 'format': '16x9'})
        self.assertEqual(code, 409)

    def test_frame_stills_still_work_in_pre_production(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        png_bytes = self.get(f'/api/frame?video={VIDEO}&frame=0&format=16x9')
        self.assertTrue(png_bytes.startswith(b'\x89PNG'))


class StartProduction(Server):
    def test_production_note_lists_open_items_and_decides_itself(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        code, body = self.post('/api/phase', {'video': VIDEO, 'phase': 'production'})
        self.assertEqual(code, 200)
        self.assertTrue(body['changed'])
        note = body['note']
        self.assertEqual(note['said'], 'Start production')
        self.assertIn('bible/script.fountain', note['text'])
        self.assertIn('bible/scenes.json', note['text'])
        self.assertIn('Look', note['text'])
        self.assertIn('say in your reply', note['text'])
        self.assertEqual(self.board()['phase'], 'production')

    def test_going_back_to_pre_production_sends_no_note(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/phase', {'video': VIDEO, 'phase': 'production'})
        code, body = self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.assertEqual(code, 200)
        self.assertIsNone(body['note'])
        self.assertEqual(self.board()['phase'], 'pre-production')

    def test_note_cap_refusal_leaves_the_phase_unchanged(self):
        self.restart(auto_land=False, account_daily_note_cap=1)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'already used up the cap'})
        code, body = self.post('/api/phase', {'video': VIDEO, 'phase': 'production'})
        self.assertEqual(code, 429)
        self.assertEqual(self.board()['phase'], 'pre-production')


if __name__ == '__main__':
    unittest.main()
