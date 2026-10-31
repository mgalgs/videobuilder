"""The builder's prompt: the "Start from the compendium" section (see
tests/test_notes.py for the whole note file, pinned verbatim)."""
import unittest

from videobuilder import __version__, prompt
from videobuilder.capabilities.settings import Choice, Option
from videobuilder.music import MusicLibrary, Source

NOTE = {'id': 'n1', 'text': 'Make it punchier'}
PAYLOAD = {'video': 'promo/film', 'film': 'promo/film.py', 'format': '16x9', 'frame': None, 'segment': None,
          'beat': None, 'time': None, 'draft': None, 'directory': 'promo'}


class CompendiumSection(unittest.TestCase):
    def render(self, **kw):
        return prompt.render(NOTE, PAYLOAD, None, **kw)

    def test_omitted_by_default(self):
        self.assertNotIn('Start from the compendium', self.render())

    def test_omitted_when_compendium_is_false(self):
        self.assertNotIn('Start from the compendium', self.render(compendium=False, votes={'x': 'up'}))

    def test_included_when_compendium_is_true(self):
        md = self.render(compendium=True)
        self.assertIn('## Start from the compendium', md)
        self.assertIn('python -m videobuilder compendium index --json', md)
        self.assertIn('Compendium: <id>, <id>', md)

    def test_no_vote_lines_with_no_votes(self):
        md = self.render(compendium=True)
        self.assertNotIn('Do not use', md)
        self.assertNotIn('Prefer these', md)

    def test_no_vote_lines_with_empty_votes(self):
        md = self.render(compendium=True, votes={})
        self.assertNotIn('Do not use', md)
        self.assertNotIn('Prefer these', md)

    def test_up_and_down_ids_listed_by_id(self):
        md = self.render(compendium=True, votes={'beat-pop-title': 'up', 'bar-chart': 'down',
                                                  'stat-counter': 'up', 'reset-component': None})
        self.assertIn('Do not use: bar-chart.', md)
        self.assertIn('Prefer these: beat-pop-title, stat-counter.', md)
        self.assertNotIn('reset-component', md)

    def test_only_down_votes_no_prefer_line(self):
        md = self.render(compendium=True, votes={'bar-chart': 'down'})
        self.assertIn('Do not use: bar-chart.', md)
        self.assertNotIn('Prefer these', md)

    def test_section_never_leaks_into_no_questions_mode(self):
        note = {**NOTE, 'no_questions': True}
        md = prompt.render(note, PAYLOAD, None, compendium=True, votes={'x': 'down'})
        self.assertIn('## Start from the compendium', md)
        self.assertIn('Do not use: x.', md)
        self.assertIn('No more questions', md)


class AttachmentsSection(unittest.TestCase):
    def render(self, attachments):
        note = dict(NOTE, attachments=attachments)
        return prompt.render(note, PAYLOAD, None)

    def test_plain_attachment_has_no_credit_sentence(self):
        md = self.render([{'name': 'ref.png', 'type': 'image/png', 'size': 100}])
        self.assertIn('Attachments (read-only reference files):', md)
        self.assertNotIn('-- credit:', md)
        self.assertNotIn('carries a credit', md)

    def test_attachment_with_credit_gets_the_credit_line_and_sentence(self):
        credit = {'title': 'Farm Safety', 'creator': 'A. Studio', 'year': '1955',
                  'license': 'Public domain', 'item_url': 'https://archive.org/details/farm-safety-1955'}
        md = self.render([{'name': 'farm-safety.mp4', 'type': 'video/mp4', 'size': 100, 'credit': credit}])
        self.assertIn('-- credit: Farm Safety, by A. Studio, 1955, Public domain, '
                     'https://archive.org/details/farm-safety-1955', md)
        self.assertIn('carries a credit', md)

    def test_a_disputed_credit_says_so_once_whatever_its_licence(self):
        for licence, line in (('Public domain', '-- credit: Disc, rights disputed, Public domain'),
                              (None, '-- credit: Disc, rights disputed'),
                              ('rights disputed (see item page)', '-- credit: Disc, rights disputed (see item page)')):
            md = self.render([{'name': 'disc.mp3', 'type': 'audio/mpeg', 'size': 100,
                               'credit': {'title': 'Disc', 'license': licence, 'disputed': True}}])
            self.assertIn(line + '\n', md)

    def test_credit_sentence_only_added_when_some_attachment_has_one(self):
        credit = {'title': 'Farm Safety'}
        md = self.render([{'name': 'ref.png', 'type': 'image/png', 'size': 100},
                          {'name': 'farm-safety.mp4', 'type': 'video/mp4', 'size': 100, 'credit': credit}])
        self.assertIn('carries a credit', md)


