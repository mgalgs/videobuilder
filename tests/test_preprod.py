"""Pre-production: the bible's phase, option sets, scenes and script, and
the board API (preprod.py, preprod_api.py, fountain.py)."""
import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from tests.fake_artbox import FakeArtbox, png
from tests.fixtures import AccountMixin, LibraryFixture, settle
from tests.test_project import TempProject
from videobuilder import fountain, preprod
from videobuilder.editor import Editor, make_handler
from videobuilder.gitutil import git
from videobuilder.notes import AgentBackend, AgentStatus

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
        self.assertEqual(body['concepts'], [])
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


class PromptShapes(unittest.TestCase):
    def test_the_prompt_examples_are_files_the_board_accepts(self):
        import re
        from videobuilder import prompt
        text = '\n'.join(prompt._preproduction_lines({'concepts': True}))
        scenes, option_set = re.findall(r'```json\n(.*?)\n```', text, re.S)[:2]
        preprod.parse_scenes(json.loads(scenes))
        preprod.parse_option_set(json.loads(option_set))
        self.assertIn('"ask first"', text)


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


class RecorderBackend(AgentBackend):
    """Takes each submitted note's prompt, then fails at once so the next
    note (if any) goes out right away."""
    name = 'recorder'

    def __init__(self):
        self.seen = []

    def submit(self, payload):
        self.seen.append(Path(payload['note_file']).read_text())
        return 'rec:' + payload['id']

    def poll(self, handle):
        return AgentStatus('failed', 'done')


class FlakyBackend(AgentBackend):
    """Fails the first submission outright (before a handle is ever
    returned), then succeeds on every one after."""
    name = 'flaky'

    def __init__(self):
        self.calls = 0
        self.seen = []

    def submit(self, payload):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError('boom')
        self.seen.append(Path(payload['note_file']).read_text())
        return 'h:' + payload['id']

    def poll(self, handle):
        return AgentStatus('failed', 'done')


class QuestionBackend(AgentBackend):
    """Always replies with the same picture-choice ```questions block."""
    name = 'question'

    def __init__(self, questions):
        self.questions = questions

    def submit(self, payload):
        return 'h:' + payload['id']

    def poll(self, handle):
        reply = 'Pick a look.\n\n```questions\n' + json.dumps({'questions': self.questions}) + '\n```\n'
        return AgentStatus('replied', reply)


class PreproductionPrompt(Server):
    def test_prompt_carries_the_section_and_the_note_carries_the_phase(self):
        backend = RecorderBackend()
        self.restart(auto_land=False, backend=backend)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'develop the opening'})
        self.assertEqual(code, 200)
        settle(self.editor)
        text = backend.seen[0]
        self.assertIn('## Pre-production', text)
        self.assertIn('do not build or render the film', text)
        for path in ('bible/phase.json', 'bible/script.fountain', 'bible/scenes.json', 'bible/options/'):
            self.assertIn(path, text)
        self.assertIn('```json', text)
        self.assertIn('outside this checkout', text)
        stored = self.editor.notes.current(note['id'])
        self.assertEqual(stored['phase'], 'pre-production')

    def test_a_production_note_carries_no_pre_production_section(self):
        backend = RecorderBackend()
        self.restart(auto_land=False, backend=backend)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'tweak it'})
        self.assertEqual(code, 200)
        settle(self.editor)
        text = backend.seen[0]
        self.assertNotIn('Pre-production', text)
        stored = self.editor.notes.current(note['id'])
        self.assertNotIn('phase', stored)


class PicksInPrompt(Server):
    def setUp(self):
        super().setUp()
        self.backend = RecorderBackend()
        self.restart(auto_land=False, backend=self.backend)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})

    def test_picks_since_last_note_then_nothing_on_the_next_one(self):
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'A'})
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': None})
        code, note1 = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'go'})
        self.assertEqual(code, 200)
        settle(self.editor)
        text1 = self.backend.seen[0]
        self.assertIn('## Picks since your last note', text1)
        self.assertIn('look: A', text1)
        self.assertIn('look: cleared', text1)
        code, note2 = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'go again'})
        self.assertEqual(code, 200)
        settle(self.editor)
        text2 = self.backend.seen[1]
        self.assertNotIn('Picks since your last note', text2)


