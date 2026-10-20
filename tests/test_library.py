"""Library routing and smart HTTP with a real git client."""
import base64
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from videobuilder.editor import make_handler
from videobuilder.library import Library, valid_name
from tests.test_project import FILM
from tests.fixtures import AccountMixin, Auth, KeyMixin, LibraryFixture


class HostedGit(LibraryFixture, unittest.TestCase):
    def test_git_roundtrip_and_routes(self):
        self.assertEqual(self.request('/git/acme/launch.git/info/refs?service=git-upload-pack')[0], 404)
        work = self.seed()
        self.assertTrue(self.library.has_main('acme/launch'))
        self.assertIn(b'acme/launch', self.request('/')[1])
        self.assertIn(self.url('acme/launch').encode(), self.request('/')[1])
        self.assertEqual(self.request('/v/acme/launch/api/project')[0], 200)
        self.assertIn(b'videobuilder editor', self.request('/v/acme/launch/')[1])
        clone = self.root / 'clone'
        self.git('clone', self.url('acme/launch'), str(clone))
        self.assertEqual((clone / 'README.md').read_text(), 'first\n')
        (work / 'big.bin').write_bytes(os.urandom(100_000))
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'large', cwd=work)
        self.git('-c', 'http.postBuffer=1024', 'push', cwd=work)
        self.assertIn(('POST', 'chunked'), self.git_requests)
        self.git('fetch', 'origin', cwd=clone)
        self.git('merge', '--ff-only', 'origin/main', cwd=clone)
        self.assertEqual((clone / 'big.bin').read_bytes(), (work / 'big.bin').read_bytes())
        self.assertTrue((self.library.checkouts / 'acme--launch' / 'big.bin').exists())
        (clone / 'other').write_text('other')
        self.git('add', '.', cwd=clone)
        self.git('commit', '-m', 'other', cwd=clone)
        self.git('push', cwd=clone)
        (work / 'stale').write_text('stale')
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'stale', cwd=work)
        self.assertNotEqual(self.git('push', cwd=work, ok=False).returncode, 0)
        self.assertNotEqual(self.git('push', '--force', cwd=work, ok=False).returncode, 0)
        self.assertNotEqual(self.git('push', 'origin', ':main', cwd=work, ok=False).returncode, 0)

    def test_pushed_config_cannot_configure_the_editor(self):
        work = self.root / 'author'
        self.git('init', '-b', 'main', str(work))
        (work / 'videobuilder.toml').write_text(
            '[editor]\nunsandboxed_previews = true\nallowed_hosts = ["evil.example"]\n'
            'auto_land = false\nrender_jobs = 64\n'
            '[editor.agent]\nbackend = "command"\nsubmit_command = ["sh", "-c", "touch pwned"]\n'
            'poll_command = ["true"]\nexecutable = "/bin/sh"\nsubmit_args = ["-c", "touch pwned"]\n')
        self.git('add', '.', cwd=work)
        self.git('commit', '-m', 'first', cwd=work)
        self.git('remote', 'add', 'origin', self.url('acme/launch'), cwd=work)
        self.git('push', '-u', 'origin', 'main', cwd=work)
        library = Library(self.root / 'library2', envs='current')
        self.addCleanup(library.close)
        # Seed the second library from the first one's bare repo.
        library.path('acme/launch').parent.mkdir(parents=True)
        self.git('clone', '--bare', str(self.library.path('acme/launch')), str(library.path('acme/launch')))
        editor = library.editor('acme/launch')
        self.assertFalse(editor.unsandboxed_previews)
        self.assertNotIn('evil.example', editor.allowed_hosts)
        self.assertEqual(type(editor.notes.backend).__name__, 'NullBackend')
        self.assertFalse(editor.auto_land)
        # As deployed: the operator picks the backend, and the repo must not fill in the rest.
        library3 = Library(self.root / 'library3', envs='current', agent={'backend': 'fork-sandbox'})
        self.addCleanup(library3.close)
        library3.path('acme/launch').parent.mkdir(parents=True)
        self.git('clone', '--bare', str(self.library.path('acme/launch')), str(library3.path('acme/launch')))
        backend = library3.editor('acme/launch').notes.backend
        self.assertEqual((backend.executable, backend.submit_args), ('fork-sandbox', ['run']))

    def test_director_assets_under_video_path(self):
        self.seed(film=True)
        for path, marker in (('', b'id="player"'), ('tuning.html', b'id="tl"'),
                             ('director.js', b'loadVersions'), ('director.css', b'.panel'),
                             ('suggest.js', b'ensureModel'), ('suggest.css', b'.sg-picker')):
            code, body = self.request('/v/acme/launch/' + path)
            self.assertEqual(code, 200, path)
            self.assertIn(marker, body)

    def test_copy_and_validation(self):
        self.seed()
        code, result = self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/promo'})
        self.assertEqual(code, 201, result)
        self.assertNotEqual(result['commit'], result['source_commit'])
        clone = self.root / 'copy'
        self.git('clone', self.url('acme/promo'), str(clone))
        self.assertEqual((clone / 'README.md').read_text(), 'first\n')
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')
        self.assertIn('acme/launch', self.git('log', '-1', '--format=%s', cwd=clone).stdout)
        for name in ('../bad', 'acme/x.git', 'acme/../bad', 'a//b', 'UPPER', 'a/b/c'):
            self.assertFalse(valid_name(name))
            self.assertEqual(self.request('/api/library/new', {'from': 'acme/launch', 'name': name})[0], 400)
            self.assertEqual(self.request('/git/' + name + '.git/info/refs?service=git-receive-pack')[0], 404)
        self.assertEqual(self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/promo'})[0], 400)

    def test_ui_edit_is_in_fresh_clone(self):
        self.seed(film=True)
        code, result = self.request('/v/acme/launch/api/copy',
                                    {'video': 'promo/film', 'segment': 'intro', 'key': 'title', 'value': 'Updated'})
        self.assertEqual(code, 200, result)
        self.assertTrue(result['commit'])
        clone = self.root / 'edited'
        self.git('clone', self.url('acme/launch'), str(clone))
        self.assertIn('Updated', (clone / 'promo' / 'film.edits.toml').read_text())

    def test_tick_reopens_only_repos_with_pending_notes(self):
        from videobuilder.agents import FakeBackend
        self.library.options['backend'] = FakeBackend(delay=0)
        self.seed(film=True)
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Highlight'})
        self.assertEqual(code, 200, note)

        def forget():
            editor = self.library.editors.pop('acme/launch')
            editor.renders.close()
            editor.pool.close()
        forget()
        self.library.tick()
        self.assertEqual(self.library.editors['acme/launch'].notes.get(note['id'])['state'], 'landed')
        forget()
        self.library.tick()
        self.assertNotIn('acme/launch', self.library.editors)

    def test_host_rule_on_git(self):
        code, _ = self.request('/git/acme/launch.git/info/refs?service=git-receive-pack',
                               headers={'Host': 'other.example'})
        self.assertEqual(code, 403)
        self.assertFalse(self.library.path('acme/launch').exists())

    def test_only_a_git_client_creates_a_repo(self):
        self.assertEqual(self.request('/git/acme/drive-by.git/info/refs?service=git-receive-pack',
                                      headers={'User-Agent': 'Mozilla/5.0'})[0], 404)
        self.assertFalse(self.library.path('acme/drive-by').exists())

    def test_git_auto_create_requires_receive_pack_and_a_git_user_agent(self):
        # Right suffix and user-agent, wrong service: refused, nothing created.
        self.assertEqual(self.request('/git/acme/wrong-service.git/info/refs?service=git-upload-pack',
                                      headers={'User-Agent': 'git/2.50.0'})[0], 404)
        self.assertFalse(self.library.path('acme/wrong-service').exists())
        # Right suffix and user-agent, no service at all: refused, nothing created.
        self.assertEqual(self.request('/git/acme/no-service.git/info/refs',
                                      headers={'User-Agent': 'git/2.50.0'})[0], 404)
        self.assertFalse(self.library.path('acme/no-service').exists())
        # All four conditions (GET, info/refs, service=git-receive-pack, git/ user-agent): created.
        self.assertEqual(self.request('/git/acme/all-conditions.git/info/refs?service=git-receive-pack',
                                      headers={'User-Agent': 'git/2.50.0'})[0], 200)
        self.assertTrue(self.library.path('acme/all-conditions').exists())

    def test_malformed_and_truncated_chunked_git_bodies_are_refused(self):
        import io
        from videobuilder.library import _copy_body

        class _FakeHandler:
            def __init__(self, body):
                self.headers = {'Transfer-Encoding': 'chunked'}
                self.rfile = io.BytesIO(body)

        # Truncated: the chunk announces more bytes than the stream actually has.
        with self.assertRaises(ConnectionError):
            _copy_body(_FakeHandler(b'5\r\nab'), io.BytesIO())
        # Malformed: the chunk size isn't valid hex.
        with self.assertRaises(ValueError):
            _copy_body(_FakeHandler(b'zz\r\nabcde\r\n0\r\n\r\n'), io.BytesIO())
        # Malformed: no CRLF after the chunk's data.
        with self.assertRaises(ValueError):
            _copy_body(_FakeHandler(b'5\r\nabcdeXX0\r\n\r\n'), io.BytesIO())

    def test_trailing_slash_redirect_and_https_clone_url(self):
        self.seed()
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1], timeout=20)
        self.addCleanup(conn.close)
        conn.request('GET', '/v/acme/launch')
        response = conn.getresponse()
        response.read()
        self.assertEqual((response.status, response.headers['Location']), (301, '/v/acme/launch/'))
        page = self.request('/', headers={'X-Forwarded-Proto': 'https'})[1]
        self.assertIn(b'https://127.0.0.1:', page)

    def test_library_page_shows_a_new_video_button_and_card_per_video(self):
        self.seed('acme/launch')
        page = self.request('/')[1]
        self.assertIn(b'New video', page)
        self.assertIn(b'href="/new"', page)
        self.assertIn(b'lib-card', page)
        self.assertIn(b'acme/launch', page)

    def test_video_page_carries_the_shared_header(self):
        self.seed('acme/launch')
        code, page = self.request('/v/acme/launch/')
        self.assertEqual(code, 200)
        self.assertIn(b'<body class="has-app-bar">', page)
        self.assertIn(b'id="video-picker"', page)

    def test_new_video_page_is_reachable_without_accounts(self):
        code, page = self.request('/new')
        self.assertEqual(code, 200)
        self.assertIn(b'<form class="nv-form"', page)
        self.assertIn(b'id="name"', page)
        self.assertIn(b'id="project"', page)
        self.assertIn(b'id="nv-data"', page)

    def test_library_page_starter_cards_are_a_hero_when_empty_then_a_compact_row(self):
        page = self.request('/')[1]
        self.assertIn(b'class="starters hero"', page)
        self.assertIn(b'href="/new?starter=paper-explainer"', page)
        self.seed('acme/launch')
        page = self.request('/')[1]
        self.assertNotIn(b'starters hero', page)
        self.assertIn(b'class="starters">', page)

    def test_new_video_page_fills_a_starter_from_the_link_without_showing_cards(self):
        page = self.request('/new?starter=paper-explainer')[1]
        self.assertNotIn(b'starter-card', page)
        self.assertIn(b'"paper-explainer":', page)

    @unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
    def test_make_a_copy_on_a_library_card_makes_a_copy(self):
        """The card's detail dialog offers Make a copy, asking only for the new
        name (same project): its script, run under node, sends the request
        that makes the copy."""
        self.seed('acme/launch', film=True)
        page = self.request('/')[1].decode()
        self.assertIn('data-copy="1"', page)
        self.assertIn('id="lib-copy-name"', page)
        data = re.search(r'<script type="application/json" id="lib-data">(.*?)</script>', page, re.S).group(1)
        script = re.search(r'</script><script>(\(function\(\)\{const data=.*?)</script>', page, re.S).group(1)
        harness = """
const els={},made=[];
function el(id){const e={id,value:'',hidden:false,disabled:false,textContent:'',dataset:{},children:[],
  appendChild(c){this.children.push(c)},addEventListener(){},focus(){},select(){},showModal(){},close(){},
  getBoundingClientRect(){return {left:0,right:0,top:0,bottom:0}}};return e}
const ids=['lib-data','lib-detail','lib-detail-name','lib-detail-project','lib-detail-open','lib-detail-url',
  'lib-detail-copy','lib-detail-meta','lib-detail-updated','lib-detail-subject','lib-copy','lib-copy-name',
  'lib-copy-error','lib-copy-project','lib-copy-go'];
for(const id of ids)els[id]=el(id);
els['lib-data'].textContent=DATA;els['lib-detail'].dataset.copy='1';
const card=el('card');card.dataset.idx='0';const close=el('close');
globalThis.document={getElementById:id=>els[id],querySelectorAll:()=>[card],querySelector:()=>close,
  createElement:t=>{const e=el(t);made.push(e);return e}};
globalThis.location={href:''};
let sent=null;
globalThis.fetch=async(url,init)=>{sent=[url,JSON.parse(init.body)];return {ok:true,json:async()=>({})}};
""".replace('DATA', json.dumps(data))
        run = """
card.onclick();
const copy=els['lib-detail-open'].children.find(c=>c.textContent==='Make a copy');
copy.onclick();
const named=[els['lib-copy-project'].textContent,els['lib-copy-name'].value,els['lib-copy'].hidden];
els['lib-copy-name'].value='Launch Again';
els['lib-copy'].onsubmit({preventDefault(){}}).then(()=>console.log(JSON.stringify({named,sent,href:location.href})));
"""
        result = subprocess.run(['node', '-'], input=(harness + script + run).encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        out = json.loads(result.stdout)
        self.assertEqual(out['named'], ['acme/', 'launch-copy', False])
        url, body = out['sent']
        self.assertEqual((url, body), ('/api/videos/new', {'name': 'acme/launch-again', 'start': 'copy',
                                                          'from': 'acme/launch'}))
        self.assertEqual(out['href'], '/v/acme/launch-again/')
        code, result = self.request(url, body)
        self.assertEqual(code, 201, result)
        clone = self.root / 'copy-of-launch'
        self.git('clone', self.url('acme/launch-again'), str(clone))
        self.assertTrue((clone / 'promo' / 'film.py').is_file())

    def test_repos_share_one_env_cache(self):
        self.seed('acme/launch')
        self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/promo'})
        self.assertIs(self.library.editor('acme/launch').envs, self.library.editor('acme/promo').envs)

    def test_empty_repo_is_listed_but_cannot_open_or_copy(self):
        self.assertEqual(self.request('/git/acme/empty.git/info/refs?service=git-receive-pack',
                                      headers={'User-Agent': 'git/2.50.0'})[0], 200)
        self.assertIn(b'Empty', self.request('/')[1])
        self.assertEqual(self.request('/v/acme/empty/')[0], 404)
        self.assertEqual(self.request('/api/library/new', {'from': 'acme/empty', 'name': 'another'})[0], 400)

    def test_library_page_cards_for_a_render_no_render_and_no_main_mix(self):
        # The render half of this mix (a video whose card actually has a JPEG to
        # serve) needs ffmpeg and is covered separately below; everything here --
        # the card markup, lib-data contents and the dropped git URL -- doesn't.
        self.seed('acme/launch', film=True)
        self.seed('acme/draft', film=True)
        self.assertEqual(self.request('/git/acme/empty.git/info/refs?service=git-receive-pack',
                                      headers={'User-Agent': 'git/2.50.0'})[0], 200)
        self.assertEqual(self.request('/v/acme/draft/api/thumbnail')[0], 404)

        page = self.request('/')[1].decode()
        self.assertNotIn('lib-git', page)  # the git URL no longer shows on the card itself
        blob = re.search(r'<script type="application/json" id="lib-data">(.*?)</script>', page, re.S).group(1)
        by_name = {c['name']: c for c in json.loads(blob)}
        self.assertEqual(set(by_name), {'acme/launch', 'acme/draft', 'acme/empty'})
        self.assertTrue(by_name['acme/launch']['hasMain'])
        self.assertTrue(by_name['acme/draft']['hasMain'])
        self.assertFalse(by_name['acme/empty']['hasMain'])
        self.assertIsNone(by_name['acme/empty']['updated'])
        self.assertIsNone(by_name['acme/empty']['subject'])
        self.assertIsNotNone(by_name['acme/launch']['updated'])
        self.assertEqual(by_name['acme/launch']['subject'], 'first')
        self.assertIn('/v/acme/launch/api/thumbnail', page)
        self.assertIn('/v/acme/draft/api/thumbnail', page)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
    def test_library_page_thumbnail_for_a_video_with_a_render(self):
        self.seed('acme/launch', film=True)
        editor = self.library.editor('acme/launch')
        sha = self.git('rev-parse', 'main', cwd=self.library.checkouts / 'acme--launch').stdout.strip()
        render_path = editor.renders.path('promo/film', sha, '16x9')
        render_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=320x180:d=4:r=5',
                        '-pix_fmt', 'yuv420p', str(render_path)], check=True, capture_output=True)

        code, data = self.request('/v/acme/launch/api/thumbnail')
        self.assertEqual(code, 200)
        self.assertEqual(data[:3], b'\xff\xd8\xff')

    def test_thumbnail_for_an_unopened_video_never_builds_its_editor(self):
        # A card's lazy <img> must not clone the repo and spin up a render-poll
        # thread for every video on the page, just because nobody has opened it.
        self.seed('acme/draft', film=True)
        self.assertEqual(self.request('/v/acme/draft/api/thumbnail')[0], 404)
        self.assertNotIn('acme/draft', self.library.editors)
        self.assertFalse((self.library.checkouts / 'acme--draft').exists())

    def test_blank_start_has_one_commit_pinned_to_the_editors_version(self):
        from videobuilder import __version__
        code, result = self.request('/api/videos/new', {'name': 'acme/blank', 'start': 'blank'})
        self.assertEqual((code, result['video']), (201, 'film'))
        clone = self.root / 'blank-clone'
        self.git('clone', self.url('acme/blank'), str(clone))
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')
        self.assertEqual((clone / 'requirements.txt').read_text(), f'videobuilder=={__version__}\n')
        self.assertTrue((clone / 'film.py').is_file())
        # The new video is actually buildable: Project discovers it as a real video.
        code, info = self.request('/v/acme/blank/api/project')
        self.assertEqual((code, [v['id'] for v in info['videos']]), (200, ['film']))

    def test_blank_start_refuses_an_existing_name(self):
        self.request('/api/videos/new', {'name': 'acme/dup', 'start': 'blank'})
        code, err = self.request('/api/videos/new', {'name': 'acme/dup', 'start': 'blank'})
        self.assertEqual(code, 400)

    def test_copy_start_still_works_through_the_new_route(self):
        self.seed('acme/launch', film=True)
        code, result = self.request('/api/videos/new', {'name': 'acme/copy', 'start': 'copy', 'from': 'acme/launch'})
        self.assertEqual((code, result['video']), (201, None))
        clone = self.root / 'copy-clone'
        self.git('clone', self.url('acme/copy'), str(clone))
        self.assertEqual(self.git('rev-list', '--count', 'main', cwd=clone).stdout.strip(), '1')

    def test_first_note_carries_description_attachments_and_a_gathering_failure_line(self):
        from videobuilder.agents import FakeBackend
        self.request('/api/videos/new', {'name': 'acme/scratch', 'start': 'blank'})
        self.library.editor('acme/scratch').notes.backend = FakeBackend(delay=0)
        import urllib.request
        req = urllib.request.Request(self.base + '/v/acme/scratch/api/attachments?video=film&name=brief.txt',
                                     data=b'notes for the builder', method='POST',
                                     headers={'Content-Type': 'text/plain'})
        with urllib.request.urlopen(req, timeout=20) as r:
            attach = json.loads(r.read())
        code, note = self.request('/v/acme/scratch/api/videos/first-note', {
            'description': 'A marketing video for the launch.',
            'attachments': [attach['id']],
            'links': ['http://127.0.0.1:1/unreachable'],
        })
        # The note is created right away, before the (possibly slow) crawl runs, so the
        # call returns the placeholder: 'gathering', with the brief already on it.
        self.assertEqual(code, 200, note)
        self.assertEqual(note['state'], 'gathering')
        self.assertEqual(note['text'], 'A marketing video for the launch.')
        note = self.wait_for_note(note['id'], lambda n: n['state'] != 'gathering')
        self.assertIn('A marketing video for the launch.', note['text'])
        self.assertIn('Some pages were not gathered', note['text'])
        self.assertEqual(note['said'], 'A marketing video for the launch.')
        names = {a['name'] for a in note['attachments']}
        self.assertIn('brief.txt', names)
        self.assertIn('gathered-pages.md', names)
        # Left 'gathering' for the normal dispatch states; a FakeBackend with no
        # delay can race straight through 'queued'/'working' to a final state.
        self.assertNotEqual(note['state'], 'gathering')

    def wait_for_note(self, nid, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        note = None
        while time.monotonic() < deadline:
            _, notes = self.request('/v/acme/scratch/api/notes?video=film')
            note = next((n for n in notes['notes'] if n['id'] == nid), None)
            if note is not None and predicate(note):
                return note
            time.sleep(0.05)
        self.fail(f'note {nid} did not reach the expected state in time: {note}')

    def test_first_note_without_links_queues_immediately(self):
        from videobuilder.agents import FakeBackend
        self.request('/api/videos/new', {'name': 'acme/no-links', 'start': 'blank'})
        self.library.editor('acme/no-links').notes.backend = FakeBackend(delay=0)
        code, note = self.request('/v/acme/no-links/api/videos/first-note', {'description': 'Simple brief.'})
        self.assertEqual(code, 200, note)
        self.assertIn('Simple brief.', note['text'])
        self.assertIn('Build a first version', note['text'])     # the builder gets the whole brief
        self.assertEqual(note['said'], 'Simple brief.')          # the chat shows only the creator's words
        self.assertEqual(note['attachments'], [])

    def test_first_note_cap_refuses_once_reached(self):
        # No accounts here: nobody is exempt, so a configured cap binds the one caller.
        from videobuilder.agents import FakeBackend
        self.request('/api/videos/new', {'name': 'acme/capped', 'start': 'blank'})
        editor = self.library.editor('acme/capped')
        editor.notes.backend = FakeBackend(delay=0)
        editor.account_daily_note_cap = 1
        code, note = self.request('/v/acme/capped/api/videos/first-note', {'description': 'First.'})
        self.assertEqual(code, 200, note)
        code, data, _ = self.request_full('/v/acme/capped/api/videos/first-note', {'description': 'Second.'})
        self.assertEqual(code, 429)
        self.assertIn("today's limit", data['error'])

    def test_first_note_refuses_malformed_links(self):
        self.request('/api/videos/new', {'name': 'acme/bad-links', 'start': 'blank'})
        # A non-string element must be refused with 400, not crash with a 500 when
        # the route tries to .strip() it.
        code, err = self.request('/v/acme/bad-links/api/videos/first-note', {'links': [1]})
        self.assertEqual(code, 400, err)
        # A bare string must be refused, not silently iterated into one-character "links".
        code, err = self.request('/v/acme/bad-links/api/videos/first-note', {'links': 'https://a.example'})
        self.assertEqual(code, 400, err)

    def _upload_png(self, project, name):
        import urllib.request
        req = urllib.request.Request(
            self.base + f'/v/{project}/api/attachments?video=film&name=' + name,
            data=b'\x89PNG\r\n\x1a\n' + b'0123456789', method='POST', headers={'Content-Type': 'image/png'})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())['id']

    def test_first_note_brief_and_attachments_reflect_the_chosen_image_order(self):
        self.request('/api/videos/new', {'name': 'acme/ordered', 'start': 'blank'})
        # Uploaded in filename order, but the creator's chosen order (sent as `attachments`) is b, a, c.
        a = self._upload_png('acme/ordered', 'a.png')
        b = self._upload_png('acme/ordered', 'b.png')
        c = self._upload_png('acme/ordered', 'c.png')
        code, note = self.request('/v/acme/ordered/api/videos/first-note', {
            'description': 'A tour of the launch.', 'attachments': [b, a, c]})
        self.assertEqual(code, 200, note)
        self.assertEqual([x['name'] for x in note['attachments']], ['b.png', 'a.png', 'c.png'])
        self.assertIn('A tour of the launch.\n\nUse the attached images in this order:\n'
                      '1. b.png\n2. a.png\n3. c.png\n\n'
                      'Keep this order unless the brief above says otherwise.', note['text'])

    def test_first_note_with_one_image_has_no_order_list_in_the_brief(self):
        self.request('/api/videos/new', {'name': 'acme/single-image', 'start': 'blank'})
        only = self._upload_png('acme/single-image', 'only.png')
        code, note = self.request('/v/acme/single-image/api/videos/first-note', {
            'description': 'Just one shot.', 'attachments': [only]})
        self.assertEqual(code, 200, note)
        self.assertNotIn('Use the attached images in this order', note['text'])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'needs ffmpeg/ffprobe')