class SourcesSection(unittest.TestCase):
    SOURCE = {'name': 'interview', 'ext': 'mp4', 'size': 123, 'duration': 95.4, 'width': 1920,
             'height': 1080, 'has_audio': True, 'caption': None, 'created': 0}

    def test_omitted_with_no_sources(self):
        with_none = prompt.render(NOTE, PAYLOAD, None)
        with_empty = prompt.render(NOTE, PAYLOAD, None, sources=[])
        self.assertEqual(with_none, with_empty)
        self.assertNotIn('Source videos', with_none)

    def test_lists_name_path_duration_resolution_and_audio(self):
        md = prompt.render(NOTE, PAYLOAD, None, sources=[self.SOURCE])
        self.assertIn('## Source videos', md)
        self.assertIn('sources/interview.mp4', md)
        self.assertIn('1:35', md)  # 95.4s -> 1:35
        self.assertIn('1920x1080', md)
        self.assertIn('has audio', md)
        self.assertIn('reference/footage.md', md)
        self.assertIn('reference/captions.md', md)

    def test_no_audio_and_caption_file_are_named(self):
        source = {**self.SOURCE, 'has_audio': False, 'caption': 'interview.vtt'}
        md = prompt.render(NOTE, PAYLOAD, None, sources=[source])
        self.assertIn('no audio', md)
        self.assertIn('caption interview.vtt', md)

    def test_hour_long_duration_uses_h_mm_ss(self):
        source = {**self.SOURCE, 'duration': 3725}
        md = prompt.render(NOTE, PAYLOAD, None, sources=[source])
        self.assertIn('1:02:05', md)

    def test_file_relative_path_convention_is_spelled_out(self):
        md = prompt.render(NOTE, PAYLOAD, None, sources=[self.SOURCE])
        self.assertIn('os.path.dirname(__file__)', md)

    def test_sandbox_marker_and_instructions(self):
        in_sandbox = {**self.SOURCE, 'in_sandbox': True}
        md = prompt.render(NOTE, PAYLOAD, None, sources=[in_sandbox])
        self.assertIn('in your sandbox', md)
        self.assertNotIn('not in your sandbox', md)
        self.assertIn('ln -s /attachments/sources promo/sources', md)
        self.assertIn('.git/info/exclude', md)
        self.assertIn('Never commit anything under sources/', md)

    def test_not_in_sandbox_marker_with_no_in_sandbox_flag(self):
        md = prompt.render(NOTE, PAYLOAD, None, sources=[self.SOURCE])
        self.assertIn('not in your sandbox', md)


