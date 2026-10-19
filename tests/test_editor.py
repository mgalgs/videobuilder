"""The editor's HTTP API, on a temp project in a git repo."""
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from videobuilder.editor import Editor
from tests.fixtures import API
from tests.test_project import TempProject


class Command(unittest.TestCase):
    def test_a_missing_project_dir(self):
        from videobuilder.cli import main
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project'])
        self.assertIn('not a directory', str(e.exception))

    def test_account_daily_caps_are_refused_outside_library_mode(self):
        from videobuilder.cli import main
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project', '--account-daily-note-cap', '5'])
        self.assertIn('--account-daily-note-cap', str(e.exception))
        self.assertIn('--library mode', str(e.exception))
        with self.assertRaises(SystemExit) as e:
            main(['editor', '/nonexistent/project', '--account-daily-cost-cap-usd', '2.5'])
        self.assertIn('--account-daily-cost-cap-usd', str(e.exception))

    def test_account_daily_caps_must_be_positive(self):
        from videobuilder.cli import main
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-note-cap', '0'])
            self.assertIn('account_daily_note_cap', str(e.exception))
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-cost-cap-usd', '-1'])
            self.assertIn('account_daily_cost_cap_usd', str(e.exception))

    def test_account_daily_cost_cap_rejects_nan_and_infinity(self):
        from videobuilder.cli import main
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-cost-cap-usd', 'nan'])
            self.assertIn('account_daily_cost_cap_usd', str(e.exception))
            with self.assertRaises(SystemExit) as e:
                main(['editor', '--library', d, '--account-daily-cost-cap-usd', 'inf'])
            self.assertIn('account_daily_cost_cap_usd', str(e.exception))