class PicksReachStartProduction(Server):
    def test_picks_just_before_start_production_are_in_its_prompt(self):
        backend = RecorderBackend()
        self.restart(auto_land=False, backend=backend)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'B'})
        code, body = self.post('/api/phase', {'video': VIDEO, 'phase': 'production'})
        self.assertEqual(code, 200)
        settle(self.editor)
        text = backend.seen[0]
        self.assertNotIn('## Pre-production', text)
        self.assertIn('## Picks since your last note', text)
        self.assertIn('look: B (Bright)', text)
        self.assertNotIn('picks', self.editor.notes.session(VIDEO))


class PhaseIsReadOnMain(Server):
    def test_an_unlanded_draft_does_not_decide_the_phase(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        git(self.root, 'branch', 'vb-draft/stale', 'main')
        self.post('/api/phase', {'video': VIDEO, 'phase': 'production'})
        brief = preprod.PreprodBrief(self.editor)
        self.assertIsNone(brief(VIDEO, {}, {'draft': 'vb-draft/stale'}))
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        git(self.root, 'branch', '-f', 'vb-draft/stale2', 'HEAD~1')
        self.assertIsNotNone(brief(VIDEO, {}, {'draft': 'vb-draft/stale2'}))


class RetryCarriesPicks(Server):
    def test_retry_after_a_failed_submission_keeps_the_picks(self):
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'B'})
        backend = FlakyBackend()
        self.restart(auto_land=False, backend=backend)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'go'})
        self.assertEqual(code, 200)
        settle(self.editor)
        failed = self.editor.notes.current(note['id'])
        self.assertEqual(failed['state'], 'failed')
        self.assertEqual(failed['picks'][0]['key'], 'B')
        code, retried = self.post(f'/api/notes/{note["id"]}/retry', {})
        self.assertEqual(code, 200)
        settle(self.editor)
        self.assertEqual(len(backend.seen), 1)
        text = backend.seen[0]
        self.assertIn('## Picks since your last note', text)
        self.assertIn('look: B', text)


class PickFromAnswer(Server):
    def setUp(self):
        super().setUp()
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})
        questions = [{'text': 'Which look?', 'set': 'look', 'choices': [
            {'text': 'Moody', 'key': 'A'}, {'text': 'Bright', 'key': 'B'}]}]
        self.backend = QuestionBackend(questions)
        self.restart(auto_land=False, backend=self.backend)

    def test_matching_answer_records_the_pick(self):
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'pick a look'})
        self.assertEqual(code, 200)
        settle(self.editor)
        stored = self.editor.notes.current(note['id'])
        self.assertEqual(stored['state'], 'questions')
        code, followup = self.post(f'/api/notes/{note["id"]}/answer', {'answers': ['Moody']})
        self.assertEqual(code, 200)
        got = next(s for s in self.board()['sets'] if s['id'] == 'look')
        self.assertEqual(got['pick'], 'A')

    def test_free_text_answer_records_no_pick(self):
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'pick a look'})
        self.assertEqual(code, 200)
        settle(self.editor)
        self.editor.notes.current(note['id'])  # polls the backend so the note reaches 'questions'
        code, followup = self.post(f'/api/notes/{note["id"]}/answer', {'answers': ['Something else entirely']})
        self.assertEqual(code, 200)
        got = next(s for s in self.board()['sets'] if s['id'] == 'look')
        self.assertIsNone(got['pick'])


class ScriptedBackend(AgentBackend):
    """Commits given files on a draft branch (or the current one) and
    replies with given text -- for scenarios FakeBackend can't script
    (committing a brand-new file, or a reply carrying a ```concepts
    block)."""
    name = 'scripted'

    def __init__(self, files, reply, extra_path=None):
        self.files, self.reply, self.extra_path = files, reply, extra_path

    def submit(self, payload):
        path = Path(payload['state_dir']) / (payload['id'] + '.scripted.json')
        path.write_text(json.dumps(payload))
        return str(path)

    def poll(self, handle):
        payload = json.loads(Path(handle).read_text())
        root = payload['project']
        branch = payload['draft'] or 'vb-draft/' + payload['session'] + '-' + payload['id']
        work = Path(payload['state_dir']) / ('scripted-work-' + payload['id'])
        if not payload['draft']:
            git(root, 'branch', branch, 'main')
        git(root, 'worktree', 'add', str(work), branch)
        try:
            files = self.files or {'promo/.scripted-marker': str(time.time())}
            for rel, data in files.items():
                full = work / rel
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_bytes(data if isinstance(data, bytes) else data.encode())
                git(work, 'add', '--', rel)
            if self.extra_path:
                target = work / self.extra_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('out of scope')
                git(work, 'add', '--', self.extra_path)
            git(work, '-c', 'user.name=Scripted agent', '-c', 'user.email=agent@example.com',
               'commit', '-qm', 'agent: scripted change')
        finally:
            git(root, 'worktree', 'remove', '--force', str(work))
        return AgentStatus('replied', self.reply, branch)