class FilmSetup(LibraryFixture, unittest.TestCase):
    """What the editor sets on a video New video only names: Film details (the
    look, length, world and characters, in the bible) and its first clip."""

    PNG = b'\x89PNG\r\n\x1a\n' + b'0123456789'

    def setUp(self):
        super().setUp()
        self.media = self.root / 'media'
        self.media.mkdir()

    def _start(self, name):
        from videobuilder.agents import FakeBackend
        code, result = self.request('/api/videos/new', {'name': name, 'start': 'blank'})
        self.assertEqual(code, 201, result)
        self.library.editor(name).notes.backend = FakeBackend(delay=0)

    def _make(self, filename, seconds, audio_only=False):
        path = self.media / filename
        cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}']
        if not audio_only:
            cmd += ['-f', 'lavfi', '-i', f'color=c=blue:s=64x36:d={seconds}:r=10', '-pix_fmt', 'yuv420p',
                    '-shortest']
        subprocess.run(cmd + [str(path)], check=True, capture_output=True)
        return path

    def _upload(self, project, path, kind, url='sources'):
        query = f'video=film&filename={path.name}' if url == 'sources' else f'video=film&name={path.name}'
        req = urllib.request.Request(f'{self.base}/v/{project}/api/{url}?{query}', data=path.read_bytes(),
                                     method='POST', headers={'Content-Type': kind})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def _picture(self, project, name='keeper.png'):
        png = self.media / name
        png.write_bytes(self.PNG)
        return self._upload(project, png, 'image/png', url='attachments')['id']

    def _clone(self, name):
        clone = self.root / ('clone-' + name.replace('/', '--'))
        shutil.rmtree(clone, ignore_errors=True)
        self.git('clone', self.url(name), str(clone))
        return clone

    def _save(self, project, **fields):
        _, film = self.request(f'/v/{project}/api/film?video=film')
        return self.request(f'/v/{project}/api/film', {'video': 'film', 'base': film['commit'], **fields})

    def test_a_character_picture_must_be_a_raster_image(self):
        self._start('sea/vector')
        svg = self.media / 'keeper.svg'
        svg.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 4"/>')
        ident = self._upload('sea/vector', svg, 'image/svg+xml', url='attachments')['id']
        code, err = self._save('sea/vector', characters=[{'name': 'Keeper', 'description': '', 'add': [ident]}])
        self.assertEqual(code, 400, err)
        self.assertIn(b'use a PNG, JPEG, WebP or GIF', err)

    def test_film_details_on_a_blank_video_write_the_bible_new_video_did(self):
        from videobuilder import looks
        self._start('sea/lighthouse')
        code, film = self.request('/v/sea/lighthouse/api/film?video=film')
        self.assertEqual(code, 200, film)
        self.assertEqual((film['unbuilt'], film['film']), (True, False))
        self.assertEqual(film['details'], {'look': None, 'length': None, 'world': '', 'characters': []})
        picture = self._picture('sea/lighthouse')
        code, saved = self._save('sea/lighthouse', look='woodblock', length='2:30', world='A lighthouse on a rock.',
                                 characters=[{'name': 'Keeper', 'description': 'The robot keeper.',
                                              'add': [picture]}])
        self.assertEqual(code, 200, saved)
        self.assertEqual((saved['changed'], saved['n'], saved['unbuilt']), (True, 2, True))
        clone = self._clone('sea/lighthouse')
        # The layout and wording New video's Start building wrote (new_video.bible), plus the length,
        # which it only ever put in the first note.
        self.assertEqual((clone / 'bible' / 'bible.md').read_text(),
                         '# Lighthouse\n\n## Look\n\n'
                         f'{looks.get("woodblock").title} (`vb.looks` name `woodblock`), for every clip.\n\n'
                         '## Length\n\nAbout 2:30.\n\n## World\n\nA lighthouse on a rock.\n\n'
                         '## Characters\n\n- Keeper: characters/keeper.md\n')
        self.assertEqual((clone / 'bible' / 'characters' / 'keeper.md').read_text(),
                         '# Keeper\n\nThe robot keeper.\n\nPictures, beside this file:\n\n- keeper-1.png\n')
        self.assertEqual((clone / 'bible' / 'characters' / 'keeper-1.png').read_bytes(), self.PNG)
        self.assertEqual(sorted(p.name for p in clone.iterdir() if p.name != '.git'),
                         ['bible', 'film.py', 'requirements.txt'])
        message = self.git('log', '-1', '--format=%B', cwd=clone).stdout
        self.assertIn('Film details: look, length, world, add Keeper', message)
        self.assertIn('Version-kind: edit', message)
        # It reads back as it was set, and the video is still waiting for its first note.
        self.assertEqual(saved['details'], {'look': 'woodblock', 'length': '2:30', 'world': 'A lighthouse on a rock.',
                                            'characters': [{'name': 'Keeper', 'slug': 'keeper',
                                                            'description': 'The robot keeper.',
                                                            'pictures': ['keeper-1.png']}]})
        _, versions = self.request('/v/sea/lighthouse/api/versions?video=film')
        self.assertEqual([(v['n'], v['unbuilt']) for v in versions['versions']], [(2, True), (1, True)])
        code, body = self.request_full('/v/sea/lighthouse/api/film/picture?video=film&name=keeper-1.png')[:2]
        self.assertEqual(code, 200)
        self.assertEqual(self.request('/v/sea/lighthouse/api/film/picture?video=film&name=..%2Ffilm.py')[0], 404)
        # Saving the same again is no new version.
        code, again = self._save('sea/lighthouse', look='woodblock', length='2:30', world='A lighthouse on a rock.',
                                 characters=[{'slug': 'keeper', 'name': 'Keeper', 'description': 'The robot keeper.',
                                              'keep': ['keeper-1.png']}])
        self.assertEqual((code, again['changed'], again['n']), (200, False, 2))

    def test_a_save_rewrites_only_what_changed_and_keeps_the_rest_of_the_bible(self):
        self._start('sea/keep')
        picture = self._picture('sea/keep')
        self._save('sea/keep', world='A rock.', characters=[{'name': 'Keeper', 'add': [picture]},
                                                            {'name': 'Gull'}])
        # A builder adds a section of its own.
        clone = self._clone('sea/keep')
        bible = clone / 'bible' / 'bible.md'
        bible.write_text(bible.read_text() + '\n## Tone\n\nQuiet, then loud.\n')
        self.git('commit', '-am', 'tone', cwd=clone)
        self.git('push', 'origin', 'main', cwd=clone)
        _, film = self.request('/v/sea/keep/api/film?video=film')
        stale = film['commit']
        code, saved = self.request('/v/sea/keep/api/film', {
            'video': 'film', 'base': stale, 'look': 'as-shot', 'world': 'A rock.',
            'characters': [{'slug': 'keeper', 'name': 'The Keeper', 'keep': []}]})
        self.assertEqual(code, 200, saved)
        clone = self._clone('sea/keep')
        text = (clone / 'bible' / 'bible.md').read_text()
        self.assertIn('## Look\n\nAs shot.', text)
        self.assertIn('## Tone\n\nQuiet, then loud.', text)
        self.assertIn('- The Keeper: characters/keeper.md', text)
        self.assertNotIn('Gull', text)
        self.assertEqual(sorted(p.name for p in (clone / 'bible' / 'characters').iterdir()), ['keeper.md'])
        self.assertTrue((clone / 'bible' / 'characters' / 'keeper.md').read_text().startswith('# The Keeper\n'))
        # A sheet opened before that save is refused rather than undoing it.
        code, err = self.request('/v/sea/keep/api/film', {'video': 'film', 'base': stale, 'world': 'Elsewhere.'})
        self.assertEqual(code, 409, err)
        code, err = self._save('sea/keep', look='velvet')
        self.assertEqual(code, 400, err)

    def test_the_first_note_after_film_details_points_the_builder_at_them(self):
        self._start('sea/brief')
        self._save('sea/brief', look='pop-art', length='0:30', world='A pier at night.')
        code, note = self.request('/v/sea/brief/api/videos/first-note', {'description': 'A short about a pier.'})
        self.assertEqual(code, 200, note)
        self.assertTrue(note['text'].startswith('A short about a pier.\n\nLength: about 0:30.\nLook: Pop-art'))
        self.assertIn('read bible/bible.md first', note['text'])

    def test_the_first_footage_clip_makes_a_blank_video_a_film_of_clips(self):
        from videobuilder import timeline_file
        self._start('snow/day-reel')
        clip = self._upload('snow/day-reel', self._make('chairlift.mp4', 2), 'video/mp4')
        song = self._upload('snow/day-reel', self._make('Avalanche.mp3', 3, audio_only=True), 'audio/mpeg')
        code, err = self.request('/v/snow/day-reel/api/film/start', {'video': 'film', 'footage': song['name']})
        self.assertEqual(code, 400, err)  # a sound goes on an Audio lane
        code, film = self.request('/v/snow/day-reel/api/film/start', {'video': 'film', 'footage': clip['name']})
        self.assertEqual(code, 200, film)
        self.assertEqual((film['film'], film['unbuilt'], film['n']), (True, False, 2))
        clone = self._clone('snow/day-reel')
        self.assertEqual((clone / '.gitignore').read_text(), '.vb-cache/\n')
        self.assertFalse((clone / 'sources').exists())  # footage is never committed
        tl = timeline_file.load(clone / 'timeline.json')
        self.assertEqual([(c.id, c.footage, c.in_frame, c.out_frame) for c in tl.clips],
                         [('chairlift', 'sources/chairlift.mp4', 0, 60)])
        self.assertIn('FILM = vb.Film(', (clone / 'film.py').read_text())
        code, info = self.request('/v/snow/day-reel/api/project')
        self.assertEqual([v['id'] for v in info['videos']], ['film'])
        _, timeline = self.request('/v/snow/day-reel/api/timeline?video=film')
        self.assertEqual([c['id'] for c in timeline['timeline']['clips']], ['chairlift'])
        # From here the timeline adds clips and songs; a second first clip is refused.
        code, err = self.request('/v/snow/day-reel/api/film/start', {'video': 'film', 'footage': clip['name']})
        self.assertEqual(code, 409, err)
        data = dict(timeline['timeline'], lanes=[{'items': [{'sound': 'sources/avalanche.mp3', 'at': 0,
                                                             'frames': 60}]}])
        code, saved = self.request('/v/snow/day-reel/api/timeline', {'video': 'film', 'timeline': data,
                                                                     'base': timeline['commit']})
        self.assertEqual(code, 200, saved)
        self.assertEqual(timeline_file.load(self._clone('snow/day-reel') / 'timeline.json').lanes[0].items[0].sound,
                         'sources/avalanche.mp3')

    def test_a_planned_clip_lands_in_the_timeline_as_a_clip_the_builder_makes(self):
        from videobuilder import film, film_brief, timeline_file
        from videobuilder.clip_cache import GitTree
        self._start('sea/planned')
        code, state = self.request('/v/sea/planned/api/film/start', {
            'video': 'film', 'plan': {'title': 'Lamp at dusk', 'line': 'Keeper lights the lamp.'}})
        self.assertEqual(code, 200, state)
        _, timeline = self.request('/v/sea/planned/api/timeline?video=film')
        self.assertEqual(timeline['timeline']['clips'], [{'id': 'lamp-at-dusk', 'dir': 'clips/lamp-at-dusk'}])
        # A second one, after it, from the timeline's + sheet: its directory comes with the timeline.
        data = dict(timeline['timeline'], clips=timeline['timeline']['clips'] + [{'id': 'storm', 'dir': 'clips/storm'}],
                    acts=[{'title': 'Alone', 'clips': ['lamp-at-dusk', 'storm']}])
        code, saved = self.request('/v/sea/planned/api/timeline', {
            'video': 'film', 'timeline': data, 'base': timeline['commit'], 'summary': 'plan clip Storm',
            'plans': {'storm': {'title': 'Storm', 'line': 'The lamp goes dark.'}}})
        self.assertEqual(code, 200, saved)
        clone = self._clone('sea/planned')
        self.assertEqual(self.git('show', '--stat', '--format=', 'HEAD', cwd=clone).stdout.count('|'), 2)
        tl = timeline_file.load(clone / 'timeline.json')
        self.assertEqual([(c.id, c.dir) for c in tl.clips], [('lamp-at-dusk', 'clips/lamp-at-dusk'),
                                                             ('storm', 'clips/storm')])
        self.assertEqual([a.title for a in tl.acts], ['Alone'])
        # Every builder is shown what each clip is for, and the placeholder plays.
        sha = self.git('rev-parse', 'HEAD', cwd=clone).stdout.strip()
        brief, _ = film_brief.brief(str(clone), sha, '.', None, '16x9', str(clone))
        self.assertEqual([c['about'] for c in brief['clips']], ['Keeper lights the lamp.', 'The lamp goes dark.'])
        # ...and a whole-video note asks for the planned ones to be made.
        from videobuilder.prompt import _clip_line
        self.assertEqual([c['planned'] for c in brief['clips']], [True, True])
        self.assertIn('planned, not made yet: make it as part of this note', _clip_line(brief['clips'][1]))
        self.assertIn('The lamp goes dark.', _clip_line(brief['clips'][1]))
        placeholder = film.load(clone / 'clips' / 'storm' / 'film.py')
        self.assertIsNotNone(placeholder.frame(0, '16x9', scale=0.1))
        self.assertIsNotNone(GitTree(str(clone), sha, '.').read('clips/storm/film.py'))
        # A plan for a clip the timeline doesn't have is refused.
        code, err = self.request('/v/sea/planned/api/timeline', {
            'video': 'film', 'timeline': data, 'base': saved['commit'], 'plans': {'nope': {'title': 'x'}}})
        self.assertEqual(code, 400, err)
        # Taken out again (as Undo does), its directory stays on main, and the timeline names it as taken,
        # so a new plan with the same title gets a fresh id rather than a 409.
        code, out = self.request('/v/sea/planned/api/timeline', {
            'video': 'film', 'timeline': timeline['timeline'], 'base': saved['commit']})
        self.assertEqual(code, 200, out)
        self.assertEqual(out['dirs'], ['lamp-at-dusk', 'storm'])
        _, again = self.request('/v/sea/planned/api/timeline?video=film')
        self.assertEqual(again['dirs'], ['lamp-at-dusk', 'storm'])

    def test_a_built_video_does_not_start_over_as_a_film_of_clips(self):
        self.seed('acme/launch', film=True)
        _, info = self.request('/v/acme/launch/api/project')
        video = info['videos'][0]['id']
        code, err = self.request('/v/acme/launch/api/film/start', {'video': video, 'plan': {'title': 'Hi'}})
        self.assertEqual(code, 409, err)

    def test_a_world_with_a_heading_in_it_reads_back_whole(self):
        import tempfile
        from pathlib import Path
        from videobuilder import film_setup
        world = 'An island.\n## Weather\nAlways storms.'
        new, _ = film_setup.parse_details({'world': world}, film_setup.Details())
        files = film_setup.bible_files('Sea', '', film_setup.Details(), new, {})
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / film_setup.BIBLE).parent.mkdir(parents=True)
            (Path(d) / film_setup.BIBLE).write_bytes(files[film_setup.BIBLE])
            back = film_setup.read_details(Path(d))
        self.assertEqual(back.world, 'An island.\n### Weather\nAlways storms.')
        self.assertEqual(back.world, new.world)

    def test_any_character_name_gets_a_file_of_its_own(self):
        from videobuilder import film_setup
        names = ['Анна', 'マラ', 'Mara', 'Mara.']
        details, _ = film_setup.parse_details({'characters': [{'name': n} for n in names]}, film_setup.Details())
        self.assertEqual([c['slug'] for c in details.characters], ['character-1', 'character-2', 'mara', 'mara-2'])
        with self.assertRaises(ValueError):
            film_setup.parse_details({'characters': [{'name': 'Mara'}, {'name': 'mara'}]}, film_setup.Details())