class RefsSection(unittest.TestCase):
    STAGED = {'name': 'acme/launch', 'staged': True, 'commit': '0123456789abcdef0123456789abcdef01234567'}

    def test_omitted_with_no_refs(self):
        with_none = prompt.render(NOTE, PAYLOAD, None)
        with_empty = prompt.render(NOTE, PAYLOAD, None, refs=[])
        self.assertEqual(with_none, with_empty)
        self.assertNotIn('Referenced videos', with_none)

    def test_a_staged_reference_names_its_commit_and_paths(self):
        md = prompt.render(NOTE, PAYLOAD, None, refs=[self.STAGED])
        self.assertIn('## Referenced videos', md)
        self.assertIn('acme/launch: its code and assets as of commit 0123456789ab', md)
        self.assertIn('/attachments/refs/acme/launch/tree/', md)
        self.assertIn('/attachments/refs/acme/launch/sheet.png', md)
        self.assertNotIn('manifest.md', md)
        self.assertIn('never write into /attachments', md)

    def test_a_manifest_is_pointed_to_when_something_was_left_out(self):
        md = prompt.render(NOTE, PAYLOAD, None, refs=[{**self.STAGED, 'manifest': True}])
        self.assertIn('/attachments/refs/acme/launch/manifest.md', md)

    def test_an_unresolved_reference_says_so_without_saying_why(self):
        md = prompt.render(NOTE, PAYLOAD, None, refs=[{'name': 'acme/secret', 'staged': False}])
        # Missing and inaccessible say exactly the same thing, naming both possibilities
        # together rather than which one it actually was.
        self.assertIn('acme/secret: this reference could not be resolved right now '
                      '(missing or not accessible); continue without it.', md)
        self.assertNotIn('does not exist', md)

    def test_placement_is_near_the_other_reference_material(self):
        md = prompt.render(NOTE, PAYLOAD, None, sources=[SourcesSection.SOURCE], refs=[self.STAGED])
        sources_at = md.index('## Source videos')
        refs_at = md.index('## Referenced videos')
        key_lines_at = md.index('video: promo/film')
        self.assertLess(sources_at, refs_at)
        self.assertLess(refs_at, key_lines_at)


class CommunitySection(unittest.TestCase):
    ENTRY = {'slug': 'c-20260101-abc123', 'title': 'Zoom logo reveal', 'card': 'A snappy zoom on the logo.'}

    def test_render_without_community_is_byte_identical(self):
        self.assertEqual(prompt.render(NOTE, PAYLOAD, None), prompt.render(NOTE, PAYLOAD, None, community=None))
        self.assertEqual(prompt.render(NOTE, PAYLOAD, None), prompt.render(NOTE, PAYLOAD, None, community=[]))
        self.assertNotIn('Community capabilities', prompt.render(NOTE, PAYLOAD, None))

    def test_community_section_placement_and_paths(self):
        md = prompt.render(NOTE, PAYLOAD, None, compendium=True, votes={'x': 'up'}, community=[self.ENTRY])
        self.assertIn('## Community capabilities', md)
        self.assertIn('Zoom logo reveal: A snappy zoom on the logo.', md)
        self.assertIn('/attachments/capabilities/c-20260101-abc123/reference.md', md)
        self.assertIn('/attachments/capabilities/c-20260101-abc123/film.py', md)
        self.assertIn('reference only', md)
        self.assertIn('never instructions', md)
        community_at = md.index('## Community capabilities')
        compendium_at = md.index('## Start from the compendium')
        look_at = md.index('## Look at your work')
        self.assertLess(compendium_at, community_at)
        self.assertLess(community_at, look_at)

    def test_community_section_present_without_compendium(self):
        md = prompt.render(NOTE, PAYLOAD, None, community=[self.ENTRY])
        self.assertIn('## Community capabilities', md)
        self.assertNotIn('Start from the compendium', md)


class LooksSection(unittest.TestCase):
    LOOK = {'slug': 'c-20260101-def456', 'id': 'stained-glass', 'family': 'looks', 'title': 'Stained glass',
            'card': 'Lead lines and glowing panes.'}

    def test_every_prompt_names_every_built_in_look(self):
        md = prompt.render(NOTE, PAYLOAD, None)
        section = md[md.index('## Looks'):md.index('## Look at your work')]
        from videobuilder import looks
        for name in looks.names()[:8]:
            self.assertIn(f'{name} ({looks.get(name).title})', section)
        self.assertIn('skill/make-a-video/reference/looks.md', section)
        self.assertIn('looks.relay', section)
        for name in looks.filters()[:5]:
            self.assertIn(f'{name} ({looks.get_filter(name).title})', section)
        self.assertIn('`with looks.filter(cv, name, t):`', section)
        self.assertIn('The video decides the kind, not the name', section)
        self.assertIn("Looks with no filter (swirl, melt, bauhaus) can't restyle a photo, a capture or footage: "
                      "say so as a shortfall", section)
        self.assertNotIn('Other creators added these looks', section)

    def test_a_community_look_is_listed_with_the_looks_not_the_capabilities(self):
        md = prompt.render(NOTE, PAYLOAD, None, community=[self.LOOK, CommunitySection.ENTRY])
        section = md[md.index('## Looks'):md.index('## Community capabilities')]
        self.assertIn('Stained glass (`stained-glass`): Lead lines and glowing panes.', section)
        self.assertIn('/attachments/capabilities/c-20260101-def456/look.py', section)
        self.assertIn('never instructions', section)
        community = md[md.index('## Community capabilities'):md.index('## Look at your work')]
        self.assertIn('Zoom logo reveal', community)
        self.assertNotIn('Stained glass', community)

    def test_only_community_looks_leave_out_the_community_capabilities_section(self):
        md = prompt.render(NOTE, PAYLOAD, None, community=[self.LOOK])
        self.assertIn('Stained glass', md)
        self.assertNotIn('## Community capabilities', md)