class BranchlessBackend(AgentBackend):
    """Replies with given text and no draft branch (it committed nothing)."""
    name = 'branchless'

    def __init__(self, reply):
        self.reply = reply

    def submit(self, payload):
        return 'h:' + payload['id']

    def poll(self, handle):
        return AgentStatus('replied', self.reply)


def _concepts_reply(lead_in, requests):
    return lead_in + '\n\n```concepts\n' + json.dumps({'concepts': requests}) + '\n```\n'


class ConceptsStripping(Server):
    def test_strip_concepts_unit(self):
        from videobuilder.notes import strip_concepts
        reply = 'Made the look options.\n\n```concepts\n' + json.dumps(
            {'concepts': [{'set': 'look', 'key': 'A', 'prompt': 'a moody lighthouse at dusk'}]}) + '\n```\n'
        cleaned, parsed = strip_concepts(reply)
        self.assertEqual(cleaned, 'Made the look options.')
        self.assertEqual(parsed, [{'set': 'look', 'key': 'A', 'prompt': 'a moody lighthouse at dusk'}])

    def test_strip_concepts_malformed_json_is_stripped_but_records_nothing(self):
        from videobuilder.notes import strip_concepts
        cleaned, parsed = strip_concepts('Before.\n\n```concepts\nnot json\n```\n')
        self.assertEqual(cleaned, 'Before.')
        self.assertIsNone(parsed)

    def test_strip_concepts_before_questions_block_leaves_questions_intact(self):
        from videobuilder.notes import strip_concepts
        reply = ('Lead.\n\n```concepts\n' + json.dumps({'concepts': [{'set': 'look', 'key': 'A', 'prompt': 'x'}]})
                + '\n```\n\n```questions\n' + json.dumps({'questions': [{'text': 'Which?', 'choices': ['A', 'B']}]})
                + '\n```\n')
        cleaned, parsed = strip_concepts(reply)
        self.assertIsNotNone(parsed)
        self.assertIn('```questions', cleaned)

    def test_production_reply_keeps_a_concepts_block_verbatim(self):
        backend = ScriptedBackend({}, _concepts_reply('Done.', [{'set': 'look', 'key': 'A', 'prompt': 'x'}]))
        self.restart(auto_land=False, backend=backend)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'tweak it'})
        self.assertEqual(code, 200)
        settle(self.editor)
        stored = self.editor.notes.current(note['id'])
        self.assertIn('```concepts', stored['reply'])
        self.assertNotIn('concepts', stored)


