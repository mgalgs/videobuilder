"""Server-rendered HTML in pages.py: the starter catalogue and the inline
scripts' basic syntax (extracted and run through `node --check`, since
there's no build step to catch a typo otherwise)."""
from importlib import resources
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
        self.assertIn('id="files-field"', page)
        self.assertIn('id="links-field"', page)

    def test_new_video_page_has_the_order_step_markup_hidden_by_default(self):
        page = pages.new_video_page(['acme/launch']).decode()
        self.assertIn('<div id="order-step" hidden>', page)
        self.assertIn('id="order-list"', page)
        self.assertIn('id="order-others"', page)
        self.assertIn('id="order-start"', page)


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


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class InlineScriptsParse(unittest.TestCase):
    def _check(self, html_bytes):
        scripts = re.findall(rb'<script(?: [^>]*)?>(.*?)</script>', html_bytes, re.S)
        self.assertTrue(scripts)
        for script in scripts:
            if not script.strip():
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
