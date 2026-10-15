"""Server-rendered HTML in pages.py: the starter catalogue and the inline
scripts' basic syntax (extracted and run through `node --check`, since
there's no build step to catch a typo otherwise)."""
import re
import shutil
import subprocess
import unittest

from videobuilder import pages
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

    def test_new_video_page_has_all_six_cards_wired_to_their_prompt(self):
        page = pages.new_video_page(['acme/launch']).decode()
        for s in STARTERS:
            self.assertIn(f'data-id="{s["id"]}"', page)
            self.assertIn(f'/capabilities/{s["poster"]}.jpg', page)
        self.assertIn('id="files-field"', page)
        self.assertIn('id="links-field"', page)


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

    def test_new_video_page_scripts_parse(self):
        self._check(pages.new_video_page(['acme/launch']))

    def test_account_page_scripts_parse(self):
        self._check(pages.account_page('dana', []))

    def test_signin_and_signup_pages_scripts_parse(self):
        self._check(pages.signin_page())
        self._check(pages.signup_page())