class ConceptsLanding(Server):
    def setUp(self):
        super().setUp()
        self.fake = FakeArtbox()
        self.addCleanup(self.fake.close)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})

    def poll_concepts(self):
        with mock.patch('time.time', return_value=time.time() + 120):
            self.editor.concepts.tick()

    def test_requests_land_commit_and_attach_to_the_set(self):
        files = {'bible/options/look.json': preprod.set_bytes({**LOOK_SET, 'pick': None,
                                                                'options': LOOK_SET['options']})}
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'a moody lighthouse'},
                   {'set': 'look', 'key': 'B', 'prompt': 'a bright lighthouse'}]
        backend = ScriptedBackend({}, _concepts_reply('Options drawn up.', requests))
        self.restart(auto_land=True, backend=backend, artbox_url=self.fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        self.assertEqual(code, 200)
        settle(self.editor)
        landed = self.editor.notes.current(note['id'])
        self.assertEqual(landed['state'], 'landed')
        # Landing started them: the note (read fresh) and the board both say so.
        self.assertEqual({c['status'] for c in landed['concepts']}, {'making'})
        self.assertEqual({c['status'] for c in self.board()['concepts']}, {'making'})
        jobs = self.editor.concepts._load()
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.fake.finish(job['remote'])
        self.poll_concepts()
        got = next(s for s in self.board()['sets'] if s['id'] == 'look')
        for option in got['options']:
            self.assertEqual(option['kind'], 'concept')
            self.assertTrue(option['image'].endswith('.png'))
            self.assertTrue((self.directory / option['image']).is_file())
        notes = self.get('/api/notes?video=' + VIDEO)
        notes = notes['notes'] if isinstance(notes, dict) else notes
        shown = next(n for n in notes if n['id'] == note['id'])
        self.assertEqual({c['status'] for c in shown['concepts']}, {'done'})
        board = self.board()['concepts']
        self.assertEqual({(c['set'], c['key'], c['status']) for c in board},
                         {('look', 'A', 'done'), ('look', 'B', 'done')})
        self.assertEqual({c['image'] for c in board}, {'bible/options/look/A.png', 'bible/options/look/B.png'})

    def test_a_reply_with_no_branch_starts_its_requests_at_once(self):
        backend = BranchlessBackend(_concepts_reply('Asked for art.', [{'set': 'look', 'key': 'A', 'prompt': 'x'}]))
        self.restart(auto_land=False, backend=backend, artbox_url=self.fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        self.assertEqual(code, 200)
        settle(self.editor)
        stored = self.editor.notes.current(note['id'])
        self.assertEqual(stored['state'], 'replied')
        self.assertEqual(stored['concepts'][0]['status'], 'making')

    def test_a_questions_note_with_no_branch_starts_its_requests(self):
        reply = (_concepts_reply('Pick one.', [{'set': 'look', 'key': 'A', 'prompt': 'x'}])
                + '\n```questions\n' + json.dumps({'questions': [{'text': 'Which look?', 'set': 'look', 'choices': [
                    {'text': 'Moody', 'key': 'A', 'image': 'bible/options/look/A.png', 'kind': 'concept'},
                    {'text': 'Bright', 'key': 'B'}]}]}) + '\n```\n')
        self.restart(auto_land=False, backend=BranchlessBackend(reply), artbox_url=self.fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        self.assertEqual(code, 200)
        settle(self.editor)
        self.assertEqual(self.editor.notes.current(note['id'])['state'], 'questions')
        self.editor.concepts.tick()
        self.assertEqual(self.editor.notes.get(note['id'])['concepts'][0]['status'], 'making')
        self.assertEqual(len(self.fake.jobs), 1)


class ConceptsUnavailable(Server):
    def setUp(self):
        super().setUp()
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})

    def test_reply_shows_and_requests_are_unavailable_with_no_artbox(self):
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests))
        self.restart(auto_land=True, backend=backend)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        self.assertEqual(code, 200)
        settle(self.editor)
        landed = self.editor.notes.current(note['id'])
        self.assertEqual(landed['reply'], 'Drawn up.')
        self.assertEqual(landed['concepts'][0]['status'], 'unavailable')

    def test_a_job_that_fails_becomes_unavailable(self):
        fake = FakeArtbox()
        self.addCleanup(fake.close)
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests))
        self.restart(auto_land=True, backend=backend, artbox_url=fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        settle(self.editor)
        self.editor.notes.current(note['id'])
        job = self.editor.concepts._load()[0]
        fake.fail(job['remote'])
        with mock.patch('time.time', return_value=time.time() + 120):
            self.editor.concepts.tick()
        jobs = self.editor.concepts._load()
        self.assertEqual(jobs[0]['status'], 'unavailable')

    def test_artbox_down_when_the_note_lands_marks_requests_unavailable(self):
        fake = FakeArtbox()
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests))
        self.restart(auto_land=True, backend=backend, artbox_url=fake.base)
        fake.close()
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        self.assertEqual(code, 200)
        settle(self.editor)
        landed = self.editor.notes.current(note['id'])
        self.assertEqual((landed['state'], landed['reply']), ('landed', 'Drawn up.'))
        job = self.editor.concepts._load()[0]
        self.assertEqual((job['status'], job['message']), ('unavailable', "The picture maker isn't answering."))

    def test_a_note_that_ends_refused_marks_requests_unavailable(self):
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests), extra_path='README.md')
        fake = FakeArtbox()
        self.addCleanup(fake.close)
        self.restart(auto_land=True, backend=backend, artbox_url=fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        settle(self.editor)
        landed = self.editor.notes.current(note['id'])
        self.assertEqual(landed['state'], 'refused')
        jobs = self.editor.concepts._load()
        self.assertEqual(jobs[0]['status'], 'unavailable')


class ConceptsCaps(Server):
    def setUp(self):
        super().setUp()
        self.fake = FakeArtbox()
        self.addCleanup(self.fake.close)
        self.restart(auto_land=False, artbox_url=self.fake.base)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})

    def test_character_set_caps_at_three(self):
        requests = [{'set': 'character-ana', 'key': k, 'prompt': 'x'} for k in ('A', 'B', 'C', 'D')]
        out = self.editor.concepts.request(VIDEO, 'note-1', requests)
        self.assertEqual([o['status'] for o in out], ['requested', 'requested', 'requested', 'unavailable'])

    def test_look_set_caps_at_four(self):
        requests = [{'set': 'look', 'key': str(i), 'prompt': 'x'} for i in range(5)]
        out = self.editor.concepts.request(VIDEO, 'note-1', requests)
        self.assertEqual([o['status'] for o in out].count('requested'), 4)

    def test_total_caps_at_sixteen(self):
        requests = [{'set': f'character-c{i}', 'key': 'A', 'prompt': 'x'} for i in range(17)]
        out = self.editor.concepts.request(VIDEO, 'note-1', requests)
        self.assertEqual([o['status'] for o in out].count('requested'), 16)