class Keys(AccountMixin, KeyMixin, LibraryFixture, unittest.TestCase):
    """Per-account API keys: git over HTTP, the video API, scope, mode and attribution."""

    def test_git_clone_fetch_with_read_key_works_and_push_is_refused(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'reader', None, 'read')
        clone = self.root / 'read-clone'
        self.git('clone', self.git_key_url('acme/launch', secret), str(clone))
        self.assertEqual((clone / 'README.md').read_text(), 'first\n')
        (clone / 'extra').write_text('extra')
        self.git('add', '.', cwd=clone)
        self.git('commit', '-m', 'extra', cwd=clone)
        result = self.git('push', cwd=clone, ok=False)
        self.assertNotEqual(result.returncode, 0)

    def test_git_push_with_write_key_works_and_stays_fast_forward_only(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        clone = self.root / 'write-clone'
        self.git('clone', self.git_key_url('acme/launch', secret), str(clone))
        stale = self.root / 'stale-clone'
        self.git('clone', self.git_key_url('acme/launch', secret), str(stale))
        (clone / 'extra').write_text('extra')
        self.git('add', '.', cwd=clone)
        self.git('commit', '-m', 'extra', cwd=clone)
        self.git('push', cwd=clone)
        (stale / 'stale').write_text('stale')
        self.git('add', '.', cwd=stale)
        self.git('commit', '-m', 'stale', cwd=stale)
        self.assertNotEqual(self.git('push', cwd=stale, ok=False).returncode, 0)

    def test_bearer_get_and_post_work_for_write_post_refused_for_read(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, write_secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        _, read_secret = self.library.accounts.create_key('mgalgs', 'reader', None, 'read')
        self.assertEqual(self.request('/v/acme/launch/api/project', headers=self.bearer(read_secret))[0], 200)
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', **self.bearer(write_secret)})
        self.assertEqual(code, 200, note)
        code, err = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                 headers={'Content-Type': 'application/json', **self.bearer(read_secret)})
        self.assertEqual(code, 403)

    def test_bearer_key_reaches_sources_list_and_preview_write_needed_for_delete(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, write_secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        _, read_secret = self.library.accounts.create_key('mgalgs', 'reader', None, 'read')
        self.assertEqual(self.request('/v/acme/launch/api/sources?video=promo/film',
                                      headers=self.bearer(read_secret))[0], 200)
        self.assertEqual(self.request('/v/acme/launch/api/sources/clip?video=promo/film',
                                      headers=self.bearer(read_secret))[0], 404)  # reaches Sources; no such clip
        code, _ = self.request('/v/acme/launch/api/sources/clip/delete', {'video': 'promo/film'},
                               headers={'Content-Type': 'application/json', **self.bearer(read_secret)})
        self.assertEqual(code, 403)  # read key refused before Sources is ever reached
        code, _ = self.request('/v/acme/launch/api/sources/clip/delete', {'video': 'promo/film'},
                               headers={'Content-Type': 'application/json', **self.bearer(write_secret)})
        self.assertEqual(code, 404)  # write key reaches Sources; 'clip' just doesn't exist

    def test_scope_refuses_another_namespace(self):
        self.seed('acme/launch', film=True)
        self.seed('gardening/promo', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.new_project(admin, 'gardening/promo', 'gardening/promo')
        _, secret = self.library.accounts.create_key('mgalgs', 'scoped', 'gardening', 'write')
        self.assertEqual(self.request('/v/gardening/promo/api/project', headers=self.bearer(secret))[0], 200)
        self.assertEqual(self.request('/v/acme/launch/api/project', headers=self.bearer(secret))[0], 404)
        code, _, headers = self.request_full(
            '/git/acme/launch.git/info/refs?service=git-receive-pack', headers=self.bearer(secret))
        # Git never accepts a bearer header; this key must act only through Basic auth there.
        self.assertIn(code, (401, 404))

    def test_scope_refuses_a_top_level_project_named_like_the_scope(self):
        # 'gardening' is a valid single-part project name in its own right, distinct from the
        # 'gardening/...' namespace: a key scoped to 'gardening' must not reach it.
        self.seed('gardening', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'gardening', 'gardening')
        _, secret = self.library.accounts.create_key('mgalgs', 'scoped', 'gardening', 'write')
        self.assertEqual(self.request('/v/gardening/api/project', headers=self.bearer(secret))[0], 404)
        basic = {'Authorization': 'Basic ' + base64.b64encode(f'x:{secret}'.encode()).decode()}
        code, _, _ = self.request_full('/git/gardening.git/info/refs?service=git-receive-pack', headers=basic)
        self.assertEqual(code, 404)

    def test_key_refused_on_api_library_new(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        self.assertNotEqual(self.request('/api/library/new', {'from': 'acme/launch', 'name': 'acme/copy'},
                                         headers={'Content-Type': 'application/json', **self.bearer(secret)})[0], 201)
        self.assertNotEqual(self.request('/api/usage', headers=self.bearer(secret))[0], 200)

    def test_write_key_creates_a_blank_video_in_its_scope_and_then_reaches_it(self):
        admin = self.admin_login()
        _, secret = self.library.accounts.create_key('mgalgs', 'agent', 'claude', 'write')
        code, result = self.request('/api/videos/new', {'name': 'claude/first', 'start': 'blank'},
                                    headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 201, result)
        self.assertEqual(result['name'], 'claude/first')
        self.assertEqual(self.request('/v/claude/first/api/access', headers=self.bearer(secret))[0], 401)
        code, access = self.request('/v/claude/first/api/access', headers={'Cookie': admin})
        self.assertEqual((code, access['owner']), (200, 'mgalgs'))
        self.assertEqual(self.request('/v/claude/first/api/project', headers=self.bearer(secret))[0], 200)

    def test_scoped_key_creating_outside_its_scope_is_403_and_nothing_is_created(self):
        self.admin_login()
        _, secret = self.library.accounts.create_key('mgalgs', 'agent', 'claude', 'write')
        code, err, _ = self.request_full('/api/videos/new', {'name': 'other/first', 'start': 'blank'},
                                         headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 403, err)
        self.assertIn('claude/', err['error'])
        self.assertFalse(self.library.path('other/first').exists())

    def test_read_only_key_cannot_create_a_video(self):
        self.admin_login()
        _, secret = self.library.accounts.create_key('mgalgs', 'agent', None, 'read')
        code, err, _ = self.request_full('/api/videos/new', {'name': 'acme/first', 'start': 'blank'},
                                         headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 403, err)
        self.assertEqual(err['error'], 'this key is read-only')
        self.assertFalse(self.library.path('acme/first').exists())

    def test_unscoped_write_key_can_create_any_free_name(self):
        self.admin_login()
        _, secret = self.library.accounts.create_key('mgalgs', 'agent', None, 'write')
        code, result = self.request('/api/videos/new', {'name': 'anywhere/first', 'start': 'blank'},
                                    headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 201, result)

    def test_invalid_key_on_videos_new_is_401(self):
        self.admin_login()
        code, err, _ = self.request_full('/api/videos/new', {'name': 'acme/first', 'start': 'blank'},
                                         headers={'Content-Type': 'application/json', **self.bearer('vbk_notarealkey')})
        self.assertEqual(code, 401, err)
        self.assertEqual(err['error'], 'invalid or revoked key')

    def test_copy_source_outside_the_keys_scope_is_the_sessions_404_and_nothing_is_created(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')  # owned by mgalgs, the key's own account
        _, secret = self.library.accounts.create_key('mgalgs', 'agent', 'claude', 'write')
        code, err, _ = self.request_full('/api/videos/new', {'name': 'claude/copy', 'start': 'copy',
                                                              'from': 'acme/launch'},
                                         headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 404, err)
        self.assertEqual(err['error'], 'repository has no main branch')
        self.assertFalse(self.library.path('claude/copy').exists())

    def test_copy_source_in_scope_but_inaccessible_to_the_keys_account_is_the_sessions_404(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')  # owned by mgalgs, not dana
        _, _, dana = self.signup('dana', 'longenoughpassword')
        _, secret = self.library.accounts.create_key('dana', 'agent', 'acme', 'write')
        code, err, _ = self.request_full('/api/videos/new', {'name': 'acme/stolen', 'start': 'copy',
                                                              'from': 'acme/launch'},
                                         headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 404, err)
        self.assertEqual(err['error'], 'repository has no main branch')
        self.assertFalse(self.library.path('acme/stolen').exists())

    def test_copy_from_an_accessible_in_scope_source_works_and_the_key_owns_the_result(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        code, original = self.request('/api/videos/new', {'name': 'acme/own', 'start': 'blank'},
                                       headers={'Content-Type': 'application/json', 'Cookie': dana})
        self.assertEqual(code, 201, original)
        _, secret = self.library.accounts.create_key('dana', 'agent', 'acme', 'write')
        code, result = self.request('/api/videos/new', {'name': 'acme/own-copy', 'start': 'copy', 'from': 'acme/own'},
                                    headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 201, result)
        code, access = self.request('/v/acme/own-copy/api/access', headers={'Cookie': dana})
        self.assertEqual((code, access['owner']), (200, 'dana'))

    def test_scope_excludes_access_management_even_though_it_is_under_api(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        self.assertEqual(self.request('/v/acme/launch/api/access', headers=self.bearer(secret))[0], 401)

    def test_password_not_prefixed_vbk_still_checks_password_and_locks_out(self):
        self.seed('acme/launch')
        from videobuilder.accounts import LOGIN_LIMIT
        import base64
        def basic(password):
            return {'Authorization': 'Basic ' + base64.b64encode(f'mgalgs:{password}'.encode()).decode()}
        for _ in range(LOGIN_LIMIT):
            code, _, _ = self.request_full('/git/acme/launch.git/info/refs?service=git-receive-pack',
                                           headers=basic('wrong'))
            self.assertEqual(code, 401)
        with self.assertRaises(ValueError) as caught:
            self.library.accounts.verify('mgalgs', self.ADMIN_PASSWORD)
        self.assertIn('too many attempts', str(caught.exception))

    def test_git_basic_auth_with_an_unknown_key_is_401(self):
        self.seed('acme/launch')
        basic = {'Authorization': 'Basic ' + base64.b64encode(b'x:vbk_not-a-real-key').decode()}
        code, _, headers = self.request_full('/git/acme/launch.git/info/refs?service=git-receive-pack',
                                             headers=basic)
        self.assertEqual(code, 401)
        self.assertEqual(headers['WWW-Authenticate'], 'Basic realm="videobuilder"')

    def test_session_cookie_plus_bad_bearer_key_is_refused(self):
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        code, _ = self.request('/v/acme/launch/api/project',
                               headers={'Cookie': admin, 'Authorization': 'Bearer vbk_notarealkey'})
        self.assertEqual(code, 401)

    def test_note_author_and_directed_by_trailer_show_key_attribution(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.library.editor('acme/launch').notes.backend = FakeBackend(delay=0)
        _, secret = self.library.accounts.create_key('mgalgs', 'claude explainer-videos', None, 'write')
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual((code, note['author']), (200, 'mgalgs (claude explainer-videos)'))
        self.request('/v/acme/launch/api/notes', headers=self.bearer(secret))
        log = self.git('show', '-s', '--format=%B', 'HEAD', cwd=self.library.checkouts / 'acme--launch').stdout
        self.assertIn('Directed-by: mgalgs (claude explainer-videos)', log)


class Tour(AccountMixin, LibraryFixture, unittest.TestCase):
    """The library's first-run tour: shown until the account dismisses it,
    recorded on the server, never for a signed-out visitor."""
    DISMISS = '/api/account/tour/dismiss'

    def dismiss(self, cookie, **headers):
        return self.request(self.DISMISS, {}, headers={'Content-Type': 'application/json', 'Cookie': cookie,
                                                       **headers})

    def test_shown_to_a_new_account_until_dismissed(self):
        cookie = self.signup('dana', 'longenoughpassword')[2]
        code, page = self.request('/', headers={'Cookie': cookie})
        self.assertEqual(code, 200)
        self.assertIn(b'id="tour"', page)
        self.assertIn(b'Start your first video', page)
        self.assertEqual(self.dismiss(cookie), (200, {'tour_seen': True}))
        page = self.request('/', headers={'Cookie': cookie})[1]
        self.assertNotIn(b'id="tour"', page)
        self.assertNotIn(b'id="showcase"', page)
        self.assertNotIn(b'class="howto"', page)
        # Once per account, not per browser: another session of the same account doesn't see it.
        other = self.login('dana', 'longenoughpassword')[2]
        self.assertNotIn(b'id="tour"', self.request('/', headers={'Cookie': other})[1])

    def test_dismissing_is_per_account(self):
        admin = self.admin_login()
        dana = self.signup('dana', 'longenoughpassword')[2]
        self.assertEqual(self.dismiss(admin)[0], 200)
        self.assertNotIn(b'id="tour"', self.request('/', headers={'Cookie': admin})[1])
        self.assertIn(b'id="tour"', self.request('/', headers={'Cookie': dana})[1])

    def test_signed_out_dismiss_is_refused(self):
        self.assertEqual(self.request(self.DISMISS, {})[0], 401)

    def test_cross_origin_dismiss_is_refused(self):
        cookie = self.signup('dana', 'longenoughpassword')[2]
        code, _ = self.dismiss(cookie, Origin='http://elsewhere.example')
        self.assertEqual(code, 403)
        self.assertFalse(self.library.accounts.tour_seen('dana'))
        self.assertEqual(self.request(self.DISMISS, {}, headers={'Content-Type': 'text/plain',
                                                                 'Cookie': cookie})[0], 415)
        self.assertFalse(self.library.accounts.tour_seen('dana'))


class NoAccountsTour(LibraryFixture, unittest.TestCase):
    def test_no_tour_without_accounts(self):
        page = self.request('/')[1]
        self.assertNotIn(b'id="tour"', page)
        self.assertEqual(self.request('/api/account/tour/dismiss', {})[0], 404)


class AccountPage(AccountMixin, KeyMixin, LibraryFixture, unittest.TestCase):
    """The /account page and its key-management routes."""

    def create(self, cookie, label='laptop', scope=None, mode='write'):
        body = {'label': label, 'mode': mode}
        if scope is not None:
            body['scope'] = scope
        return self.request('/api/account/keys', body, headers={'Content-Type': 'application/json', 'Cookie': cookie})

    def test_unauthenticated_get_is_the_signin_page_not_the_account_page(self):
        code, page = self.request('/account')
        self.assertEqual(code, 200)
        self.assertIn(b'Sign in', page)
        self.assertNotIn(b'New key', page)

    def test_library_page_links_to_it(self):
        admin = self.admin_login()
        code, page = self.request('/', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertIn(b'href="/account"', page)

    def test_page_lists_no_keys_then_a_created_one(self):
        admin = self.admin_login()
        code, page = self.request('/account', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertIn(b'No keys yet', page)
        code, record = self.create(admin, label='laptop', scope='gardening', mode='read')
        self.assertEqual(code, 201, record)
        self.assertEqual(record['label'], 'laptop')
        self.assertEqual(record['scope'], 'gardening')
        self.assertEqual(record['mode'], 'read')
        self.assertTrue(record['secret'].startswith('vbk_'))
        code, page = self.request('/account', headers={'Cookie': admin})
        self.assertIn(b'laptop', page)
        self.assertIn(b'gardening', page)
        self.assertNotIn(record['secret'].encode(), page)  # never shown again on reload

    def test_create_validates_label_scope_and_mode(self):
        admin = self.admin_login()
        self.assertEqual(self.create(admin, label='')[0], 400)
        self.assertEqual(self.create(admin, label='has (parens)')[0], 400)
        self.assertEqual(self.create(admin, scope='Not Valid')[0], 400)
        self.assertEqual(self.create(admin, mode='delete')[0], 400)

    def test_revoke_takes_effect_on_the_next_request(self):
        admin = self.admin_login()
        _, record = self.create(admin, label='revoke-me')
        secret = record['secret']
        self.assertEqual(self.request('/api/account/keys/' + record['id'] + '/revoke', {},
                                      headers={'Content-Type': 'application/json', 'Cookie': admin})[0], 200)
        code, page = self.request('/account', headers={'Cookie': admin})
        self.assertIn(b'No keys yet', page)
        self.assertNotIn(b'revoke-me', page)
        self.seed('acme/launch', film=True)
        self.new_project(admin, 'acme/launch', 'acme/launch')
        self.assertEqual(self.request('/v/acme/launch/api/project', headers=self.bearer(secret))[0], 401)

    def test_revoke_unknown_id_404(self):
        admin = self.admin_login()
        code, _ = self.request('/api/account/keys/nosuchid/revoke', {},
                               headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual(code, 404)

    def test_key_refused_on_account_page_and_key_management(self):
        admin = self.admin_login()
        _, record = self.create(admin)
        secret = record['secret']
        code, page = self.request('/account', headers=self.bearer(secret))
        self.assertEqual(code, 200)
        self.assertNotIn(b'New key', page)  # the sign-in page, not the account page
        code, _ = self.request('/api/account/keys', {'label': 'x', 'mode': 'write'},
                               headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 401)
        code, _ = self.request('/api/account/keys/' + record['id'] + '/revoke', {},
                               headers={'Content-Type': 'application/json', **self.bearer(secret)})
        self.assertEqual(code, 401)

    def test_a_deleted_accounts_keys_cannot_be_listed_or_created(self):
        _, _, dana = self.signup('dana', 'longenoughpassword')
        self.create(dana, label='dana-key')
        del self.library.accounts._data['users']['dana']
        self.library.accounts._save()
        code, page = self.request('/account', headers={'Cookie': dana})
        self.assertEqual(code, 200)
        self.assertIn(b'Sign in', page)  # the old session no longer resolves to an account
        self.assertEqual(self.create(dana)[0], 401)

    def test_usage_limits_section_shown_only_to_an_admin(self):
        admin = self.admin_login()
        code, page = self.request('/account', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertIn(b'Usage limits', page)
        _, _, bob = self.signup('bob', 'longenoughpassword')
        code, page = self.request('/account', headers={'Cookie': bob})
        self.assertEqual(code, 200)
        self.assertNotIn(b'Usage limits', page)


class AdminLimits(AccountMixin, KeyMixin, LibraryFixture, unittest.TestCase):
    """GET/POST /api/admin/limits: library-wide defaults, per-account overrides and usage."""

    def test_signed_out_is_401(self):
        self.assertEqual(self.request('/api/admin/limits')[0], 401)
        self.assertEqual(self.request('/api/admin/limits', {'user': 'bob', 'kind': 'unlimited'})[0], 401)

    def test_non_admin_is_403(self):
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.assertEqual(self.request('/api/admin/limits', headers={'Cookie': bob})[0], 403)
        self.assertEqual(self.request('/api/admin/limits', {'user': 'bob', 'kind': 'unlimited'},
                                      headers={'Content-Type': 'application/json', 'Cookie': bob})[0], 403)

    def test_admin_get_lists_defaults_and_every_account_with_usage(self):
        from videobuilder.agents import FakeBackend
        self.seed('acme/launch', film=True)
        admin = self.admin_login()
        self.new_project(admin, 'acme/launch', 'acme/launch')
        _, _, bob = self.signup('bob', 'longenoughpassword')
        self.request('/v/acme/launch/api/access', {'action': 'invite', 'username': 'bob'},
                     headers={'Content-Type': 'application/json', 'Cookie': admin})
        editor = self.library.editor('acme/launch')
        editor.notes.backend = FakeBackend(delay=0, cost_usd=1.5)
        editor.account_daily_note_cap = 10
        code, note = self.request('/v/acme/launch/api/notes', {'video': 'promo/film', 'text': 'Hi'},
                                  headers={'Content-Type': 'application/json', 'Cookie': bob})
        self.assertEqual(code, 200, note)
        self.request('/v/acme/launch/api/notes?video=promo/film', headers={'Cookie': bob})  # force poll
        code, data = self.request('/api/admin/limits', headers={'Cookie': admin})
        self.assertEqual(code, 200)
        self.assertEqual(data['defaults'], {'notes': None, 'cost_usd': None})  # library-wide: unset here
        by_name = {a['name']: a for a in data['accounts']}
        self.assertEqual(by_name['mgalgs']['admin'], True)
        self.assertEqual(by_name['bob']['admin'], False)
        self.assertEqual(by_name['bob']['limit'], {'kind': 'default', 'notes': None, 'cost_usd': None})
        self.assertEqual(by_name['bob']['usage'], {'notes': 1, 'cost_usd': 1.5})

    def test_post_sets_a_custom_limit_and_get_reflects_it(self):
        admin = self.admin_login()
        _, _, bob = self.signup('bob', 'longenoughpassword')
        code, result = self.request('/api/admin/limits', {'user': 'bob', 'kind': 'custom', 'notes': 3,
                                                           'cost_usd': 2.5},
                                    headers={'Content-Type': 'application/json', 'Cookie': admin})
        self.assertEqual((code, result), (200, {'user': 'bob', 'limit': {'kind': 'custom', 'notes': 3,
                                                                          'cost_usd': 2.5}}))
        code, data = self.request('/api/admin/limits', headers={'Cookie': admin})
        by_name = {a['name']: a for a in data['accounts']}
        self.assertEqual(by_name['bob']['limit'], {'kind': 'custom', 'notes': 3, 'cost_usd': 2.5})

    def test_malformed_posts_are_400_not_500(self):
        admin = self.admin_login()
        _, _, bob = self.signup('bob', 'longenoughpassword')
        headers = {'Content-Type': 'application/json', 'Cookie': admin}
        cases = (
            {'user': 'nosuchuser', 'kind': 'unlimited'},
            {'user': 'bob', 'kind': 'bogus'},
            {'user': 'bob'},
            {'user': 'bob', 'kind': 'custom', 'notes': 0},
            {'user': 'bob', 'kind': 'custom', 'notes': -1},
            {'user': 'bob', 'kind': 'custom', 'notes': 'five'},
            {'user': 'bob', 'kind': 'custom', 'cost_usd': -2},
            {'user': 'bob', 'kind': 'default', 'notes': 5},
            {'user': 'bob', 'kind': 'unlimited', 'cost_usd': 5},
            {'user': 123, 'kind': 'unlimited'},
            {'user': 'bob', 'kind': 'custom', 'cost_usd': float('nan')},
            {'user': 'bob', 'kind': 'custom', 'cost_usd': float('inf')},
        )
        for body in cases:
            with self.subTest(body=body):
                code, data = self.request('/api/admin/limits', body, headers=headers)
                self.assertEqual(code, 400, data)
        code, data = self.request('/api/admin/limits', [1, 2, 3], headers=headers)  # not an object
        self.assertEqual(code, 400, data)

    def test_an_api_key_cannot_reach_the_admin_limits_routes(self):
        admin = self.admin_login()
        _, secret = self.library.accounts.create_key('mgalgs', 'writer', None, 'write')
        self.assertEqual(self.request('/api/admin/limits', headers=self.bearer(secret))[0], 401)

    def test_with_no_accounts_system_the_route_is_open_but_empty(self):
        self.library.accounts = None  # as if --admin was never given
        code, data = self.request('/api/admin/limits')
        self.assertEqual((code, data), (200, {'defaults': {'notes': None, 'cost_usd': None}, 'accounts': []}))


if __name__ == '__main__':
    unittest.main()
