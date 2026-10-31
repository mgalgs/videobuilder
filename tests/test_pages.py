"""Server-rendered HTML in pages.py: the starter catalogue and the inline
scripts' basic syntax (extracted and run through `node --check`, since
there's no build step to catch a typo otherwise)."""
from importlib import resources
import html
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from videobuilder import capabilities, pages
from videobuilder.starters import STARTERS


def _entry(name, has_main=True, updated=None, subject=None):
    return {'name': name, 'has_main': has_main, 'updated': updated, 'subject': subject}


class StarterCatalogue(unittest.TestCase):
    def test_six_starters_with_distinct_ids(self):
        self.assertEqual(len(STARTERS), 6)
        self.assertEqual(len({s['id'] for s in STARTERS}), 6)

    def test_every_starter_poster_is_a_real_capability_id(self):
        ids = set(capabilities.ids())     # a family's members too (paper-collage is a look): each has its poster
        for s in STARTERS:
            self.assertIn(s['poster'], ids, s['id'])

    def test_every_starter_needs_is_a_known_field(self):
        for s in STARTERS:
            self.assertIn(s['needs'], ('files', 'links', 'none'), s['id'])


class StarterCardsOnPages(unittest.TestCase):
    def test_library_page_is_a_hero_when_the_creator_has_no_videos(self):
        page = pages.index([], False, None, 'example.com').decode()
        self.assertIn('class="starters hero"', page)
        for s in STARTERS:
            self.assertIn(s['title'], page)

    def test_library_page_is_a_compact_row_once_a_video_exists(self):
        page = pages.index([_entry('acme/launch')], False, None, 'example.com').decode()
        self.assertIn('class="starters">', page)
        self.assertNotIn('starters hero', page)

    def test_the_tour_leads_with_the_showcase_then_the_howto_then_one_button(self):
        page = pages.index([], True, 'dana', 'example.com', showcase=True, tour=True).decode()
        tour = page[page.index('id="tour"'):]
        self.assertLess(tour.index('id="showcase"'), tour.index('class="howto"'))
        self.assertLess(tour.index('class="howto"'), tour.index('Start your first video'))
        self.assertIn('id="tour-start" href="/new"', tour)
        self.assertIn('/api/account/tour/dismiss', tour)
        self.assertNotIn('autoplay', page)
        self.assertIn(' controls ', page)   # the native controls carry full screen, iPhone included

    def test_the_tour_shows_without_the_reel_when_it_is_not_built(self):
        page = pages.index([], True, 'dana', 'example.com', showcase=False, tour=True).decode()
        self.assertIn('id="tour"', page)
        self.assertIn('class="howto"', page)
        self.assertIn('Start your first video', page)
        self.assertNotIn('id="showcase"', page)

    def test_the_library_itself_carries_neither_the_reel_nor_the_howto(self):
        for entries in ([], [_entry('acme/launch')]):
            for accounts in (True, False):
                page = pages.index(entries, accounts, 'dana' if accounts else None, 'example.com',
                                   showcase=True).decode()
                self.assertNotIn('id="tour"', page)
                self.assertNotIn('id="showcase"', page)
                self.assertNotIn('class="howto"', page)

    def test_every_new_key_block_has_a_copy_button(self):
        page = pages.account_page('dana', []).decode()
        for target in ('secret-value', 'git-clone', 'git-cred', 'api-header'):
            self.assertIn(f'id="{target}"', page)
            self.assertIn(f'data-copy="{target}"', page)
        self.assertNotIn('.panel code,', page)   # inline <code> in a sentence must stay inline

    def test_library_cards_put_the_prompt_above_the_poster_and_the_name_last(self):
        page = pages.index([], False, None, 'example.com').decode()
        s = STARTERS[0]
        card = page[page.index(f'href="/new?starter={s["id"]}"'):]
        self.assertLess(card.index('class="starter-prompt"'), card.index('class="starter-poster"'))
        self.assertLess(card.index('class="starter-poster"'), card.index('class="starter-title"'))

    def test_new_video_page_has_no_cards_but_knows_every_starter_prompt(self):
        page = pages.new_video_page(['acme/launch']).decode()
        self.assertNotIn('starter-card', page)
        for s in STARTERS:
            self.assertIn(json.dumps(s['id']) + ':', page)


