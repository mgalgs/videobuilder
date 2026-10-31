"""Pre-production: the bible's phase, option sets, scenes and script, and
the board API (preprod.py, preprod_api.py, fountain.py)."""
import json
import os
import re
import shutil
import subprocess
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from tests.fake_artbox import FakeArtbox, png
from tests.fake_gemini import FakeGemini
from tests.fixtures import AccountMixin, LibraryFixture, settle
from tests.test_project import TempProject
from videobuilder import fountain, listen, preprod, speech
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


MP3 = b'ID3' + b'song' * 20


class ListenEarly(LibraryFixture, unittest.TestCase):
    """Listening starts as soon as an audio file is staged or attached, not
    only once a note is submitted (A17)."""

    def library_kwargs(self):
        self.backend = RecorderBackendLibrary()
        return {'backend': self.backend}

    def setUp(self):
        super().setUp()
        self.fake = FakeGemini()
        self.addCleanup(self.fake.close)
        patcher = mock.patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key', 'VIDEOBUILDER_GEMINI_URL': self.fake.url})
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = mock.patch.object(speech.time, 'sleep')
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def _wait_for_requests(self, n, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(self.fake.requests) >= n:
                time.sleep(0.2)   # let the warm thread finish writing the cache
                return
            time.sleep(0.02)
        self.fail(f'gave up waiting for {n} Gemini request(s); saw {len(self.fake.requests)}')

    def test_staged_audio_is_already_cached_by_the_time_the_video_is_created(self):
        req = urllib.request.Request(self.base + '/api/videos/staging?name=song.mp3', data=MP3, method='POST',
                                     headers={'Content-Type': 'audio/mpeg'})
        with urllib.request.urlopen(req, timeout=20) as r:
            record = json.loads(r.read())
        self._wait_for_requests(1)
        code, result = self.request('/api/videos/new', {
            'name': 'acme/listen', 'start': 'blank', 'plan': False, 'prompt': 'use this song',
            'attachments': [record['id']]})
        self.assertEqual(code, 201, result)
        self.assertEqual(len(self.fake.requests), 1)   # no second call once the note needs it too
        self.assertIn('## Listening notes', self.backend.seen[-1])

    def test_attaching_audio_to_an_existing_video_warms_it_too(self):
        code, result = self.request('/api/videos/new', {'name': 'acme/compose', 'start': 'blank'})
        self.assertEqual(code, 201, result)
        req = urllib.request.Request(self.base + '/v/acme/compose/api/attachments?video=film&name=song.mp3',
                                     data=MP3, method='POST', headers={'Content-Type': 'audio/mpeg'})
        with urllib.request.urlopen(req, timeout=20) as r:
            attach = json.loads(r.read())
        self._wait_for_requests(1)
        code, note = self.request('/v/acme/compose/api/videos/first-note', {
            'description': 'use it', 'attachments': [attach['id']]})
        self.assertEqual(code, 200, note)
        self.assertEqual(len(self.fake.requests), 1)
        self.assertIn('## Listening notes', self.backend.seen[-1])


PKG = Path(__file__).resolve().parents[1] / 'videobuilder'


def _fns(js, *names):
    """Extract named top-level function (or async function) declarations
    from director.js: they all close with a bare `}` at column 0, so a
    lazy DOTALL search finds exactly the function's own body."""
    return '\n'.join(re.search(r'\n(?:async )?function ' + re.escape(n) + r'\(.*?\n\}', js, re.S).group(0)
                     for n in names)


def _consts(js, *names):
    """Extract top-level const/let declarations. A braces-bodied arrow (node's) closes with
    a bare '};' line; everything else here is lazy up to its own first ';' (none embed one)."""
    out = []
    for n in names:
        pat = r'\n(?:const|let) ' + re.escape(n) + r' ?=\s*\([^()]*\)\s*=>\s*\{.*?\n\};\n'
        m = re.search(pat, js, re.S) or re.search(r'\n(?:const|let) ' + re.escape(n) + r' ?=.*?;\n', js, re.S)
        out.append(m.group(0))
    return '\n'.join(out)


def run_node(script):
    result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


SCRIPT_TEXT = (
    "Title: The Keeper's Light\n"
    "Draft: 2\n"
    "\n"
    "# Act One\n"
    "\n"
    "= A keeper faces the storm, alone in the light.\n"
    "\n"
    "INT. LIGHTHOUSE - LANTERN ROOM - NIGHT #1#\n"
    "\n"
    'The lamp turns. Rain needles the glass. <b>Bright</b> & "loud".\n'
    "\n"
    "MARA\n"
    "(checking the log)\n"
    "Still turning. Good.\n"
    "\n"
    "> CUT TO:\n"
    "\n"
    "EXT. LIGHTHOUSE - CLIFF - NIGHT #2#\n"
    "\n"
    "The sea throws itself at the rock.\n"
)

BOARD_SONGS = [{
    'id': 'storm-theme', 'name': 'Storm theme', 'file': 'storm-theme.mp3',
    'duration': 142.5, 'bpm': 92, 'mood': 'tense, building',
    'sections': [{'name': 'intro', 'start': 0, 'end': 18, 'text': 'sparse, just wind'}],
}]
BOARD_SCENES = [
    {'id': 'lantern-room', 'slugline': 'INT. LIGHTHOUSE - LANTERN ROOM - NIGHT',
     'summary': 'Mara checks the lamp as the storm builds.', 'seconds': 28,
     'song': 'storm-theme', 'section': 'intro', 'from': 0, 'to': 18, 'look': None},
    {'id': 'cliff', 'slugline': 'EXT. LIGHTHOUSE - CLIFF - NIGHT',
     'summary': 'The sea throws itself at the rock.', 'seconds': 20,
     'song': None, 'section': None, 'from': None, 'to': None,
     'look': {'name': 'Sunbleached', 'reason': 'a small warm light against a huge dark sea'}},
    {'id': 'dawn', 'slugline': 'EXT. LIGHTHOUSE - DAWN',
     'summary': 'The storm breaks; the light finally rests.', 'seconds': 18,
     'song': None, 'section': None, 'from': None, 'to': None, 'look': None},
]
BOARD_LOOK_SET = {
    'topic': 'look', 'id': 'look', 'question': 'Which look fits the storm best?',
    'options': [
        {'key': 'A', 'label': 'Moody', 'text': 'Low-key lighting, long shadows, a single warm light.',
         'image': 'bible/options/look/A.png', 'kind': 'vb', 'swatches': ['#101418', '#5a4632', '#8aa0b0']},
        {'key': 'B', 'label': 'Bright', 'text': 'High-key, saturated colour, storm as spectacle.',
         'image': 'bible/options/look/B.png', 'kind': 'concept'},
    ]}
MARA_SET = {
    'topic': 'character', 'id': 'character-mara', 'character': 'mara', 'question': 'Who is Mara?',
    'options': [{'key': 'A', 'label': 'Weathered keeper', 'text': 'Decades at the light; quiet, exact.'},
               {'key': 'B', 'label': 'Reluctant heir', 'text': 'New to the post, still learning the lamp.'}]}
TOM_SET = {
    'topic': 'character', 'id': 'character-tom', 'character': 'tom', 'question': 'Who is Tom?',
    'options': [{'key': 'A', 'label': 'Worried brother', 'text': 'Calls every night the radio allows.'},
               {'key': 'B', 'label': 'Estranged brother', 'text': "Hasn't spoken to Mara in years."}]}
LANTERN_SET = {
    'topic': 'scene', 'id': 'scene-lantern-room', 'scene': 'lantern-room',
    'question': 'How does this scene open?',
    'options': [{'key': 'A', 'label': 'Calm before', 'text': 'Mara checks the lamp, unhurried.',
                'image': 'bible/options/scene-lantern-room/A.png', 'kind': 'vb'},
               {'key': 'B', 'label': 'Already tense', 'text': 'The storm is already audible.'}]}
CLIFF_SET = {
    'topic': 'scene', 'id': 'scene-cliff', 'scene': 'cliff', 'question': 'What does the sea look like?',
    'options': [{'key': 'A', 'label': 'Calm', 'text': 'Deceptively still.'},
               {'key': 'B', 'label': 'Violent', 'text': 'Already breaking over the rocks.'}]}


class BoardFixture(Server):
    """The lighthouse film (docs/preproduction.md's own example), built entirely through
    the documented API: a draft-2 script with all 8 Fountain element types (and one line
    carrying `<b>&"` to prove the renderer escapes it), two characters (Mara with an
    uploaded picture, Tom with none), a 3-scene plan with one per-scene look override,
    a look set (A a committed vb picture, B a concept not yet made) and two scene-plot
    sets (lantern-room's with a picture). Look and Mara are picked; Tom and both scene
    sets are left open, so the checklist reads 3 of 5 settled."""

    def setUp(self):
        super().setUp()
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        (self.directory / 'bible').mkdir(exist_ok=True)
        (self.directory / 'bible/bible.md').write_text(
            '## Logline\n\nA keeper rides out a storm that found her brother first.\n')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'logline')
        mara_att = self.editor.attachments.upload(VIDEO, 'mara-1.png', 'image/png', png((80, 40, 120)))
        self.post('/api/film', {'video': VIDEO, 'base': self.commit_main(), 'characters': [
            {'name': 'Mara', 'description': 'The keeper.', 'keep': [], 'add': [mara_att['id']]},
            {'name': 'Tom', 'description': 'Her brother, ashore.', 'keep': [], 'add': []},
        ]})
        self.post('/api/preprod/script', {'video': VIDEO, 'base': self.commit_main(), 'text': SCRIPT_TEXT})
        self.post('/api/preprod/scenes', {'video': VIDEO, 'base': self.commit_main(),
                                          'songs': BOARD_SONGS, 'scenes': BOARD_SCENES})
        (self.directory / 'bible/options/look').mkdir(parents=True)
        (self.directory / 'bible/options/look/A.png').write_bytes(png((10, 20, 30)))
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'look vb frame')
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': BOARD_LOOK_SET})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': MARA_SET})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': TOM_SET})
        (self.directory / 'bible/options/scene-lantern-room').mkdir(parents=True)
        (self.directory / 'bible/options/scene-lantern-room/A.png').write_bytes(png((40, 90, 60)))
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'scene vb frame')
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LANTERN_SET})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': CLIFF_SET})
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'look', 'key': 'A'})
        self.post('/api/preprod/pick', {'video': VIDEO, 'set': 'character-mara', 'key': 'A'})

    def script(self):
        return self.get('/api/preprod/script?video=' + VIDEO)


