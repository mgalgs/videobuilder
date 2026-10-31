"""Review notes: the store, the AgentBackend interface and the null backend."""
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path

import videobuilder
import videobuilder.editor as editor_module
import videobuilder.notes as notes_module
from videobuilder.notes import AgentBackend, AgentStatus, NoteStore, NullBackend, parse_questions

from tests.fixtures import settle


def sent(store, note):
    """`note` as stored once `store`'s background submitter has had its turn."""
    settle(store)
    return store.get(note['id'])


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
        self.assertEqual((n['state'], n['handle']), ('queued', None))  # stored; sent in the background
        n = sent(store, n)
        self.assertEqual({k: n[k] for k in ('video', 'format', 'frame', 'segment', 'text', 'author', 'backend',
                                            'handle', 'state', 'reply', 'branch')},
                         {'video': 'promo/film', 'format': '16x9', 'frame': 12, 'segment': 'intro',
                          'text': 'Bigger title', 'author': 'sam', 'backend': 'null', 'handle': f'null:{n["id"]}',
                          'state': 'queued', 'reply': None, 'branch': None})
        self.assertEqual(store.get(n['id']), n)
        self.assertEqual(store.image(n['id']), b'png-bytes')
        self.assertEqual(sorted(os.listdir(self.dir)), [f'{n["id"]}.json', f'{n["id"]}.png'])
        m = store.add('other/film', '1x1', 0, None, 'x', b'')
        settle(store)
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
        n = sent(store, store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png'))
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
        n = sent(store, store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png'))
        self.assertIsNone(store.get(n['id'])['cost_usd'])
        self.assertIsNone(store.get(n['id'])['tokens'])
        agent.states['h1'] = AgentStatus('replied', 'Done', 'notes/shorter', 0.42, {'input': 100, 'output': 20})
        got = store.list()[0]
        self.assertEqual(got['cost_usd'], 0.42)
        self.assertEqual(got['tokens'], {'input': 100, 'output': 20})

    def test_an_unreported_cost_stays_null_never_zero(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        n = sent(store, store.add('promo/film', '16x9', 3, 'intro', 'Shorter', b'png'))
        agent.states['h1'] = AgentStatus('replied', 'Done', 'notes/shorter')
        got = store.list()[0]
        self.assertIsNone(got['cost_usd'])
        self.assertIsNone(got['tokens'])

    def test_a_backend_that_fails_to_submit(self):
        class Down(NullBackend):
            def submit(self, note):
                raise ConnectionError('unreachable')
        store = NoteStore(self.dir, Down())
        n = sent(store, store.add('v', '16x9', 0, None, 'hello', b''))
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
        settle(restarted)

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
        settle(restarted)
        self.assertEqual(restarted.get(followup['id'])['handle'], 'h2')

    def test_note_file_asks_by_default_then_not_after_an_answer(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = sent(store, store.add('promo/film', '16x9', 0, None, 'Make it punchier', b''))
        md = (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        self.assertIn('ask the director 1 to 3 short questions', md)
        self.assertNotIn('Do not ask clarifying questions', md)
        self.assertIn('unless you are asking clarifying questions', md)  # no Summary line conflict

        reply = 'Quick check before building:\n\n```questions\n' + json.dumps(
            {'questions': [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']}]}) + '\n```\n'
        agent.states[note['handle']] = AgentStatus('replied', reply, None)
        self.assertEqual(store.list('promo/film')[0]['state'], 'questions')

        followup = store.answer(note['id'], False, ['Dark'])
        settle(store)
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
                note = sent(store, store.add(video, '16x9', None, None, 'A pier at dawn\n\nBuild a first version.',
                                             None, said='A pier at dawn'))
                agent.states[note['handle']] = AgentStatus('replied', reply, None)
                self.assertEqual(store.list(video)[0]['state'], 'questions')
                followup = store.answer(note['id'], build, None if build else ['Dark'])
                settle(store)
                self.assertIn('Build a first version.', followup['text'])
                self.assertEqual(followup['said'], said)

    def test_builder_prompt_golden_text(self):
        """Pins the exact note file the builder reads, byte for byte: a change here
        means the prompt itself changed, not just where it's built."""
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = sent(store, store.add('promo/film', '16x9', None, None, 'Make it punchier', None))
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
            'in a different capability — stop and ask instead, the same way as above, saying '
            'plainly what is not possible and offering 2 to 4 concrete alternatives as the '
            'choices. If you can do it but not well, build the best version you can, then say '
            'so in your reply: name the weak spot, and add one line on what would improve it '
            '(a reference image, a different format, a simpler ask). If the request is merely '
            'ambiguous and the choice changes most of the work, ask about that instead, as '
            'above.\n'
            'Never quietly substitute a different capability and call it done. Whenever a reply '
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
            'Commit every file film.py reads. `.gitignore` may ignore only render outputs by path '
            '(preview frames, `*.mp4` renders, caches), never a whole file type such as `*.png`. '
            'Before you reply, make sure your commit loads from a clean checkout: the editor '
            'checks, and a change that does not load is not kept.\n'
            'Continue the supplied draft, or start from main when draft is null.\n'
            'End your reply with Summary: <one line> — unless you are asking clarifying '
            'questions instead of building, in which case end with the ```questions block as '
            'described above and do not add a Summary line.\n'
        ))

    def test_a_preproduction_callable_returning_none_leaves_the_prompt_and_note_untouched(self):
        """R20: a NoteStore whose `preproduction` always says "not pre-production" (as a
        production video's does) must submit and store a note exactly as one with no
        `preproduction` wired at all -- no `phase` or `picks` key appears."""
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        store.preproduction = lambda video, note, state: None
        note = sent(store, store.add('promo/film', '16x9', None, None, 'Make it punchier', None))
        md = (store.session_dir('promo/film') / (note['id'] + '.md')).read_text()
        plain = NoteStore(Path(self.tmp.name, 'notes2'), FakeAgent())
        plain_note = sent(plain, plain.add('promo/film', '16x9', None, None, 'Make it punchier', None))
        plain_md = (plain.session_dir('promo/film') / (plain_note['id'] + '.md')).read_text()
        self.assertEqual(md, plain_md)
        for key in ('phase', 'picks'):
            self.assertNotIn(key, note)

    def test_retry_carries_no_questions_forward(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = sent(store, store.add('promo/film', '16x9', 0, None,
                                     'Build it with your best judgement; do not ask questions.',
                                     b'', no_questions=True, said='Make it'))
        agent.states[note['handle']] = AgentStatus('failed', 'could not apply')
        failed = store.list('promo/film')[0]
        self.assertEqual(failed['state'], 'failed')
        retried = store.retry(failed['id'])
        settle(store)
        self.assertTrue(retried.get('no_questions'))
        self.assertEqual(retried['said'], 'Make it')         # the chat still shows the creator's words
        md = (store.session_dir('promo/film') / (retried['id'] + '.md')).read_text()
        self.assertIn('No more questions', md)
        self.assertNotIn('Ask first if truly unclear', md)

    def test_retry_and_answer_carry_over_budget_music_forward(self):
        # Without it, the follow-up's prompt calls an over-budget pick "could not be fetched".
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        picks = dict(music=['track-2'], music_over_budget=['track-2'])
        failed = sent(store, store.add('promo/film', '16x9', 0, None, 'Add music', b'', **picks))
        agent.states[failed['handle']] = AgentStatus('failed', 'could not apply')
        self.assertEqual({n['id']: n['state'] for n in store.list('promo/film')}[failed['id']], 'failed')
        self.assertEqual(store.retry(failed['id'])['music_over_budget'], ['track-2'])

        asked = sent(store, store.add('promo/other', '16x9', 0, None, 'Add music', b'', **picks))  # own video: no queue
        reply = '```questions\n' + json.dumps({'questions': [{'text': 'Loud?', 'choices': ['Yes', 'No']}]}) + '\n```\n'
        agent.states[asked['handle']] = AgentStatus('replied', reply, None)
        states = {n['id']: n['state'] for n in store.list('promo/other')}
        self.assertEqual(states[asked['id']], 'questions')
        self.assertEqual(store.answer(asked['id'], False, ['Yes'])['music_over_budget'], ['track-2'])
        settle(store)

    def test_a_no_questions_note_never_shows_a_stray_block(self):
        # A backend that ignores the no-questions instruction must not leak the raw
        # block into the reply, and must not put the note back into questions state.
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        note = sent(store, store.add('promo/film', '16x9', 0, None, 'Make it punchier', b'', no_questions=True))
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
        note = sent(store, store.add('promo/film', '16x9', 0, None, 'Make it punchier', b''))
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


class QuestionsWithPictureChoices(unittest.TestCase):
    def _block(self, questions):
        return '```questions\n' + json.dumps({'questions': questions}) + '\n```\n'

    def test_string_only_blocks_parse_exactly_as_before(self):
        reply = self._block([{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
                             {'text': 'Any specific line of copy?'}])
        _, questions = parse_questions(reply)
        self.assertEqual(questions, [{'text': 'Light or dark logo?', 'choices': ['Light', 'Dark']},
                                     {'text': 'Any specific line of copy?', 'choices': []}])
        self.assertNotIn('options', questions[0])
        self.assertNotIn('set', questions[0])

    def test_each_image_kind_is_accepted(self):
        for kind in ('vb', 'concept', 'yours'):
            with self.subTest(kind=kind):
                reply = self._block([{'text': 'Which look?', 'choices': [
                    {'text': 'Moody', 'image': 'bible/options/look/a.png', 'kind': kind},
                    {'text': 'Bright', 'image': 'bible/options/look/b.png', 'kind': kind}]}])
                _, questions = parse_questions(reply)
                self.assertEqual(questions[0]['choices'], ['Moody', 'Bright'])
                self.assertEqual(questions[0]['options'][0],
                                 {'text': 'Moody', 'image': 'bible/options/look/a.png', 'kind': kind, 'key': None})

    def test_a_mix_of_string_and_object_choices(self):
        reply = self._block([{'text': 'Which look?', 'choices': [
            {'text': 'Moody', 'image': 'bible/options/look/a.png', 'kind': 'concept'},
            'Bright']}])
        _, questions = parse_questions(reply)
        self.assertEqual(questions[0]['choices'], ['Moody', 'Bright'])
        self.assertEqual(questions[0]['options'],
                         [{'text': 'Moody', 'image': 'bible/options/look/a.png', 'kind': 'concept', 'key': None},
                          None])

    def test_set_and_key_are_carried_through(self):
        reply = self._block([{'text': 'Which look?', 'set': 'look', 'choices': [
            {'text': 'Moody', 'image': 'bible/options/look/a.png', 'kind': 'concept', 'key': 'A'},
            {'text': 'Bright', 'image': 'bible/options/look/b.png', 'kind': 'concept', 'key': 'B'}]}])
        _, questions = parse_questions(reply)
        self.assertEqual(questions[0]['set'], 'look')
        self.assertEqual([o['key'] for o in questions[0]['options']], ['A', 'B'])

    def test_malformed_image_choices_invalidate_the_whole_block(self):
        bad = [
            {'text': 'X', 'image': '../bible/options/a.png', 'kind': 'vb'},
            {'text': 'X', 'image': 'options/a.png', 'kind': 'vb'},
            {'text': 'X', 'image': 'bible/options/a.exe', 'kind': 'vb'},
            {'text': 'X', 'image': 'bible/options/a.png'},
            {'text': 'X', 'image': 'bible/options/a.png', 'kind': 'bogus'},
            {'text': 'x' * 200, 'image': 'bible/options/a.png', 'kind': 'vb'},
        ]
        for choice in bad:
            with self.subTest(choice=choice):
                reply = self._block([{'text': 'Which?', 'choices': [choice, 'Other']}])
                self.assertIsNone(parse_questions(reply))

    def test_image_builder_reply_is_stored_on_the_note(self):
        from tests.fixtures import settle

        class PictureAgent(AgentBackend):
            name = 'picture'

            def submit(self, note):
                return 'h1'

            def poll(self, handle):
                reply = ('Pick a look.\n\n```questions\n' + json.dumps({'questions': [
                    {'text': 'Which look?', 'set': 'look', 'choices': [
                        {'text': 'Moody', 'image': 'bible/options/look/a.png', 'kind': 'concept', 'key': 'A'},
                        {'text': 'Bright', 'image': 'bible/options/look/b.png', 'kind': 'concept', 'key': 'B'}]}]})
                          + '\n```\n')
                return AgentStatus('replied', reply)

        tmp = tempfile.TemporaryDirectory()
        try:
            store = NoteStore(Path(tmp.name, 'notes'), PictureAgent())
            note = store.add('promo/film', '16x9', 0, None, 'Pick a look', b'')
            settle(store)
            note = store.current(note['id'])
            self.assertEqual(note['state'], 'questions')
            self.assertIn('options', note['questions'][0])
            self.assertEqual(note['questions'][0]['set'], 'look')
        finally:
            tmp.cleanup()


class BackgroundSubmit(unittest.TestCase):
    """Submitting a note (staging, the prompt, backend.submit) runs on a thread
    of its own, never in the request that stored the note."""
    BLOCK = 10  # the slow submit's own timeout: far longer than any prompt return

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name, 'notes')

    def slow_agent(self, slow_texts=None):
        """A FakeAgent whose submit blocks until its `release` is set, for every
        note or only those whose text is in `slow_texts`; `calls` records the
        order submissions start in."""
        agent = FakeAgent()
        agent.entered, agent.release, agent.calls = threading.Event(), threading.Event(), []
        submit = agent.submit

        def slow(note):
            agent.calls.append(note['text'])
            if slow_texts is None or note['text'] in slow_texts:
                agent.entered.set()
                agent.release.wait(self.BLOCK)
            return submit(note)
        agent.submit = slow
        self.addCleanup(agent.release.set)
        return agent

    def test_a_slow_submit_never_holds_up_the_request_or_a_poll(self):
        agent = self.slow_agent()
        store = NoteStore(self.dir, agent)
        self.addCleanup(settle, store)
        start = time.monotonic()
        n = store.add('promo/film', '16x9', 0, None, 'Bigger title', b'')
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual((n['state'], n['handle']), ('queued', None))
        self.assertTrue(agent.entered.wait(5))  # the submitter is in backend.submit, holding the video's lock

        listed = []
        poll = threading.Thread(target=lambda: listed.append(store.list('promo/film')))
        start = time.monotonic()
        poll.start()
        poll.join(2)
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual([(x['id'], x['state'], x['handle']) for x in listed[0]], [(n['id'], 'queued', None)])
        self.assertEqual((store.current(n['id'])['handle'], store.get(n['id'])['handle']), (None, None))

        agent.release.set()  # no further request: the submitter finishes on its own
        settle(store)
        self.assertEqual(store.get(n['id'])['handle'], 'h1')
        self.assertEqual(len(agent.submitted), 1)

    def test_notes_added_back_to_back_are_submitted_in_order_one_at_a_time(self):
        agent = self.slow_agent(slow_texts={'First'})
        store = NoteStore(self.dir, agent)
        self.addCleanup(settle, store)
        first = store.add('promo/film', '16x9', 0, None, 'First', b'')
        self.assertTrue(agent.entered.wait(5))
        start = time.monotonic()
        second = store.add('promo/film', '16x9', 0, None, 'Second', b'')  # while the first is still submitting
        self.assertLess(time.monotonic() - start, 2)
        other = store.add('other/film', '16x9', 0, None, 'Elsewhere', b'')
        # Another video's note goes out on its own while this video's first is still submitting.
        deadline = time.monotonic() + 5
        while store.get(other['id'])['handle'] is None and time.monotonic() < deadline:
            agent.release.wait(0.01)
        self.assertEqual(store.get(other['id'])['handle'], 'h1')
        self.assertEqual(agent.calls, ['First', 'Elsewhere'])
        agent.release.set()
        settle(store)
        # This video's second waits for its first to finish.
        self.assertEqual(store.get(first['id'])['handle'], 'h2')
        self.assertIsNone(store.get(second['id'])['handle'])

        agent.states[store.get(first['id'])['handle']] = AgentStatus('replied', 'Done', 'notes/first')
        store.list('promo/film')  # a poll sees the first replied and kicks the submitter for the second
        settle(store)
        self.assertEqual(agent.calls, ['First', 'Elsewhere', 'Second'])
        self.assertEqual(store.get(second['id'])['handle'], 'h3')

    def test_a_note_left_queued_is_sent_by_the_tick_with_no_page_open(self):
        agent = FakeAgent()
        store = NoteStore(self.dir, agent)
        store.kick = lambda video: None  # the editor stops before its submitter runs
        n = store.add('promo/film', '16x9', 0, None, 'Bigger title', b'')
        self.assertEqual((store.get(n['id'])['state'], agent.submitted), ('queued', []))

        restarted = NoteStore(self.dir, agent)
        stop = threading.Event()
        with mock.patch.object(editor_module, 'NOTE_TICK', 0.05):
            ticker = editor_module._ticker(restarted.tick, stop)
            # a tick in flight still writes notes: stop it before the directory goes
            self.addCleanup(lambda: (stop.set(), ticker.join(10), settle(restarted)))
            deadline = time.monotonic() + 10
            while restarted.get(n['id'])['handle'] is None and time.monotonic() < deadline:
                settle(restarted)
                stop.wait(0.05)
        self.assertEqual(restarted.get(n['id'])['handle'], 'h1')
        self.assertEqual([s['text'] for s in agent.submitted], ['Bigger title'])


if __name__ == '__main__':
    unittest.main()
