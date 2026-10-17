"""The capabilities catalog: every entry has a demo and every demo loads,
draws, and passes the skill's own review check."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from videobuilder import capabilities, load

ROOT = Path(__file__).resolve().parent.parent
DEMOS = ROOT / 'examples' / 'capabilities'
CHECK = ROOT / 'skill' / 'make-a-video' / 'scripts' / 'check.py'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


class Catalog(unittest.TestCase):
    def test_every_entry_has_a_demo_and_every_demo_has_an_entry(self):
        demo_files = {p.name for p in DEMOS.glob('*.py') if not p.name.startswith('_')}
        catalog_files = {os.path.basename(e['demo']) for e in capabilities.entries()}
        self.assertEqual(catalog_files, demo_files)
        for e in capabilities.entries():
            self.assertTrue((ROOT / e['demo']).is_file(), e['demo'])

    def test_ids_are_unique_kebab_case(self):
        seen = set()
        for e in capabilities.entries():
            self.assertRegex(e['id'], r'\A[a-z][a-z0-9]*(-[a-z0-9]+)*\Z')
            self.assertNotIn(e['id'], seen)
            seen.add(e['id'])

    def test_prompts_are_plain_language_not_api_names(self):
        """'What to tell the builder' is spoken by a non-technical director:
        no prompt should read like code (an underscore name, or `vb.`)."""
        for e in capabilities.entries():
            for p in e['prompts']:
                with self.subTest(id=e['id'], prompt=p):
                    self.assertNotIn('_', p)
                    self.assertNotIn('vb.', p)

    def test_every_demo_draws_first_middle_last_frame(self):
        for e in capabilities.entries():
            with self.subTest(id=e['id']):
                film = load(str(ROOT / e['demo']))
                fmt = film.formats[0]
                self.assertGreaterEqual(film.frames, 2)
                for n in (0, film.frames // 2, film.frames - 1):
                    film.frame(n, fmt, scale=0.1)

    def test_every_demo_passes_check(self):
        for e in capabilities.entries():
            with self.subTest(id=e['id']):
                result = subprocess.run([sys.executable, str(CHECK), str(ROOT / e['demo'])],
                                        capture_output=True, text=True, env=ENV)
                self.assertIn('0 failed', result.stdout, result.stdout + result.stderr)


class Families(unittest.TestCase):
    def test_looks_is_one_family_card_holding_every_look(self):
        from videobuilder import looks
        self.assertEqual([f['id'] for f in capabilities.families()], ['looks'])
        family = capabilities.get('looks')
        self.assertIn(family, capabilities.CATALOG)
        self.assertEqual(family['category'], 'Imagery and camera')
        self.assertEqual(family['noun'], ('look', 'looks'))
        self.assertEqual([c['id'] for c in family['children']], [f'look-{n}' for n in looks.names()[:8]])
        for child in family['children']:
            with self.subTest(id=child['id']):
                self.assertNotIn(child, capabilities.CATALOG)      # reached through the family only
                self.assertEqual(child['family'], 'looks')
                self.assertEqual(child['category'], family['category'])
                self.assertIs(capabilities.get(child['id']), child)
                self.assertIn(child['id'], capabilities.ids())
                name = child['id'].removeprefix('look-')
                self.assertEqual(child['title'], looks.get(name).title)
                self.assertTrue(any(f"'{name}'" in api for api in child['apis']))

    def test_entries_lists_each_family_then_its_members(self):
        ids = [e['id'] for e in capabilities.entries()]
        at = ids.index('looks')
        self.assertEqual(ids[at + 1:at + 9], [c['id'] for c in capabilities.get('looks')['children']])
        self.assertEqual(len(ids), len(set(ids)))
        for e in capabilities.CATALOG:
            if e['id'] != 'looks':
                self.assertIsNone(e['family'])

    def test_the_sheet_lists_every_look_by_name(self):
        sheet = capabilities.sheet_markdown()
        self.assertIn('**The looks** (8; ask for any look by name)', sheet)
        for child in capabilities.get('looks')['children']:
            self.assertIn(f"(`{child['id'].removeprefix('look-')}`)", sheet)
            self.assertIn(child['demo'], sheet)


def _data(page):
    return json.loads(re.search(r'<script id="capabilities-data" type="application/json">(.*?)</script>', page,
                                re.S).group(1))


COMMUNITY_LOOK = {'slug': 'c-20260101-abc123', 'id': 'stained-glass', 'family': 'looks',
                  'category': 'Imagery and camera', 'title': 'Stained glass', 'card': 'Lead lines and glowing panes.',
                  'description': 'Panes.', 'prompts': ('a', 'b', 'c'), 'available': True, 'pending_update': False}


class FamilyPage(unittest.TestCase):
    def _page(self, built=(), community=None):
        with tempfile.TemporaryDirectory() as d:
            for id_ in built:
                Path(d, f'{id_}.mp4').write_bytes(b'mp4')
            return capabilities.page_html(d, '0', community=community).decode()

    def test_the_family_is_one_card_with_a_count_and_its_looks_are_not_cards(self):
        page = self._page(built=('looks', 'look-pixel'))
        main = page[page.index('<main>'):page.index('</main>')]
        self.assertEqual(main.count('data-card="looks"'), 1)
        card = main[main.index('data-card="looks"'):]
        card = card[:card.index('</button>')]
        self.assertIn('<span class="count">8 looks</span>', card)
        self.assertIn('/capabilities/looks.jpg', card)
        self.assertIn('aria-label="Looks: 8 looks"', card)
        for child in capabilities.get('looks')['children']:
            self.assertNotIn(f'data-card="{child["id"]}"', main)

    def test_opening_the_family_lists_its_looks_with_their_posters(self):
        page = self._page(built=('look-pixel',))
        panel = page[page.index('data-family-panel="looks"'):]
        panel = panel[:panel.index('</section>')]
        self.assertIn('The 8 looks', panel)
        for child in capabilities.get('looks')['children']:
            self.assertIn(f'data-card="{child["id"]}"', panel)
            self.assertIn(child['title'], panel)
        self.assertIn('<img src="/capabilities/look-pixel.jpg"', panel)
        self.assertEqual(panel.count('clip not built'), 7)

    def test_the_page_data_knows_families_and_members(self):
        data = {e['id']: e for e in _data(self._page(built=('look-melt',)))}
        self.assertEqual(data['looks']['members'], 8)
        self.assertEqual(data['looks']['plural'], 'looks')
        self.assertEqual(data['look-melt']['family'], 'looks')
        self.assertEqual(data['look-melt']['familyTitle'], 'Looks')
        self.assertTrue(data['look-melt']['available'])
        self.assertFalse(data['look-pixel']['available'])
        self.assertNotIn('family', data['eased-entrances'])

    def test_a_published_community_look_sits_inside_the_family_not_the_grid(self):
        community = {'published': [COMMUNITY_LOOK], 'drafts': [], 'can_submit': True, 'is_admin': True,
                     'fetch': False}
        page = self._page(community=community)
        main = page[page.index('<main>'):page.index('</main>')]
        self.assertNotIn('community:c-20260101-abc123', main)
        self.assertIn('<span class="count">9 looks</span>', main)
        panel = page[page.index('data-family-panel="looks"'):]
        panel = panel[:panel.index('</section>')]
        self.assertIn('The 9 looks', panel)
        self.assertIn('data-card="community:c-20260101-abc123"', panel)
        self.assertIn('Community</span>', panel)
        self.assertIn('data-cap-action="reject"', panel)        # an admin can still take it down
        community_data = json.loads(re.search(r'<script id="community-data" type="application/json">(.*?)</script>',
                                              page, re.S).group(1))
        self.assertEqual(community_data[0]['family'], 'looks')

    def test_a_community_capability_with_no_family_stays_in_its_category(self):
        other = dict(COMMUNITY_LOOK, family=None, slug='c-20260101-def456', id='zoom-reveal')
        page = self._page(community={'published': [other], 'drafts': [], 'can_submit': False,
                                     'is_admin': False, 'fetch': False})
        main = page[page.index('<main>'):page.index('</main>')]
        self.assertIn('data-card="community:c-20260101-def456"', main)
        self.assertIn('<span class="count">8 looks</span>', main)

    def test_the_modal_has_a_back_button_and_44px_touch_targets(self):
        page = self._page()
        self.assertIn('id="modal-back"', page)
        self.assertIn('#modal .close{position:absolute;top:10px;right:10px;width:44px;height:44px;', page)
        self.assertRegex(page, r'#modal \.back\{[^}]*min-height:44px')
        self.assertRegex(page, r'\.member\{[^}]*min-height:44px')


if __name__ == '__main__':
    unittest.main()
