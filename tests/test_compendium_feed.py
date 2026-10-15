"""The compendium vote feed: routes, the access matrix, the vote store,
request validation and index.json's loop windows, following
tests/test_capabilities_routes.py's and tests/test_compendium.py's
fixtures."""
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from videobuilder import compendium, compendium_feed

from tests import fixtures

COMPONENT_ID = next(c.id for c in compendium.CATALOG if c.kind != 'transition')
TRANSITION_ID = next(c.id for c in compendium.CATALOG if c.kind == 'transition')
RECIPE_ID = compendium.RECIPES[0].id
FMT = compendium.get(COMPONENT_ID).formats[0]


def _status(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.read(), e.headers


def _build(out_dir, ids):
    """`compendium.build(out_dir, only=ids)` with ffmpeg mocked out, the way
    tests/test_compendium.py's Build tests do."""
    def fake_render(film, out, fmt, **kw):
        Path(out).write_bytes(b'0123456789')
    with mock.patch('videobuilder.render.render', fake_render):
        compendium.build(out_dir, only=set(ids))


class IndexJSON(unittest.TestCase):
    def test_build_writes_a_loop_window_for_every_transition(self):
        transitions = {c.id for c in compendium.CATALOG if c.kind == 'transition'}
        with tempfile.TemporaryDirectory() as d:
            _build(d, transitions)
            with open(Path(d) / 'index.json', encoding='utf-8') as fh:
                index = json.load(fh)
        total_new = total_naive = 0.0
        for tid in transitions:
            with self.subTest(id=tid):
                c = compendium.get(tid)
                film = compendium.component_film(c)
                grid = film.timeline.grid
                lo_f, hi_f = film.timeline.span('to')
                move_start = grid.seconds(lo_f)
                clip_duration = grid.seconds(film.frames)
                # The window the old (reviewer-flagged) code used -- the
                # whole overlap, padded -- which a fixed window must never
                # exceed, even though for a transition whose move genuinely
                # takes the whole overlap (a continuous slide, say) the fix
                # won't shrink it.
                pad_f = round(0.5 * grid.fps)
                naive_lo_f, naive_hi_f = max(0, lo_f - pad_f), min(film.frames, hi_f + pad_f)
                naive_duration = grid.seconds(naive_hi_f) - grid.seconds(naive_lo_f)
                entries = [e for e in index['clips'] if e['id'] == tid]
                self.assertEqual({e['format'] for e in entries}, set(c.formats))
                for e in entries:
                    self.assertEqual(e['kind'], 'transition')
                    lo, hi = e['loop']
                    # Inside the clip...
                    self.assertGreaterEqual(lo, 0)
                    self.assertLessEqual(hi, clip_duration)
                    self.assertLess(lo, hi)
                    # ...covering the move (padded a bit before it starts)...
                    self.assertLessEqual(lo, move_start)
                    self.assertGreater(hi, move_start)
                    # ...and never longer than the old, whole-overlap window.
                    self.assertLessEqual(hi - lo, naive_duration + 1e-9)
                total_new += entries[0]['loop'][1] - entries[0]['loop'][0]
                total_naive += naive_duration
        # For most of these transitions the move is much shorter than the
        # overlap (the bug this guards against), so the fixed windows are,
        # in total, far shorter than the naive whole-overlap ones.
        self.assertLess(total_new, total_naive * 0.6)

    def test_non_transition_clips_have_no_loop_window(self):
        with tempfile.TemporaryDirectory() as d:
            _build(d, {COMPONENT_ID, RECIPE_ID})
            with open(Path(d) / 'index.json', encoding='utf-8') as fh:
                index = json.load(fh)
        for e in index['clips']:
            with self.subTest(id=e['id'], format=e['format']):
                self.assertIsNone(e['loop'])
        self.assertEqual({e['id'] for e in index['clips']}, {COMPONENT_ID, RECIPE_ID})
        self.assertTrue(any(e['kind'] == 'recipe' for e in index['clips'] if e['id'] == RECIPE_ID))


class VoteStore(unittest.TestCase):
    def test_last_vote_per_user_and_id_wins_but_history_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / 'compendium-votes.jsonl')
            store = compendium_feed.CompendiumVotes(path)
            store.record('alice', COMPONENT_ID, 'up', None)
            store.record('alice', COMPONENT_ID, 'down', 'too busy')
            store.record('bob', COMPONENT_ID, 'up', None)
            self.assertEqual(store.for_user('alice'), {COMPONENT_ID: {'vote': 'down', 'reason': 'too busy'}})
            self.assertEqual(store.for_user('bob'), {COMPONENT_ID: {'vote': 'up', 'reason': None}})
            lines = [l for l in Path(path).read_text(encoding='utf-8').splitlines() if l.strip()]
            self.assertEqual(len(lines), 3)  # nothing rewritten or compacted
            for line in lines:
                event = json.loads(line)
                self.assertEqual(set(event), {'at', 'by', 'id', 'vote', 'reason', 'version'})

    def test_votes_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / 'compendium-votes.jsonl')
            compendium_feed.CompendiumVotes(path).record('alice', COMPONENT_ID, 'up', None)
            reopened = compendium_feed.CompendiumVotes(path)
            self.assertEqual(reopened.for_user('alice'), {COMPONENT_ID: {'vote': 'up', 'reason': None}})

    def test_null_vote_clears_it(self):
        with tempfile.TemporaryDirectory() as d:
            store = compendium_feed.CompendiumVotes(str(Path(d) / 'v.jsonl'))
            store.record('alice', COMPONENT_ID, 'up', None)
            store.record('alice', COMPONENT_ID, None, None)
            self.assertEqual(store.for_user('alice'), {COMPONENT_ID: {'vote': None, 'reason': None}})

    def test_no_file_yet_is_no_votes(self):
        with tempfile.TemporaryDirectory() as d:
            store = compendium_feed.CompendiumVotes(str(Path(d) / 'missing.jsonl'))
            self.assertEqual(store.for_user('alice'), {})