class AccountCapConfigKeys(TempProject):
    def _editor(self, state_dir, **kw):
        editor = Editor(self.root, state_dir=state_dir, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def test_unset_by_default(self):
        editor = self._editor('state-defaults')
        self.assertIsNone(editor.account_daily_note_cap)
        self.assertIsNone(editor.account_daily_cost_cap_usd)

    def test_configured_in_videobuilder_toml(self):
        (self.root / 'videobuilder.toml').write_text(
            '[editor]\n'
            'account_daily_note_cap = 3\n'
            'account_daily_cost_cap_usd = 1.5\n')
        editor = self._editor('state-configured')
        self.assertEqual(editor.account_daily_note_cap, 3)
        self.assertEqual(editor.account_daily_cost_cap_usd, 1.5)

    def test_explicit_kwarg_overrides_the_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\naccount_daily_note_cap = 3\n')
        editor = self._editor('state-override', account_daily_note_cap=9)
        self.assertEqual(editor.account_daily_note_cap, 9)

    def test_rejects_a_non_positive_cap(self):
        with self.assertRaisesRegex(ValueError, 'account_daily_note_cap'):
            self._editor('state-bad-note-cap', account_daily_note_cap=0)
        with self.assertRaisesRegex(ValueError, 'account_daily_cost_cap_usd'):
            self._editor('state-bad-cost-cap', account_daily_cost_cap_usd=-1)


class CompendiumForBuilderConfigKey(TempProject):
    def _editor(self, state_dir, **kw):
        editor = Editor(self.root, state_dir=state_dir, unsandboxed_previews=True, auto_land=False, **kw)
        self.addCleanup(editor.pool.close)
        self.addCleanup(editor.renders.close)
        return editor

    def test_defaults_to_true(self):
        self.assertIs(self._editor('state-defaults').compendium_for_builder, True)

    def test_configured_in_videobuilder_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\ncompendium_for_builder = false\n')
        self.assertIs(self._editor('state-configured').compendium_for_builder, False)

    def test_explicit_kwarg_overrides_the_toml(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\ncompendium_for_builder = false\n')
        editor = self._editor('state-override', compendium_for_builder=True)
        self.assertIs(editor.compendium_for_builder, True)

    def test_a_non_bool_value_is_a_clear_config_error(self):
        (self.root / 'videobuilder.toml').write_text('[editor]\ncompendium_for_builder = "yes"\n')
        with self.assertRaisesRegex(ValueError, 'compendium_for_builder'):
            self._editor('state-bad')

    def test_votes_for_the_builder_come_from_this_editors_own_store_in_single_project_mode(self):
        editor = self._editor('state-votes')
        editor.compendium_votes.record('owner', 'a', 'up', None)
        editor.compendium_votes.record('owner', 'b', 'down', None)
        editor.compendium_votes.record('owner', 'c', None, None)  # reset: never surfaced
        self.assertEqual(editor._compendium_votes_for_builder(), {'a': 'up', 'b': 'down'})

    def test_votes_for_the_builder_come_from_the_library_store_once_library_hosted(self):
        editor = self._editor('state-votes-library')
        editor.compendium_votes.record('owner', 'a', 'up', None)  # this project's own store: ignored once hosted

        class FakeVotes:
            def current(self):
                return {'z': {'vote': 'down', 'reason': None}}

        class FakeLibrary:
            compendium_votes = FakeVotes()
        editor.library = FakeLibrary()
        self.assertEqual(editor._compendium_votes_for_builder(), {'z': 'down'})

    def test_a_stale_vote_is_left_out_of_the_builders_lists(self):
        """A vote cast against a fingerprint the entry no longer has doesn't
        count: `current()` reports it with `vote: None` (see
        CompendiumVotes._view), which this method's own "up"/"down" filter
        already excludes."""
        editor = self._editor('state-votes-stale')
        with mock.patch('videobuilder.compendium.fingerprint', return_value='oldoldoldold'):
            editor.compendium_votes.record('owner', 'a', 'up', None)
        with mock.patch('videobuilder.compendium.fingerprint', return_value='newnewnewnew'):
            self.assertEqual(editor._compendium_votes_for_builder(), {})

    def test_a_legacy_vote_with_no_fingerprint_still_counts_for_the_builder(self):
        editor = self._editor('state-votes-legacy')
        path = editor.compendium_votes.path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps({'at': '2026-01-01T00:00:00Z', 'by': 'owner', 'id': 'a',
                                 'vote': 'up', 'reason': None, 'version': '0.1.0'}) + '\n')
        self.assertEqual(editor._compendium_votes_for_builder(), {'a': 'up'})


PKG = Path(__file__).resolve().parents[1] / 'videobuilder'


class DirectorPageRoutes(API):
    def test_director_source_line_length(self):
        for name in ('director.js', 'director.css'):
            path = PKG / name
            long_lines = [number for number, line in enumerate(path.read_text().splitlines(), 1)
                          if len(line) > 120]
            self.assertEqual(long_lines, [], f'{path}: lines over 120 characters')

    def test_director_assets_and_api_contract(self):
        import re
        for path, content_type, marker in (
            ('/', 'text/html', b'id="player"'),
            ('/tuning.html', 'text/html', b'id="tl"'),
            ('/director.js', 'text/javascript', b"json('versions'"),
            ('/director.css', 'text/css', b'.panel')):
            with urllib.request.urlopen(self.base + path, timeout=20) as response:
                self.assertEqual(response.headers.get_content_type(), content_type)
                self.assertIn(marker, response.read())
        js = (PKG / 'director.js').read_text()
        tuning = (PKG / 'tuning.html').read_text()
        paths = set(re.findall(r"(?:api|json|postJSON|getJSON)\('([a-z][a-z/-]*)'", js+tuning))
        expected = {'project','name','info','frame','video','notes','versions','versions/restore',
                    'attachments','video/retry','roll','copy','undo','draft','draft/info','draft/frame',
                    'draft/accept','draft/drop','upgrade','access','music/sources','music/tracks','music/attach',
                    'videos/first-note','sources','pictures','pictures/gpu',
                    'clip','timeline','timeline/thumb','timeline/footage'}
        # Dynamic attachment, draft and source actions have their own router patterns.
        self.assertTrue(paths - {'attachments/', 'draft/', 'sources/', 'pictures/'} <= expected, paths - expected)
        # The route literals live wherever make_handler's pieces do now, not all in editor.py.
        router = ''.join((PKG / name).read_text() for name in
                         ('editor.py', 'handler_library.py', 'video_api.py'))
        for path in paths - {'attachments/', 'draft/', 'sources/', 'pictures/'}:
            self.assertIn("'/api/" + path + "'", router, path)
        self.assertIn("api('attachments/'", js)
        self.assertIn("api('video'", js)
        self.assertIn("api('sources/'", js)
        self.assertIn("json('sources'", js)

    def test_a_video_without_a_timeline_file_has_no_timeline(self):
        from tests.test_project import git
        git(self.root, 'branch', '-M', 'main')
        t = self.get('/api/timeline?video=promo/film')
        self.assertEqual(t, {'commit': git(self.root, 'rev-parse', 'main').strip(), 'timeline': None})
        code, out = self.post('/api/timeline', {'video': 'promo/film', 'base': t['commit'],
                                                'timeline': {'version': 1, 'clips': [{'id': 'a', 'dir': 'a'}]}})
        self.assertEqual((code, out['error']), (400, 'this video is not a film of clips: it has no timeline.json'))

    def test_signed_out_handling_pins_resume_probe_banner_and_draft_order(self):
        # A session can expire while the director tab sits open: the 401 handler
        # must show the banner, stop polling, keep whatever was typed, and the
        # resume check (on regaining focus) must hit a route that actually
        # exists under /v/<name>/api/ -- 'project', not the top-level-only 'name'.
        import re
        js = (PKG / 'director.js').read_text()
        resume = re.search(r'async function resumeFromSignedOut\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertIn("json('project')", resume)
        self.assertNotIn("json('name')", resume)
        self.assertIn("$('signed-out-banner').hidden=false", js)
        self.assertIn("$('signed-out-banner').hidden=true", js)
        for guard in ("state.video&&!state.signedOut", "document.hidden||state.signedOut",
                      "document.hidden||!state.project||state.signedOut"):
            self.assertIn(guard, js)
        send_pending = re.search(r'async function sendPending\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertLess(send_pending.index("await json('notes'"), send_pending.index('state.pending=[]'),
                         'the pending draft must only be cleared after the send succeeds')
        send_now = re.search(r'async function sendNow\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertLess(send_now.index("await json('notes'"), send_now.index("$('message').value=''"),
                         'the typed note must only be cleared after the send succeeds')

    def test_timeline_wiring(self):
        # A film of clips' timeline in director.js: notes say which clip they are about and the
        # chat shows those, falling back to every note when the server sends no `clip`; each
        # direct edit posts the whole file against the commit it was made on.
        import re
        js = (PKG / 'director.js').read_text()
        for name in ('sendPending', 'sendNow'):
            body = re.search(r'async function ' + name + r'\(\) \{(.*?)\n\}', js, re.S).group(1)
            self.assertIn('...noteScope()', body, name)
        self.assertIn('for(const note of notesInView())', js)
        in_view = re.search(r'function notesInView\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertIn("if(!state.tl||!all.some(n=>'clip' in n))return all;", in_view)
        save = re.search(r'async function saveTimeline\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertIn("json('timeline',null,{video:state.video,timeline:sent,base:t.commit", save)
        self.assertLess(save.index('await ensureName()'), save.index("json('timeline'"))
        # A video without a timeline file shows no timeline and no This clip / Whole video switch.
        render = re.search(r'function renderTimeline\(\) \{(.*?)\n\}', js, re.S).group(1)
        self.assertIn("$('play-scope').hidden=!t;", render)
        html = (PKG / 'editor.html').read_text()
        for marker in ('id="timeline" class="tl-card collapsed" aria-label="Timeline" hidden',
                       'id="play-scope" class="play-scope" role="group" aria-label="What the player plays" hidden'):
            self.assertIn(marker, html)

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_moving_a_clip_keeps_acts_runs_of_clips(self):
        # tlMove, run as it is in director.js: the moved clip joins its new left neighbour's act
        # (else its right one's), and an act left with no clip goes.
        import re
        import subprocess
        js = (PKG / 'director.js').read_text()
        move = ''.join(re.search(r'\nfunction ' + name + r'\(data,.*?\n\}', js, re.S).group(0)
                       for name in ('tlInsert', 'tlMove'))
        cases = [
            ('d', 0, ['d', 'a', 'b', 'c'], [['d', 'a', 'b'], ['c']]),
            ('a', 3, ['b', 'c', 'd', 'a'], [['b'], ['c', 'd', 'a']]),
            ('c', 1, ['a', 'c', 'b', 'd'], [['a', 'c', 'b'], ['d']]),
        ]
        script = move + """
const out=[];
for(const [id,to] of %s){
  const data={clips:['a','b','c','d'].map(id=>({id})),acts:[{title:'One',clips:['a','b']},{title:'Two',clips:['c','d']}]};
  tlMove(data,id,to);
  out.push([data.clips.map(c=>c.id),data.acts.map(a=>a.clips)]);
}
const lone={clips:['a','b','c'].map(id=>({id})),acts:[{title:'One',clips:['a']},{title:'Two',clips:['b','c']}]};
tlMove(lone,'a',2);
out.push([lone.clips.map(c=>c.id),lone.acts.map(a=>a.title+':'+a.clips.join(''))]);
console.log(JSON.stringify(out));
""" % json.dumps([[c[0], c[1]] for c in cases])
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        self.assertEqual(out[:3], [[order, acts] for _, _, order, acts in cases])
        self.assertEqual(out[3], [['b', 'c', 'a'], ['Two:bca']])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_inserting_footage_inside_an_act_keeps_it_a_run_of_clips(self):
        # tlInsert, as tlAddFootage uses it: a footage clip added at a cut inside an act joins
        # that act, at an act boundary the left act, and the result passes the loader.
        import re
        import subprocess
        from videobuilder import timeline_file
        js = (PKG / 'director.js').read_text()
        insert = re.search(r'\nfunction tlInsert\(data,.*?\n\}', js, re.S).group(0)
        script = insert + """
const out=[];
for(const to of [1,2,0,4]){
  const data={version:VERSION,clips:['a','b','c','d'].map(id=>({id,footage:`sources/${id}.mp4`,out:30})),acts:[{title:'One',clips:['a','b']},{title:'Two',clips:['c','d']}]};
  tlInsert(data,{id:'new',footage:'sources/new.mp4',in:0,out:30},to);
  out.push(data);
}
console.log(JSON.stringify(out));
""".replace('VERSION', json.dumps(timeline_file.VERSION))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        for data in out:
            timeline_file.parse(data)
        self.assertEqual([[a['clips'] for a in d['acts']] for d in out], [
            [['a', 'new', 'b'], ['c', 'd']],
            [['a', 'b', 'new'], ['c', 'd']],
            [['new', 'a', 'b'], ['c', 'd']],
            [['a', 'b'], ['c', 'd', 'new']],
        ])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_a_reels_trims_step_a_beat_at_a_time(self):
        # tlGrid, tlStep and tlSnapCut, run as they are in director.js on a footage reel at 128 bpm
        # (14.0625 frames a beat): the grid is beats.BeatGrid's, a beat step puts the cut it moves on
        # the next beat, and "Put it on the beat" moves an off-beat cut onto the nearest one; the cuts
        # after either that were on the beat stay on it.
        import re
        import subprocess
        from videobuilder import timeline_file
        js = (PKG / 'director.js').read_text()
        parts = [re.search(r'\nconst ' + name + r'=.*?\n', js).group(0) for name in ('tlInfo', 'tlFootage', 'tlCutAt')]
        parts += [re.search(r'\nfunction ' + name + r'\(.*?\n\}', js, re.S).group(0)
                  for name in ('tlPlace', 'tlGrid', 'tlStep', 'tlOnBeat', 'tlKeepOnBeat', 'tlSnapCut')]
        data = {'version': 1, 'fps': 30, 'clips': [
            {'id': f'c{k}', 'footage': f'sources/c{k}.mp4', 'in': 0, 'out': 100} for k in range(4)],
            'lanes': [{'items': [{'sound': 'sources/song.wav', 'at': 0, 'offset': 4, 'frames': 400}]}],
            'beats': {'lane': 1, 'item': 1, 'bpm': 128, 'first': 15}}
        data['clips'][0]['out'] = 67
        data['clips'][2]['head'] = 20
        script = '\n'.join(parts) + """
const state={tl:{fps:30,clips:[],data:DATA}};
const toasts=[];
const toast=m=>toasts.push(m);
const tlChange=change=>{change(state.tl.data)};
const g=tlGrid();
const out={frames:[...Array(g.last-g.first+1)].map((_,j)=>g.frame(g.first+j)),
  snap:[0,17,18,30,399].map(g.snap),step:[[25,1],[30,1],[30,-1],[11,-2]].map(([f,n])=>g.step(f,n))};
const cuts=()=>tlPlace().places.slice(1).map(tlCutAt);
out.before=cuts();
tlStep(1,'tail',1,'beat');   // the end of c0 a beat earlier: the cut into c1 to the beat before
out.tail=cuts();
tlStep(2,'head',-1,'beat');  // c2 starts as it did, and ends a beat later
out.head=[cuts(),state.tl.data.clips[2].head];
tlSnapCut(2);
out.snapped=cuts();
console.log(JSON.stringify(out));
""".replace('DATA', json.dumps(data))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        grid = timeline_file.beat_grid(timeline_file.parse(data))
        self.assertEqual(out['frames'], grid.frames())
        self.assertEqual(out['snap'], [grid.snap(f) for f in (0, 17, 18, 30, 399)])
        self.assertEqual(out['step'], [grid.step(25, 1), grid.step(30, 1), grid.step(30, -1), grid.step(11, -2)])
        self.assertEqual(out['before'], [67, 167, 247])
        # Beats on the timeline: 11, 25, 39, 53, 67, 81, ... (the file's first beat, 15, at 15 - 4).
        self.assertEqual(out['tail'], [53, 153, 233])
        self.assertEqual(out['head'], [[53, 153, grid.step(233, 1)], 20 - (grid.step(233, 1) - 233)])
        self.assertEqual(grid.snap(153), 152)
        # The cut after it was on the beat, and stays there: c2 shows a frame more.
        self.assertEqual(out['snapped'], [53, 152, grid.step(233, 1)])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_a_reels_cuts_stay_on_the_beat_through_transitions_and_new_clips(self):
        # tlTransition, tlStep's length step, tlAddFootage and the lane sheet's "Remove", run as they
        # are in director.js on a footage reel at 120 bpm (15 frames a beat) with every cut on the beat:
        # a whip, a longer flash and a new clip leave every cut on it (the clip before each shows more,
        # out to the end of its file), and removing the song's lane takes the beat grid with it.
        import re
        import subprocess
        from videobuilder import timeline_file
        js = (PKG / 'director.js').read_text()
        parts = [re.search(r'\nconst ' + name + r'=.*?\n', js).group(0)
                 for name in ('TL_LEN', 'tlInfo', 'tlFootage', 'tlCutAt')]
        parts.append(re.search(r'\nconst tlNewId=.*?\n\};', js, re.S).group(0))
        parts += [re.search(r'\nfunction ' + name + r'\(.*?\n\}', js, re.S).group(0)
                  for name in ('tlPlace', 'tlGrid', 'tlStep', 'tlOnBeat', 'tlKeepOnBeat', 'tlTransition',
                               'tlAddFootage', 'tlInsert')]
        remove = re.search(r"\n    if\(x==='remove'\) \{.*?\n      return\n    \}", js, re.S).group(0)
        data = {'version': 1, 'fps': 30, 'clips': [
            {'id': f'c{k}', 'footage': f'sources/c{k}.mp4', 'in': 0, 'out': 30} for k in range(4)],
            'lanes': [{'items': [{'sound': 'sources/song.wav', 'at': 0, 'frames': 300}]},
                      {'items': [{'sound': 'sources/vo.wav', 'at': 0, 'frames': 60}]}],
            'beats': {'lane': 1, 'item': 1, 'bpm': 120}}
        script = '\n'.join(parts) + """
const clips=['c0','c1','c2','c3','n'].map(id=>({id,frames:90}));
const state={tl:{fps:30,clips,data:DATA}};
const toast=()=>{},tlCloseSheet=()=>{};
const tlChange=change=>{change(state.tl.data)};
const cuts=()=>tlPlace().places.slice(1).map(tlCutAt);
const out={before:cuts()};
tlTransition(1,'whip');
out.whip=[cuts(),state.tl.data.clips[1].cut];
tlTransition(2,'flash');
tlStep(2,'len',4);
out.flash=[cuts(),state.tl.data.clips[2].cut.frames];
tlAddFootage(2,{name:'n',ext:'mp4',duration:1.5});
out.added=cuts();
out.data=JSON.parse(JSON.stringify(state.tl.data));
const removed=k=>{
  state.tl.data=JSON.parse(JSON.stringify(out.data));
  const t=state.tl,n=k+1;
  (()=>{const x='remove';REMOVE})();
  return state.tl.data;
};
out.removed=[removed(1),removed(0)];
console.log(JSON.stringify(out));
""".replace('DATA', json.dumps(data)).replace('REMOVE', remove)
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        self.assertEqual(out['before'], [30, 60, 90])
        self.assertEqual(out['whip'], [[30, 60, 90], {'transition': 'whip', 'frames': 8, 'direction': 'left'}])
        self.assertEqual(out['flash'], [[30, 60, 90], 10])
        self.assertEqual(out['added'], [30, 60, 105, 135])
        reel = timeline_file.parse(out['data'])
        placements, _ = timeline_file.place(reel, {}, known=True)
        self.assertEqual(timeline_file.offbeat(reel, placements), [])
        # Audio 2 goes and the grid stays on the song; Audio 1 goes and the film is no longer a reel.
        self.assertEqual(out['removed'][0]['beats'], data['beats'])
        self.assertEqual(len(out['removed'][0]['lanes']), 1)
        song_gone = out['removed'][1]
        self.assertNotIn('beats', song_gone)
        timeline_file.parse(song_gone)

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_a_cuts_sound_effect_survives_a_change_of_transition(self):
        # tlTransition as in director.js: a named sound effect stays on the cut through a whip, a hard cut
        # and a dissolve; "auto" stays on a flash, and is dropped (saying so) where it can't go.
        import re
        import subprocess
        from videobuilder import timeline_file
        js = (PKG / 'director.js').read_text()
        parts = [re.search(r'\nconst ' + name + r'=.*?\n', js).group(0)
                 for name in ('TL_LEN', 'tlInfo', 'tlFootage', 'tlCutAt')]
        parts += [re.search(r'\nfunction ' + name + r'\(.*?\n\}', js, re.S).group(0)
                  for name in ('tlPlace', 'tlGrid', 'tlOnBeat', 'tlKeepOnBeat', 'tlTransition')]
        data = {'version': 1, 'fps': 30, 'clips': [
            {'id': 'a', 'footage': 'sources/a.mp4', 'in': 0, 'out': 60},
            {'id': 'b', 'footage': 'sources/b.mp4', 'in': 0, 'out': 60,
             'cut': {'transition': 'dissolve', 'frames': 12, 'sound': 'pro_impact/short'}},
            {'id': 'c', 'footage': 'sources/c.mp4', 'in': 0, 'out': 60,
             'cut': {'transition': 'whip', 'frames': 8, 'sound': {'sfx': 'auto', 'gain_db': -3}}}]}
        script = '\n'.join(parts) + """
const clips=['a','b','c'].map(id=>({id,frames:90}));
const state={tl:{fps:30,clips,data:DATA}};
const said=[],tlChange=(change,what)=>{change(state.tl.data);said.push(what)};
const cut=i=>JSON.parse(JSON.stringify(state.tl.data.clips[i].cut??null));
const out={};
tlTransition(1,'whip');out.whip=cut(1);
tlTransition(1,'cut');out.hard=cut(1);
tlTransition(1,'dissolve');out.dissolve=cut(1);
tlTransition(2,'flash');out.flash=cut(2);
tlTransition(2,'wipe');out.wipe=cut(2);
out.said=said;
out.data=state.tl.data;
console.log(JSON.stringify(out));
""".replace('DATA', json.dumps(data))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        self.assertEqual(out['whip'], {'transition': 'whip', 'frames': 12, 'direction': 'left',
                                       'sound': 'pro_impact/short'})
        self.assertEqual(out['hard'], {'transition': 'cut', 'sound': 'pro_impact/short'})
        self.assertEqual(out['dissolve']['sound'], 'pro_impact/short')
        self.assertEqual(out['flash']['sound'], {'sfx': 'auto', 'gain_db': -3})
        self.assertNotIn('sound', out['wipe'])
        self.assertIn('"auto" sound dropped', out['said'][-1])
        self.assertNotIn('dropped', ' '.join(out['said'][:-1]))
        timeline_file.parse(out['data'])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_a_reels_cuts_stay_on_the_beat_when_a_clip_moves(self):
        # tlMoveTo, run as it is in director.js on a reel at 120 bpm whose first beat is frame 11 and
        # whose first clip runs over the intro (films.md, "Cutting a reel"): moving the last clip to
        # the front leaves both cuts on the beat, by the trims of the clip before each.
        import re
        import subprocess
        from videobuilder import timeline_file
        js = (PKG / 'director.js').read_text()
        parts = [re.search(r'\nconst ' + name + r'=.*?\n', js).group(0) for name in ('tlInfo', 'tlFootage', 'tlCutAt')]
        parts += [re.search(r'\nfunction ' + name + r'\(.*?\n\}', js, re.S).group(0)
                  for name in ('tlPlace', 'tlGrid', 'tlOnBeat', 'tlKeepOnBeat', 'tlInsert', 'tlMove', 'tlMoveTo')]
        data = {'version': 1, 'fps': 30, 'clips': [
            {'id': 'a', 'footage': 'sources/a.mp4', 'in': 0, 'out': 71},
            {'id': 'b', 'footage': 'sources/b.mp4', 'in': 0, 'out': 60},
            {'id': 'c', 'footage': 'sources/c.mp4', 'in': 0, 'out': 60}],
            'lanes': [{'items': [{'sound': 'sources/song.wav', 'at': 0, 'frames': 300}]}],
            'beats': {'lane': 1, 'item': 1, 'bpm': 120, 'first': 11}}
        script = '\n'.join(parts) + """
const clips=['a','b','c'].map(id=>({id,frames:90}));
const state={tl:{fps:30,clips,data:DATA}};
const tlChange=change=>{change(state.tl.data)};
const cuts=()=>tlPlace().places.slice(1).map(tlCutAt);
const out={before:cuts()};
tlMoveTo('c',0);
out.moved=[state.tl.data.clips.map(c=>c.id),cuts()];
out.data=state.tl.data;
console.log(JSON.stringify(out));
""".replace('DATA', json.dumps(data))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        self.assertEqual(out['before'], [71, 131])
        self.assertEqual(out['moved'][0], ['c', 'a', 'b'])
        reel = timeline_file.parse(out['data'])
        placements, _ = timeline_file.place(reel, {}, known=True)
        self.assertEqual(timeline_file.offbeat(reel, placements), [])

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_a_refused_timeline_edit_is_not_left_on_screen(self):
        # saveTimeline and loadTimeline, run as they are in director.js against a server that
        # refuses the POST (or a user who gives no name) while main stays at the same commit: the
        # strip goes back to main's file, so the next edit isn't built on the one that was refused.
        import re
        import subprocess
        js = (PKG / 'director.js').read_text()
        parts = [re.search(r'\n(async )?function ' + name + r'\(.*?\n\}', js, re.S).group(0)
                 for name in ('tlSetStatus', 'loadTimeline', 'tlTake', 'tlChange', 'saveTimeline', 'tlUnsaved')]
        script = '\n'.join(parts) + """
const main={clips:[{id:'a',trim:{after:0}},{id:'b'}]};
const tlClone=x=>JSON.parse(JSON.stringify(x));
let named=true;
const toasts=[];
const state={video:'v',format:''};
const $=()=>null,toast=m=>toasts.push(m),renderTimeline=()=>{},renderScope=()=>{},loadVersions=()=>{};
const ensureName=async()=>named;
const json=async(path,query,body)=>{
  if(body)throw new Error('trim runs past the clip');
  return {timeline:tlClone(main),commit:'c1',fps:30,clips:{a:{state:'done'}}};
};
const setTimeout=()=>0,clearTimeout=()=>{};
(async()=>{
  const out=[];
  for(const name of [true,false]){
    named=name;
    await loadTimeline(true);
    tlChange(d=>{d.clips[0].trim.after=99},'trim');
    await saveTimeline();
    out.push([state.tl.data,state.tl.status,state.tl.dirty]);
  }
  console.log(JSON.stringify(out));
})();
"""
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        main = {'clips': [{'id': 'a', 'trim': {'after': 0}}, {'id': 'b'}]}
        self.assertEqual(json.loads(result.stdout), [[main, 'Not saved', False]] * 2)

    def test_fine_tuning_edit_endpoints(self):
        self.assertIn(b'id="pane-copy"', self.get('/tuning.html'))
        video = 'promo/film'
        self.assertEqual(self.post('/api/roll', {'video': video, 'segment': 'intro', 'until': 6})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['cuts'][1], 90)
        self.assertEqual(self.post('/api/copy', {'video': video, 'segment': 'intro', 'key': 'title', 'value': 'New'})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['segments'][0]['copy']['title'], 'New')
        self.assertEqual(self.post('/api/undo', {'video': video})[0], 200)
        self.assertEqual(self.get('/api/info?video=promo/film')['timeline']['segments'][0]['copy']['title'], 'Hello')


class ServerErrors(API):
    """An unhandled exception must never put its traceback (or any other internal
    detail) in the response a guest sees; the operator still gets it, in the log."""
    LEAK = '/nonexistent/secret-path/traceback-marker'

    def test_unhandled_exception_on_an_api_route_hides_internals(self):
        with mock.patch.object(self.editor, 'info', side_effect=RuntimeError(self.LEAK)), \
             mock.patch('sys.stderr', new_callable=io.StringIO) as err:
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.get('/api/info?video=promo/film')
            with e.exception:
                self.assertEqual(e.exception.code, 500)
                self.assertEqual(e.exception.headers.get_content_type(), 'application/json')
                body = e.exception.read()
            log = err.getvalue()
        self.assertEqual(json.loads(body), {'error': 'internal error'})
        self.assertNotIn(self.LEAK.encode(), body)
        self.assertNotIn(b'Traceback', body)
        self.assertIn(self.LEAK, log)
        self.assertIn('Traceback', log)

    def test_unhandled_exception_on_a_page_route_is_a_plain_html_error(self):
        with mock.patch('videobuilder.video_api._page', side_effect=RuntimeError(self.LEAK)), \
             mock.patch('sys.stderr', new_callable=io.StringIO) as err:
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(self.base + '/', timeout=20)
            with e.exception:
                self.assertEqual(e.exception.code, 500)
                self.assertEqual(e.exception.headers.get_content_type(), 'text/html')
                body = e.exception.read()
            log = err.getvalue()
        self.assertNotIn(self.LEAK.encode(), body)
        self.assertNotIn(b'Traceback', body)
        self.assertIn(self.LEAK, log)
        self.assertIn('Traceback', log)


class _MusicServer:
    """A local http.server answering fixed GETs by path, so route tests never touch
    the network. `routes` maps a path to (bytes, content_type)."""

    def __init__(self, routes):
        self.routes = routes
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hit = outer.routes.get(self.path)
                if hit is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                data, content_type = hit
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *a):
                pass
        self.httpd = HTTPServer(('127.0.0.1', 0), Handler)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Music(API):
    """GET api/music/sources, api/music/tracks and POST api/music/attach."""

    TRACK_MP3 = b'ID3' + b'\x00' * 7 + b'fake mp3 bytes for the test'

    def _configure(self):
        self.server = _MusicServer({'/track.mp3': (self.TRACK_MP3, 'audio/mpeg')})
        self.addCleanup(self.server.close)
        track = {'id': 'calm-1', 'title': 'Calm Piano', 'audio_url': self.server.base + '/track.mp3',
                'tags': ['calm', 'piano'], 'duration': 61}
        self.server.routes['/tracks.json'] = (json.dumps({'tracks': [track]}).encode(), 'application/json')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, 'music.toml')
        path.write_text(f'''
            [[sources]]
            id = "calm"
            name = "Calm Library"
            license = "CC BY-NC 4.0"
            url = "{self.server.base}/tracks.json"
            [sources.fields]
            tracks = "tracks"
            id = "id"
            title = "title"
            audio_url = "audio_url"
            tags = "tags"
            duration = "duration"
        ''')
        self.start(music_sources=str(path))

    def test_no_sources_configured(self):
        self.assertEqual(self.get('/api/music/sources'), [])
        self.assertEqual(self.post('/api/music/attach', {'video': 'promo/film', 'source': 'x', 'track': 'y'})[0], 404)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/api/music/tracks?source=x')
        e.exception.close()
        self.assertEqual(e.exception.code, 404)
        with urllib.request.urlopen(self.base + '/', timeout=20) as response:
            html = response.read()
        self.assertIn(b'id="music-button"', html)
        self.assertIn(b'hidden', html.split(b'id="music-button"', 1)[1].split(b'>', 1)[0])
        js = (PKG / 'director.js').read_text()
        self.assertIn("$('music-button').hidden=!state.musicSources.length", js)

    def test_sources_and_tracks_listing(self):
        self._configure()
        self.assertEqual(self.get('/api/music/sources'),
                         [{'id': 'calm', 'name': 'Calm Library', 'license': 'CC BY-NC 4.0'}])
        data = self.get('/api/music/tracks?source=calm')
        self.assertEqual(data['source'], {'id': 'calm', 'name': 'Calm Library', 'license': 'CC BY-NC 4.0'})
        self.assertEqual(data['tracks'], [{'id': 'calm-1', 'title': 'Calm Piano', 'tags': ['calm', 'piano'],
                                           'duration': 61.0, 'audio_url': self.server.base + '/track.mp3'}])
        self.assertEqual(self._status('/api/music/tracks?source=nope'), 404)

    def _status(self, path):
        try:
            self.get(path)
            return 200
        except urllib.error.HTTPError as e:
            with e:
                return e.code

    def test_attach_stores_the_right_name_type_and_upload_shaped_record(self):
        self._configure()
        code, record = self.post('/api/music/attach', {'video': 'promo/film', 'source': 'calm', 'track': 'calm-1'})
        self.assertEqual(code, 201, record)
        self.assertEqual((record['name'], record['type']), ('Calm_Piano.mp3', 'audio/mpeg'))
        self.assertEqual(record['size'], len(self.TRACK_MP3))
        self.assertEqual(set(record), {'id', 'name', 'type', 'size'})
        stored = self.get('/api/attachments/' + record['id'])
        self.assertEqual(stored, self.TRACK_MP3)

    def test_attach_unknown_source_or_track_is_404(self):
        self._configure()
        self.assertEqual(self.post('/api/music/attach',
                                   {'video': 'promo/film', 'source': 'nope', 'track': 'calm-1'})[0], 404)
        self.assertEqual(self.post('/api/music/attach',
                                   {'video': 'promo/film', 'source': 'calm', 'track': 'nope'})[0], 404)

    def test_attach_never_fetches_a_url_from_the_request_body(self):
        self._configure()
        # A non-routable test address: if the server fetched this instead of the
        # track's own cached audio_url, the request would hang or fail.
        code, record = self.post('/api/music/attach', {
            'video': 'promo/film', 'source': 'calm', 'track': 'calm-1',
            'url': 'http://192.0.2.1/evil.mp3', 'audio_url': 'http://192.0.2.1/evil.mp3',
        })
        self.assertEqual(code, 201, record)
        self.assertEqual(self.get('/api/attachments/' + record['id']), self.TRACK_MP3)

    def test_attach_over_size_limit_is_refused(self):
        self._configure()
        self.editor.attachments.max_file = len(self.TRACK_MP3) - 1
        code, result = self.post('/api/music/attach', {'video': 'promo/film', 'source': 'calm', 'track': 'calm-1'})
        self.assertEqual(code, 413, result)


if __name__ == '__main__':
    unittest.main()
