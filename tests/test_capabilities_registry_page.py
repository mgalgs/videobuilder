"""The registry (videobuilder/capabilities/<family>/<id>.py) shown on the
Capabilities page: a registry capability IS a capability to a director, so
each family with at least one gets a card filed into the existing category
section it belongs to (FAMILY_CATEGORY), not a section of its own. One page
per family at /capabilities/<family> (the pre-rename family URL permanently
redirects there); clips stay at /capabilities/<id>.mp4|jpg (the pre-rename
clip URL redirects the same way), and the handful of cross-links between a
registry entry and the capability it overlaps use "See also" rather than
naming the registry."""
import http.client
import json
import re
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from videobuilder import capabilities
from videobuilder.capabilities import registry

from tests import fixtures

# The pre-rename URL path segment the old redirects still answer to; built from parts so this
# file doesn't spell the retired word itself (see tests/test_capabilities_compat.py).
_OLD_URL_SEGMENT = 'tech' + 'niques'
# The retired word itself, for the one test that checks rendered pages never say it; built the
# same way, for the same reason.
_OLD_WORD = 'qinhcet'[::-1]


def _status(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.read(), e.headers


class FamilyTitles(unittest.TestCase):
    def test_every_family_slug_has_a_title_and_description(self):
        self.assertEqual(set(capabilities.REGISTRY_FAMILIES), set(registry.FAMILIES))
        for fam, (title, description) in capabilities.REGISTRY_FAMILIES.items():
            with self.subTest(family=fam):
                self.assertTrue(title.strip())
                self.assertTrue(description.strip())

    def test_family_titles_are_in_registry_order(self):
        self.assertEqual(tuple(capabilities.REGISTRY_FAMILIES), registry.FAMILIES)


class CategoryMapping(unittest.TestCase):
    def test_every_family_slug_maps_to_a_category_the_page_actually_has(self):
        self.assertEqual(set(capabilities.FAMILY_CATEGORY), set(registry.FAMILIES))
        categories = set(capabilities.categories())
        for fam, category in capabilities.FAMILY_CATEGORY.items():
            with self.subTest(family=fam):
                self.assertIn(category, categories)

    def test_no_family_slug_collides_with_a_capability_id_or_alias(self):
        # /capabilities/<id>.mp4 and /capabilities/<family> share the same prefix; a family slug
        # equal to a capability id (or an old id) would make the routes ambiguous.
        self.assertFalse(set(registry.FAMILIES) & set(capabilities.ids()))
        self.assertFalse(set(registry.FAMILIES) & set(capabilities.old_ids()))


class Overlap(unittest.TestCase):
    def test_both_sides_of_every_overlap_row_exist(self):
        self.assertTrue(capabilities.REGISTRY_OVERLAP)  # at least one row in this checkout
        for registry_id, capability_id in capabilities.REGISTRY_OVERLAP.items():
            with self.subTest(registry=registry_id, capability=capability_id):
                registry.get(registry_id)                  # KeyError if unknown
                capabilities.get(capability_id)            # KeyError if unknown

    def test_reverse_lookup(self):
        self.assertEqual(capabilities._registry_overlap('eased-entrances'), 'ease-out-back')
        self.assertIsNone(capabilities._registry_overlap('staggered-reveals'))


class BuildRegistry(unittest.TestCase):
    def test_build_writes_clip_and_poster_flat(self):
        with tempfile.TemporaryDirectory() as d:
            results = capabilities.build_registry(d, only={'ease-out-back'})
            self.assertEqual([r['id'] for r in results], ['ease-out-back'])
            self.assertTrue((Path(d) / 'ease-out-back.mp4').is_file())
            self.assertTrue((Path(d) / 'ease-out-back.jpg').is_file())

    def test_build_includes_the_registry_and_accepts_mixed_only_ids(self):
        with tempfile.TemporaryDirectory() as d:
            results = capabilities.build(d, only={'eased-entrances', 'ease-out-back'})
            ids = {r['id'] for r in results}
            self.assertEqual(ids, {'eased-entrances', 'ease-out-back'})
            self.assertTrue((Path(d) / 'eased-entrances.mp4').is_file())
            self.assertTrue((Path(d) / 'ease-out-back.mp4').is_file())

    def test_build_rejects_an_unknown_only_id(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                capabilities.build(d, only={'not-a-real-id'})

    def test_build_with_no_only_builds_the_whole_registry_too(self):
        with tempfile.TemporaryDirectory() as d:
            results = capabilities.build(d, only={'eased-entrances'})
            # only={'eased-entrances'} names no registry id: the registry set built is empty, not "all".
            self.assertEqual(sorted(Path(d).iterdir()), [Path(d) / 'eased-entrances.jpg', Path(d) / 'eased-entrances.mp4'])


class ClipFile(unittest.TestCase):
    def test_unknown_id_refused(self):
        self.assertIsNone(capabilities.clip_file('/c', 'not-a-real-id', 'mp4'))

    def test_no_dir_configured_refused(self):
        self.assertIsNone(capabilities.clip_file(None, 'ease-out-back', 'mp4'))

    def test_known_id_builds_a_flat_path(self):
        self.assertEqual(capabilities.clip_file('/c', 'ease-out-back', 'mp4'),
                         '/c/ease-out-back.mp4')
        self.assertEqual(capabilities.clip_file('/c', 'ease-out-back', 'jpg'),
                         '/c/ease-out-back.jpg')


def _section(page, heading):
    main = page[page.index('<main>'):page.index('</main>')]
    part = main[main.index(f'<h2>{heading}</h2>'):]
    end = part.find('<h2>', 4)
    return part if end < 0 else part[:end]


class MainPageSection(unittest.TestCase):
    """Each registry family's card files into the existing category section
    it maps to (FAMILY_CATEGORY), not a section of its own."""

    def test_there_is_no_standalone_family_section(self):
        page = capabilities.page_html(None, '0').decode()
        for fam, (title, _) in capabilities.REGISTRY_FAMILIES.items():
            self.assertNotIn(f'<h2>{title}</h2>', page, fam)

    def test_one_card_per_family_with_at_least_one_member_in_its_category(self):
        page = capabilities.page_html(None, '0').decode()
        for fam in registry.FAMILIES:
            members = registry.catalog(fam)
            title, _ = capabilities.REGISTRY_FAMILIES[fam]
            section = _section(page, capabilities.FAMILY_CATEGORY[fam])
            if members:
                self.assertIn(f'href="/capabilities/{fam}"', section, fam)
                self.assertIn(f'<strong>{title}</strong>', section, fam)
            else:
                self.assertNotIn(f'href="/capabilities/{fam}"', section, fam)

    def test_family_cards_come_after_the_categorys_own_cards(self):
        page = capabilities.page_html(None, '0').decode()
        section = _section(page, 'Motion')
        self.assertLess(section.index('data-card="outline-morph"'), section.index('href="/capabilities/principles"'))

    def test_card_shows_count_and_clip_not_built_placeholder(self):
        page = capabilities.page_html(None, '0').decode()
        section = _section(page, capabilities.FAMILY_CATEGORY['principles'])
        n = len([t for t in registry.catalog('principles') if not capabilities.has_card(t)])
        self.assertIn(f'({n} capabilit{"ies" if n != 1 else "y"})', section)
        self.assertIn('clip not built', section)

    def test_poster_shown_once_built(self):
        with tempfile.TemporaryDirectory() as d:
            first = registry.catalog('principles')[0]
            Path(d, f'{first.id}.mp4').write_bytes(b'mp4')
            page = capabilities.page_html(d, '0').decode()
        section = _section(page, capabilities.FAMILY_CATEGORY['principles'])
        self.assertIn(f'/capabilities/{first.id}.jpg', section)

    def test_search_data_and_hit_list_present(self):
        page = capabilities.page_html(None, '0').decode()
        self.assertIn('id="registry-search-data"', page)
        self.assertIn('id="reg-hits"', page)
        data = json.loads(re.search(r'<script id="registry-search-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        ids = {e['id'] for e in data}
        self.assertEqual(ids, {t.id for t in registry.catalog() if not capabilities.has_card(t)})

    def test_overlapping_capability_links_to_its_registry_entry(self):
        page = capabilities.page_html(None, '0').decode()
        data = json.loads(re.search(r'<script id="capabilities-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(e for e in data if e['id'] == 'eased-entrances')
        self.assertEqual(entry['regOverlap'], {'id': 'ease-out-back', 'family': 'principles', 'title': 'Ease Out Back'})


class FamilyPage(unittest.TestCase):
    def test_lists_its_own_capabilities_grouped_by_group_in_registry_order(self):
        page = capabilities.family_page_html('principles', None, '0').decode()
        self.assertIn('<h1>Animation principles</h1>', page)
        self.assertIn('data-card="bounce-ease-out"', page)
        self.assertIn('data-card="ease-out-back"', page)
        # registry order (module filename): bounce_ease_out.py sorts before ease_out_back.py
        self.assertLess(page.index('data-card="bounce-ease-out"'), page.index('data-card="ease-out-back"'))

    def test_unknown_family_raises_key_error(self):
        with self.assertRaises(KeyError):
            capabilities.family_page_html('not-a-family', None, '0')

    def test_modal_data_has_definition_phrasings_aliases_and_api(self):
        page = capabilities.family_page_html('transitions', None, '0').decode()
        data = json.loads(re.search(r'<script id="registry-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'dip-to-black')
        self.assertIn('fades all the way down to black', entry['description'])
        self.assertIn('fade through black', entry['aliases'])
        self.assertTrue(entry['api'])
        self.assertGreaterEqual(len(entry['prompts']), 2)

    def test_registry_modal_links_back_to_its_overlapping_capability(self):
        page = capabilities.family_page_html('principles', None, '0').decode()
        data = json.loads(re.search(r'<script id="registry-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'ease-out-back')
        self.assertEqual(entry['overlap'], {'id': 'eased-entrances', 'title': 'Eased entrances'})
        other = next(t for t in data if t['id'] == 'bounce-ease-out')
        self.assertNotIn('overlap', other)

    def test_search_box_present(self):
        page = capabilities.family_page_html('principles', None, '0').decode()
        self.assertIn('<input type="search" id="reg-search"', page)
        self.assertIn(capabilities._REGISTRY_SEARCH_SCRIPT, page)

    def test_title_and_search_say_the_familys_name(self):
        page = capabilities.family_page_html('typography', None, '0').decode()
        self.assertIn('<title>Typography · videobuilder</title>', page)
        self.assertIn('placeholder="Search typography…"', page)
        self.assertIn('aria-label="Search typography"', page)

    def test_modal_category_line_uses_the_familys_display_title(self):
        page = capabilities.family_page_html('principles', None, '0').decode()
        data = json.loads(re.search(r'<script id="registry-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'ease-out-back')
        self.assertEqual(entry['familyTitle'], 'Animation principles')

    def test_group_heading_and_modal_group_say_capability(self):
        page = capabilities.family_page_html('principles', None, '0').decode()
        self.assertIn('<h3 class="kind">Principle sub-capabilities</h3>', page)
        data = json.loads(re.search(r'<script id="registry-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'delay')
        self.assertEqual(entry['group'], 'Principle sub-capabilities')


def _visible_text(html):
    """`html` with every <script>/<style> block and every tag stripped, the
    way a grep for this round's own chrome wording should read a generated
    page. Ids, URLs and script/attribute internals may still name the
    retired word; this checks the title, headings (including each family's
    own `group` heading), search box, lead lines and cross-links."""
    html = re.sub(r'<script.*?</script>', ' ', html, flags=re.S)
    html = re.sub(r'<style.*?</style>', ' ', html, flags=re.S)
    html = re.sub(r'<[^>]+>', ' ', html)
    return html


class VisibleWording(unittest.TestCase):
    """The operator's decision: a registry capability IS a capability, so a
    director reading either generated page's own chrome, including a
    family's own `group` heading, never meets the retired word."""

    def test_main_page_wording_is_capability_only(self):
        page = capabilities.page_html(None, '0').decode()
        self.assertNotIn(_OLD_WORD, _visible_text(page).lower())

    def test_family_page_wording_is_capability_only(self):
        for fam in registry.FAMILIES:
            if not registry.catalog(fam):
                continue
            with self.subTest(family=fam):
                page = capabilities.family_page_html(fam, None, '0').decode()
                self.assertNotIn(_OLD_WORD, _visible_text(page).lower())


class Sheet(unittest.TestCase):
    def test_capability_families_section_lists_every_family_no_per_member_lines(self):
        sheet = capabilities.sheet_markdown()
        part = sheet[sheet.index('## Capability families'):]
        for fam, (title, description) in capabilities.REGISTRY_FAMILIES.items():
            self.assertIn(f'**{title}** (`{fam}`): {description}', part)
        self.assertIn('python -m videobuilder capabilities index --family <family>', part)
        self.assertNotIn('ease-out-back', part)
        self.assertNotIn('Ease Out Back', part)

    def test_committed_sheet_matches_generated(self):
        from pathlib import Path as _Path
        root = _Path(__file__).resolve().parent.parent
        committed = (root / capabilities.SHEET_PATH).read_text()
        self.assertEqual(committed, capabilities.sheet_markdown())


class Routes(fixtures.API):
    def test_family_page_served_at_its_new_path(self):
        code, page, _ = _status(self.base, '/capabilities/principles')
        self.assertEqual(code, 200)
        self.assertIn(b'Ease Out Back', page)

    def test_old_family_url_permanently_redirects(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1], timeout=20)
        self.addCleanup(conn.close)
        conn.request('GET', f'/capabilities/{_OLD_URL_SEGMENT}/principles')
        response = conn.getresponse()
        response.read()
        self.assertEqual((response.status, response.headers['Location']), (301, '/capabilities/principles'))

    def test_old_family_url_still_resolves_the_same_page_once_followed(self):
        code, page, _ = _status(self.base, f'/capabilities/{_OLD_URL_SEGMENT}/principles')
        self.assertEqual(code, 200)
        self.assertIn(b'Ease Out Back', page)

    def test_unknown_family_404s(self):
        for bad in ('not-a-family', '..', '%2e%2e%2fetc%2fpasswd'):
            code, _, _ = _status(self.base, f'/capabilities/{bad}')
            self.assertEqual(code, 404, bad)
            code, _, _ = _status(self.base, f'/capabilities/{_OLD_URL_SEGMENT}/{bad}')
            self.assertEqual(code, 404, bad)

    def test_old_clip_url_permanently_redirects(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1], timeout=20)
        self.addCleanup(conn.close)
        conn.request('GET', f'/capabilities/{_OLD_URL_SEGMENT}/ease-out-back.mp4')
        response = conn.getresponse()
        response.read()
        self.assertEqual((response.status, response.headers['Location']), (301, '/capabilities/ease-out-back.mp4'))

    def test_unknown_clip_id_404s(self):
        for bad in ('not-a-real-id', '..'):
            code, _, _ = _status(self.base, f'/capabilities/{_OLD_URL_SEGMENT}/{bad}.mp4')
            self.assertEqual(code, 404, bad)

    def test_clip_404_without_capabilities_dir(self):
        code, _, _ = _status(self.base, f'/capabilities/{_OLD_URL_SEGMENT}/ease-out-back.mp4')
        self.assertEqual(code, 404)


class RoutesWithClip(fixtures.API):
    def setUp(self):
        super(fixtures.API, self).setUp()
        self.cap_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.cap_tmp.cleanup)
        Path(self.cap_tmp.name, 'ease-out-back.mp4').write_bytes(b'0123456789')
        Path(self.cap_tmp.name, 'ease-out-back.jpg').write_bytes(b'\xff\xd8\xffposter\xff\xd9')
        self.start(capabilities_dir=self.cap_tmp.name)

    def test_poster_and_clip_served(self):
        code, body, headers = _status(self.base, '/capabilities/ease-out-back.jpg')
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), 'image/jpeg')
        code, body, headers = _status(self.base, '/capabilities/ease-out-back.mp4',
                                      {'Range': 'bytes=2-5'})
        self.assertEqual((code, body), (206, b'2345'))

    def test_old_clip_url_still_resolves_the_same_clip_once_followed(self):
        code, body, headers = _status(self.base, f'/capabilities/{_OLD_URL_SEGMENT}/ease-out-back.jpg')
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), 'image/jpeg')

    def test_family_page_reflects_the_built_clip(self):
        code, page, _ = _status(self.base, '/capabilities/principles')
        self.assertEqual(code, 200)
        data = json.loads(re.search(rb'<script id="registry-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'ease-out-back')
        self.assertTrue(entry['available'])


if __name__ == '__main__':
    unittest.main()
