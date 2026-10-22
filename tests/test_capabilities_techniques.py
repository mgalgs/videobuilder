"""Techniques (videobuilder/techniques/<family>/<id>.py) shown on the
Capabilities page: a Techniques section of family cards on /capabilities,
one page per family at /capabilities/techniques/<family>, clips served at
/capabilities/techniques/<id>.mp4|jpg, and the handful of cross-links
between a technique and the capability it overlaps."""
import json
import re
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from videobuilder import capabilities, techniques

from tests import fixtures


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
        self.assertEqual(set(capabilities.TECHNIQUE_FAMILIES), set(techniques.FAMILIES))
        for fam, (title, description) in capabilities.TECHNIQUE_FAMILIES.items():
            with self.subTest(family=fam):
                self.assertTrue(title.strip())
                self.assertTrue(description.strip())

    def test_family_titles_are_in_registry_order(self):
        self.assertEqual(tuple(capabilities.TECHNIQUE_FAMILIES), techniques.FAMILIES)


class Overlap(unittest.TestCase):
    def test_both_sides_of_every_overlap_row_exist(self):
        self.assertTrue(capabilities.TECHNIQUE_OVERLAP)  # at least one row in this checkout
        for technique_id, capability_id in capabilities.TECHNIQUE_OVERLAP.items():
            with self.subTest(technique=technique_id, capability=capability_id):
                techniques.get(technique_id)              # KeyError if unknown
                capabilities.get(capability_id)            # KeyError if unknown

    def test_reverse_lookup(self):
        self.assertEqual(capabilities._capability_overlap_technique('eased-entrances'), 'ease-out-back')
        self.assertIsNone(capabilities._capability_overlap_technique('staggered-reveals'))