class NewVideoPage(unittest.TestCase):
    """New video is one small form: a name, an optional project and Create.
    The first note, and everything else, happens in the editor."""

    def _page(self, names=('acme/launch', 'acme/teaser', 'solo', 'zeta/one', 'capabilities/demo')):
        return pages.new_video_page(list(names)).decode()

    def test_the_form_has_a_name_files_an_idea_a_mode_switch_a_format_and_create(self):
        page = self._page()
        form = re.search(r'<form class="nv-form" id="nv-form" novalidate>(.*?)</form>', page, re.S).group(1)
        self.assertEqual(re.findall(r'<(input|select|textarea|button)\b[^>]*\bid="([^"]+)"', form),
                         [('input', 'name'), ('button', 'suggest-name'), ('select', 'project'),
                          ('input', 'new-project'), ('button', 'add-files'), ('input', 'file-input'),
                          ('textarea', 'idea'), ('button', 'idea-attach'), ('select', 'format'),
                          ('button', 'mode-plan'), ('button', 'mode-build'), ('button', 'go')])
        self.assertIn('>Create</button>', form)
        self.assertIn('Project <i>(optional)</i>', form)
        self.assertIn('Everything below is optional', form)
        main = re.search(r'<main class="nv">(.*?)</main>', page, re.S).group(1)
        for gone in ('class="ways"', 'id="parts"', 'copy-from', 'nv-pick', 'Look', 'Characters', 'Start building'):
            self.assertNotIn(gone, main)
        self.assertNotIn('suggest.js', page)
        self.assertNotIn('sg-chips', page)

    def test_suggest_name_button_is_present_but_starts_hidden(self):
        page = self._page()
        self.assertIn('id="suggest-name" hidden>Suggest</button>', page)

    def test_file_input_accepts_every_attachment_type(self):
        page = self._page()
        m = re.search(r'<input type="file" id="file-input" multiple hidden accept="([^"]+)">', page)
        self.assertIsNotNone(m)
        accept = html.unescape(m.group(1)).split(',')
        self.assertIn('image/png', accept)
        self.assertIn('.pdf', accept)
        self.assertNotIn('.zip', accept)

    def test_the_project_dropdown_starts_on_no_project(self):
        select = re.search(r'<select id="project">(.*?)</select>', self._page()).group(1)
        options = re.findall(r'<option value="([^"]*)"( selected)?>([^<]*)</option>', select)
        self.assertEqual([(v, label) for v, _, label in options],
                         [('', 'No project'), ('acme', 'acme'), ('zeta', 'zeta'), ('+new', '+ New project…')])
        self.assertEqual([v for v, sel, _ in options if sel], [''])
        self.assertEqual(pages.new_video_projects([]), [])


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class NewVideoCreate(unittest.TestCase):
    """new_video.js run under node against a small stand-in for the page:
    the create flow (a bare name, unchanged; plus idea/files/plan/format),
    and the Suggest-a-name button."""

    HARNESS = """
const els={};
function el(id,value=''){const e={id,value,hidden:false,disabled:false,textContent:'',innerHTML:'',
  options:[],listeners:{},attrs:{},dataset:{},classes:new Set(),
  classList:{toggle(c,on){on?e.classes.add(c):e.classes.delete(c)}},
  addEventListener(t,f){(this.listeners[t]??=[]).push(f)},
  setAttribute(n,v){this.attrs[n]=String(v)},getAttribute(n){return this.attrs[n]},focus(){}};
  els[id]=e;return e}
['go','name-error','nv-form','go-note','drop','files','file-input','file-count','add-files','idea-attach',
 'why','mode-plan','mode-build','sugg-plan','sugg-build','suggest-name','page-drop'].forEach(id=>el(id));
el('nv-data').textContent=JSON.stringify({starters:{explainer:'A [topic] explainer.'}});
el('name',__NAME__);el('new-project',__NEWPROJECT__);el('idea',__IDEA__);el('format',__FORMAT__);
const project=el('project',__PROJECT__);
const session=new Map();
globalThis.sessionStorage={getItem:k=>session.get(k)??null,setItem:(k,v)=>session.set(k,v)};
globalThis.document={getElementById:id=>els[id],querySelector:s=>els[s.slice(1)]};
globalThis.location={search:__QUERY__,href:''};
const calls=[];
function routeFetch(url){
  if(url==='/api/suggest/config')return{ok:true,json:async()=>(__SUGGEST_CONFIG__)};
  if(url==='/api/videos/mode')return{ok:true,json:async()=>(__MODE_ANSWER__)};
  if(url==='/api/videos/suggest-name')return{ok:true,json:async()=>(__SUGGEST_NAME_ANSWER__)};
  if(url==='/api/videos/new')return __FAIL__?{ok:false,json:async()=>({error:'that name is taken'})}
    :{ok:true,json:async()=>({video:'film'})};
  return{ok:true,json:async()=>({})};
}
globalThis.fetch=async(url,init)=>{
  const body=init&&init.body?JSON.parse(init.body):undefined;
  if(url==='/api/videos/new'||url==='/api/videos/suggest-name')calls.push([url,body]);
  return routeFetch(url,body);
};
globalThis.xhrs=[];
class FakeXHR{
  constructor(){this.upload={};globalThis.xhrs.push(this)}
  open(m,u){this.method=m;this.url=u}
  setRequestHeader(){}
  send(body){this.sentBody=body}
  abort(){this.aborted=true}
}
globalThis.XMLHttpRequest=FakeXHR;
"""

    def run_page(self, name='a', project='', new_project='', query='', fail=False, idea='', fmt='',
                suggest_config=None, mode_answer=None, suggest_name_answer=None, before_submit='', submit=True):
        script = (resources.files('videobuilder') / 'new_video.js').read_text()
        harness = self.HARNESS
        tokens = {
            '__NEWPROJECT__': new_project, '__NAME__': name, '__PROJECT__': project, '__QUERY__': query,
            '__FAIL__': fail, '__IDEA__': idea, '__FORMAT__': fmt,
            '__SUGGEST_CONFIG__': suggest_config if suggest_config is not None else {'model': False},
            '__MODE_ANSWER__': mode_answer if mode_answer is not None else
                {'plan': False, 'why': 'empty', 'reason': "There's nothing to go on yet."},
            '__SUGGEST_NAME_ANSWER__': suggest_name_answer if suggest_name_answer is not None else {'name': None},
        }
        for k, v in tokens.items():
            harness = harness.replace(k, json.dumps(v))
        submit_js = (
            "for(const f of els['nv-form'].listeners.submit)await f({preventDefault(){}});"
            if submit else '')
        run = f"""
(async()=>{{
  {before_submit}
  {submit_js}
  await new Promise(r=>setTimeout(r,0));
  console.log(JSON.stringify({{calls,href:location.href,session:Object.fromEntries(session),
    error:els['name-error'].textContent,name:els['name'].value,why:els['why'].innerHTML,
    goText:els['go'].textContent,
    modePlan:els['mode-plan'].attrs['aria-checked'],modeBuild:els['mode-build'].attrs['aria-checked'],
    suggestHidden:els['suggest-name'].hidden,suggestDisabled:els['suggest-name'].disabled}}));
}})();
"""
        result = subprocess.run(['node', '-'], input=(harness + script + run).encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_create_makes_a_blank_video_with_no_project_and_opens_the_editor(self):
        out = self.run_page('Snow Day')
        self.assertEqual(out['calls'], [['/api/videos/new', {'name': 'snow-day', 'start': 'blank'}]])
        self.assertEqual(out['href'], '/v/snow-day/')
        self.assertEqual(out['session'], {})

    def test_a_project_goes_in_front_of_the_name(self):
        self.assertEqual(self.run_page('a', project='zeta')['calls'][0][1]['name'], 'zeta/a')
        self.assertEqual(self.run_page('a', project='+new', new_project='My Shorts')['calls'][0][1]['name'],
                         'my-shorts/a')

    def test_a_starter_prompt_is_left_for_the_editor_note_box(self):
        out = self.run_page('a', query='?starter=explainer')
        self.assertEqual(len(out['calls']), 1)
        self.assertEqual(out['session'], {'vb-draft:/v/a/': 'A [topic] explainer.'})

    def test_a_refused_name_stays_on_the_page_and_says_why(self):
        out = self.run_page('a', fail=True)
        self.assertEqual(out['href'], '')
        self.assertEqual(out['error'], 'that name is taken')

    def test_an_idea_alone_rides_along_as_the_prompt(self):
        out = self.run_page('a', idea='A storm film.')
        self.assertEqual(out['calls'], [['/api/videos/new', {'name': 'a', 'start': 'blank', 'prompt': 'A storm film.'}]])

    def test_a_picked_format_is_included(self):
        out = self.run_page('a', fmt='9x16')
        self.assertEqual(out['calls'][0][1]['format'], '9x16')

    def test_accepting_the_suggested_plan_omits_plan_and_lets_the_server_decide(self):
        out = self.run_page('a', idea='A screenplay with three characters.',
                            mode_answer={'plan': True, 'why': 'story', 'reason': 'Reads like a story.'})
        self.assertNotIn('plan', out['calls'][0][1])
        self.assertEqual(out['modePlan'], 'true')
        self.assertIn('Reads like a story.', out['why'])

    def test_flipping_the_mode_sends_plan_explicitly(self):
        out = self.run_page(
            'a', idea='A screenplay with three characters.',
            mode_answer={'plan': True, 'why': 'story', 'reason': 'Reads like a story.'},
            before_submit="for(const f of els['mode-build'].listeners.click)await f({});"
                          "await new Promise(r=>setTimeout(r,0));")
        self.assertEqual(out['calls'][0][1]['plan'], False)
        self.assertEqual(out['modeBuild'], 'true')
        self.assertIn('Switch back', out['why'])

    def test_a_staged_file_rides_along_as_an_attachment(self):
        out = self.run_page('a', before_submit="""
els['file-input'].value='pic.png';
for(const f of els['file-input'].listeners.change)
  await f({target:{files:[{name:'pic.png',type:'image/png',size:3}],value:''}});
xhrs[0].status=201;xhrs[0].responseText=JSON.stringify({id:'abc123',name:'pic.png',type:'image/png',size:3});
xhrs[0].onload();
await new Promise(r=>setTimeout(r,0));
""")
        self.assertEqual(out['calls'], [['/api/videos/new', {'name': 'a', 'start': 'blank',
                                                              'attachments': ['abc123']}]])

    def test_files_an_idea_and_a_flip_to_plan_all_ride_along(self):
        out = self.run_page('a', idea='A quick reel.', fmt='1x1',
                            mode_answer={'plan': False, 'why': 'short-idea', 'reason': 'A quick idea.'},
                            before_submit="""
for(const f of els['file-input'].listeners.change)
  await f({target:{files:[{name:'pic.png',type:'image/png',size:3},{name:'song.mp3',type:'audio/mpeg',size:9}],
           value:''}});
xhrs.forEach((x,i)=>{x.status=201;x.responseText=JSON.stringify({id:'id'+i});x.onload()});
for(const f of els['mode-plan'].listeners.click)await f({});
await new Promise(r=>setTimeout(r,0));
""")
        self.assertEqual(out['calls'], [['/api/videos/new', {
            'name': 'a', 'start': 'blank', 'prompt': 'A quick reel.', 'attachments': ['id0', 'id1'],
            'format': '1x1', 'plan': True}]])
        self.assertEqual(out['goText'], 'Creating…')
        self.assertEqual(out['href'], '/v/a/')

    def test_the_why_line_names_the_suggestion_and_is_neutral_with_nothing_to_go_on(self):
        out = self.run_page('a', idea='A screenplay.', submit=False,
                            mode_answer={'plan': True, 'why': 'story', 'reason': 'Reads like a story.'},
                            before_submit='await new Promise(r=>setTimeout(r,0));')
        self.assertIn('Suggested <b>Plan it first</b>: Reads like a story.', out['why'])
        out = self.run_page('a', submit=False, before_submit='await new Promise(r=>setTimeout(r,0));')
        self.assertIn('the builder suggests one', out['why'])

    def test_submit_is_refused_while_a_file_is_still_uploading(self):
        out = self.run_page('a', before_submit="""
for(const f of els['file-input'].listeners.change)
  await f({target:{files:[{name:'pic.png',type:'image/png',size:3}],value:''}});
""")
        self.assertEqual(out['calls'], [])
        self.assertIn('finish uploading', out['error'])

    def test_suggest_name_button_is_hidden_without_a_model(self):
        out = self.run_page('a', submit=False)
        self.assertEqual(out['suggestHidden'], True)

    def test_suggest_name_button_fills_in_a_slugified_name(self):
        out = self.run_page('a', idea='A lighthouse keeper riding out a storm.',
                            suggest_config={'model': True}, suggest_name_answer={'name': 'Lighthouse Storm'},
                            submit=False,
                            before_submit="await new Promise(r=>setTimeout(r,0));"
                                         "for(const f of els['suggest-name'].listeners.click)await f({});"
                                         "await new Promise(r=>setTimeout(r,0));")
        self.assertEqual(out['name'], 'lighthouse-storm')
        self.assertEqual(out['calls'], [['/api/videos/suggest-name',
                                         {'idea': 'A lighthouse keeper riding out a storm.', 'attachments': []}]])

    def test_the_editor_reads_the_same_draft_key(self):
        js = (resources.files('videobuilder') / 'director.js').read_text()
        self.assertIn("const DRAFT='vb-draft:';", js)
        self.assertIn("sessionStorage.getItem(DRAFT+location.pathname)", js)


class LibrarySort(unittest.TestCase):
    ENTRIES = [_entry('acme/launch', updated=100), _entry('acme/teaser', updated=300),
               _entry('solo', updated=200), _entry('acme/blank', has_main=False)]

    def _page(self, entries=None):
        return pages.index(entries or self.ENTRIES, True, 'dana', 'example.com').decode()

    def test_recent_is_the_default_newest_first_with_unstarted_videos_last(self):
        page = self._page()
        recent = page[page.index('id="lib-recent"'):page.index('id="lib-projects"')]
        titles = re.findall(r'class="lib-title">([^<]*)<', recent)
        self.assertEqual(titles, ['teaser', 'solo', 'launch', 'blank'])
        self.assertIn('<div id="lib-projects" hidden>', page)
        self.assertIn('data-sort="recent" aria-pressed="true"', page)

    def test_recent_cards_carry_their_project_as_a_pill_and_project_view_does_not(self):
        page = self._page()
        recent = page[page.index('id="lib-recent"'):page.index('id="lib-projects"')]
        projects = page[page.index('id="lib-projects"'):]
        self.assertEqual(recent.count('class="lib-pill">acme<'), 3)
        self.assertNotIn('lib-pill', projects)
        self.assertIn('class="lib-group">acme<', projects)

    def test_no_switch_when_no_video_is_in_a_project(self):
        page = self._page([_entry('solo', updated=1), _entry('other', updated=2)])
        self.assertNotIn('lib-sort"', page)
        self.assertNotIn('lib-projects', page)
        self.assertNotIn('lib-pill"', page)


class AccountPageLimits(unittest.TestCase):
    def test_no_limits_section_by_default(self):
        page = pages.account_page('dana', []).decode()
        self.assertNotIn('Usage limits', page)

    def test_limits_section_shows_defaults_and_each_account(self):
        limits = {'defaults': {'notes': 20, 'cost_usd': None},
                  'accounts': [{'name': 'bob', 'admin': False,
                               'limit': {'kind': 'custom', 'notes': 5, 'cost_usd': 1.5},
                               'usage': {'notes': 2, 'cost_usd': 0.3}}]}
        page = pages.account_page('dana', [], limits).decode()
        self.assertIn('Usage limits', page)
        self.assertIn('20 notes/day', page)
        self.assertIn('No cap', page)  # cost_usd default unset
        self.assertIn('data-user="bob"', page)
        self.assertIn('selected', page)  # the custom option is pre-selected
        self.assertIn('value="5"', page)
        self.assertIn('value="1.5"', page)


class EditorPageHeader(unittest.TestCase):
    def test_library_editor_page_carries_the_shared_header(self):
        page = pages.editor_page('<dana>').decode()
        self.assertIn('<body class="has-app-bar">', page)
        self.assertIn('<div id="app"><div class="desktop-only app-bar-wrap"><header class="app-bar">', page)
        self.assertIn('.app-bar{', page)
        self.assertIn('Signed in as <strong>&lt;dana&gt;</strong>', page)
        self.assertIn('href="/new"', page)
        # The editor's own topbar stays, for the title row and for phones.
        self.assertIn('id="library-link"', page)

    def test_no_new_video_button_without_create_rights(self):
        self.assertNotIn('href="/new"', pages.editor_page('dana', can_create=False).decode())

    def test_whats_new_link_only_when_there_are_entries(self):
        self.assertIn('data-whats-new="2026-10-19 sfx"',
                      pages.editor_page('dana', whats_new='2026-10-19 sfx').decode())
        self.assertNotIn('href="/whats-new"', pages.editor_page('dana').decode())


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class InlineScriptsParse(unittest.TestCase):
    def _check(self, html_bytes):
        scripts = re.findall(rb'<script( [^>]*)?>(.*?)</script>', html_bytes, re.S)
        self.assertTrue(scripts)
        for attrs, script in scripts:
            if not script.strip():
                continue
            if b'application/json' in (attrs or b''):
                json.loads(script)  # a data block, not a script
                continue
            result = subprocess.run(['node', '--check', '-'], input=script, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_index_page_scripts_parse(self):
        self._check(pages.index([_entry('acme/launch')], True, 'dana', 'example.com'))
        self._check(pages.index([], True, 'dana', 'example.com', showcase=True))
        self._check(pages.index([], True, 'dana', 'example.com', showcase=True, tour=True))

    def test_new_video_page_scripts_parse(self):
        self._check(pages.new_video_page(['acme/launch']))

    def test_account_page_scripts_parse(self):
        self._check(pages.account_page('dana', []))

    def test_whats_new_page_scripts_parse(self):
        entry = {'id': '2026-10-18', 'kind': 'local', 'title': 'T', 'headline': '', 'date': '2026-10-18',
                 'versions': '1', 'notes': 'n', 'videos': ['9x16'], 'key': '2026-10-18 2026-10-18'}
        self._check(pages.whats_new_page([entry], 'dana', is_admin=True, max_bytes=1048576, today='2026-10-18'))
        self._check(pages.whats_new_page([]))

    def test_capabilities_page_with_community_scripts_parse(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'showcase-16x9.mp4').write_bytes(b'mp4')
            community = {'published': [], 'drafts': [], 'can_submit': True, 'is_admin': True, 'fetch': True}
            self._check(capabilities.page_html(d, '0', pages.app_header('capabilities', 'dana'),
                                               pages.APP_HEADER_STYLE, community=community))
            community['fetch'] = False
            self._check(capabilities.page_html(d, '0', pages.app_header('capabilities', 'dana'),
                                               pages.APP_HEADER_STYLE, community=community))

    def test_capabilities_page_scripts_parse(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'showcase-16x9.mp4').write_bytes(b'mp4')
            self._check(capabilities.page_html(d, '0'))
            self._check(capabilities.page_html(d, '0', pages.app_header('capabilities', 'dana'),
                                               pages.APP_HEADER_STYLE))

    def test_account_page_with_limits_scripts_parse(self):
        limits = {'defaults': {'notes': 20, 'cost_usd': None},
                  'accounts': [{'name': 'dana', 'admin': True,
                               'limit': {'kind': 'custom', 'notes': 5, 'cost_usd': 1.5},
                               'usage': {'notes': 2, 'cost_usd': 0.3}}]}
        self._check(pages.account_page('dana', [], limits))

    def test_signin_and_signup_pages_scripts_parse(self):
        self._check(pages.signin_page())
        self._check(pages.signup_page())

    def test_library_editor_page_scripts_parse(self):
        self._check(pages.editor_page('dana'))

    def test_editor_page_director_js_parses(self):
        # editor.html's own JS is all in director.js (a <script src>, not inline): checked as
        # a whole file, which also covers the Sources panel's upload/list/player wiring.
        script = resources.files('videobuilder').joinpath('director.js').read_bytes()
        result = subprocess.run(['node', '--check', '-'], input=script, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
