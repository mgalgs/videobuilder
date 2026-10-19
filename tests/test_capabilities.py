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

from videobuilder import capabilities, load, load_module

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
    def test_looks_is_a_family_with_a_category_of_its_own(self):
        from videobuilder import looks
        self.assertEqual([f['id'] for f in capabilities.families()], ['looks', 'type'])
        family = capabilities.get('looks')
        self.assertIn(family, capabilities.CATALOG)
        self.assertEqual(family['category'], 'Looks')
        self.assertEqual([e['id'] for e in capabilities.CATALOG if e['category'] == 'Looks'], ['looks'])
        self.assertEqual(capabilities.categories().index('Looks'), capabilities.categories().index('Imagery and camera') + 1)
        self.assertEqual(family['noun'], ('look', 'looks'))
        ids = [c['id'] for c in family['children']]
        self.assertEqual(ids[:8], [f'look-{n}' for n in looks.names()[:8]])
        self.assertIn('paper-collage', ids)
        self.assertEqual([i for i in ids if i.startswith('look-filter-')], [f'look-filter-{n}' for n in looks.filters()[:5]])
        for child in family['children']:
            with self.subTest(id=child['id']):
                self.assertNotIn(child, capabilities.CATALOG)      # reached through the family only
                self.assertEqual(child['family'], 'looks')
                self.assertEqual(child['category'], 'Looks')
                self.assertIs(capabilities.get(child['id']), child)
                self.assertIn(child['id'], capabilities.ids())
                self.assertIn(child['kind'], ('scene', 'filter'))
                if child['look'] is None:
                    continue
                if child['kind'] == 'scene':
                    self.assertEqual(child['title'], looks.get(child['look']).title)
                    self.assertTrue(any(f"looks.paint(cv, '{child['look']}'" in api for api in child['apis']))
                else:
                    self.assertEqual(child['title'], looks.get_filter(child['look']).title)
                    self.assertTrue(any(f"looks.filter(cv, '{child['look']}'" in api for api in child['apis']))

    def test_type_is_a_family_one_card_per_style(self):
        from videobuilder import type as vt
        family = capabilities.get('type')
        self.assertIn(family, capabilities.CATALOG)
        self.assertEqual(family['category'], 'Type')
        self.assertEqual([e['id'] for e in capabilities.CATALOG if e['category'] == 'Type'], ['type'])
        self.assertEqual(capabilities.categories().index('Type'), capabilities.categories().index('Looks') + 1)
        self.assertEqual(family['noun'], ('type style', 'type styles'))
        self.assertEqual((family['lead'], family['kinds']), ('A few type styles', None))
        self.assertEqual(family['member']['file'], 'style.py')
        self.assertEqual([c['id'] for c in family['children']], [f'type-{n}' for n in vt.names()])
        for child in family['children']:
            with self.subTest(id=child['id']):
                self.assertNotIn(child, capabilities.CATALOG)
                self.assertEqual((child['family'], child['category']), ('type', 'Type'))
                self.assertEqual(child['title'], vt.get(child['style']).title)
                self.assertEqual(child['doc'], 'skill/make-a-video/reference/type.md')
                self.assertEqual(child['demo'], f"examples/capabilities/type-{child['style']}.py")
                self.assertTrue(any(f"vb.type.draw(cv, '{child['style']}'" in api for api in child['apis']))
                self.assertEqual(len(child['prompts']), 3)

    def test_every_type_demo_takes_the_same_props(self):
        props = set()
        for child in capabilities.get('type')['children']:
            film = load(str(ROOT / child['demo']))
            self.assertEqual(film.formats[0].name, 'cap')
            props.add(load_module(str(ROOT / child['demo']))._type.PROPS)
        self.assertEqual(len(props), 1)

    def test_entries_lists_each_family_then_its_members(self):
        ids = [e['id'] for e in capabilities.entries()]
        at = ids.index('looks')
        children = capabilities.get('looks')['children']
        self.assertEqual(ids[at + 1:at + 1 + len(children)], [c['id'] for c in children])
        self.assertEqual(len(ids), len(set(ids)))
        for e in capabilities.CATALOG:
            self.assertIsNone(e['family'])

    def test_the_sheet_lists_every_look_by_name_in_its_kind(self):
        sheet = capabilities.sheet_markdown()
        looks_part = sheet[sheet.index('## Looks'):]
        looks_part = looks_part[:looks_part.index('\n## ', 3)]
        self.assertIn('**The looks** (14; ask for any look by name)', looks_part)
        scene, filters = looks_part.index('*Scene looks*'), looks_part.index('*Filter looks*')
        for child in capabilities.get('looks')['children']:
            line = looks_part[looks_part.index(f"- **{child['title']}** (`{child['look'] or child['id']}`)"):]
            self.assertIn(child['demo'], line[:line.index('\n')])
            self.assertEqual(looks_part.index(line[:40]) > filters, child['kind'] == 'filter')
            self.assertGreater(looks_part.index(line[:40]), scene)
        self.assertIn('`comic-halftone` is the **Pop-art filter**', looks_part)
        self.assertIn('`pixel-art-layer` is the **8-bit pixel filter**', looks_part)

    def test_the_merged_entries_document_both_apis(self):
        self.assertTrue(any('halftone_pattern' in a for a in capabilities.get('look-filter-pop-art')['apis']))
        self.assertTrue(any('cv.pixelated' in a for a in capabilities.get('look-filter-pixel')['apis']))


