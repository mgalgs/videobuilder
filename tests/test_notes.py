"""Review notes: the store, the AgentBackend interface and the null backend."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import videobuilder
import videobuilder.notes as notes_module
from videobuilder.notes import AgentBackend, AgentStatus, NoteStore, NullBackend, parse_questions


class FakeAgent(AgentBackend):
    name = 'fake'

    def __init__(self):
        self.submitted = []
        self.states = {}

    def submit(self, note):
        self.submitted.append(note)
        self.states[f'h{len(self.submitted)}'] = AgentStatus('queued')
        return f'h{len(self.submitted)}'

    def poll(self, handle):
        return self.states[handle]


class Notes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name, 'notes')

    def tearDown(self):
        self.tmp.cleanup()

    def test_store_with_the_null_backend(self):
        store = NoteStore(self.dir)
        self.assertEqual(store.list(), [])
        n = store.add('promo/film', '16x9', 12, 'intro', '  Bigger title  ', b'png-bytes', author='sam')
        self.assertEqual({k: n[k] for k in ('video', 'format', 'frame', 'segment', 'text', 'author', 'backend',
                                            'handle', 'state', 'reply', 'branch')},
                         {'video': 'promo/film', 'format': '16x9', 'frame': 12, 'segment': 'intro',
                          'text': 'Bigger title', 'author': 'sam', 'backend': 'null', 'handle': f'null:{n["id"]}',
                          'state': 'queued', 'reply': None, 'branch': None})
        self.assertEqual(store.get(n['id']), n)
        self.assertEqual(store.image(n['id']), b'png-bytes')
        self.assertEqual(sorted(os.listdir(self.dir)), [f'{n["id"]}.json', f'{n["id"]}.png'])
        m = store.add('other/film', '1x1', 0, None, 'x', b'')
        self.assertEqual([x['id'] for x in store.list()], [n['id'], m['id']])
        self.assertEqual([x['id'] for x in store.list('other/film')], [m['id']])
        store.delete(n['id'])
        self.assertEqual([x['id'] for x in store.list()], [m['id']])
        for bad in (lambda: store.get(n['id']), lambda: store.delete(n['id']), lambda: store.get('../escape')):
            with self.assertRaises(KeyError):
                bad()
        with self.assertRaisesRegex(ValueError, 'some text'):
            store.add('promo/film', '16x9', 0, None, '   ', b'')

    def test_null_backend(self):
        b = NullBackend()
        h = b.submit({'id': 'abc'})
        self.assertEqual(h, 'null:abc')
        self.assertEqual(b.poll(h), AgentStatus('queued', None, None))
        with self.assertRaises(ValueError):
            AgentStatus('lost')

    def test_a_backend_moves_notes_along(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        n = store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png')
        self.assertEqual(agent.submitted[0]['image'], str(self.dir / f'{n["id"]}.png'))
        self.assertEqual(agent.submitted[0]['text'], 'Shorter')
        self.assertEqual(store.get(n['id'])['handle'], 'h1')
        agent.states['h1'] = AgentStatus('replied', 'Done: cut two words.', 'notes/shorter')
        got = store.list()[0]
        self.assertEqual((got['state'], got['reply'], got['branch']), ('replied', 'Done: cut two words.', 'notes/shorter'))
        self.assertEqual(store.get(n['id'])['state'], 'replied')  # stored
        agent.states['h1'] = AgentStatus('working')  # a final state isn't polled again
        self.assertEqual(store.list()[0]['state'], 'replied')

    def test_cost_and_tokens_land_on_the_note_once_final(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        n = store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png')
        self.assertIsNone(store.get(n['id'])['cost_usd'])
        self.assertIsNone(store.get(n['id'])['tokens'])
        agent.states['h1'] = AgentStatus('replied', 'Done', 'notes/shorter', 0.42, {'input': 100, 'output': 20})
        got = store.list()[0]
        self.assertEqual(got['cost_usd'], 0.42)
        self.assertEqual(got['tokens'], {'input': 100, 'output': 20})

    def test_an_unreported_cost_stays_null_never_zero(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        n = store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png')
        agent.states['h1'] = AgentStatus('replied', 'Done', 'notes/shorter')
        got = store.list()[0]
        self.assertIsNone(got['cost_usd'])
        self.assertIsNone(got['tokens'])

    def test_a_backend_that_fails_to_submit(self):
        class Down(NullBackend):
            def submit(self, note):
                raise ConnectionError('unreachable')
        n = NoteStore(self.dir, Down()).add('v', '16x9', 0, None, 'hello', b'')
        self.assertEqual((n['state'], n['handle']), ('failed', None))
        self.assertIn('unreachable', n['reply'])

    def test_a_stuck_gathering_note_recovers_after_a_restart_and_unblocks_the_queue(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        gathering = store.start_gathering('promo/film', '16x9', text='Brief for the video')
        # A fresh NoteStore on the same directory stands in for the editor restarting
        # mid-crawl: the thread that would have called finish_gathering is gone for good.
        restarted = NoteStore(self.dir, agent)
        followup = restarted.add('promo/film', '16x9', None, None, 'A second note', None)
        self.assertEqual(restarted.get(followup['id'])['state'], 'queued')
        self.assertIsNone(restarted.get(followup['id'])['handle'])  # waits behind gathering

        # Not yet stale: still stuck, same as while the crawl is genuinely running.
        self.assertEqual(restarted.list('promo/film')[0]['state'], 'gathering')

        old_stale = notes_module.GATHER_STALE_SECONDS
        notes_module.GATHER_STALE_SECONDS = 0
        try:
            restarted.tick()
        finally:
            notes_module.GATHER_STALE_SECONDS = old_stale

        recovered = restarted.get(gathering['id'])
        self.assertNotEqual(recovered['state'], 'gathering')
        self.assertIn('Brief for the video', recovered['text'])
        self.assertIn('interrupted', recovered['text'])
        self.assertIsNotNone(recovered['handle'])
        self.assertEqual(agent.submitted[-1]['text'], recovered['text'])

        # A crawl thread that outlived the stale cutoff must not pull the submitted note back.
        late = restarted.finish_gathering(gathering['id'], 'Late brief', [])
        self.assertEqual(late['state'], recovered['state'])
        self.assertEqual(restarted.get(gathering['id'])['text'], recovered['text'])

        # Once the recovered note finishes, the follow-up that was waiting behind it
        # is dispatched too: the video is unblocked for good, not just for one poll.
        agent.states[recovered['handle']] = AgentStatus('replied', 'Done', 'notes/branch')
        restarted.tick()
        self.assertEqual(restarted.get(followup['id'])['handle'], 'h2')

    def test_note_file_asks_by_default_then_not_after_an_answer(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make it punchier', b'')
        md = (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('ask the director 1 to 3 short questions', md)
        self.assertNotIn('Do not ask clarifying questions', md)
        self.assertIn('unless you are asking clarifying questions', md)  # no Summary line conflict

        reply = 'Quick check before building:\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) + '\n```\n'
        agent.states[note['handle']] = AgentStatus('replied', reply, None)
        self.assertEqual(store.list('promo/film')[0]['state'], 'questions')

        followup = store.answer(note['id'], False, ['Dark'])
        md2 = (store.session_dir('promo/film') / (followup['id'] + '.md')).read_text()
        self.assertIn('Do not ask clarifying questions', md2)
        self.assertNotIn('ask the director 1 to 3 short questions', md2)
        self.assertIn('End your reply with Summary: <one line>.', md2)
        self.assertNotIn('unless you are asking clarifying questions', md2)

    def test_an_answer_shows_the_creators_words_and_sends_the_whole_brief(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        reply = '```questions\n' + json.dumps({'questions': [{'text': 'Light or dark?'}]}) + '\n```\n'
        for build, said in ((False, 'A pier at dawn\n\nQ: Light or dark?\nA: Dark'), (True, 'A pier at dawn')):
            with self.subTest(build=build):
                video = f'promo/film-{int(build)}'
                note = store.add(video, '16x9', None, None, 'A pier at dawn\n\nBuild a first version.', None,
                                 said='A pier at dawn')
                agent.states[note['handle']] = AgentStatus('replied', reply, None)
                self.assertEqual(store.list(video)[0]['state'], 'questions')
                followup = store.answer(note['id'], build, None if build else ['Dark'])
                self.assertIn('Build a first version.', followup['text'])
                self.assertEqual(followup['said'], said)

    def test_builder_prompt_golden_text(self):
        """Pins the exact note file the builder reads, byte for byte: a change here
        means the prompt itself changed, not just where it's built."""
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', None, None, 'Make it punchier', None)
        md = (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertEqual(md, (
            '# Review request\n'
            '\n'
            'Make it punchier\n'
            '\n'
            'video: promo/film\n'
            'film: None\n'
            'format: 16x9\n'
            'frame: None\n'
            'segment: None\n'
            'beat: None\n'
            'time: None\n'
            'image: None\n'
            'draft: None\n'
            '\n'
            '## Ask first if truly unclear\n'
            '\n'
            'Before doing any work, check whether this note leaves open a choice that would '
            'substantially change the result, and that nothing already here (this note, the '
            'pinned frame, any attachments, or the video itself) settles. If so, stop and ask '
            'the director 1 to 3 short questions instead of building: ask before changing '
            'anything, and commit nothing. Keep each question short, in plain language (never '
            'a file, function or parameter name), and either give it 2 to 4 short choices (under 100 characters each) or '
            'leave it as free text. End your reply with a line containing only ```questions, '
            'then one line of JSON {"questions": [{"text": "...", "choices": ["...", "..."]}]} '
            '(omit or empty "choices" for free text), then a line containing only ```, and '
            'nothing after it: if you ask, that block is the very end of your reply, with no '
            'Summary line. You may put one short line of plain text before the block as a '
            'lead-in. If the note is already clear enough, never ask: just build it as usual.\n'
            '\n'
            '## Be honest about what you can build\n'
            '\n'
            'Not every request is something this tool can do, or do well. Sort each one: if it '
            'asks for something you have no means to do at all (real-world footage of real '
            'people, a voice you cannot produce, and the like), never fake it or quietly swap '
            'in a different technique — stop and ask instead, the same way as above, saying '
            'plainly what is not possible and offering 2 to 4 concrete alternatives as the '
            'choices. If you can do it but not well, build the best version you can, then say '
            'so in your reply: name the weak spot, and add one line on what would improve it '
            '(a reference image, a different format, a simpler ask). If the request is merely '
            'ambiguous and the choice changes most of the work, ask about that instead, as '
            'above.\n'
            'Never quietly substitute a different technique and call it done. Whenever a reply '
            'falls short either way, say so in plain language, with no file names or internal '
            'terms, and end that part of your reply with one more fenced block — placed before '
            'the ```questions block if you are asking — a line containing only ```shortfalls, '
            'then one line of JSON {"shortfalls": [{"kind": "cannot", "what": "..."}]} '
            '("kind" is "cannot" or "weak", "what" a short plain-language phrase naming the '
            'thing asked for, not the workaround; 1 to 5 of them), then a line containing only '
            '```. Add this block only when a reply actually falls short.\n'
            '\n'
            '## Looks\n'
            '\n'
            'A note that asks for a look or an art style ("make it pop art", "paint it like a woodblock '
            'print", "try a few looks") means one of these named looks, each with its own motion, in two '
            'kinds. Scene looks repaint a picture this video describes as a `looks.Scene` (a few shapes '
            'with roles, the sun, a beacon): swirl (Post-Impressionist swirl), pointillism (Pointillism), '
            'woodblock (Ukiyo-e woodblock), melt (Surrealist melt), bauhaus (Bauhaus geometry), pop-art '
            '(Pop-art halftone), pixel (8-bit pixel), blueprint (Blueprint). Filter looks restyle whatever '
            'the video draws -- a photo, a screen capture, footage -- every pixel, frame by frame: pop-art '
            '(Pop-art filter), pixel (8-bit pixel filter), woodblock (Woodblock filter), blueprint '
            '(Blueprint filter), pointillism (Pointillism filter). The video decides the kind, not the '
            'name: a drawn scene takes `looks.paint(cv, name, scene, t)`; anything else (a product demo, '
            'photos, clips) draws as usual inside `with looks.filter(cv, name, t):`. They share names, so '
            '"pop art" means the pop-art scene look on a drawn scene and the pop-art filter on anything '
            "else. Read skill/make-a-video/reference/looks.md before using one, and draw the video's own "
            'words after the look, on top (outside a filter, or a filter turns them into its style too). To '
            "try several scene looks, `looks.relay` wipes from one to the next. Keep the look's motion: it "
            'is what makes it read as that look. Paper collage is a look too, built by hand: see its entry '
            "in the capabilities catalog. Looks with no filter (swirl, melt, bauhaus) can't restyle a "
            'photo, a capture or footage: say so as a shortfall and offer the nearest filter, or the look '
            'on a drawn part (a title card, a backdrop behind the footage). If `from videobuilder import '
            "looks` fails, or it has no `looks.filter`, this video's videobuilder is older than the looks: in "
            'its own requirements.txt, raise only the version on the videobuilder line, up to '
            f'{videobuilder.__version__}, and change nothing else in that file. If it has no '
            'requirements.txt of its own, leave the shared one alone and say in your reply that the video '
            'needs an upgrade.\n'
            '\n'
            '## Type\n'
            '\n'
            'A note that asks for a type-only moment by name or by what it does ("make the title a split-'
            'flap board", "type it on like a terminal", "make the letters bounce") means one of these '
            'named type styles: split-flap (Split-flap board), typewriter (Typewriter), terminal '
            '(Terminal), rubber (Rubber letters), rack-focus (Rack focus), letter-cloud (Letter cloud), '
            'editorial (Editorial stack). Every style takes the same props -- one to four short lines '
            '(never rewrapped), three colours (ink, paper, accent) and a length in seconds -- and enters,'
            ' holds (still moving) and leaves inside it: `vb.type.draw(cv, name, '
            'vb.type.props(lines=[...], ...), t)`, `t` the seconds since it started. Over another '
            'picture, `paper=None` and a `box=`. Read skill/make-a-video/reference/type.md before using '
            "one. If `vb.type` is missing, this video's videobuilder is older than the Type family: in its "
            'own requirements.txt, raise only the version on the videobuilder line, up to '
            f'{videobuilder.__version__}, and change nothing else in that file. If it has no '
            'requirements.txt of its own, leave the shared one alone and say in your reply that the video '
            'needs an upgrade.'
            '\n'
            '\n'
            '## Look at your work\n'
            '\n'
            'Before each distinct step of your work, write one line in your own message that '
            'starts with "Step: " and says what you are about to do and why, in plain words '
            'for the director (for example, "Step: make the logo arrive faster in the intro"). '
            'One line per step, never inside a tool call.\n'
            'The director is a creator, not a programmer. In every Step line and in your '
            'reply, describe what changes on screen in plain language: no file names, function '
            'or parameter names, code, frame counts or easing names.\n'
            'You can see images: open a PNG with the Read tool. When `image` is set it is the '
            'frame the director was looking at; open it before anything else.\n'
            'For anything about how the video looks, iterate visually: `still` the frames the '
            'note is about and open them, change the code, `still` them again and open them, '
            'and repeat until the problem is plainly gone when you look, not just in the code. '
            'A change you can only see side by side has not fixed it. For motion, `sheet '
            '--frames` around the moment.\n'
            'Open your final frames before you reply, and say in the reply what you saw wrong '
            'and what it looks like now.\n'
            '\n'
            'Change files only under promo/film.\n'
            'Commit only changes to the video. Never commit a reply or notes file: end with a '
            'short answer for the reviewer as your final message, and it is shown to them as '
            'your reply.\n'
            'Continue the supplied draft, or start from main when draft is null.\n'
            'End your reply with Summary: <one line> — unless you are asking clarifying '
            'questions instead of building, in which case end with the ```questions block as '
            'described above and do not add a Summary line.\n'
        ))

    def test_retry_carries_no_questions_forward(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Build it with your best judgement; do not ask questions.',
                         b'', no_questions=True)
        agent.states[note['handle']] = AgentStatus('failed', 'could not apply')
        failed = store.list('promo/film')[0]
        self.assertEqual(failed['state'], 'failed')
        retried = store.retry(failed['id'])
        self.assertTrue(retried.get('no_questions'))
        md = (store.session_dir('promo/film') / (retried['id'] + '.md')).read_text()
        self.assertIn('No more questions', md)
        self.assertNotIn('Ask first if truly unclear', md)

    def test_a_no_questions_note_never_shows_a_stray_block(self):
        # A backend that ignores the no-questions instruction must not leak the raw
        # block into the reply, and must not put the note back into questions state.
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = store.add('promo/film', '16x9', 0, None, 'Make it punchier', b'', no_questions=True)
        reply = 'Done.\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) + '\n```\n'
        agent.states[note['handle']] = AgentStatus('replied', reply, 'notes/branch')
        got = store.list('promo/film')[0]
        self.assertEqual(got['state'], 'replied')
        self.assertEqual(got['reply'], 'Done.')
        self.assertNotIn('questions', got)


class CompendiumAgent(FakeAgent):
    """A FakeAgent that can tell the note store what its staged source's
    compendium directory is (or isn't) -- the optional-attribute interface
    NoteStore._submit checks with getattr, same as ForkSandboxBackend's."""

    def __init__(self, compendium_dir):
        super().__init__()
        self.compendium_dir = compendium_dir

    def compendium_source(self, note):
        return self.compendium_dir


class CompendiumForBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name, 'notes')

    def tearDown(self):
        self.tmp.cleanup()

    def _md(self, store):
        note = store.add('promo/film', '16x9', 0, None, 'Make it punchier', b'')
        return (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()

    def test_section_appears_when_the_backend_has_a_compendium_and_the_switch_is_on(self):
        agent = CompendiumAgent('/staged/videobuilder/compendium')
        store = NoteStore(self.dir, agent, compendium_for_builder=True, compendium_votes=lambda: {'a': 'up'})
        md = self._md(store)
        self.assertIn('## Start from the compendium', md)
        self.assertIn('Prefer these: a.', md)

    def test_section_omitted_when_the_backend_cannot_tell(self):
        store = NoteStore(self.dir, FakeAgent(), compendium_for_builder=True, compendium_votes=lambda: {'a': 'up'})
        self.assertNotIn('Start from the compendium', self._md(store))

    def test_section_omitted_when_the_backends_pin_predates_the_compendium(self):
        store = NoteStore(self.dir, CompendiumAgent(None), compendium_for_builder=True,
                          compendium_votes=lambda: {'a': 'up'})
        self.assertNotIn('Start from the compendium', self._md(store))

    def test_switch_off_omits_the_section_even_with_a_compendium(self):
        agent = CompendiumAgent('/staged/videobuilder/compendium')
        store = NoteStore(self.dir, agent, compendium_for_builder=False, compendium_votes=lambda: {'a': 'up'})
        self.assertNotIn('Start from the compendium', self._md(store))

    def test_default_is_off_with_no_explicit_switch(self):
        store = NoteStore(self.dir, CompendiumAgent('/staged/videobuilder/compendium'))
        self.assertNotIn('Start from the compendium', self._md(store))

    def test_no_votes_configured_still_shows_the_section_without_vote_lines(self):
        agent = CompendiumAgent('/staged/videobuilder/compendium')
        store = NoteStore(self.dir, agent, compendium_for_builder=True)
        md = self._md(store)
        self.assertIn('Start from the compendium', md)
        self.assertNotIn('Prefer these', md)
        self.assertNotIn('Do not use', md)


class Questions(unittest.TestCase):
    def test_a_valid_block_with_choice_and_free_text(self):
        reply = ('Here is a quick check.\n\n```questions\n' + json.dumps({'questions': [
            {'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
            {'text': 'Any specific line of copy?'},
        ]}) + '\n```\n')
        lead_in, questions = parse_questions(reply)
        self.assertEqual(lead_in, 'Here is a quick check.')
        self.assertEqual(questions, [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
                                     {'text': 'Any specific line of copy?', 'choices': []}])

    def test_malformed_json_falls_back_to_an_ordinary_reply(self):
        self.assertIsNone(parse_questions('```questions\nnot json\n```\n'))

    def test_zero_or_four_questions_is_invalid(self):
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': []}) + '\n```\n'))
        four = [{'text': f'Q{i}'} for i in range(4)]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': four}) + '\n```\n'))

    def test_one_or_five_choices_is_invalid(self):
        one = [{'text': 'Q', 'choices': ['A']}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': one}) + '\n```\n'))
        five = [{'text': 'Q', 'choices': ['A', 'B', 'C', 'D', 'E']}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': five}) + '\n```\n'))

    def test_overlong_strings_are_invalid(self):
        long_text = [{'text': 'x' * 500}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': long_text}) + '\n```\n'))
        long_choice = [{'text': 'Q', 'choices': ['ok', 'y' * 200]}]
        self.assertIsNone(parse_questions('```questions\n' + json.dumps({'questions': long_choice}) + '\n```\n'))

    def test_a_sentence_long_choice_is_valid(self):
        choice = "Character jams through the video, with the promo's titles and 'OUT NOW' ending on top"
        block = [{'text': 'How should the character fit?', 'choices': [choice, 'Replace the promo']}]
        _, questions = parse_questions('```questions\n' + json.dumps({'questions': block}) + '\n```\n')
        self.assertEqual(questions[0]['choices'][0], choice)

    def test_a_missing_block_falls_back_to_an_ordinary_reply(self):
        self.assertIsNone(parse_questions('Just a plain reply, no questions here.'))
        self.assertIsNone(parse_questions(None))

    def test_trailing_text_after_the_block_is_dropped(self):
        reply = ('Quick check:\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) +
            '\n```\n\nSummary: asked about the logo.')
        self.assertEqual(parse_questions(reply),
                         ('Quick check:', [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]))


if __name__ == '__main__':
    unittest.main()
