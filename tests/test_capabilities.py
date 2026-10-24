"""The capabilities with cards of their own: every one has a worked example
demo and every demo loads, draws, and passes the skill's own review check."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from videobuilder import capabilities, load_module

ROOT = Path(__file__).resolve().parent.parent
DEMOS = ROOT / 'examples' / 'capabilities'
CHECK = ROOT / 'skill' / 'make-a-video' / 'scripts' / 'check.py'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


class Catalog(unittest.TestCase):
    def test_every_card_has_a_demo_and_every_demo_has_a_card(self):
        # A card with no `category` of its own is a grouping capability's member, shown on the page
        # right after it (capabilities.cards): most keep the registry's short in-module demo, not a
        # worked example film, so this only checks the ones that give an Example.
        demo_files = {p.name for p in DEMOS.glob('*.py') if not p.name.startswith('_')}
        catalog_files = {os.path.basename(e.demo.path) for e in capabilities.cards() if e.is_example}
        self.assertEqual(catalog_files, demo_files)
        for e in capabilities.cards():
            if e.is_example:
                self.assertTrue((ROOT / e.demo.path).is_file(), e.demo.path)

    def test_ids_are_unique_kebab_case(self):
        seen = set()
        for e in capabilities.cards():
            self.assertRegex(e.id, r'\A[a-z][a-z0-9]*(-[a-z0-9]+)*\Z')
            self.assertNotIn(e.id, seen)
            seen.add(e.id)

    def test_prompts_are_plain_language_not_api_names(self):
        """'What to tell the builder' is spoken by a non-technical director:
        no prompt should read like code (an underscore name, or `vb.`)."""
        for e in capabilities.cards():
            for p in e.phrasings:
                with self.subTest(id=e.id, prompt=p):
                    self.assertNotIn('_', p)
                    self.assertNotIn('vb.', p)

    def test_every_demo_draws_first_middle_last_frame(self):
        for e in capabilities.cards():
            with self.subTest(id=e.id):
                film = e.demo()
                fmt = film.formats[0]
                self.assertGreaterEqual(film.frames, 2)
                for n in (0, film.frames // 2, film.frames - 1):
                    film.frame(n, fmt, scale=0.1)

    def test_every_demo_passes_check(self):
        for e in capabilities.cards():
            if not e.is_example:   # a member with the registry's own short demo, not a worked example film
                continue
            with self.subTest(id=e.id):
                result = subprocess.run([sys.executable, str(CHECK), str(ROOT / e.demo.path)],
                                        capture_output=True, text=True, env=ENV)
                self.assertIn('0 failed', result.stdout, result.stdout + result.stderr)


def _top():
    """The capabilities with a `category` of their own, page order."""
    return [t for t in capabilities.cards() if t.category]


class Families(unittest.TestCase):
    def test_looks_is_a_family_with_a_category_of_its_own(self):
        from videobuilder import looks
        groupers = [f.id for f in capabilities.with_members()]
        self.assertIn('looks', groupers)
        self.assertIn('type', groupers)
        family = capabilities.get('looks')
        self.assertIn(family, _top())
        self.assertEqual(family.category, 'Looks')
        self.assertEqual([e.id for e in _top() if e.category == 'Looks'], ['looks'])
        self.assertEqual(capabilities.categories().index('Looks'), capabilities.categories().index('Imagery and camera') + 1)
        self.assertEqual(family.members.noun, ('look', 'looks'))
        ids = list(family.members.ids)
        self.assertEqual(ids[:8], [f'look-{n}' for n in looks.names()[:8]])
        self.assertIn('paper-collage', ids)
        self.assertEqual([i for i in ids if i.startswith('look-filter-')], [f'look-filter-{n}' for n in looks.filters()[:5]])
        for child in capabilities.members(family):
            with self.subTest(id=child.id):
                self.assertNotIn(child, _top())      # reached through the family only
                self.assertEqual(capabilities.parent(child).id, 'looks')
                self.assertEqual(capabilities.category(child), 'Looks')
                self.assertEqual(child.category, '')
                self.assertIs(capabilities.get(child.id), child)
                self.assertIn(child.id, capabilities.ids())
                kind, look = capabilities.kind(child), capabilities.member_name(child)
                self.assertIn(kind, ('scene', 'filter'))
                if look is None:
                    continue
                if kind == 'scene':
                    self.assertEqual(child.name, looks.get(look).title)
                    self.assertTrue(any(f"looks.paint(cv, '{look}'" in api for api in child.api))
                else:
                    self.assertEqual(child.name, looks.get_filter(look).title)
                    self.assertTrue(any(f"looks.filter(cv, '{look}'" in api for api in child.api))

    def test_type_is_a_family_one_card_per_style(self):
        from videobuilder import type as vt
        family = capabilities.get('type')
        self.assertIn(family, _top())
        self.assertEqual(family.category, 'Type')
        self.assertEqual([e.id for e in _top() if e.category == 'Type'], ['type'])
        self.assertEqual(capabilities.categories().index('Type'), capabilities.categories().index('Looks') + 1)
        self.assertEqual(family.members.noun, ('type style', 'type styles'))
        self.assertEqual((family.members.lead, family.members.kinds), ('A few type styles', ()))
        self.assertEqual(family.members.brief.file, 'style.py')
        self.assertEqual(list(family.members.ids), [f'type-{n}' for n in vt.names()])
        for child in capabilities.members(family):
            with self.subTest(id=child.id):
                style = capabilities.member_name(child)
                self.assertNotIn(child, _top())
                self.assertEqual((capabilities.parent(child).id, capabilities.category(child)), ('type', 'Type'))
                self.assertEqual(child.name, vt.get(style).title)
                self.assertEqual(child.doc, 'skill/make-a-video/reference/type.md')
                self.assertEqual(child.demo.path, f"examples/capabilities/type-{style}.py")
                self.assertTrue(any(f"vb.type.draw(cv, '{style}'" in api for api in child.api))
                # Usually 3; type-split-flap carries split-flap-display's own phrasings too (merges.json).
                self.assertGreaterEqual(len(child.phrasings), 3)

    def test_every_type_demo_takes_the_same_props(self):
        props = set()
        for child in capabilities.members(capabilities.get('type')):
            film = child.demo()
            self.assertEqual(film.formats[0].name, 'cap')
            props.add(load_module(str(ROOT / child.demo.path))._type.PROPS)
        self.assertEqual(len(props), 1)

    def test_cards_lists_each_family_then_its_members(self):
        ids = [e.id for e in capabilities.cards()]
        at = ids.index('looks')
        children = capabilities.get('looks').members.ids
        self.assertEqual(ids[at + 1:at + 1 + len(children)], list(children))
        self.assertEqual(len(ids), len(set(ids)))
        for e in _top():
            self.assertIsNone(capabilities.parent(e))

    def test_the_sheet_lists_every_look_by_name_in_its_kind(self):
        sheet = capabilities.sheet_markdown()
        looks_part = sheet[sheet.index('## Looks'):]
        looks_part = looks_part[:looks_part.index('\n## ', 3)]
        self.assertIn('**The looks** (14; ask for any look by name)', looks_part)
        scene, filters = looks_part.index('*Scene looks*'), looks_part.index('*Filter looks*')
        for child in capabilities.members(capabilities.get('looks')):
            line = looks_part[looks_part.index(f"- **{child.name}** (`{capabilities.member_name(child) or child.id}`)"):]
            self.assertIn(child.demo.path, line[:line.index('\n')])
            self.assertEqual(looks_part.index(line[:40]) > filters, capabilities.kind(child) == 'filter')
            self.assertGreater(looks_part.index(line[:40]), scene)
        self.assertIn('`comic-halftone` is the **Pop-art filter**', looks_part)
        self.assertIn('`pixel-art-layer` is the **8-bit pixel filter**', looks_part)

    def test_the_merged_entries_document_both_apis(self):
        self.assertTrue(any('halftone_pattern' in a for a in capabilities.get('look-filter-pop-art').api))
        self.assertTrue(any('cv.pixelated' in a for a in capabilities.get('look-filter-pixel').api))


BEFORE_RECORDS = (
    'eased-entrances', 'springs-with-character', 'staggered-reveals', 'pop-on-the-beat', 'character-motion',
    'puppet-motion', 'pose-swaps', 'walk-in-place', 'stick-figure', 'impact-frame', 'overlap-transitions',
    'drawn-on-diagram', 'outline-morph', 'kinetic-typography', 'word-timed-captions', 'terminal-log',
    'counting-numbers', 'bar-charts', 'gauges-and-rings', 'line-chart-callout', 'camera-on-a-screenshot',
    'redrawn-product-ui', 'image-treatments', 'generated-art', 'orbit-3d', 'hard-light-sweep', 'parallax-scene',
    'looks', 'look-swirl', 'look-pointillism', 'look-woodblock', 'look-melt', 'look-bauhaus', 'look-pop-art',
    'look-pixel', 'look-blueprint', 'paper-collage', 'look-filter-pop-art', 'look-filter-pixel',
    'look-filter-woodblock', 'look-filter-blueprint', 'look-filter-pointillism', 'type', 'type-split-flap',
    'type-typewriter', 'type-terminal', 'type-rubber', 'type-rack-focus', 'type-letter-cloud', 'type-editorial',
    'beat-lock', 'footage-with-sound', 'narration', 'sound-effects', 'every-format', 'seamless-loops')


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

    def test_an_old_id_is_not_a_capability_of_its_own(self):
        old = capabilities.old_ids()
        self.assertEqual(old['comic-halftone'], 'look-filter-pop-art')
        self.assertEqual(old['pixel-art-layer'], 'look-filter-pixel')
        for o in old:
            self.assertNotIn(o, capabilities.ids())
            self.assertFalse((ROOT / 'examples' / 'capabilities' / f'{o}.py').exists())

    def test_resolve_requested_dedupes_an_old_id_against_its_keep(self):
        # A note made before the merge can hold both the old id and the one it was folded
        # into (they were separate capabilities then); resolve_requested must not return the
        # survivor twice.
        requested = capabilities.resolve_requested(['comic-halftone', 'look-filter-pop-art'])
        self.assertEqual([r['id'] for r in requested], ['look-filter-pop-art'])
        requested = capabilities.resolve_requested(['comic-halftone', 'pixel-art-layer', 'look-filter-pop-art'])
        self.assertEqual([r['id'] for r in requested], ['look-filter-pop-art', 'look-filter-pixel'])

    def test_every_id_from_before_the_one_record_format_still_resolves_to_itself(self):
        # Films, notes and suggestion history name these: the hand-written capabilities became
        # one-file records under the same ids (and the registry's own kept theirs). Some since
        # picked up `members` (a grouping capability's members get cards of their own too, right
        # after it: see capabilities.cards), so this only checks every one of these still has a
        # card -- not that no other id does.
        for i in BEFORE_RECORDS:
            with self.subTest(id=i):
                self.assertEqual(capabilities.resolve(i), i)
                self.assertEqual(capabilities.get(i).id, i)
                self.assertEqual(capabilities.resolve_requested([i])[0]['id'], i)
        self.assertLessEqual(set(BEFORE_RECORDS), {t.id for t in capabilities.cards()})

    def test_an_old_ids_clip_is_the_new_entrys(self):
        self.assertEqual(capabilities.clip_file('/c', 'comic-halftone', 'mp4'), '/c/look-filter-pop-art.mp4')
        self.assertEqual(capabilities.clip_file('/c', 'pixel-art-layer', 'jpg'), '/c/look-filter-pixel.jpg')
        self.assertIsNone(capabilities.clip_file('/c', 'never-was', 'mp4'))


class _Regrouped:
    """The records patched so `grouper` groups `ids` (a Members of nothing
    but ids; None: its members as they are) and takes `changes`, and every cache that read them cleared, on the way in and out."""

    def __init__(self, grouper, ids, **changes):
        import dataclasses
        from videobuilder.capabilities import registry
        from videobuilder.capabilities.schema import Members
        self.registry = registry
        t = registry.get(grouper)
        self.module = sys.modules[f'{registry.PACKAGE}.{t.family}.{grouper.replace("-", "_")}']
        self.before = t
        if ids is not None:
            changes['members'] = Members(ids=tuple(ids))
        self.after = dataclasses.replace(t, **changes)

    def _clear(self):
        for f in (self.registry._all, capabilities.cards, capabilities._parents, capabilities.old_ids,
                  capabilities._ids):
            f.cache_clear()

    def __enter__(self):
        self.module.CAPABILITY = self.after
        self._clear()

    def __exit__(self, *exc):
        self.module.CAPABILITY = self.before
        self._clear()


class GeneralMembers(unittest.TestCase):
    """`members` groups any capabilities, not only Looks and Type's: the
    next round's merges group with it too."""

    def test_a_grouper_in_a_shared_section_is_one_card_among_the_rest(self):
        before = _section(capabilities.page_html(None, 'v').decode(), 'Timing, sound and formats')
        with _Regrouped('narration', ['sonic-logo']):
            page = capabilities.page_html(None, 'v').decode()
            section = _section(page, 'Timing, sound and formats')
            for i in ('beat-lock', 'footage-with-sound', 'sound-effects', 'every-format', 'narration',
                      'sonic-logo'):
                self.assertIn(f'data-card="{i}"', section, i)
            self.assertIn('href="/capabilities/sound"', section)
            self.assertIsNone(capabilities.section_owner('Timing, sound and formats'))
            self.assertIn('Timing, sound and formats', capabilities.loose_categories())
            self.assertEqual(capabilities.category(capabilities.get('sonic-logo')), 'Timing, sound and formats')
            from videobuilder import suggest
            ids = {i for i, _ in suggest._capability_docs()}
            self.assertLessEqual({'narration', 'sonic-logo'}, ids)
        self.assertEqual(_section(capabilities.page_html(None, 'v').decode(), 'Timing, sound and formats'), before)

    def test_the_editor_picker_lists_a_grouper_in_a_shared_section_and_its_members(self):
        def picker_ids():
            from videobuilder import video_api

            class Handler:
                def _json(self, status, data):
                    return data

            class Editor:
                music = None
            data = video_api._get_suggest_catalog(Handler(), None, {}, Editor(), None)
            return [c['id'] for c in data['capabilities']], data
        before, _ = picker_ids()
        with _Regrouped('narration', ['sonic-logo']):
            after, data = picker_ids()
            self.assertEqual(sorted(after), sorted(before))
            self.assertNotIn('looks', after)
            self.assertNotIn('type', [c['id'] for c in data['type']])

    def test_only_a_sections_lead_card_has_no_id_to_copy(self):
        def page_data():
            page = capabilities.page_html(None, 'v').decode()
            m = re.search(r'<script id="capabilities-data" type="application/json">(.*?)</script>', page)
            return {e['id']: e for e in json.loads(m.group(1))}
        data = page_data()
        self.assertTrue(data['looks'].get('lead') and data['type'].get('lead'))
        with _Regrouped('narration', ['sonic-logo']):
            data = page_data()
            self.assertEqual(data['narration']['members'], 1)
            self.assertFalse(data['narration'].get('lead'))

    def test_the_sheet_takes_a_record_whose_demo_is_its_own_film(self):
        with _Regrouped('narration', ['sonic-logo']):
            sheet = capabilities.sheet_markdown()
            self.assertIn('Example: `videobuilder/capabilities/sound/sonic_logo.py`', sheet)
        with _Regrouped('sonic-logo', None, category='Timing, sound and formats'):
            sheet = capabilities.sheet_markdown()
            self.assertIn('**Worked example:** `videobuilder/capabilities/sound/sonic_logo.py`', sheet)
            self.assertNotIn('Read ``', sheet)

    def test_a_member_of_a_grouper_with_no_card_stays_on_its_family_page(self):
        with _Regrouped('ambience', ['sonic-logo']):
            self.assertFalse(capabilities.has_card(capabilities.get('sonic-logo')))
            self.assertNotIn('sonic-logo', {t.id for t in capabilities.cards()})
            self.assertIn('sonic-logo', {t.id for t in capabilities._family_members('sound')})
            from videobuilder import suggest
            self.assertIn('sonic-logo', {i for i, _ in suggest._capability_docs()})

    def test_looks_and_type_keep_their_sections_to_themselves(self):
        self.assertEqual(capabilities.section_owner('Looks').id, 'looks')
        self.assertEqual(capabilities.section_owner('Type').id, 'type')