class OldIds(unittest.TestCase):
    """Entries merged away keep their old ids, answered by the entry that took them over."""

    def test_an_old_id_resolves_to_the_entry_it_was_merged_into(self):
        self.assertEqual(capabilities.resolve('comic-halftone'), 'look-filter-pop-art')
        self.assertEqual(capabilities.resolve('pixel-art-layer'), 'look-filter-pixel')
        self.assertEqual(capabilities.resolve('paper-collage'), 'paper-collage')
        self.assertIs(capabilities.get('comic-halftone'), capabilities.get('look-filter-pop-art'))
        self.assertIs(capabilities.get('pixel-art-layer'), capabilities.get('look-filter-pixel'))
        with self.assertRaises(KeyError):
            capabilities.resolve('never-was')

    def test_an_old_id_is_not_an_entry_of_its_own(self):
        for old in capabilities.ALIASES:
            self.assertNotIn(old, capabilities.ids())
            self.assertFalse((ROOT / 'examples' / 'capabilities' / f'{old}.py').exists())

    def test_an_old_ids_clip_is_the_new_entrys(self):
        self.assertEqual(capabilities.clip_file('/c', 'comic-halftone', 'mp4'), '/c/look-filter-pop-art.mp4')
        self.assertEqual(capabilities.clip_file('/c', 'pixel-art-layer', 'jpg'), '/c/look-filter-pixel.jpg')
        self.assertIsNone(capabilities.clip_file('/c', 'never-was', 'mp4'))


def _data(page):
    return json.loads(re.search(r'<script id="capabilities-data" type="application/json">(.*?)</script>', page,
                                re.S).group(1))


COMMUNITY_LOOK = {'slug': 'c-20260101-abc123', 'id': 'stained-glass', 'family': 'looks',
                  'category': 'Looks', 'title': 'Stained glass', 'card': 'Lead lines and glowing panes.',
                  'description': 'Panes.', 'prompts': ('a', 'b', 'c'), 'available': True, 'pending_update': False}


def _section(page, heading):
    main = page[page.index('<main>'):page.index('</main>')]
    part = main[main.index(f'<h2>{heading}</h2>'):]
    end = part.find('<h2>', 4)
    return part if end < 0 else part[:end]


class LooksSection(unittest.TestCase):
    def _page(self, built=(), community=None):
        with tempfile.TemporaryDirectory() as d:
            for id_ in built:
                Path(d, f'{id_}.mp4').write_bytes(b'mp4')
            return capabilities.page_html(d, '0', community=community).decode()

    def test_looks_is_a_section_of_cards_grouped_by_kind(self):
        page = self._page(built=('looks', 'look-pixel'))
        section = _section(page, 'Looks')
        self.assertIn('<span class="count">14 looks</span>', section)
        self.assertIn('data-card="looks"', section)
        self.assertIn('<strong>Try a few looks</strong>', section)
        scene, filters = section.index('data-kind="scene"'), section.index('data-kind="filter"')
        for child in capabilities.get('looks')['children']:
            at = section.index(f'data-card="{child["id"]}"')
            self.assertEqual(at > filters, child['kind'] == 'filter', child['id'])
            self.assertGreater(at, scene)
        self.assertIn('<img src="/capabilities/look-pixel.jpg"', section)
        self.assertNotIn('data-card="comic-halftone"', page)
        self.assertNotIn('data-card="pixel-art-layer"', page)
        imagery = _section(page, 'Imagery and camera')
        self.assertNotIn('data-card="looks"', imagery)
        self.assertNotIn('data-card="paper-collage"', imagery)

    def test_on_a_phone_the_looks_sit_three_across_without_their_line(self):
        page = self._page()
        phone = page[page.index('@media (max-width:700px){\n  #modal{padding:0}'):]
        self.assertIn('.looks-grid{grid-template-columns:repeat(3,1fr)', phone)
        self.assertIn('.looks-grid .card .meta span{display:none}', phone)

    def test_the_page_data_knows_families_members_and_their_kind(self):
        data = {e['id']: e for e in _data(self._page(built=('look-melt',)))}
        self.assertEqual(data['looks']['members'], 14)
        self.assertEqual(data['looks']['plural'], 'looks')
        self.assertEqual(data['look-melt']['family'], 'looks')
        self.assertEqual(data['look-melt']['kindTitle'], 'Scene look')
        self.assertEqual(data['look-filter-pixel']['kindTitle'], 'Filter look')
        self.assertTrue(data['look-melt']['available'])
        self.assertFalse(data['look-pixel']['available'])
        self.assertNotIn('family', data['eased-entrances'])

    def test_a_published_community_look_sits_in_the_section_with_the_scene_looks(self):
        community = {'published': [COMMUNITY_LOOK], 'drafts': [], 'can_submit': True, 'is_admin': True,
                     'fetch': False}
        page = self._page(community=community)
        section = _section(page, 'Looks')
        self.assertIn('<span class="count">15 looks</span>', section)
        at = section.index('data-card="community:c-20260101-abc123"')
        self.assertLess(at, section.index('data-kind="filter"'))
        self.assertIn('Community</span>', section)
        self.assertIn('data-cap-action="reject"', section)        # an admin can still take it down
        community_data = json.loads(re.search(r'<script id="community-data" type="application/json">(.*?)</script>',
                                              page, re.S).group(1))
        self.assertEqual(community_data[0]['family'], 'looks')
        self.assertEqual(community_data[0]['kindTitle'], 'Scene look')

    def test_a_community_capability_with_no_family_stays_in_its_category(self):
        other = dict(COMMUNITY_LOOK, family=None, slug='c-20260101-def456', id='zoom-reveal',
                     category='Imagery and camera')
        page = self._page(community={'published': [other], 'drafts': [], 'can_submit': False,
                                     'is_admin': False, 'fetch': False})
        self.assertIn('data-card="community:c-20260101-def456"', _section(page, 'Imagery and camera'))
        self.assertIn('<span class="count">14 looks</span>', _section(page, 'Looks'))

    def test_the_modal_keeps_44px_touch_targets(self):
        page = self._page()
        self.assertNotIn('id="modal-back"', page)
        self.assertIn('#modal .close{position:absolute;top:10px;right:10px;width:44px;height:44px;', page)
        self.assertRegex(page, r'\.card\{[^}]*min-height:44px')