class Validation(unittest.TestCase):
    def test_unknown_id_is_rejected(self):
        with self.assertRaises(ValueError):
            compendium_feed.validate_vote({'id': 'no-such-id', 'vote': 'up'})

    def test_bad_vote_value_is_rejected(self):
        with self.assertRaises(ValueError):
            compendium_feed.validate_vote({'id': COMPONENT_ID, 'vote': 'maybe'})

    def test_reason_over_300_characters_is_rejected(self):
        with self.assertRaises(ValueError):
            compendium_feed.validate_vote({'id': COMPONENT_ID, 'vote': 'down', 'reason': 'x' * 301})

    def test_reason_must_be_a_string(self):
        with self.assertRaises(ValueError):
            compendium_feed.validate_vote({'id': COMPONENT_ID, 'vote': 'down', 'reason': 123})

    def test_null_vote_is_allowed_to_clear(self):
        self.assertEqual(compendium_feed.validate_vote({'id': COMPONENT_ID, 'vote': None}),
                         (COMPONENT_ID, None, None))

    def test_a_recipe_id_is_accepted_too(self):
        self.assertEqual(compendium_feed.validate_vote({'id': RECIPE_ID, 'vote': 'up'}), (RECIPE_ID, 'up', None))


class SingleProjectRoutes(fixtures.API):
    """No accounts in single-project mode: the feed is always reachable."""

    def test_page_and_api_render_with_no_compendium_dir(self):
        code, page, _ = _status(self.base, '/compendium')
        self.assertEqual(code, 200)
        self.assertIn(b'Compendium', page)
        data = self.get('/api/compendium')
        self.assertTrue(data['items'])
        self.assertEqual(data['votes'], {})
        for item in data['items']:
            self.assertEqual(item['formats'], [])
            self.assertIsNone(item['loop'])

    def test_vote_round_trips_with_no_accounts(self):
        code, vote = self.post('/api/compendium/vote', {'id': COMPONENT_ID, 'vote': 'up'})
        self.assertEqual(code, 200, vote)
        self.assertEqual(self.get('/api/compendium')['votes'][COMPONENT_ID], {'vote': 'up', 'reason': None})
        code, _ = self.post('/api/compendium/vote', {'id': COMPONENT_ID, 'vote': 'down', 'reason': 'meh'})
        self.assertEqual(code, 200)
        self.assertEqual(self.get('/api/compendium')['votes'][COMPONENT_ID], {'vote': 'down', 'reason': 'meh'})

    def test_malformed_vote_is_400_never_500(self):
        for body in ({'id': 'no-such-id', 'vote': 'up'}, {'id': COMPONENT_ID, 'vote': 'maybe'},
                     {'vote': 'up'}, {'id': COMPONENT_ID, 'vote': 'down', 'reason': 'x' * 301}):
            with self.subTest(body=body):
                code, err = self.post('/api/compendium/vote', body)
                self.assertEqual(code, 400, err)

    def test_unknown_and_traversal_shaped_clip_ids_404(self):
        for bad in ('not-a-real-id-16x9', '..', '%2e%2e%2fetc%2fpasswd'):
            with self.subTest(bad=bad):
                code, _, _ = _status(self.base, f'/compendium/{bad}.mp4')
                self.assertEqual(code, 404)