EMPTY_BOARD = {'script': {'exists': False, 'draft': None, 'title': None, 'scenes': 0},
              'characters': [], 'sets': [],
              'scenes': {'songs': [], 'scenes': [], 'seconds': 0, 'length': '0:00'}}


class BoardLayoutJS(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_layout_for_each_phase(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppLayout') + """
console.log(JSON.stringify(['pre-production','production',null].map(ppLayout)));
"""
        pre, prod, none = run_node(script)
        self.assertEqual(pre, {'board': True, 'watch': False, 'header': True, 'phoneFormat': False,
                               'timestamp': False, 'back': False, 'dock': True, 'phoneRail': False})
        self.assertEqual(prod, {'board': False, 'watch': True, 'header': False, 'phoneFormat': True,
                                'timestamp': True, 'back': True, 'dock': False, 'phoneRail': True})
        self.assertEqual(none, prod)


class BoardJS(BoardFixture):
    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_settled_count_and_tab_statuses(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppSettled', 'ppTabStatus') + """
console.log(JSON.stringify([ppSettled(BOARD.checklist), ppTabStatus(BOARD), ppTabStatus(EMPTY)]));
""".replace('BOARD', json.dumps(self.board())).replace('EMPTY', json.dumps(EMPTY_BOARD))
        settled, status, empty_status = run_node(script)
        self.assertEqual(settled, 3)
        self.assertEqual(status, {'script': 'Draft 2', 'characters': '1 of 2 picked',
                                  'look': 'Moody', 'scenes': '3 · 2 to pick'})
        self.assertEqual(empty_status, {'script': 'No draft yet', 'characters': 'No characters yet',
                                        'look': 'Open', 'scenes': 'No scenes yet'})

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_start_production_checklist(self):
        js = (PKG / 'director.js').read_text()
        script = (_consts(js, 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_CHECK_TAB', 'PP_TAB_LABEL') +
                 _fns(js, 'ppChecklistDetail', 'ppChecklistHtml') + """
console.log(ppChecklistHtml(BOARD));
""".replace('BOARD', json.dumps(self.board())))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        html = result.stdout.decode()
        self.assertEqual(html.count('class="pp-check '), 5)
        self.assertEqual(html.count('>Settled</span>'), 3)
        self.assertEqual(html.count('>Open</span>'), 2)
        self.assertEqual(html.count('data-pp="goto"'), 2)
        self.assertIn('data-pp-tab="characters"', html)
        self.assertIn('data-pp-tab="scenes"', html)
        self.assertNotIn('data-pp-tab="script"', html)   # script and look are already settled

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_problems_are_listed(self):
        (self.directory / 'bible/options/broken.json').write_text('not json')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-qm', 'hand-broken set')
        board = self.board()
        self.assertEqual(len(board['problems']), 1)
        js = (PKG / 'director.js').read_text()
        script = (_consts(js, 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_CHECK_TAB', 'PP_TAB_LABEL') +
                  _fns(js, 'ppProblemsText', 'ppSettled', 'ppTabStatus', 'ppChecklistDetail',
                       'ppChecklistHtml') + """
console.log(JSON.stringify([ppProblemsText(BOARD.problems), ppTabStatus(BOARD), ppSettled(BOARD.checklist),
  ppChecklistHtml(BOARD).split('class="pp-check ').length-1]));
""".replace('BOARD', json.dumps(board)))
        text, status, settled, checks = run_node(script)
        problem = board['problems'][0]
        self.assertIn('bible/options/broken.json', text)
        self.assertIn(f"{problem['file']} ({problem['error']})", text)
        # everything else still renders from the same body
        self.assertEqual(status, {'script': 'Draft 2', 'characters': '1 of 2 picked',
                                  'look': 'Moody', 'scenes': '3 · 2 to pick'})
        self.assertEqual((settled, checks), (3, 5))

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_script_renders_screenplay_elements(self):
        js = (PKG / 'director.js').read_text()
        board_script = self.script()
        dialogue_line = next(e['line'] for e in board_script['elements'] if e['type'] == 'dialogue')
        script = _consts(js, 'esc') + _fns(js, 'ppScriptHtml', 'ppScriptElementHtml', 'ppCommentBoxHtml') + """
const base={drafting:false,draftingNote:null,commentAt:null,pendingQuotes:new Set()};
console.log(JSON.stringify([
  ppScriptHtml(SCRIPT, base),
  ppScriptHtml(SCRIPT, {...base,pendingQuotes:new Set([LINE])}),
  ppScriptHtml(null, base),
]));
""".replace('SCRIPT', json.dumps(board_script)).replace('LINE', str(dialogue_line))
        html, with_marker, empty_html = run_node(script)
        for t in ('heading', 'action', 'character', 'parenthetical', 'dialogue', 'transition', 'section',
                 'synopsis'):
            self.assertIn(f'class="pp-el {t}"', html)
        self.assertIn('id="pp-sc-1"', html)
        self.assertEqual(html.count('>1<'), 2)   # scene 1's number shows on both sides of its heading
        self.assertIn('Draft 2', html)
        self.assertIn('&lt;b&gt;Bright&lt;/b&gt; &amp; &quot;loud&quot;', html)
        self.assertEqual(html.count('data-pp="jump"'), 2)
        self.assertNotIn('Not sent yet', html)
        self.assertIn('Not sent yet', with_marker)
        self.assertIn('No script yet', empty_html)

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_drafting_banner_only_while_a_note_runs(self):
        js = (PKG / 'director.js').read_text()
        script = (_consts(js, 'esc', 'svg', 'TL_ICON') +
                 _fns(js, 'ppScriptHtml', 'ppScriptElementHtml') + """
const base={drafting:false,draftingNote:null,commentAt:null,pendingQuotes:new Set()};
console.log(JSON.stringify([
  ppScriptHtml(SCRIPT, base).includes('pp-drafting'),
  ppScriptHtml(SCRIPT, {...base,drafting:true,draftingNote:'Drafting scene 3'}).includes('Drafting scene 3'),
]));
""".replace('SCRIPT', json.dumps(self.script())))
        off, on = run_node(script)
        self.assertFalse(off)
        self.assertTrue(on)

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_look_tab(self):
        js = (PKG / 'director.js').read_text()
        script = (_consts(js, 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_KIND', 'api') +
                 _fns(js, 'ppTag', 'ppConceptFor', 'ppPicture', 'ppSetStatus', 'ppOptionCard', 'ppSceneLookRow',
                      'ppLookHtml') + """
console.log(ppLookHtml(BOARD,'promo/film'));
""".replace('BOARD', json.dumps(self.board())))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        html = result.stdout.decode()
        self.assertIn('Picked A', html)
        self.assertIn('pp-swatches', html)
        self.assertEqual(html.count('data-pp="pick"'), 2)
        self.assertEqual(html.count('<select'), 3)                 # one row per scene
        self.assertIn('value="" selected>Film look</option>', html)      # lantern-room/dawn: no override
        self.assertIn('value="Sunbleached" selected', html)              # cliff's own override, unknown to the set

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_scenes_tab(self):
        js = (PKG / 'director.js').read_text()
        script = (_consts(js, 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_KIND', 'api') +
                 _fns(js, 'ppTag', 'ppConceptFor', 'ppPicture', 'ppSetStatus', 'ppOptionCard', 'ppSceneThumb',
                      'ppSceneMusicLine', 'ppSceneCard', 'ppScenesHtml') + """
console.log(ppScenesHtml(BOARD,'promo/film'));
""".replace('BOARD', json.dumps(self.board())))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        html = result.stdout.decode()
        self.assertEqual(html.count('class="pp-scene-card"'), 3)
        self.assertIn('INT. LIGHTHOUSE - LANTERN ROOM - NIGHT', html)
        self.assertIn('Mara checks the lamp as the storm builds.', html)
        self.assertIn('Storm theme', html)
        self.assertIn('0:00', html)
        self.assertIn('0:28', html)
        # lantern-room's thumb, plus its own option A card -- cliff and dawn have no picture at all
        self.assertEqual(html.count('class="pp-pic'), 2)
        self.assertEqual(html.count('data-pp="pick"'), 4)         # lantern-room's 2 options + cliff's 2
        self.assertEqual(html.count('class="pp-scene-music"'), 1)  # only lantern-room sits on a song


class BoardActionsJS(BoardFixture):
    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_start_production_posts_phase_and_survives_a_refusal(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppStartProduction', 'ppOpenStart') + """
const state={video:'promo/film'};
const els={};
const mk=()=>({hidden:true,textContent:'',disabled:false,setAttribute(){}});
const $=id=>els[id]??=mk();
const calls=[];
const applyPhase=p=>calls.push(['applyPhase',p]);
const loadNotes=async()=>calls.push('loadNotes');
const loadVersions=async()=>calls.push('loadVersions');
let reply=null;
const json=async(path,params,body)=>{calls.push([path,body]);
  if(reply instanceof Error)throw reply;
  return reply};
(async()=>{
  const out=[];
  reply=Object.assign(new Error('the video does not load; fix it before starting production'),{status:409});
  const b1={disabled:false};
  await ppStartProduction(b1);
  out.push([calls.splice(0), $('pp-start-error').hidden, $('pp-start-error').textContent, b1.disabled]);
  state.commit='c1';
  state.deliberate=true;
  reply={phase:'production',changed:true,commit:'c2',n:2,note:{id:'n1'}};
  const b2={disabled:false};
  await ppStartProduction(b2);
  out.push([calls.splice(0), $('pp-start-pop').hidden, b2.disabled, state.commit, state.deliberate]);
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        posted = ['phase', {'video': VIDEO, 'phase': 'production'}]
        self.assertEqual(out[0], [[posted], False,
                                  'the video does not load; fix it before starting production', False])
        self.assertEqual(out[1][0], [posted, ['applyPhase', 'production'], 'loadNotes', 'loadVersions'])
        self.assertTrue(out[1][1])     # the popover closes on success
        self.assertFalse(out[1][2])
        # production plays the phase commit, not whatever was latest when the video opened
        self.assertEqual(out[1][3:], ['c2', False])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_back_to_preproduction_arms_then_posts(self):
        js = (PKG / 'director.js').read_text()
        script = _consts(js, 'ppBackArmed') + _fns(js, 'ppBackToPreprod', 'confirmBackToPreprod',
                                                    'loadPreprod') + """
const timers=[];
const setTimeout=fn=>{timers.push(fn);return timers.length};
const clearTimeout=()=>{};
const state={video:'promo/film',ppSeq:0};
const calls=[];
const applyPhase=p=>calls.push(['applyPhase',p]);
const renderBoard=()=>calls.push('renderBoard');
const toast=()=>{};
let reply={phase:'pre-production',changed:true,commit:'c3',n:3,checklist:[],sets:[],
  scenes:{scenes:[],songs:[],seconds:0,length:'0:00'},problems:[],characters:[],
  script:{exists:false,draft:null,title:null,scenes:0}};
const json=async(path,params,body)=>{calls.push([path,body]);return reply};
(async()=>{
  const out=[];
  const b={textContent:'Back to pre-production'};
  ppBackToPreprod(b);
  out.push([b.textContent, calls.splice(0)]);
  await ppBackToPreprod(b);                  // second click within the window: posts
  out.push([b.textContent, calls.splice(0)]);
  const b2={textContent:'Back to pre-production'};
  ppBackToPreprod(b2);
  timers.pop()();                            // 3 s pass, unarmed
  ppBackToPreprod(b2);                       // a click now only re-arms
  out.push([b2.textContent, calls.splice(0)]);
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        self.assertEqual(out[0], ['Really go back to planning?', []])
        self.assertEqual(out[1][0], 'Back to pre-production')
        self.assertEqual(out[1][1][0], ['phase', {'video': 'promo/film', 'phase': 'pre-production'}])
        self.assertEqual(out[1][1][1], ['applyPhase', 'pre-production'])
        self.assertIn(['preprod', None], out[1][1])
        self.assertEqual(out[2], ['Really go back to planning?', []])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_board_refreshes_from_existing_polls_only(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'loadNotes', 'loadVersions') + """
const calls={loadPreprod:0,loadPlayer:0};
const toasts=[];
const state={video:'promo/film',phase:'pre-production',notes:[],versions:[],versionCursor:null,
  loadingVersions:false,deliberate:false,commit:null,restarting:false,pollError:null};
const els={};
const $=id=>els[id]??=({textContent:''});
const showError=()=>{};
const renderNotes=()=>{};
const notBuilt=()=>false;
const currentVersion=()=>null;
const showBlank=()=>{};
const updateBuildPill=()=>{};
const updateLabels=()=>{};
const toast=m=>toasts.push(m);
const loadPreprod=()=>{calls.loadPreprod++};
const loadPlayer=()=>{calls.loadPlayer++};
let notesQueue=[{notes:[{id:'n1',state:'queued'}]},{notes:[{id:'n1',state:'queued'}]},
  {notes:[{id:'n1',state:'working'}]},{notes:[{id:'n1',state:'replied'}]}];
let versionsQueue=[{versions:[{n:1,commit:'a'}]},{versions:[{n:2,commit:'b'}]}];
const json=async path=>path==='notes'?notesQueue.shift():versionsQueue.shift();
(async()=>{
  const out=[];
  await loadNotes();
  out.push(calls.loadPreprod);
  await loadNotes();
  out.push(calls.loadPreprod);
  await loadNotes();
  out.push(calls.loadPreprod);
  state.phase='production';
  await loadNotes();
  out.push(calls.loadPreprod);
  state.phase='pre-production';
  await loadVersions();
  out.push([calls.loadPreprod,calls.loadPlayer,toasts.length]);
  await loadVersions();
  out.push([calls.loadPreprod,calls.loadPlayer,toasts.length,state.commit]);
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        self.assertEqual(out[:4], [1, 1, 2, 2])
        self.assertEqual(out[4], [2, 1, 0])     # the first version ever seen just starts playback
        # a later commit in pre-production refreshes the board only, but still becomes current
        self.assertEqual(out[5], [3, 1, 0, 'b'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_failures_leave_the_board_as_it_was(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppStartProduction', 'loadPreprod') + """
const state={video:'promo/film',phase:null,board:null,ppSeq:0};
const els={};
const mk=()=>({hidden:true,textContent:'',disabled:false});
const $=id=>els[id]??=mk();
const applyPhase=p=>{};
const renderBoard=()=>{};
const loadNotes=async()=>{};
const loadVersions=async()=>{};
const showError=()=>{};
const resolvers=[];
const json=(path,params,body)=>new Promise((resolve,reject)=>resolvers.push([path,body,resolve,reject]));
(async()=>{
  const out=[];
  const button={disabled:false};
  const p1=ppStartProduction(button);
  const [path1,,,reject1]=resolvers.shift();
  reject1(Object.assign(new Error('the video does not load; fix it before starting production'),{status:409}));
  await p1;
  out.push([path1,state.phase,$('pp-start-error').textContent,$('pp-start-error').hidden,button.disabled]);
  const p2=loadPreprod();
  const [,,resolve2]=resolvers.shift();
  const p3=loadPreprod();
  const [,,resolve3]=resolvers.shift();
  resolve3({phase:'pre-production',commit:'new',script:{exists:false}});
  await p3;
  resolve2({phase:'pre-production',commit:'stale',script:{exists:false}});
  await p2;
  out.push(state.board&&state.board.commit);
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        self.assertEqual(out[0], ['phase', None,
                                  'the video does not load; fix it before starting production', False, False])
        self.assertEqual(out[1], 'new')

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_pick_failure_leaves_the_board_unchanged(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppPick') + """
const state={video:'promo/film',board:{marker:'kept'}};
const renderBoard=()=>{throw new Error('renderBoard must not run on failure')};
const toasts=[];
const toast=m=>toasts.push(m);
const json=async()=>{throw Object.assign(new Error('no such option set'),{status:404})};
(async()=>{
  await ppPick('look','Z');
  console.log(JSON.stringify([state.board, toasts]));
})();
"""
        board, toasts = run_node(script)
        self.assertEqual(board, {'marker': 'kept'})
        self.assertEqual(toasts, ['no such option set'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_checklist_goto_closes_the_dialog_and_shows_the_tab(self):
        js = (PKG / 'director.js').read_text()
        script = _consts(js, 'PP_TABS') + _fns(js, 'ppGoto', 'ppOpenStart', 'ppShowTab') + """
const state={ppTab:'script'};
const els={};
const $=id=>els[id]??=({hidden:false,attrs:{},setAttribute(k,v){this.attrs[k]=v}});
const renderStartPop=()=>{};
ppGoto('scenes');
console.log(JSON.stringify([state.ppTab,$('pp-start-pop').hidden,$('pp-start-shade').hidden,
  $('pp-panel-scenes').hidden,$('pp-panel-script').hidden,$('pp-tab-scenes').attrs['aria-selected']]));
"""
        self.assertEqual(run_node(script), ['scenes', True, True, False, True, 'true'])
        # the checklist lives in the dialog, outside #board's delegated listener
        wiring = re.search(r"\$\('pp-checks'\)\.addEventListener\('click',.*?\n\}\);", js, re.S)
        self.assertIsNotNone(wiring)
        self.assertIn('ppGoto(b.dataset.ppTab)', wiring.group(0))

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_an_open_comment_box_survives_a_board_refresh(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'renderBoard', 'ppToggleComment', 'ppQueueComment', 'ppCommentText') + """
const draft1={draft:1,elements:[{type:'action',text:'The lamp turns.',line:3,scene:1},
  {type:'dialogue',text:'Still turning.',line:5,scene:1}]};
const draft2={draft:2,elements:[{type:'action',text:'A new opening line.',line:3,scene:1},
  {type:'action',text:'The lamp turns.',line:5,scene:1}]};
const state={board:{checklist:[],problems:[],scenes:{scenes:[]}},script:draft1,ppShown:draft1,
  ppComment:null,pending:[]};
const calls=[];
const panel={querySelector:q=>q==='.pp-comment-box'?null:{focus(){}}};
const $=id=>id==='pp-panel-script'?panel:{hidden:true,textContent:''};
const PP_TABS=[];
const ppSettled=()=>0, ppTabStatus=()=>({});
const renderScript=()=>{state.ppShown=state.script;calls.push('renderScript')};
const renderCharacters=()=>{}, renderLook=()=>{}, renderScenes=()=>{};
const savePending=()=>{}, renderPending=()=>{};
const tlPhone=()=>false;
const ppCommentBoxHtml=()=>'';
const line={dataset:{i:'0'},closest:()=>({insertAdjacentHTML:()=>calls.push('box inserted')})};
ppToggleComment(line);
state.script=draft2;          // the builder redrafts while the director types
renderBoard();
const out=[calls.splice(0)];
ppQueueComment(state.ppComment,'Slower here.');
out.push(state.pending[0].text, calls.splice(0), state.ppShown===draft2, state.ppComment);
console.log(JSON.stringify(out));
"""
        out = run_node(script)
        self.assertEqual(out[0], ['box inserted'])   # no re-render: the typed text stays put
        self.assertEqual(out[1], 'Script, draft 1, scene 1, line 3: "The lamp turns."\nSlower here.')
        self.assertEqual(out[2], ['renderScript'])   # the panel catches up once the box closes
        self.assertTrue(out[3])
        self.assertIsNone(out[4])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_comment_queues_a_quoted_pending_note(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppCommentText', 'ppQueueComment') + """
const calls=[];
const state={script:{draft:2,elements:[
  {type:'dialogue',text:'Still turning. Good.',line:7,scene:1},
  {type:'action',text:'A note.',line:3,scene:null},
]},pending:[],ppComment:null};
const savePending=()=>calls.push('save');
const renderPending=()=>calls.push('render');
const renderScript=()=>calls.push('renderScript');
const tlPhone=()=>false;
const openSheet=()=>calls.push('openSheet');
const json=()=>{throw new Error('no network call expected')};
state.ppComment={draft:2,el:state.script.elements[0]};
ppQueueComment(state.ppComment,'Can she sound more rattled?');
const out=[calls.splice(0),JSON.parse(JSON.stringify(state.pending)),state.ppComment];
state.ppComment={draft:null,el:state.script.elements[1]};
ppQueueComment(state.ppComment,'A second note.');
out.push(state.pending[1].text);
console.log(JSON.stringify(out));
"""
        out = run_node(script)
        self.assertEqual(out[0], ['save', 'render', 'renderScript'])
        self.assertEqual(out[1], [{'text': 'Script, draft 2, scene 1, line 7: "Still turning. Good."\n'
                                            'Can she sound more rattled?',
                                   'time': None, 'attachments': [], 'capabilities': [], 'fonts': [], 'sfx': [],
                                   'music': [], 'scriptLine': 7}])
        self.assertIsNone(out[2])
        self.assertEqual(out[3], 'Script, line 3: "A note."\nA second note.')

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_characters_tab(self):
        js = (PKG / 'director.js').read_text()
        script = (_consts(js, 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_KIND', 'api') +
                 _fns(js, 'ppTag', 'ppConceptFor', 'ppPicture', 'ppSetStatus', 'ppOptionCard',
                      'ppCharacterCard', 'ppCastHtml') + """
const board={commit:'c1',concepts:[],characters:[
  {slug:'mara',name:'Mara',description:'The keeper.',pictures:['mara-1.png'],set:'character-mara'},
  {slug:'tom',name:'Tom',description:'Her brother.',pictures:[],set:null},
],sets:[
  {id:'character-mara',topic:'character',character:'mara',pick:'A',
   options:[{key:'A',label:'Weathered keeper',text:'x',image:null,kind:null},
            {key:'B',label:'Reluctant heir',text:'y',image:null,kind:null}]},
  {id:'character-ghost',topic:'character',character:'ghost',pick:null,
   options:[{key:'A',label:'Ghost A',text:'x',image:null,kind:null},
            {key:'B',label:'Ghost B',text:'y',image:null,kind:null}]},
]};
console.log(ppCastHtml(board,'promo/film'));
""")
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        html = result.stdout.decode()
        self.assertIn('Mara', html)
        self.assertIn('The keeper.', html)
        self.assertIn('Picked A', html)
        self.assertIn('>yours<', html)
        self.assertIn('film/picture?', html)
        self.assertIn('Tom', html)
        self.assertIn('No takes yet', html)
        self.assertIn('ghost', html)       # the orphan set still gets a card, titled by its slug
        self.assertEqual(html.count('data-pp="pick"'), 4)   # 2 for Mara, 2 for the orphan; none for Tom

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_pick_posts_for_character_look_and_scene_sets(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppPick') + """
const state={video:'promo/film',board:{marker:'old'}};
const calls=[];
const renderBoard=()=>calls.push('renderBoard');
const toast=()=>{};
let reply=null;
const json=async(path,params,body)=>{calls.push([path,body]);return reply};
(async()=>{
  const out=[];
  reply={marker:'character'};
  await ppPick('character-mara','B');
  out.push([calls.splice(0),state.board]);
  reply={marker:'look'};
  await ppPick('look','A');
  out.push([calls.splice(0),state.board]);
  reply={marker:'scene'};
  await ppPick('scene-lantern-room',null);
  out.push([calls.splice(0),state.board]);
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        self.assertEqual(out[0], [[['preprod/pick', {'video': 'promo/film', 'set': 'character-mara', 'key': 'B'}],
                                   'renderBoard'], {'marker': 'character'}])
        self.assertEqual(out[1], [[['preprod/pick', {'video': 'promo/film', 'set': 'look', 'key': 'A'}],
                                   'renderBoard'], {'marker': 'look'}])
        self.assertEqual(out[2], [[['preprod/pick',
                                   {'video': 'promo/film', 'set': 'scene-lantern-room', 'key': None}],
                                   'renderBoard'], {'marker': 'scene'}])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_picture_kind_labels_and_concept_states(self):
        js = (PKG / 'director.js').read_text()
        script = _consts(js, 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_KIND', 'api') + _fns(js, 'ppTag', 'ppPicture') + """
const out={};
out.vb=ppPicture('bible/options/look/A.png','vb',null,'promo/film','c1');
out.concept=ppPicture('bible/options/look/B.png','concept',null,'promo/film','c1');
out.yours=ppPicture('bible/options/char/x.png','yours',null,'promo/film','c1');
out.requested=ppPicture('bible/options/look/C.png','concept',{status:'requested'},'promo/film','c1');
out.making=ppPicture('bible/options/look/C.png','concept',{status:'making'},'promo/film','c1');
out.unavailable=ppPicture('bible/options/look/C.png','concept',
  {status:'unavailable',message:'no artbox configured'},'promo/film','c1');
out.done=ppPicture('bible/options/look/C.png','concept',{status:'done'},'promo/film','c1');
console.log(JSON.stringify(out));
"""
        out = run_node(script)
        self.assertIn('vb frame', out['vb'])
        self.assertIn('concept, not final', out['concept'])
        self.assertIn('>yours<', out['yours'])
        for status in ('requested', 'making'):
            self.assertIn('Making concept art…', out[status])
        self.assertIn('Concept art unavailable', out['unavailable'])
        self.assertIn('no artbox configured', out['unavailable'])
        self.assertIn('preprod/image', out['done'])
        self.assertIn('v=c1', out['done'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_scene_look_override_posts_the_stored_plan(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppStoredScenes', 'ppSaveScenes', 'ppSetSceneLook') + """
function freshBoard() {
  return {commit:'c1',scenes:{songs:[{id:'storm-theme'}],scenes:[
    {id:'lantern-room',slugline:'A',summary:'s',seconds:28,song:'storm-theme',section:'intro',from:0,to:18,
     look:null,number:1,length:'0:28',from_clock:'0:00',to_clock:'0:18',set:'scene-lantern-room'},
    {id:'cliff',slugline:'B',summary:'t',seconds:20,song:null,section:null,from:null,to:null,
     look:{name:'Sunbleached',reason:'x'},number:2,length:'0:20',from_clock:null,to_clock:null,set:null},
  ]}};
}
let state={video:'promo/film',board:freshBoard()};
const calls=[];
const toasts=[];
const toast=m=>toasts.push(m);
const renderBoard=()=>calls.push('renderBoard');
const loadPreprod=()=>calls.push('loadPreprod');
let reply=null;
const json=async(path,params,body)=>{calls.push([path,body]);
  if(reply instanceof Error)throw reply;
  return reply};
(async()=>{
  const out=[];
  reply={commit:'c2'};
  await ppSetSceneLook('lantern-room','Moody');
  out.push([calls.splice(0),state.board]);
  state=JSON.parse(JSON.stringify({video:'promo/film',board:freshBoard()}));
  reply={commit:'c3'};
  await ppSetSceneLook('cliff','');
  out.push(calls.splice(0)[0][1].scenes.find(s=>s.id==='cliff').look);
  state.board=freshBoard();
  reply=Object.assign(new Error('scenes[1].to must be greater than from'),{status:400});
  await ppSetSceneLook('lantern-room','Moody');
  out.push([calls.splice(0),toasts.splice(0),state.board]);
  reply=Object.assign(new Error('stale'),{status:409});
  await ppSetSceneLook('lantern-room','Moody');
  out.push([calls.splice(0),toasts.splice(0)]);
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        self.assertEqual(out[0][0][0][0], 'preprod/scenes')
        body = out[0][0][0][1]
        self.assertEqual(body['base'], 'c1')
        self.assertEqual(body['songs'], [{'id': 'storm-theme'}])
        lantern = next(s for s in body['scenes'] if s['id'] == 'lantern-room')
        self.assertEqual(lantern['look'], {'name': 'Moody', 'reason': ''})
        for key in ('number', 'length', 'from_clock', 'to_clock', 'set'):
            self.assertNotIn(key, lantern)
        self.assertEqual(out[0][0][1], 'renderBoard')
        self.assertEqual(out[0][1]['commit'], 'c2')     # the response replaces state.board
        self.assertIsNone(out[1])                        # '' (Film look) clears the override
        self.assertEqual(out[2][0], [['preprod/scenes', mock.ANY], 'renderBoard'])
        self.assertEqual(out[2][1], ['scenes[1].to must be greater than from'])
        self.assertEqual(out[2][2]['commit'], 'c1')       # and leaves the board exactly as it was
        self.assertEqual(out[3][0], [['preprod/scenes', mock.ANY], 'loadPreprod'])
        self.assertEqual(out[3][1], ['The plan changed while you were dragging. Here it is now.'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_reorder_posts_new_order_and_handles_conflict(self):
        js = (PKG / 'director.js').read_text()
        script = _fns(js, 'ppMoveScene', 'ppStoredScenes', 'ppSaveScenes', 'ppReorder') + """
const scenes=['a','b','c','d'].map(id=>({id}));
const moves={
  firstToLast: ppMoveScene(scenes,'a',3).map(s=>s.id),
  lastToFirst: ppMoveScene(scenes,'d',0).map(s=>s.id),
  middle: ppMoveScene(scenes,'b',2).map(s=>s.id),
};
function freshBoard() {
  return {commit:'c1',scenes:{songs:[],scenes:[
    {id:'a',number:1,length:'0:10',from_clock:null,to_clock:null,set:null,slugline:'A',summary:'',seconds:10},
    {id:'b',number:2,length:'0:10',from_clock:null,to_clock:null,set:null,slugline:'B',summary:'',seconds:10},
  ]}};
}
let state={video:'promo/film',board:freshBoard()};
const calls=[];
const toasts=[];
const toast=m=>toasts.push(m);
const renderBoard=()=>calls.push('renderBoard');
const loadPreprod=()=>calls.push('loadPreprod');
let reply=null;
const json=async(path,params,body)=>{calls.push([path,body]);
  if(reply instanceof Error)throw reply;
  return reply};
(async()=>{
  const out=[moves];
  await ppReorder('a',0);                     // dropped where it already was: no request
  out.push(calls.splice(0));
  reply={commit:'c2'};
  await ppReorder('b',0);
  const snap=calls.splice(0);
  out.push([snap[0][1].scenes.map(s=>s.id), snap[1]]);
  state.board=freshBoard();
  reply=Object.assign(new Error('stale'),{status:409});
  await ppReorder('a',1);
  out.push(calls.splice(0));
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(script)
        self.assertEqual(out[0], {'firstToLast': ['b', 'c', 'd', 'a'], 'lastToFirst': ['d', 'a', 'b', 'c'],
                                  'middle': ['a', 'c', 'b', 'd']})
        self.assertEqual(out[1], [])
        self.assertEqual(out[2], [['b', 'a'], 'renderBoard'])
        self.assertEqual(out[3], [['preprod/scenes', mock.ANY], 'loadPreprod'])


PICTURE_QUESTIONS = [{'text': 'Which look fits best?', 'set': 'look', 'choices': [
    {'text': 'Moody, low-key lighting', 'image': 'bible/options/look/A.png', 'kind': 'vb', 'key': 'A'},
    {'text': 'Bright and saturated', 'image': 'bible/options/look/B.png', 'kind': 'concept', 'key': 'B'},
]}]


class ChatPictureCardsJS(Server):
    """renderQuestionsCard is node()-built and reads a live `answers`/`refresh` closure, so
    these tests run it for real (not a pure string function) against a note that actually
    came out of the documented pre-production flow (QuestionBackend + settle), the same
    picture-choice shape docs/preproduction.md shows."""

    def setUp(self):
        super().setUp()
        self.post('/api/phase', {'video': VIDEO, 'phase': 'pre-production'})
        self.post('/api/preprod/sets', {'video': VIDEO, 'base': self.commit_main(), 'set': LOOK_SET})

    def _ask(self, questions):
        self.restart(auto_land=False, backend=QuestionBackend(questions))
        code, note = self.post('/api/notes', {'video': VIDEO, 'frame': 0, 'text': 'pick a look'})
        self.assertEqual(code, 200)
        settle(self.editor)
        return self.get('/api/notes?video=' + VIDEO)['notes'][-1]

    # A minimal DOM: node()-built elements with real parent/child tracking, so querySelectorAll
    # (by class) and a click handler set by the real code actually work, with no HTML parser
    # (none is available under plain node) -- innerHTML is stored as a string, not parsed.
    DOM_STUB = """
function mkEl(tag) {
  const el={tag,className:'',textContent:'',innerHTML:'',children:[],dataset:{},attrs:{},hidden:false,
    disabled:false,type:'',value:'',
    append(...cs){this.children.push(...cs)},
    replaceChildren(){this.children=[]},
    setAttribute(k,v){this.attrs[k]=String(v)},
    getAttribute(k){return this.attrs[k]},
    classList:{
      add:(...cs)=>{for(const c of cs){const parts=el.className.split(' ').filter(Boolean);
        if(!parts.includes(c))parts.push(c);el.className=parts.join(' ')}},
      remove:(...cs)=>{el.className=el.className.split(' ').filter(c=>c&&!cs.includes(c)).join(' ')}
    },
    querySelectorAll(sel){
      const cls=sel.replace('.','');
      const out=[];
      const walk=n=>{for(const c of n.children){
        if((c.className||'').split(' ').filter(Boolean).includes(cls))out.push(c);
        walk(c)
      }};
      walk(el);
      return out
    }
  };
  return el
}
const document={createElement:mkEl};
const text=n=>[n.textContent,n.innerHTML,...n.children.map(text)].join(' ');
"""

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_picture_question_renders_cards_and_answers_with_choice_text(self):
        note = self._ask(PICTURE_QUESTIONS)
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node', 'esc', 'svg', 'TL_ICON', 'PP_ICON', 'PP_KIND', 'api') +
                 _fns(js, 'ppTag', 'questionAnswered', 'ppPictureNode', 'ppUnpickCards', 'questionPictureCards',
                      'renderQuestionsCard', 'sendAnswers') + """
const state={pendingAnswers:{},video:'promo/film'};
const calls=[];
let reply={};
// A copy: sendAnswers posts the live `answers` array, which the Other… click below mutates.
const json=async(path,params,body)=>{calls.push([path,structuredClone(body)]);return reply};
const loadNotes=async()=>calls.push('loadNotes');
const showError=()=>{};
(async()=>{
  const out=[];
  const wrap=renderQuestionsCard(NOTE);
  const row=wrap.querySelectorAll('.choice-row')[0];
  const cards=row.querySelectorAll('.pp-opt');
  out.push(cards.map(text));
  cards[1].onclick();
  out.push(cards.map(c=>c.className.includes('picked')));
  out.push(cards.map(c=>c.attrs['aria-pressed']));
  const send=wrap.querySelectorAll('.questions-send')[0];
  await send.onclick();
  out.push(calls.splice(0));
  out.push(wrap.querySelectorAll('.questions-build').length);
  const otherChip=wrap.querySelectorAll('.other')[0];
  out.push(otherChip?.textContent);
  wrap.querySelectorAll('.other-input')[0].focus=()=>{};
  otherChip.onclick();
  out.push([cards.map(c=>c.className.includes('picked')),cards.map(c=>c.attrs['aria-pressed'])]);
  out.push(text(ppPictureNode('bible/options/look/C.png','concept',{status:'making'},'c1')));
  console.log(JSON.stringify(out));
})();
""".replace('NOTE', json.dumps(note)))
        out = run_node(script)
        self.assertIn('vb frame', out[0][0])
        self.assertIn('Moody, low-key lighting', out[0][0])
        self.assertIn('concept, not final', out[0][1])
        self.assertIn('Bright and saturated', out[0][1])
        self.assertEqual(out[1], [False, True])
        self.assertEqual(out[2], ['false', 'true'])
        self.assertTrue(out[3][0][0].endswith('/answer'))
        self.assertEqual(out[3][0][1], {'answers': ['Bright and saturated']})
        self.assertEqual(out[3][1], 'loadNotes')
        self.assertEqual(out[4], 1)                 # Just build it remains
        self.assertEqual(out[5], 'Other…')           # Other… remains
        self.assertIn('Making concept art…', out[7])
        # Other… takes the pick away from the picture cards, so two answers never look chosen.
        self.assertEqual(out[6], [[False, False], ['false', 'false']])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_text_only_question_renders_chips_as_before(self):
        note = self._ask([{'text': 'Which look?', 'choices': ['Moody', 'Bright']}])
        js = (PKG / 'director.js').read_text()
        script = self.DOM_STUB + _consts(js, 'node') + _fns(js, 'questionAnswered', 'renderQuestionsCard') + """
const state={pendingAnswers:{}};
const wrap=renderQuestionsCard(NOTE);
const row=wrap.querySelectorAll('.choice-row')[0];
console.log(JSON.stringify({
  chips: row.querySelectorAll('.choice-chip').map(c=>c.textContent),
  opts: row.querySelectorAll('.pp-opt').length,
  otherInput: wrap.querySelectorAll('.other-input').length,
  send: wrap.querySelectorAll('.questions-send').length,
  build: wrap.querySelectorAll('.questions-build').length,
}));
""".replace('NOTE', json.dumps(note))
        out = run_node(script)
        self.assertEqual(out['chips'], ['Moody', 'Bright', 'Other…'])
        self.assertEqual(out['opts'], 0)
        self.assertEqual(out['otherInput'], 1)
        self.assertEqual(out['send'], 1)
        self.assertEqual(out['build'], 1)


class ChatAttachmentsJS(unittest.TestCase):
    """The composer tray, the drop overlay, sent-bubble media and the lightbox
    (director.js's trayItemNode/bubbleAttachments/openLightbox family), run for
    real against plain attachment-record data -- not the mockup's own JS, the
    same node()-built code the editor actually ships."""

    # Like ChatPictureCardsJS.DOM_STUB, but also resolves #icon-* templates (icon()/
    # sizedIcon() clone one) and keeps a $(id) registry (the glue functions -- renderFiles,
    # openLightbox -- read/write specific ids, not just build detached nodes).
    DOM_STUB = """
function mkEl(tag) {
  const el={tag,className:'',textContent:'',innerHTML:'',children:[],dataset:{},attrs:{},hidden:false,
    disabled:false,type:'',value:'',src:'',alt:'',controls:false,autoplay:false,style:{},
    append(...cs){this.children.push(...cs)},
    replaceChildren(...cs){this.children=cs},
    remove(){},
    setAttribute(k,v){this.attrs[k]=String(v)},
    getAttribute(k){return this.attrs[k]},
    cloneNode(){const c=mkEl(this.tag);c.className=this.className;return c},
    classList:{
      add:(...cs)=>{for(const c of cs){const parts=el.className.split(' ').filter(Boolean);
        if(!parts.includes(c))parts.push(c);el.className=parts.join(' ')}},
      remove:(...cs)=>{el.className=el.className.split(' ').filter(c=>c&&!cs.includes(c)).join(' ')}
    },
    querySelector(sel){return this.querySelectorAll(sel)[0]||null},
    querySelectorAll(sel){
      const cls=sel.replace('.','');
      const out=[];
      const walk=n=>{for(const c of (n.children||[])){
        if((c.className||'').split(' ').filter(Boolean).includes(cls))out.push(c);
        walk(c)
      }};
      walk(el);
      return out
    }
  };
  return el
}
const ICON_EL={};
const document={
  createElement:mkEl,
  querySelector(sel){
    const m=/^#icon-(.+)$/.exec(sel);
    if(!m)return null;
    if(!ICON_EL[m[1]])ICON_EL[m[1]]=mkEl('svg');
    return {content:{firstElementChild:ICON_EL[m[1]]}}
  },
  addEventListener(){},removeEventListener(){}
};
const ELS={};
const $=id=>ELS[id]||(ELS[id]=mkEl('div'));
const text=n=>[n.textContent,n.innerHTML,...(n.children||[]).map(text)].join(' ');
const classes=n=>(n.className||'').split(' ').filter(Boolean);
"""

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_tray_renders_each_attachment_type_with_progress_and_error(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node', 'api') +
                 _fns(js, 'icon', 'sizedIcon', 'sizeLabel', 'waveSvg', 'ringSvg', 'ringDash',
                      'attachmentUrl', 'trayAudioSrc', 'trayItemNode') + """
const timeLabel=s=>{s=Math.max(0,Math.floor(s||0));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`};
let trayPlayingId=null;
const uploadingImage=trayItemNode({localId:1,file:null,id:null,name:'screenshot.png',type:'image/png',
  size:900000,progress:45,error:null,url:'blob:local',frame:null,duration:null,peaks:null,thumb:null});
const plainImage=trayItemNode({localId:2,file:null,id:'img2',name:'lamp-room.jpg',type:'image/jpeg',
  size:120000,progress:null,error:null,url:null,frame:null,duration:null,peaks:null,thumb:null});
const video=trayItemNode({localId:3,file:null,id:'vid3',name:'waves.mp4',type:'video/mp4',
  size:3000000,progress:null,error:null,url:null,frame:'data:image/jpeg;base64,x',duration:75,peaks:null});
const audio=trayItemNode({localId:4,file:null,id:'au4',name:'storm-theme.wav',type:'audio/wav',
  size:5000000,progress:null,error:null,url:null,frame:null,duration:187,peaks:[.1,.4,.9,.2]});
const doc=trayItemNode({localId:5,file:null,id:null,name:'treatment.pdf',type:'application/pdf',
  size:600000,progress:null,error:'attachment exceeds file size limit',url:null,frame:null,duration:null,peaks:null});
console.log(JSON.stringify({
  uploadingImage:{cls:classes(uploadingImage),up:uploadingImage.querySelectorAll('up').length,
    pct:text(uploadingImage.querySelectorAll('up')[0])},
  plainImage:{cls:classes(plainImage),name:plainImage.querySelectorAll('tname-ov')[0].textContent,
    imgSrc:plainImage.children.find(c=>c.className==='art').children[0].src},
  video:{cls:classes(video),dur:video.querySelectorAll('dur')[0].textContent,
    imgSrc:video.children.find(c=>c.className==='art').children[0].src},
  audio:{cls:classes(audio),times:audio.querySelectorAll('times')[0].textContent,
    wave:audio.querySelectorAll('wave')[0].innerHTML.includes('<svg')},
  doc:{cls:classes(doc),kind:doc.querySelectorAll('doc-ic')[0].textContent,
    sub:text(doc.querySelectorAll('doc-sub')[0]),bad:doc.querySelectorAll('bad')[0].textContent}
}));
""")
        out = run_node(script)
        self.assertEqual(out['uploadingImage']['cls'], ['tile'])
        self.assertEqual(out['uploadingImage']['up'], 1)
        self.assertIn('45%', out['uploadingImage']['pct'])
        self.assertEqual(out['plainImage']['cls'], ['tile'])
        self.assertEqual(out['plainImage']['name'], 'lamp-room.jpg')
        # No local url/thumb: falls back to the uploaded attachment's own URL.
        self.assertEqual(out['plainImage']['imgSrc'], 'api/attachments/img2')
        self.assertEqual(out['video']['cls'], ['tile'])
        self.assertEqual(out['video']['dur'], '1:15')
        self.assertEqual(out['video']['imgSrc'], 'data:image/jpeg;base64,x')
        self.assertEqual(out['audio']['cls'], ['aud'])
        self.assertEqual(out['audio']['times'], '3:07')
        self.assertTrue(out['audio']['wave'])
        self.assertEqual(out['doc']['cls'], ['tile', 'doc'])
        self.assertEqual(out['doc']['kind'], 'PDF')
        self.assertIn('PDF ·', out['doc']['sub'])
        self.assertEqual(out['doc']['bad'], 'attachment exceeds file size limit')

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_drop_overlay_shows_while_dragging_and_hides_on_leave_or_drop(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'dropDepth') +
                 _fns(js, 'panelDragEnter', 'panelDragLeave', 'panelDragOver', 'panelDrop') + """
function setView(){}
function addFiles(){}
const ev=()=>({preventDefault(){},dataTransfer:{types:['Files'],files:[]}});
const out=[];
panelDragEnter(ev());
out.push(['afterFirstEnter',$('drop-overlay').hidden]);
panelDragEnter(ev());
out.push(['afterNestedEnter',$('drop-overlay').hidden]);
panelDragLeave();
out.push(['afterOneLeave',$('drop-overlay').hidden]);
panelDragLeave();
out.push(['afterSecondLeave',$('drop-overlay').hidden]);
panelDragEnter(ev());
panelDrop(ev());
out.push(['afterDrop',$('drop-overlay').hidden]);
console.log(JSON.stringify(out));
""")
        out = dict(run_node(script))
        self.assertFalse(out['afterFirstEnter'], 'the overlay should show as soon as a drag carries files in')
        self.assertFalse(out['afterNestedEnter'], 'still showing while the drag is over a child element')
        self.assertFalse(out['afterOneLeave'], 'one dragleave (a child) must not hide it -- the drag is still over the panel')
        self.assertTrue(out['afterSecondLeave'], 'the matching second dragleave actually left the panel')
        self.assertTrue(out['afterDrop'], 'dropping hides the overlay')

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_sent_bubble_groups_images_into_a_grid_with_plus_n_then_video_audio_and_file_chips(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node', 'api', 'TL_ICON', 'svg', 'remoteMediaCache') +
                 _fns(js, 'icon', 'sizedIcon', 'sizeLabel', 'attachmentUrl', 'attachmentKind',
                      'bubbleImageGrid', 'enrichRemoteVideo', 'bubbleVideoTile', 'enrichRemoteAudio',
                      'bubbleAudioState', 'bubbleAudioTile', 'bubbleFileChip', 'bubbleAttachments') + """
const timeLabel=s=>{s=Math.max(0,Math.floor(s||0));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`};
let bubbleAudioId=null,bubbleAudioPlayer=null;
function renderNotes(){}
const atts=[
  {id:'i1',name:'cliff-night.jpg',type:'image/jpeg',size:1},
  {id:'i2',name:'keeper-ref.png',type:'image/png',size:1},
  {id:'i3',name:'harbor-ref.jpg',type:'image/jpeg',size:1},
  {id:'i4',name:'window-rain.jpg',type:'image/jpeg',size:1},
  {id:'i5',name:'dawn-grid.png',type:'image/png',size:1},
  {id:'v1',name:'waves.mp4',type:'video/mp4',size:1},
  {id:'a1',name:'storm-theme.wav',type:'audio/wav',size:1},
  {id:'f1',name:'treatment.pdf',type:'application/pdf',size:2100000}
];
const bubble=mkEl('div');
bubbleAttachments(bubble,atts);
const grid=bubble.children.find(c=>classes(c).includes('igrid'));
console.log(JSON.stringify({
  order:bubble.children.map(c=>classes(c)[0]),
  gridClass:classes(grid),
  tileCount:grid.children.length,
  plusN:grid.children[3].querySelectorAll('more')[0].textContent,
  videoDur:classes(bubble.children.find(c=>classes(c).includes('bubble-video'))),
  audioChip:classes(bubble.children.find(c=>classes(c).includes('aud'))),
  fileChipKind:bubble.children.find(c=>c.tag==='a').querySelectorAll('doc-mini')[0].textContent,
  fileChipName:text(bubble.children.find(c=>c.tag==='a')).includes('treatment.pdf'),
}));
""")
        out = run_node(script)
        # images, then the video tile, then the audio chip, then the file chip.
        self.assertEqual(out['order'], ['igrid', 'tile', 'aud', 'file-chip'])
        self.assertEqual(out['gridClass'], ['igrid', 'n4'])
        self.assertEqual(out['tileCount'], 4, 'only 4 tiles shown for 5 images, the 5th folds into "+1"')
        self.assertEqual(out['plusN'], '+1')
        self.assertIn('bubble-video', out['videoDur'])
        self.assertIn('aud', out['audioChip'])
        self.assertEqual(out['fileChipKind'], 'PDF')
        self.assertTrue(out['fileChipName'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_lightbox_opens_on_an_item_steps_next_and_wraps_and_closes(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node', 'api', 'lightboxItems') +
                 _fns(js, 'attachmentUrl', 'attachmentKind', 'renderLightbox', 'lightboxStep',
                      'lightboxKeydown', 'openLightbox', 'closeLightbox') + """
const items=[{id:'i1',name:'a.jpg',type:'image/jpeg'},{id:'i2',name:'b.mp4',type:'video/mp4'},
  {id:'i3',name:'c.jpg',type:'image/jpeg'}];
openLightbox(items,1);
const afterOpen={hidden:$('lightbox').hidden,name:$('lb-name').textContent,count:$('lb-count').textContent,
  stageTag:$('lb-stage').children[0].tag,prevHidden:$('lb-prev').hidden,nextHidden:$('lb-next').hidden};
lightboxStep(1);
const afterNext={name:$('lb-name').textContent,stageTag:$('lb-stage').children[0].tag};
lightboxStep(1);
const afterWrap={name:$('lb-name').textContent};
closeLightbox();
const afterClose={hidden:$('lightbox').hidden,stageChildren:$('lb-stage').children.length};
console.log(JSON.stringify({afterOpen,afterNext,afterWrap,afterClose}));
""")
        out = run_node(script)
        self.assertEqual(out['afterOpen'], {'hidden': False, 'name': 'b.mp4', 'count': '2 / 3',
                                            'stageTag': 'video', 'prevHidden': False, 'nextHidden': False})
        self.assertEqual(out['afterNext'], {'name': 'c.jpg', 'stageTag': 'img'})
        self.assertEqual(out['afterWrap']['name'], 'a.jpg', 'next from the last item wraps to the first')
        self.assertEqual(out['afterClose'], {'hidden': True, 'stageChildren': 0})

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_bubble_attachments_is_a_no_op_for_a_text_only_note(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node') +
                 _fns(js, 'attachmentKind', 'bubbleAttachments') + """
const bubbleA=mkEl('div'),bubbleB=mkEl('div');
bubbleAttachments(bubbleA,undefined);
bubbleAttachments(bubbleB,[]);
console.log(JSON.stringify({a:bubbleA.children.length,b:bubbleB.children.length}));
""")
        out = run_node(script)
        self.assertEqual(out, {'a': 0, 'b': 0})


    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_lightbox_swipe_steps_sideways_closes_downward_and_ignores_taps(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node', 'api', 'lightboxItems') +
                 _fns(js, 'attachmentUrl', 'attachmentKind', 'renderLightbox', 'lightboxStep',
                      'lightboxKeydown', 'lightboxSwipe', 'openLightbox', 'closeLightbox') + """
const items=[{id:'i1',name:'a.jpg',type:'image/jpeg'},{id:'i2',name:'b.jpg',type:'image/jpeg'},
  {id:'i3',name:'c.jpg',type:'image/jpeg'}];
openLightbox(items,0);
lightboxSwipe(-120,10);
const left=$('lb-name').textContent;
lightboxSwipe(120,-5);
const right=$('lb-name').textContent;
lightboxSwipe(8,4);
const tap={name:$('lb-name').textContent,hidden:$('lightbox').hidden};
lightboxSwipe(10,140);
console.log(JSON.stringify({left,right,tap,closed:$('lightbox').hidden}));
""")
        out = run_node(script)
        self.assertEqual(out['left'], 'b.jpg', 'swiping left shows the next item')
        self.assertEqual(out['right'], 'a.jpg', 'swiping right shows the previous item')
        self.assertEqual(out['tap'], {'name': 'a.jpg', 'hidden': False})
        self.assertTrue(out['closed'], 'swiping down closes it')

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_bubble_audio_chip_keeps_its_progress_and_elapsed_time_across_a_rerender(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _consts(js, 'node', 'api') +
                 _fns(js, 'icon', 'sizedIcon', 'attachmentUrl', 'bubbleAudioState', 'bubbleAudioTile') + """
const timeLabel=s=>{s=Math.max(0,Math.floor(s||0));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`};
const remoteMediaCache=new Map([['a1',{duration:192}],['a2',{duration:228}]]);
const enrichRemoteAudio=()=>{};
const bubbleAudioPlayer={duration:192,currentTime:48};
let bubbleAudioId='a1';
const playing=bubbleAudioTile({id:'a1',name:'storm-theme.wav',type:'audio/wav'});
const idle=bubbleAudioTile({id:'a2',name:'harbor-song.mp3',type:'audio/mpeg'});
const fill=n=>n.querySelector('.bar-wave').children[0].style.width;
const times=n=>n.children.find(c=>c.className==='times').textContent;
const label=n=>n.children[0].attrs['aria-label'];
console.log(JSON.stringify({playing:[fill(playing),times(playing),label(playing)],
  idle:[fill(idle),times(idle),label(idle)]}));
""")
        out = run_node(script)
        self.assertEqual(out['playing'], ['25%', '0:48 / 3:12', 'Pause storm-theme.wav'])
        self.assertEqual(out['idle'], ['0%', '3:48', 'Play harbor-song.mp3'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_removing_or_sending_tray_items_frees_their_previews_and_stops_playback(self):
        js = (PKG / 'director.js').read_text()
        script = (self.DOM_STUB + _fns(js, 'releaseFileRecord', 'removeFileRecord', 'clearFiles') + """
const revoked=[],aborted=[];
const URL={revokeObjectURL:u=>revoked.push(u)};
let paused=0;
const trayPlayer={pause(){paused++}};
let trayPlayingId=2;
let renders=0;
const renderFiles=()=>renders++;
const xhr={abort(){aborted.push('img')}};
const state={files:[
  {localId:1,url:'blob:img',audioUrl:null,xhr},
  {localId:2,url:null,audioUrl:'blob:song',xhr:null},
  {localId:3,url:null,audioUrl:null,xhr:null}]};
removeFileRecord(state.files[0]);
const afterRemove={left:state.files.map(r=>r.localId),revoked:[...revoked],aborted};
clearFiles();
console.log(JSON.stringify({afterRemove,revoked,paused,trayPlayingId,files:state.files.length,renders}));
""")
        out = run_node(script)
        self.assertEqual(out['afterRemove'], {'left': [2, 3], 'revoked': ['blob:img'], 'aborted': ['img']})
        self.assertEqual(out['revoked'], ['blob:img', 'blob:song'])
        self.assertEqual((out['paused'], out['trayPlayingId']), (1, None))
        self.assertEqual((out['files'], out['renders']), (0, 2))


class Docs(unittest.TestCase):
    """docs/preproduction.md must name every route preprod_api registers,
    the library-only New-video routes, and every bible/ file -- so a route
    added later without updating the doc fails this test (R42)."""

    def test_every_preprod_route_and_bible_file_is_documented(self):
        from videobuilder import video_api
        doc = (Path(__file__).resolve().parents[1] / 'docs' / 'preproduction.md').read_text()
        routes = set()
        for pattern, handler in video_api.GET_ROUTES + video_api.POST_ROUTES:
            if getattr(handler, '__module__', '') != 'videobuilder.preprod_api':
                continue
            routes |= {pattern} if isinstance(pattern, str) else set(pattern)
        self.assertTrue(routes, "no route resolved to preprod_api -- the test itself needs updating")
        library_routes = {'/api/videos/new', '/api/videos/staging', '/api/videos/mode', '/api/phase'}
        for route in routes | library_routes:
            self.assertIn(route, doc, f'{route} is not documented in docs/preproduction.md')
        for name in ('bible/phase.json', 'bible/script.fountain', 'bible/scenes.json',
                    'bible/options/<id>.json'):
            self.assertIn(name, doc)


if __name__ == '__main__':
    unittest.main()