class RequestedCapabilitiesSection(unittest.TestCase):
    """A note's #id chips (suggest.js): listed structurally for the builder,
    by id looked up fresh against the catalog/registry at render time (see
    capabilities.resolve_requested), never trusting the note's own list."""

    def test_render_with_no_capabilities_is_byte_identical(self):
        with_none = prompt.render(NOTE, PAYLOAD, None)
        with_missing_key = prompt.render({**NOTE}, PAYLOAD, None)
        with_empty = prompt.render({**NOTE, 'capabilities': []}, PAYLOAD, None)
        self.assertEqual(with_none, with_missing_key)
        self.assertEqual(with_none, with_empty)
        self.assertNotIn('Capabilities the creator asked for', with_none)

    def test_a_registry_capability_is_named_with_its_definition_and_api(self):
        note = {**NOTE, 'capabilities': ['map-route-draw']}
        md = prompt.render(note, PAYLOAD, None)
        self.assertIn('## Capabilities the creator asked for', md)
        self.assertIn('`map-route-draw`: **Map route draw**. A line traces a journey', md)
        self.assertIn('videobuilder.capabilities.shapes.map_route_draw.draw_route', md)

    def test_a_curated_catalog_capability_is_named_too(self):
        note = {**NOTE, 'capabilities': ['look-melt']}
        md = prompt.render(note, PAYLOAD, None)
        self.assertIn('`look-melt`: **Surrealist melt**.', md)

    def test_an_unknown_id_is_dropped_silently(self):
        md = prompt.render({**NOTE, 'capabilities': ['not-a-real-capability']}, PAYLOAD, None)
        self.assertNotIn('Capabilities the creator asked for', md)
        self.assertNotIn('not-a-real-capability', md)

    def test_duplicate_ids_are_listed_once(self):
        md = prompt.render({**NOTE, 'capabilities': ['map-route-draw', 'map-route-draw']}, PAYLOAD, None)
        self.assertEqual(md.count('map-route-draw'), 1)

    def test_section_placed_after_community_before_look_at_your_work(self):
        md = prompt.render({**NOTE, 'capabilities': ['look-melt']}, PAYLOAD, None,
                           community=[{'slug': 'c-1', 'title': 'Zoom logo reveal', 'card': 'A zoom.'}])
        community_at = md.index('## Community capabilities')
        requested_at = md.index('## Capabilities the creator asked for')
        look_at = md.index('## Look at your work')
        self.assertLess(community_at, requested_at)
        self.assertLess(requested_at, look_at)