class SingleProjectWithClip(fixtures.API):
    """Single-project mode with a --compendium-dir configured and clips built."""

    def setUp(self):
        super(fixtures.API, self).setUp()
        self.comp_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.comp_tmp.cleanup)
        _build(self.comp_tmp.name, {COMPONENT_ID, TRANSITION_ID, RECIPE_ID})
        self.start(compendium_dir=self.comp_tmp.name)

    def test_api_reports_built_formats_and_the_transition_loop(self):
        by_id = {i['id']: i for i in self.get('/api/compendium')['items']}
        self.assertTrue(by_id[COMPONENT_ID]['formats'])
        self.assertIsNone(by_id[COMPONENT_ID]['loop'])
        self.assertTrue(by_id[TRANSITION_ID]['formats'])
        self.assertIsNotNone(by_id[TRANSITION_ID]['loop'])
        self.assertTrue(by_id[RECIPE_ID]['is_recipe'])
        self.assertTrue(by_id[RECIPE_ID]['formats'])

    def test_page_serves_200(self):
        code, page, _ = _status(self.base, '/compendium')
        self.assertEqual(code, 200)

    def test_poster_served(self):
        code, body, headers = _status(self.base, f'/compendium/{COMPONENT_ID}-{FMT}.jpg')
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), 'image/jpeg')

    def test_range_request_on_a_clip_gets_206(self):
        code, body, headers = _status(self.base, f'/compendium/{COMPONENT_ID}-{FMT}.mp4', {'Range': 'bytes=2-5'})
        self.assertEqual((code, body), (206, b'2345'))
        self.assertEqual(headers['Content-Range'], 'bytes 2-5/10')

    def test_unknown_id_still_404s_with_a_dir_configured(self):
        code, _, _ = _status(self.base, '/compendium/not-a-real-id-16x9.mp4')
        self.assertEqual(code, 404)


class AuthCompendium(fixtures.Auth):
    """Library mode with accounts: admin only, everywhere."""

    def library_kwargs(self):
        self.comp_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.comp_tmp.cleanup)
        _build(self.comp_tmp.name, {COMPONENT_ID, TRANSITION_ID})
        return {**super().library_kwargs(), 'compendium_dir': self.comp_tmp.name}

    def test_anonymous_gets_signin_page_and_401_everywhere_else(self):
        code, page, _ = self.request_full('/compendium')
        self.assertEqual(code, 200)
        self.assertIn(b'Sign in', page)
        code, body, _ = self.request_full(f'/compendium/{COMPONENT_ID}-{FMT}.mp4')
        self.assertEqual(code, 401)
        code, body = self.request('/api/compendium')
        self.assertEqual(code, 401)
        code, body = self.request('/api/compendium/vote', {'id': COMPONENT_ID, 'vote': 'up'})
        self.assertEqual(code, 401)

    def test_signed_in_non_admin_gets_403_everywhere(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        headers = {'Cookie': dana}
        self.assertEqual(self.request('/compendium', headers=headers)[0], 403)
        self.assertEqual(self.request(f'/compendium/{COMPONENT_ID}-{FMT}.mp4', headers=headers)[0], 403)
        self.assertEqual(self.request('/api/compendium', headers=headers)[0], 403)
        code, _ = self.request('/api/compendium/vote', {'id': COMPONENT_ID, 'vote': 'up'},
                               headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 403)

    def test_admin_can_browse_and_vote_and_it_persists(self):
        admin = self.admin_login()
        headers = {'Cookie': admin}
        code, page = self.request('/compendium', headers=headers)
        self.assertEqual(code, 200)
        self.assertIn(b'Compendium', page)
        code, data = self.request('/api/compendium', headers=headers)
        self.assertEqual(code, 200)
        self.assertTrue(data['items'])
        code, vote = self.request('/api/compendium/vote', {'id': COMPONENT_ID, 'vote': 'down', 'reason': 'meh'},
                                  headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 200, vote)
        code, data2 = self.request('/api/compendium', headers=headers)
        self.assertEqual(data2['votes'][COMPONENT_ID], {'vote': 'down', 'reason': 'meh'})
        code, clip, _ = self.request_full(f'/compendium/{COMPONENT_ID}-{FMT}.mp4', headers=headers)
        self.assertEqual(code, 200)

    def test_malformed_vote_body_is_400_not_500(self):
        admin = self.admin_login()
        code, err = self.request('/api/compendium/vote', {'id': 'nonsense'},
                                 headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 400, err)

    def test_compendium_link_shown_to_admin_only(self):
        admin = self.admin_login()
        code, page = self.request('/', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertIn(b'href="/compendium"', page)
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, page2 = self.request('/', headers={'Cookie': dana})
        self.assertEqual(code, 200)
        self.assertNotIn(b'href="/compendium"', page2)


if __name__ == '__main__':
    unittest.main()