class TypeSection(unittest.TestCase):
    """The Type family wired like Looks, through the same family fields:
    its own section, a lead card, one card per style, and the add flow."""

    def _page(self, built=(), community=None):
        with tempfile.TemporaryDirectory() as d:
            for id_ in built:
                Path(d, f'{id_}.mp4').write_bytes(b'mp4')
            return capabilities.page_html(d, '0', community=community).decode()

    def test_type_is_a_section_with_a_lead_card_then_one_card_per_style(self):
        section = _section(self._page(built=('type', 'type-rubber')), 'Type')
        self.assertIn('<span class="count">7 type styles</span>', section)
        lead = section.index('<strong>A few type styles</strong>')
        self.assertIn('The same three lines, one style after another.', section)
        for child in capabilities.get('type')['children']:
            self.assertGreater(section.index(f'data-card="{child["id"]}"'), lead)
        self.assertNotIn('data-kind=', section)                      # one group: no kind headings
        self.assertIn('<img src="/capabilities/type-rubber.jpg"', section)
        self.assertNotIn('data-card="type-rubber"', _section(self._page(), 'Looks'))

    def test_the_page_data_says_what_a_member_is(self):
        data = {e['id']: e for e in _data(self._page())}
        self.assertEqual((data['type']['members'], data['type']['plural']), (7, 'type styles'))
        self.assertEqual((data['type-split-flap']['family'], data['type-split-flap']['kindTitle']), ('type', 'Type style'))
        self.assertEqual(data['look-melt']['kindTitle'], 'Scene look')

    def test_the_add_flow_offers_a_new_type_style(self):
        page = self._page(community={'published': [], 'drafts': [], 'can_submit': True, 'is_admin': False,
                                     'fetch': False})
        self.assertIn('<input type="radio" name="family" value="type"><strong>A new type style</strong>', page)
        self.assertIn('data-heading="Add a type style"', page)
        self.assertIn('Added to Type, for any video to ask for', page)
        self.assertIn('A one-line description of the type style', page)

    def test_a_published_community_style_sits_in_the_type_section(self):
        style = dict(COMMUNITY_LOOK, family='type', category='Type', slug='c-20260101-fff000', id='neon-sign',
                     title='Neon sign')
        page = self._page(community={'published': [style], 'drafts': [], 'can_submit': False, 'is_admin': False,
                                     'fetch': False})
        self.assertIn('data-card="community:c-20260101-fff000"', _section(page, 'Type'))
        self.assertIn('<span class="count">8 type styles</span>', _section(page, 'Type'))
        self.assertNotIn('data-card="community:c-20260101-fff000"', _section(page, 'Looks'))

    def test_the_sheet_lists_every_style_by_name(self):
        sheet = capabilities.sheet_markdown()
        part = sheet[sheet.index('## Type\n'):]
        part = part[:part.index('\n## ', 3)]
        self.assertIn('**The type styles** (7; ask for any type style by name)', part)
        for child in capabilities.get('type')['children']:
            self.assertIn(f"- **{child['title']}** (`{child['style']}`)", part)


if __name__ == '__main__':
    unittest.main()