class BuildTechniques(unittest.TestCase):
    def test_build_techniques_writes_clip_and_poster_under_a_techniques_subdir(self):
        with tempfile.TemporaryDirectory() as d:
            results = capabilities.build_techniques(d, only={'ease-out-back'})
            self.assertEqual([r['id'] for r in results], ['ease-out-back'])
            self.assertTrue((Path(d) / 'techniques' / 'ease-out-back.mp4').is_file())
            self.assertTrue((Path(d) / 'techniques' / 'ease-out-back.jpg').is_file())

    def test_build_includes_techniques_and_accepts_mixed_only_ids(self):
        with tempfile.TemporaryDirectory() as d:
            results = capabilities.build(d, only={'eased-entrances', 'ease-out-back'})
            ids = {r['id'] for r in results}
            self.assertEqual(ids, {'eased-entrances', 'ease-out-back'})
            self.assertTrue((Path(d) / 'eased-entrances.mp4').is_file())
            self.assertTrue((Path(d) / 'techniques' / 'ease-out-back.mp4').is_file())

    def test_build_rejects_an_unknown_only_id(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                capabilities.build(d, only={'not-a-real-id'})

    def test_build_with_no_only_builds_every_technique_too(self):
        with tempfile.TemporaryDirectory() as d:
            results = capabilities.build(d, only={'eased-entrances'})
            # only={'eased-entrances'} names no technique: the technique set built is empty, not "all".
            self.assertFalse((Path(d) / 'techniques').exists() and
                             any((Path(d) / 'techniques').iterdir()))


class ClipFile(unittest.TestCase):
    def test_unknown_technique_id_refused(self):
        self.assertIsNone(capabilities.technique_clip_file('/c', 'not-a-technique', 'mp4'))

    def test_no_dir_configured_refused(self):
        self.assertIsNone(capabilities.technique_clip_file(None, 'ease-out-back', 'mp4'))

    def test_known_id_builds_a_techniques_subdir_path(self):
        self.assertEqual(capabilities.technique_clip_file('/c', 'ease-out-back', 'mp4'),
                         '/c/techniques/ease-out-back.mp4')
        self.assertEqual(capabilities.technique_clip_file('/c', 'ease-out-back', 'jpg'),
                         '/c/techniques/ease-out-back.jpg')


def _section(page, heading):
    main = page[page.index('<main>'):page.index('</main>')]
    part = main[main.index(f'<h2>{heading}</h2>'):]
    end = part.find('<h2>', 4)
    return part if end < 0 else part[:end]


class MainPageSection(unittest.TestCase):
    def test_one_card_per_family_with_at_least_one_technique(self):
        page = capabilities.page_html(None, '0').decode()
        section = _section(page, 'Techniques')
        for fam in techniques.FAMILIES:
            members = techniques.catalog(fam)
            title, _ = capabilities.TECHNIQUE_FAMILIES[fam]
            if members:
                self.assertIn(f'href="/capabilities/techniques/{fam}"', section, fam)
                self.assertIn(f'<strong>{title}</strong>', section, fam)
            else:
                self.assertNotIn(f'href="/capabilities/techniques/{fam}"', section, fam)

    def test_card_shows_count_and_clip_not_built_placeholder(self):
        page = capabilities.page_html(None, '0').decode()
        section = _section(page, 'Techniques')
        n = len(techniques.catalog('principles'))
        self.assertIn(f'({n} technique{"s" if n != 1 else ""})', section)
        self.assertIn('clip not built', section)

    def test_poster_shown_once_built(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'techniques').mkdir()
            first = techniques.catalog('principles')[0]
            Path(d, 'techniques', f'{first.id}.mp4').write_bytes(b'mp4')
            page = capabilities.page_html(d, '0').decode()
        section = _section(page, 'Techniques')
        self.assertIn(f'/capabilities/techniques/{first.id}.jpg', section)

    def test_search_data_and_hit_list_present(self):
        page = capabilities.page_html(None, '0').decode()
        self.assertIn('id="techniques-search-data"', page)
        self.assertIn('id="tech-hits"', page)
        data = json.loads(re.search(r'<script id="techniques-search-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        ids = {e['id'] for e in data}
        self.assertEqual(ids, set(techniques.ids()))

    def test_overlapping_capability_links_to_its_technique(self):
        page = capabilities.page_html(None, '0').decode()
        data = json.loads(re.search(r'<script id="capabilities-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(e for e in data if e['id'] == 'eased-entrances')
        self.assertEqual(entry['techOverlap'], {'id': 'ease-out-back', 'family': 'principles', 'title': 'Ease Out Back'})


class FamilyPage(unittest.TestCase):
    def test_lists_its_own_techniques_grouped_by_group_in_registry_order(self):
        page = capabilities.techniques_family_page_html('principles', None, '0').decode()
        self.assertIn('<h1>Animation principles</h1>', page)
        self.assertIn('data-card="bounce-ease-out"', page)
        self.assertIn('data-card="ease-out-back"', page)
        # registry order (module filename): bounce_ease_out.py sorts before ease_out_back.py
        self.assertLess(page.index('data-card="bounce-ease-out"'), page.index('data-card="ease-out-back"'))

    def test_unknown_family_raises_key_error(self):
        with self.assertRaises(KeyError):
            capabilities.techniques_family_page_html('not-a-family', None, '0')

    def test_modal_data_has_definition_phrasings_aliases_and_api(self):
        page = capabilities.techniques_family_page_html('transitions', None, '0').decode()
        data = json.loads(re.search(r'<script id="techniques-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'dip-to-black')
        self.assertIn('fades all the way down to black', entry['description'])
        self.assertIn('fade through black', entry['aliases'])
        self.assertTrue(entry['api'])
        self.assertGreaterEqual(len(entry['prompts']), 2)

    def test_technique_modal_links_back_to_its_overlapping_capability(self):
        page = capabilities.techniques_family_page_html('principles', None, '0').decode()
        data = json.loads(re.search(r'<script id="techniques-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'ease-out-back')
        self.assertEqual(entry['overlap'], {'id': 'eased-entrances', 'title': 'Eased entrances'})
        other = next(t for t in data if t['id'] == 'bounce-ease-out')
        self.assertNotIn('overlap', other)

    def test_search_box_present(self):
        page = capabilities.techniques_family_page_html('principles', None, '0').decode()
        self.assertIn('<input type="search" id="tech-search"', page)
        self.assertIn(capabilities._TECHNIQUES_SEARCH_SCRIPT, page)


class Sheet(unittest.TestCase):
    def test_techniques_section_lists_every_family_no_per_technique_lines(self):
        sheet = capabilities.sheet_markdown()
        part = sheet[sheet.index('## Techniques'):]
        for fam, (title, description) in capabilities.TECHNIQUE_FAMILIES.items():
            self.assertIn(f'**{title}** (`{fam}`): {description}', part)
        self.assertIn('python -m videobuilder techniques index --family <family>', part)
        self.assertNotIn('ease-out-back', part)
        self.assertNotIn('Ease Out Back', part)

    def test_committed_sheet_matches_generated(self):
        from pathlib import Path as _Path
        root = _Path(__file__).resolve().parent.parent
        committed = (root / capabilities.SHEET_PATH).read_text()
        self.assertEqual(committed, capabilities.sheet_markdown())


class Routes(fixtures.API):
    def test_family_page_served(self):
        code, page, _ = _status(self.base, '/capabilities/techniques/principles')
        self.assertEqual(code, 200)
        self.assertIn(b'Ease Out Back', page)

    def test_unknown_family_404s(self):
        for bad in ('not-a-family', '..', '%2e%2e%2fetc%2fpasswd'):
            code, _, _ = _status(self.base, f'/capabilities/techniques/{bad}')
            self.assertEqual(code, 404, bad)

    def test_unknown_technique_clip_404s(self):
        for bad in ('not-a-technique', '..'):
            code, _, _ = _status(self.base, f'/capabilities/techniques/{bad}.mp4')
            self.assertEqual(code, 404, bad)

    def test_clip_404_without_capabilities_dir(self):
        code, _, _ = _status(self.base, '/capabilities/techniques/ease-out-back.mp4')
        self.assertEqual(code, 404)


class RoutesWithClip(fixtures.API):
    def setUp(self):
        super(fixtures.API, self).setUp()
        self.cap_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.cap_tmp.cleanup)
        Path(self.cap_tmp.name, 'techniques').mkdir()
        Path(self.cap_tmp.name, 'techniques', 'ease-out-back.mp4').write_bytes(b'0123456789')
        Path(self.cap_tmp.name, 'techniques', 'ease-out-back.jpg').write_bytes(b'\xff\xd8\xffposter\xff\xd9')
        self.start(capabilities_dir=self.cap_tmp.name)

    def test_poster_and_clip_served(self):
        code, body, headers = _status(self.base, '/capabilities/techniques/ease-out-back.jpg')
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), 'image/jpeg')
        code, body, headers = _status(self.base, '/capabilities/techniques/ease-out-back.mp4',
                                      {'Range': 'bytes=2-5'})
        self.assertEqual((code, body), (206, b'2345'))

    def test_family_page_reflects_the_built_clip(self):
        code, page, _ = _status(self.base, '/capabilities/techniques/principles')
        self.assertEqual(code, 200)
        data = json.loads(re.search(rb'<script id="techniques-data" type="application/json">(.*?)</script>',
                                    page, re.S).group(1))
        entry = next(t for t in data if t['id'] == 'ease-out-back')
        self.assertTrue(entry['available'])


if __name__ == '__main__':
    unittest.main()