class Posters(unittest.TestCase):
    def test_the_gallery_and_the_page_take_an_example_demos_poster_from_the_same_frame(self):
        from videobuilder.capabilities import gallery, registry

        class Film:
            frames = 120
            keyframes = ()
        t = capabilities.get('eased-entrances')
        self.assertIsNone(t.poster)
        self.assertEqual(registry.poster_frame(t, Film, int(Film.frames * gallery.POSTER_AT)), 60)
        self.assertEqual(registry.poster_frame(capabilities.get('stick-figure'), Film, 0), 130)


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
        for child in capabilities.members(capabilities.get('looks')):
            at = section.index(f'data-card="{child.id}"')
            self.assertEqual(at > filters, capabilities.kind(child) == 'filter', child.id)
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
        for child in capabilities.get('type').members.ids:
            self.assertGreater(section.index(f'data-card="{child}"'), lead)
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
        for child in capabilities.members(capabilities.get('type')):
            self.assertIn(f"- **{child.name}** (`{capabilities.member_name(child)}`)", part)


class Search(unittest.TestCase):
    """The search field filters the cards in the page itself; its script reads
    the same page data the modal does, so every card's words are searchable."""

    def test_the_header_has_a_search_field_and_the_page_its_script(self):
        page = capabilities.page_html(None, '0').decode()
        head = page[page.index('<div class="cap-head">'):page.index('</div>', page.index('<div class="cap-head">'))]
        self.assertIn('<input type="search" id="cap-search"', head)
        self.assertIn('aria-label="Search capabilities"', head)
        self.assertIn('id="search-none"', page)
        self.assertIn(capabilities._SEARCH_SCRIPT, page)
        self.assertIn("'capabilities-data', 'community-data'", capabilities._SEARCH_SCRIPT)

    def test_with_add_capability_the_search_sits_before_it(self):
        page = capabilities.page_html(None, '0', community={'published': [], 'drafts': [], 'can_submit': True,
                                                          'is_admin': False, 'fetch': False}).decode()
        self.assertLess(page.index('id="cap-search"'), page.index('id="add-capability"'))


if __name__ == '__main__':
    unittest.main()
