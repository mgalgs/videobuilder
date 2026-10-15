"""The builder's prompt: the "Start from the compendium" section (see
tests/test_notes.py for the whole note file, pinned verbatim)."""
import unittest

from videobuilder import prompt

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
