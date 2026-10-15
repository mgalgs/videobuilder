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