class ConceptsResume(Server):
    def setUp(self):
        super().setUp()
        self.fake = FakeArtbox()
        self.addCleanup(self.fake.close)
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})

    def test_resumes_after_restart(self):
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests))
        self.restart(auto_land=True, backend=backend, artbox_url=self.fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        settle(self.editor)
        self.editor.notes.current(note['id'])
        job = self.editor.concepts._load()[0]
        self.fake.finish(job['remote'])
        self.restart(auto_land=True, backend=backend, artbox_url=self.fake.base)
        with mock.patch('time.time', return_value=time.time() + 120):
            self.editor.concepts.tick()
        self.assertEqual(self.editor.concepts._load()[0]['status'], 'done')

    def test_dirty_main_checkout_retries_next_tick(self):
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests))
        self.restart(auto_land=True, backend=backend, artbox_url=self.fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        settle(self.editor)
        self.editor.notes.current(note['id'])
        job = self.editor.concepts._load()[0]
        self.fake.finish(job['remote'])
        (self.directory / 'dirty.txt').write_text('uncommitted')
        with mock.patch('time.time', return_value=time.time() + 120):
            self.editor.concepts.tick()
        self.assertEqual(self.editor.concepts._load()[0]['status'], 'ready')
        (self.directory / 'dirty.txt').unlink()
        with mock.patch('time.time', return_value=time.time() + 240):
            self.editor.concepts.tick()
        self.assertEqual(self.editor.concepts._load()[0]['status'], 'done')

    def test_gives_up_past_the_time_limit(self):
        requests = [{'set': 'look', 'key': 'A', 'prompt': 'x'}]
        backend = ScriptedBackend({}, _concepts_reply('Drawn up.', requests))
        self.restart(auto_land=True, backend=backend, artbox_url=self.fake.base)
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'offer look options'})
        settle(self.editor)
        self.editor.notes.current(note['id'])
        from videobuilder.concepts import GIVE_UP_SECONDS
        with mock.patch('time.time', return_value=time.time() + GIVE_UP_SECONDS + 3600):
            self.editor.concepts.tick()
        self.assertEqual(self.editor.concepts._load()[0]['status'], 'unavailable')


class SuggestMode(unittest.TestCase):
    """preprod.suggest_mode/decide_mode: the plan-or-build rule for New
    video (A16), checked directly rather than through the HTTP route."""

    def test_a_story_keyword_outranks_everything_else(self):
        out = preprod.suggest_mode('Develop a screenplay about a lighthouse keeper.', ['image/png'])
        self.assertEqual(out, {'plan': True, 'why': 'story', 'reason': preprod.WHY_REASONS['story']})

    def test_eighty_words_counts_as_story_like_even_without_a_keyword(self):
        prompt = ' '.join(['word'] * 80)
        self.assertEqual(preprod.suggest_mode(prompt)['why'], 'story')

    def test_seventy_nine_words_is_not_enough_on_its_own(self):
        prompt = ' '.join(['word'] * 79)
        self.assertEqual(preprod.suggest_mode(prompt)['why'], 'short-idea')

    def test_a_reference_image_outranks_media_only_and_short_idea(self):
        out = preprod.suggest_mode('', ['image/jpeg'])
        self.assertEqual(out, {'plan': True, 'why': 'references', 'reason': preprod.WHY_REASONS['references']})

    def test_a_reference_pdf_also_counts(self):
        self.assertEqual(preprod.suggest_mode('', ['application/pdf'])['why'], 'references')

    def test_media_only_with_no_words_builds(self):
        out = preprod.suggest_mode('', ['video/mp4', 'audio/mpeg'])
        self.assertEqual(out, {'plan': False, 'why': 'media-only', 'reason': preprod.WHY_REASONS['media-only']})

    def test_a_short_idea_with_no_references_builds(self):
        out = preprod.suggest_mode('A quick promo for the launch.', [])
        self.assertEqual(out, {'plan': False, 'why': 'short-idea', 'reason': preprod.WHY_REASONS['short-idea']})

    def test_nothing_at_all_builds(self):
        out = preprod.suggest_mode('', [])
        self.assertEqual(out, {'plan': False, 'why': 'empty', 'reason': preprod.WHY_REASONS['empty']})

    def test_decide_mode_lets_an_explicit_choice_override_the_guess(self):
        self.assertEqual(preprod.decide_mode('a screenplay', [], plan=False),
                         {'plan': False, 'why': 'chosen', 'reason': 'You chose to build it straight away.'})
        self.assertEqual(preprod.decide_mode('', [], plan=True),
                         {'plan': True, 'why': 'chosen', 'reason': 'You chose to plan it first.'})

    def test_bad_input_is_rejected(self):
        with self.assertRaises(ValueError):
            preprod.suggest_mode(123)
        with self.assertRaises(ValueError):
            preprod.suggest_mode('', [1, 2])
        with self.assertRaises(ValueError):
            preprod.decide_mode('', [], plan='yes')


PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 20


class RecorderBackendLibrary(AgentBackend):
    """Records each submitted note's rendered prompt -- the library-mode
    twin of RecorderBackend above, shared across every project the library
    opens (see NewVideo.library_kwargs)."""
    name = 'recorder'

    def __init__(self):
        self.seen = []

    def submit(self, payload):
        self.seen.append(Path(payload['note_file']).read_text())
        return 'rec:' + payload['id']

    def poll(self, handle):
        return AgentStatus('failed', 'done')


class NewVideo(LibraryFixture, unittest.TestCase):
    """POST /api/videos/staging, its delete route, and the extra New video
    fields on POST /api/videos/new (prompt, attachments, format, plan)."""

    def library_kwargs(self):
        self.backend = RecorderBackendLibrary()
        return {'backend': self.backend}

    def stage(self, name, data, ctype):
        req = urllib.request.Request(self.base + '/api/videos/staging?name=' + name, data=data, method='POST',
                                     headers={'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                body = e.read()
                return e.code, json.loads(body) if body else None
        finally:
            settle(self.library)

    def test_a_valid_image_stages_successfully(self):
        code, record = self.stage('pic.png', PNG, 'image/png')
        self.assertEqual(code, 201, record)
        self.assertEqual((record['name'], record['type'], record['size']), ('pic.png', 'image/png', len(PNG)))

    def test_bad_magic_is_refused_and_nothing_is_written(self):
        code, err = self.stage('pic.png', b'not a real png', 'image/png')
        self.assertEqual(code, 400)
        self.assertEqual(list(self.library.staging.root.glob('*/meta.json')), [])

    def test_oversize_by_content_length_is_refused_before_reading(self):
        with mock.patch('videobuilder.staging.MAX_FILE', 10):
            code, err = self.stage('big.png', PNG, 'image/png')
        self.assertEqual(code, 413)
        self.assertEqual(list(self.library.staging.root.glob('*/meta.json')), [])

    def test_the_51st_file_is_refused(self):
        with mock.patch('videobuilder.staging.MAX_FILES', 2):
            self.stage('a.png', PNG, 'image/png')
            self.stage('b.png', PNG, 'image/png')
            code, err = self.stage('c.png', PNG, 'image/png')
        self.assertEqual(code, 413, err)

    def test_a_zip_is_refused(self):
        code, err = self.stage('bundle.zip', b'PK\x03\x04', 'application/zip')
        self.assertEqual(code, 400)
        self.assertIn('unpack the zip', err['error'])

    def test_delete_removes_the_staged_file(self):
        _, record = self.stage('pic.png', PNG, 'image/png')
        code, body = self.request(f"/api/videos/staging/{record['id']}/delete", {})
        self.assertEqual((code, body), (200, {'deleted': record['id']}))
        code, err = self.request(f"/api/videos/staging/{record['id']}/delete", {})
        self.assertEqual(code, 404)

    def test_unclaimed_files_expire_after_a_day(self):
        _, record = self.stage('old.png', PNG, 'image/png')
        with mock.patch('time.time', return_value=time.time() + 86400 + 1):
            self.stage('new.png', PNG, 'image/png')   # expire() runs as a side effect of the next upload
        self.assertEqual(list(self.library.staging.root.glob(record['id'] + '/meta.json')), [])

    def test_mode_route_wires_to_suggest_mode(self):
        code, body = self.request('/api/videos/mode', {'prompt': 'a screenplay about a lighthouse keeper'})
        self.assertEqual(code, 200)
        self.assertEqual((body['plan'], body['why']), (True, 'story'))

    def test_plan_true_with_prompt_and_attachments_starts_pre_production(self):
        _, record = self.stage('ref.png', PNG, 'image/png')
        code, result = self.request('/api/videos/new', {
            'name': 'acme/preprod-pitch', 'start': 'blank', 'plan': True,
            'prompt': 'Develop a multi-scene screenplay for a lighthouse keeper film.',
            'attachments': [record['id']]})
        self.assertEqual(code, 201, result)
        self.assertTrue(result['plan'])
        self.assertIsNotNone(result['note'])
        self.assertEqual([a['name'] for a in result['attachments']], ['ref.png'])
        self.assertEqual([a['name'] for a in result['note']['attachments']], ['ref.png'])
        self.assertNotIn('Build a first version', result['note']['text'])
        code, err = self.request(f"/api/videos/staging/{record['id']}/delete", {})
        self.assertEqual(code, 404)   # claimed, so no longer staged
        clone = self.root / 'preprod-clone'
        self.git('clone', self.url('acme/preprod-pitch'), str(clone))
        self.assertEqual(json.loads((clone / 'bible' / 'phase.json').read_text())['phase'], 'pre-production')
        self.assertIn('## Pre-production', self.backend.seen[-1])

    def test_plan_omitted_decides_from_the_prompt(self):
        code, result = self.request('/api/videos/new', {
            'name': 'acme/auto-plan', 'start': 'blank',
            'prompt': 'Write me a screenplay with three characters and a twist ending.'})
        self.assertEqual(code, 201, result)
        self.assertEqual((result['plan'], result['why']), (True, 'story'))

    def test_plan_omitted_with_only_media_builds(self):
        _, record = self.stage('song.mp3', b'ID3' + b'0' * 20, 'audio/mpeg')
        code, result = self.request('/api/videos/new', {
            'name': 'acme/media-only', 'start': 'blank', 'attachments': [record['id']]})
        self.assertEqual(code, 201, result)
        self.assertEqual((result['plan'], result['why']), (False, 'media-only'))
        self.assertIn('Build a first version', result['note']['text'])

    def test_defaults_match_todays_behaviour(self):
        code, result = self.request('/api/videos/new', {'name': 'acme/plain', 'start': 'blank'})
        self.assertEqual(code, 201, result)
        self.assertEqual((result['note'], result['plan']), (None, False))
        clone = self.root / 'plain-clone'
        self.git('clone', self.url('acme/plain'), str(clone))
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')
        self.assertFalse((clone / 'bible').exists())

    def test_plan_false_with_prompt_matches_first_note_text_exactly(self):
        from videobuilder.editor import _first_brief
        code, result = self.request('/api/videos/new', {
            'name': 'acme/build-now', 'start': 'blank', 'plan': False, 'prompt': 'A quick promo clip.'})
        self.assertEqual(code, 201, result)
        self.assertEqual(result['note']['text'], _first_brief('A quick promo clip.', [], [], []))

    def test_format_narrows_the_blank_film_and_the_brief(self):
        code, result = self.request('/api/videos/new', {
            'name': 'acme/square', 'start': 'blank', 'format': '9x16', 'plan': False,
            'prompt': 'A square test.'})
        self.assertEqual(code, 201, result)
        self.assertIn('Format: 9x16.', result['note']['text'])
        clone = self.root / 'square-clone'
        self.git('clone', self.url('acme/square'), str(clone))
        self.assertIn("formats=('9x16',)", (clone / 'film.py').read_text())

    def test_bad_format_is_refused_and_creates_nothing(self):
        code, err = self.request('/api/videos/new', {'name': 'acme/bad-fmt', 'start': 'blank', 'format': '4x3'})
        self.assertEqual(code, 400, err)
        self.assertFalse(self.library.has_main('acme/bad-fmt'))

    def test_invalid_input_leaves_no_repo(self):
        staged = self.stage('ref.png', png((1, 2, 3)), 'image/png')[1]['id']
        cases = [
            {'name': 'acme/x1', 'start': 'blank', 'attachments': ['0' * 32]},
            {'name': 'acme/x2', 'start': 'blank', 'format': 'nope'},
            {'name': 'acme/x3', 'start': 'blank', 'plan': 'yes'},
            {'name': 'acme/x4', 'start': 'copy', 'from': 'acme/does-not-exist', 'prompt': 'hi'},
            {'name': 'acme/x5', 'start': 'blank', 'prompt': 'hi', 'attachments': [staged, staged]},
        ]
        for body in cases:
            code, err = self.request('/api/videos/new', body)
            self.assertEqual(code, 400, (body, err))
            self.assertFalse(self.library.has_main(body['name']))

    def test_note_cap_reached_leaves_no_repo(self):
        code, result = self.request('/api/videos/new', {'name': 'acme/first', 'start': 'blank', 'prompt': 'First.'})
        self.assertEqual(code, 201, result)
        self.library.account_daily_note_cap = 1
        code, err = self.request('/api/videos/new', {
            'name': 'acme/capped', 'start': 'blank', 'prompt': 'Second.'})
        self.assertEqual(code, 429, err)
        self.assertFalse(self.library.has_main('acme/capped'))

    def test_note_error_after_creation_keeps_the_video_and_the_staged_file(self):
        from videobuilder.editor import Editor, HTTPError
        _, record = self.stage('ref.png', PNG, 'image/png')
        with mock.patch.object(Editor, 'start_video', side_effect=HTTPError(409, 'boom')):
            code, result = self.request('/api/videos/new', {
                'name': 'acme/stuck', 'start': 'blank', 'prompt': 'hi', 'attachments': [record['id']]})
        self.assertEqual(code, 201, result)
        self.assertIsNone(result['note'])
        self.assertIn('boom', result['note_error'])
        self.assertTrue(self.library.has_main('acme/stuck'))
        meta, _ = self.library.staging.get(record['id'])
        self.assertEqual(meta['name'], 'ref.png')


class FirstNoteInPreproduction(LibraryFixture, unittest.TestCase):
    """POST .../api/videos/first-note reads the video's phase, so a video
    started in pre-production with no prompt still gets the planning brief
    -- including through a links gather, whose spec must survive a restart."""

    def library_kwargs(self):
        return {'backend': RecorderBackendLibrary()}

    def wait_for(self, editor, nid, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            note = editor.notes.current(nid)
            if note['state'] != 'gathering':
                return note
            time.sleep(0.05)
        self.fail(f'note {nid} is still gathering')

    def test_first_note_on_a_pre_production_video_gets_the_planning_brief(self):
        code, result = self.request('/api/videos/new', {'name': 'acme/plan-later', 'start': 'blank', 'plan': True})
        self.assertEqual((code, result['note']), (201, None))
        code, note = self.request('/v/acme/plan-later/api/videos/first-note', {'description': 'A storm film.'})
        self.assertEqual(code, 200, note)
        self.assertIn("don't build or render the film yet", note['text'])
        self.assertNotIn('Build a first version', note['text'])

    def gathered(self, name, plan):
        self.request('/api/videos/new', {'name': name, 'start': 'blank', 'plan': plan})
        editor = self.library.editor(name)
        started = []
        real = editor._start_gather
        with mock.patch.object(editor, '_start_gather', side_effect=lambda n: started.append(n)):
            code, note = self.request(f'/v/{name}/api/videos/first-note', {
                'description': 'A storm film.', 'links': ['http://127.0.0.1:1/unreachable']})
        self.assertEqual((code, note['state']), (200, 'gathering'), note)
        self.assertEqual(len(started), 1)
        real(started[0])       # what _resume_gathering does with the saved spec after a restart
        return started[0]['gather'], self.wait_for(editor, note['id'])

    def test_a_gathered_first_note_keeps_the_planning_brief(self):
        spec, note = self.gathered('acme/plan-gather', True)
        self.assertIs(spec['plan'], True)
        self.assertIn("don't build or render the film yet", note['text'])
        self.assertNotIn('Build a first version', note['text'])

    def test_a_production_gather_spec_has_no_plan_key(self):
        spec, note = self.gathered('acme/build-gather', False)
        self.assertNotIn('plan', spec)
        self.assertIn('Build a first version', note['text'])


class StagingAccounts(AccountMixin, LibraryFixture, unittest.TestCase):
    def test_someone_elses_staged_file_is_404(self):
        _, _, cookie_a = self.signup('alice', 'alicepassword1')
        _, _, cookie_b = self.signup('bob', 'bobpassword1')
        req = urllib.request.Request(self.base + '/api/videos/staging?name=pic.png', data=PNG, method='POST',
                                     headers={'Content-Type': 'image/png', 'Cookie': cookie_a})
        with urllib.request.urlopen(req, timeout=20) as r:
            record = json.loads(r.read())
        code, err, _ = self.request_full(f"/api/videos/staging/{record['id']}/delete", {},
                                         headers={'Content-Type': 'application/json', 'Cookie': cookie_b})
        self.assertEqual(code, 404)


if __name__ == '__main__':
    unittest.main()
