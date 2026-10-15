"""Server-rendered HTML in pages.py: the starter catalogue and the inline
scripts' basic syntax (extracted and run through `node --check`, since
there's no build step to catch a typo otherwise)."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from videobuilder import capabilities, pages
from videobuilder.capabilities import CATALOG
from videobuilder.starters import STARTERS


class StarterCatalogue(unittest.TestCase):
    def test_six_starters_with_distinct_ids(self):
        self.assertEqual(len(STARTERS), 6)
        self.assertEqual(len({s['id'] for s in STARTERS}), 6)

    def test_every_starter_poster_is_a_real_capability_id(self):
        ids = {e['id'] for e in CATALOG}
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
        page = pages.index([('acme/launch', True)], False, None, 'example.com').decode()
        self.assertIn('class="starters">', page)
        self.assertNotIn('starters hero', page)

    def test_empty_library_leads_with_the_showcase_when_it_is_built(self):
        page = pages.index([], True, 'dana', 'example.com', showcase=True).decode()
        self.assertIn('id="showcase"', page)
        self.assertLess(page.index('id="showcase"'), page.index('class="starters hero"'))
        self.assertNotIn('autoplay', page)
        self.assertIn(' controls ', page)   # the native controls carry full screen, iPhone included

    def test_showcase_is_absent_once_a_video_exists_or_when_unbuilt(self):
        with_video = pages.index([('acme/launch', True)], False, None, 'example.com', showcase=True).decode()
        self.assertNotIn('id="showcase"', with_video)
        self.assertNotIn('id="showcase"', pages.index([], False, None, 'example.com').decode())

    def test_new_video_page_has_all_six_cards_wired_to_their_prompt(self):
        page = pages.new_video_page(['acme/launch']).decode()
        for s in STARTERS:
            self.assertIn(f'data-id="{s["id"]}"', page)
            self.assertIn(f'/capabilities/{s["poster"]}.jpg', page)
        self.assertIn('id="files-field"', page)
        self.assertIn('id="links-field"', page)

    def test_new_video_page_has_the_order_step_markup_hidden_by_default(self):
        page = pages.new_video_page(['acme/launch']).decode()
        self.assertIn('<div id="order-step" hidden>', page)
        self.assertIn('id="order-list"', page)
        self.assertIn('id="order-others"', page)
        self.assertIn('id="order-start"', page)


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
        self._check(pages.index([('acme/launch', True)], True, 'dana', 'example.com'))
        self._check(pages.index([], True, 'dana', 'example.com', showcase=True))

    def test_new_video_page_scripts_parse(self):
        self._check(pages.new_video_page(['acme/launch']))

    def test_account_page_scripts_parse(self):
        self._check(pages.account_page('dana', []))

    def test_capabilities_page_scripts_parse(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'showcase-16x9.mp4').write_bytes(b'mp4')
            self._check(capabilities.page_html(d, '0'))

    def test_account_page_with_limits_scripts_parse(self):
        limits = {'defaults': {'notes': 20, 'cost_usd': None},
                  'accounts': [{'name': 'dana', 'admin': True,
                               'limit': {'kind': 'custom', 'notes': 5, 'cost_usd': 1.5},
                               'usage': {'notes': 2, 'cost_usd': 0.3}}]}
        self._check(pages.account_page('dana', [], limits))

    def test_signin_and_signup_pages_scripts_parse(self):
        self._check(pages.signin_page())
        self._check(pages.signup_page())