class RequestedCapabilitiesSettingsLines(unittest.TestCase):
    """A capability whose chip settings card picked a non-default value
    (resolve_requested's `values`, from the note's {id, settings} entry) gets
    one plain line per value under its capability line -- a Number's value
    as-is, a Choice's suffixed with its own label so an opaque value (a
    voice id, say) still reads plainly. A note with nothing but defaults
    renders exactly as if its chip carried no settings at all."""

    def test_a_number_settings_value_is_listed_and_the_sentence_appears(self):
        note = {**NOTE, 'capabilities': [{'id': 'narration', 'settings': {'speed': 1.4}}]}
        md = prompt.render(note, PAYLOAD, None)
        self.assertIn('- speed: 1.4', md)
        self.assertIn("chip's settings card", md)

    def test_a_default_settings_value_adds_no_line_and_no_sentence(self):
        note = {**NOTE, 'capabilities': [{'id': 'narration', 'settings': {'speed': 1.0}}]}
        md = prompt.render(note, PAYLOAD, None)
        self.assertNotIn('- speed:', md)
        self.assertNotIn("settings card", md)

    def test_the_old_plain_string_format_renders_byte_identically(self):
        with_string = prompt.render({**NOTE, 'capabilities': ['narration']}, PAYLOAD, None)
        with_object = prompt.render({**NOTE, 'capabilities': [{'id': 'narration', 'settings': {}}]}, PAYLOAD, None)
        self.assertEqual(with_string, with_object)
        self.assertNotIn('settings card', with_string)

    def test_a_choice_value_line_is_suffixed_with_the_settings_label(self):
        items = [{'id': 'x', 'name': 'X', 'definition': 'A thing.', 'api': [],
                 'settings': (Choice('voice', 'Voice', options=(Option('A', 'a'), Option('B', 'b')), default='a'),),
                 'values': {'voice': 'b'}}]
        self.assertIn('  - voice: b (B)', prompt._requested_capabilities_lines(items))


class RequestedAssetsSection(unittest.TestCase):
    """A note's picked font/sfx/music chips (suggest.js: picked only, never
    typed, never written into the note's own text): listed next to
    '## Capabilities the creator asked for', by kind, resolved fresh against
    the real catalog at render time (fonts.get, the sfx pack, the configured
    music sources) -- see prompt._resolved_assets. A note with none of them
    renders byte-identical to one from before these chips existed."""

    def music_library(self, on_fetch=None):
        def func(cfg):
            if on_fetch:
                on_fetch()
            return [{'id': 'track-1', 'title': 'Theme', 'audio_url': 'https://example.com/t.mp3',
                    'tags': ['calm']}]
        source = Source('test-source', 'Test Music', 'CC0', 'entry_point', func=func, config=None)
        return MusicLibrary([source])

    def test_render_with_none_of_them_is_byte_identical(self):
        with_none = prompt.render(NOTE, PAYLOAD, None)
        with_missing_keys = prompt.render({**NOTE}, PAYLOAD, None)
        with_empty = prompt.render({**NOTE, 'fonts': [], 'sfx': [], 'music': []}, PAYLOAD, None)
        self.assertEqual(with_none, with_missing_keys)
        self.assertEqual(with_none, with_empty)
        self.assertNotIn('the creator picked', with_none)

    def test_a_font_pick_is_named_by_its_family_with_its_source(self):
        md = prompt.render({**NOTE, 'fonts': ['inter']}, PAYLOAD, None)
        self.assertIn('## Fonts, sound effects and music the creator picked', md)
        self.assertIn('Fonts:', md)
        self.assertIn('`Inter`: The clean default sans; variable weight. '
                      '(examples/assets (Inter-Variable.ttf))', md)
        self.assertNotIn('Sound effects:', md)
        self.assertNotIn('Music:', md)

    def test_an_sfx_pick_is_named_by_its_own_id(self):
        md = prompt.render({**NOTE, 'sfx': ['whoosh_fast/tight']}, PAYLOAD, None)
        self.assertIn('Sound effects:', md)
        self.assertIn('`whoosh_fast/tight`: whoosh (classic). a fast pass', md)

    def test_a_fetched_music_pick_points_at_its_attachment(self):
        attachment = {'id': 'abc123', 'name': 'Theme.mp3', 'type': 'audio/mpeg', 'size': 10,
                      'music_track': 'track-1'}
        md = prompt.render({**NOTE, 'music': ['track-1'], 'attachments': [attachment]}, PAYLOAD, None,
                           music=self.music_library())
        self.assertIn('Music:', md)
        self.assertIn('"Theme" (Test Music; calm): use /attachments/Theme.mp3 as this track.', md)

    def test_a_music_pick_whose_fetch_failed_says_so(self):
        md = prompt.render({**NOTE, 'music': ['track-1']}, PAYLOAD, None, music=self.music_library())
        self.assertIn('Music:', md)
        self.assertIn('"Theme" (Test Music; calm): could not be fetched', md)

    def test_an_unknown_font_id_is_dropped_silently(self):
        md = prompt.render({**NOTE, 'fonts': ['not-a-real-font']}, PAYLOAD, None)
        self.assertNotIn('the creator picked', md)
        self.assertNotIn('not-a-real-font', md)

    def test_a_music_id_with_no_music_library_given_is_dropped_silently(self):
        # Render never trusts the note's own stored id either, the same as editor._note_assets
        # at creation time -- here, resolved against whatever `music` render() is given.
        md = prompt.render({**NOTE, 'music': ['track-1']}, PAYLOAD, None)
        self.assertNotIn('the creator picked', md)
        self.assertNotIn('track-1', md)

    def test_section_placed_after_capabilities_before_look_at_your_work(self):
        md = prompt.render({**NOTE, 'capabilities': ['look-melt'], 'fonts': ['inter']}, PAYLOAD, None)
        requested_at = md.index('## Capabilities the creator asked for')
        assets_at = md.index('## Fonts, sound effects and music the creator picked')
        look_at = md.index('## Look at your work')
        self.assertLess(requested_at, assets_at)
        self.assertLess(assets_at, look_at)

    def test_a_note_with_no_music_pick_never_fetches_the_catalog(self):
        fetches = []
        prompt.render(NOTE, PAYLOAD, None, music=self.music_library(on_fetch=lambda: fetches.append(1)))
        self.assertEqual(fetches, [])

    def test_all_three_kinds_at_once(self):
        md = prompt.render({**NOTE, 'fonts': ['inter'], 'sfx': ['whoosh_fast/tight'], 'music': ['track-1']},
                           PAYLOAD, None, music=self.music_library())
        self.assertIn('Fonts:', md)
        self.assertIn('Sound effects:', md)
        self.assertIn('Music:', md)


class Preproduction(unittest.TestCase):
    def render(self, **kw):
        return prompt.render(NOTE, PAYLOAD, None, **kw)

    def test_omitted_by_default(self):
        self.assertNotIn('Pre-production', self.render())

    def test_section_appears_before_ask_first(self):
        md = self.render(preproduction={'concepts': True})
        self.assertIn('## Pre-production', md)
        self.assertLess(md.index('## Pre-production'), md.index('## Ask first'))

    def test_concepts_available_describes_the_concepts_block_and_its_caps(self):
        md = self.render(preproduction={'concepts': True})
        self.assertIn('```concepts', md)
        self.assertIn('3 per character', md)
        self.assertIn('4 for the look', md)

    def test_concepts_unavailable_says_to_use_vb_or_yours_instead(self):
        md = self.render(preproduction={'concepts': False})
        self.assertNotIn('```concepts', md)
        self.assertIn('cannot be generated right now', md)

    def test_picks_section_lists_each_pick_and_a_cleared_one(self):
        note = {**NOTE, 'picks': [{'set': 'look', 'key': 'A', 'label': 'Moody'}, {'set': 'character-ana', 'key': None}]}
        md = prompt.render(note, PAYLOAD, None)
        self.assertIn('## Picks since your last note', md)
        self.assertIn('look: A (Moody)', md)
        self.assertIn('character-ana: cleared', md)

    def test_no_picks_key_omits_the_section(self):
        self.assertNotIn('Picks since your last note', self.render())


class PinGuidance(unittest.TestCase):
    def test_looks_and_type_tell_the_builder_to_raise_only_the_version(self):
        # drafts.inspect() only keeps a pin change that raises just the version on the
        # videobuilder line and touches nothing else -- the prompt must ask for exactly
        # that, not the old "raise the pin" wording, which a builder could satisfy in a
        # way the editor would then refuse and throw the whole change away for.
        md = prompt.render(NOTE, PAYLOAD, None)
        self.assertNotIn('raise the pin', md)
        self.assertNotIn('version installed here', md)
        phrase = (f'raise only the version on the videobuilder line, up to {__version__}, '
                  'and change nothing else in that file')
        self.assertEqual(md.count(phrase), 2)
