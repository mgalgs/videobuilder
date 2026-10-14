"""The builder transcript reader and formatter (videobuilder/transcript.py)."""
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from videobuilder import transcript
from videobuilder.transcript import discover, format_transcript, read_feed


def line(obj):
    return json.dumps(obj)


def assistant(*content):
    return line({'type': 'assistant', 'message': {'role': 'assistant', 'content': list(content)}})


TEXT = {'type': 'text', 'text': '  Looking   at the\nframe now.  '}
THINKING = {'type': 'thinking', 'thinking': 'secret reasoning nobody should see'}
TOOL_READ = {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '/proj/promo/film.py'}}
TOOL_EDIT = {'type': 'tool_use', 'name': 'Edit', 'input': {'file_path': '/proj/promo/film.py'}}
TOOL_WRITE = {'type': 'tool_use', 'name': 'Write', 'input': {'file_path': '/proj/promo/new.py'}}
TOOL_BASH = {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'echo ' + 'x' * 200 + '\nsecond line'}}
TOOL_GREP = {'type': 'tool_use', 'name': 'Grep', 'input': {'pattern': 'FILM ='}}
TOOL_GLOB = {'type': 'tool_use', 'name': 'Glob', 'input': {'pattern': '**/*.py'}}
TOOL_UNKNOWN = {'type': 'tool_use', 'name': 'MysteryTool', 'input': {'anything': 'goes'}}

RESULT = line({'type': 'result', 'num_turns': 4, 'duration_ms': 135000, 'total_cost_usd': 1.2345})


class FormatterTests(unittest.TestCase):
    def test_text_and_every_tool_summary(self):
        lines = [
            assistant(TEXT),
            assistant(TOOL_READ),
            assistant(TOOL_EDIT),
            assistant(TOOL_WRITE),
            assistant(TOOL_BASH),
            assistant(TOOL_GREP),
            assistant(TOOL_GLOB),
            assistant(TOOL_UNKNOWN),
        ]
        entries = format_transcript([('Building', lines)], project_root='/proj')
        kinds_and_text = [(e['kind'], e['text']) for e in entries]
        self.assertEqual(kinds_and_text[0], ('leg', 'Building'))
        self.assertEqual(kinds_and_text[1], ('text', 'Looking at the frame now.'))
        self.assertEqual(kinds_and_text[2], ('tool', 'Read promo/film.py'))
        self.assertEqual(kinds_and_text[3], ('tool', 'Edit promo/film.py'))
        self.assertEqual(kinds_and_text[4], ('tool', 'Write promo/new.py'))
        self.assertTrue(kinds_and_text[5][1].startswith('Bash: echo '))
        self.assertNotIn('second line', kinds_and_text[5][1])
        self.assertTrue(kinds_and_text[5][1].endswith('…'))
        self.assertLessEqual(len(kinds_and_text[5][1]), len('Bash: ') + 160 + 1)
        self.assertEqual(kinds_and_text[6], ('tool', 'Grep FILM ='))
        self.assertEqual(kinds_and_text[7], ('tool', 'Glob **/*.py'))
        self.assertEqual(kinds_and_text[8], ('tool', 'MysteryTool'))

    def test_long_text_is_truncated(self):
        long_text = 'word ' * 200
        entries = format_transcript([('Building', [assistant({'type': 'text', 'text': long_text})])])
        self.assertLessEqual(len(entries[1]['text']), 401)
        self.assertTrue(entries[1]['text'].endswith('…'))

    def test_tool_result_and_thinking_and_system_are_absent(self):
        tool_result_user = line({'type': 'user', 'message': {'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': 'x', 'content': 'secret output'}]}})
        system_event = line({'type': 'system', 'subtype': 'init'})
        lines = [system_event, assistant(THINKING, TEXT), tool_result_user]
        entries = format_transcript([('Building', lines)])
        texts = [e['text'] for e in entries]
        self.assertNotIn('secret reasoning nobody should see', texts)
        self.assertNotIn('secret output', texts)
        self.assertEqual(texts, ['Building', 'Looking at the frame now.'])

    def test_malformed_line_is_skipped(self):
        entries = format_transcript([('Building', ['not json at all', assistant(TEXT)])])
        self.assertEqual([e['text'] for e in entries], ['Building', 'Looking at the frame now.'])

    def test_result_line_shows_turns_duration_and_cost(self):
        entries = format_transcript([('Building', [RESULT])])
        self.assertEqual(entries, [{'kind': 'leg', 'text': 'Building'},
                                    {'kind': 'result', 'text': '4 turns · 2m 15s · $1.23'}])

    def test_cost_hidden_for_non_admin_with_accounts_on(self):
        entries = format_transcript([('Building', [RESULT])], show_cost=False)
        self.assertEqual(entries[1]['text'], '4 turns · 2m 15s')

    def test_leg_ordering_across_legs(self):
        entries = format_transcript([
            ('Building', [assistant(TEXT)]),
            ('Review 1', [assistant(TEXT)]),
            ('Fix 1', [assistant(TEXT)]),
        ])
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'leg'], ['Building', 'Review 1', 'Fix 1'])

    def test_step_lines_become_their_own_kind_with_details_following(self):
        step_one = {'type': 'text', 'text': 'Step: tighten the logo entrance in the intro to 12 frames'}
        step_two = {'type': 'text', 'text': '  Step: brighten the close so it reads on a phone  '}
        lines = [
            assistant(TEXT),            # a detail before any step: unaffected
            assistant(step_one),
            assistant(TOOL_EDIT),       # a detail of the first step
            assistant(step_two),
            assistant(TOOL_GREP),       # a detail of the second step
        ]
        entries = format_transcript([('Building', lines)], project_root='/proj')
        kinds = [(e['kind'], e['text']) for e in entries]
        self.assertEqual(kinds, [
            ('leg', 'Building'),
            ('text', 'Looking at the frame now.'),
            ('step', 'tighten the logo entrance in the intro to 12 frames'),
            ('tool', 'Edit promo/film.py'),
            ('step', 'brighten the close so it reads on a phone'),
            ('tool', 'Grep FILM ='),
        ])

    def test_leg_with_no_step_lines_is_unaffected(self):
        entries = format_transcript([('Building', [assistant(TEXT), assistant(TOOL_READ)])])
        self.assertEqual([e['kind'] for e in entries], ['leg', 'text', 'tool'])

    def test_paths_relativize_to_the_leg_s_own_cwd_not_project_root(self):
        system_init = line({'type': 'system', 'subtype': 'init', 'cwd': '/sandbox/clone/proj'})
        lines = [system_init, assistant({'type': 'tool_use', 'name': 'Read',
                                          'input': {'file_path': '/sandbox/clone/proj/promo/film.py'}})]
        entries = format_transcript([('Building', lines)], project_root='/home/op/proj')
        tool = next(e for e in entries if e['kind'] == 'tool')
        self.assertEqual(tool['text'], 'Read promo/film.py')

    def test_leg_without_cwd_falls_back_to_project_root(self):
        entries = format_transcript([('Building', [assistant(TOOL_READ)])], project_root='/proj')
        tool = next(e for e in entries if e['kind'] == 'tool')
        self.assertEqual(tool['text'], 'Read promo/film.py')

    def test_empty_leg_produces_no_header(self):
        entries = format_transcript([('Building', [assistant(TEXT)]), ('Review 1', [])])
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'leg'], ['Building'])


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.handle = Path(self.tmp.name)

    def _write(self, directory, name, events):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text('\n'.join(json.dumps(e) for e in events) + '\n')

    def test_file_discovery_and_ordering(self):
        self._write(self.handle, 'events.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-review-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-fix-1.jsonl', [{'type': 'result'}])
        headers = [h for h, _ in discover(self.handle)]
        self.assertEqual(headers, ['Building', 'Review 1', 'Fix 1'])

    def test_review_and_fix_rounds_interleave_by_round(self):
        self._write(self.handle, 'events.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-review-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-fix-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-review-2.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-fix-2.jsonl', [{'type': 'result'}])
        headers = [h for h, _ in discover(self.handle)]
        self.assertEqual(headers, ['Building', 'Review 1', 'Fix 1', 'Review 2', 'Fix 2'])

    def test_evidence_fallback_when_handle_has_nothing(self):
        evidence = self.handle / 'evidence'
        self._write(evidence, 'events.jsonl', [{'type': 'result'}])
        headers = [h for h, _ in discover(self.handle)]
        self.assertEqual(headers, ['Building'])

    def test_union_of_handle_and_evidence_prefers_handle_copy(self):
        self._write(self.handle, 'events.jsonl', [{'type': 'result', 'num_turns': 1}])
        evidence = self.handle / 'evidence'
        self._write(evidence, 'events.jsonl', [{'type': 'result', 'num_turns': 99}])
        self._write(evidence, 'events-review-1.jsonl', [{'type': 'result', 'num_turns': 2}])
        files = dict(discover(self.handle))
        self.assertEqual(set(files), {'Building', 'Review 1'})
        self.assertEqual(files['Building'].parent, self.handle)
        entries = read_feed(self.handle)
        result = next(e for e in entries if e['kind'] == 'result')
        self.assertIn('1 turn', result['text'])

    def test_composed_run_naming_and_order(self):
        self._write(self.handle, 'events-s2-code-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-s1-plan-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-s3-review-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-s4-fix-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-s5-maintain-1.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-s2-code-2.jsonl', [{'type': 'result'}])
        self._write(self.handle, 'events-s6-polish-1.jsonl', [{'type': 'result'}])
        headers = [h for h, _ in discover(self.handle)]
        self.assertEqual(headers, ['Plan', 'Building', 'Building 2', 'Review 1', 'Fix 1', 'Maintain 1', 'Polish'])

    def test_symlink_out_of_handle_is_refused(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(outside, ignore_errors=True))
        secret = outside / 'events.jsonl'
        secret.write_text(json.dumps({'type': 'result', 'num_turns': 999}) + '\n')
        self.handle.mkdir(exist_ok=True)
        link = self.handle / 'events-review-1.jsonl'
        os.symlink(secret, link)
        self.assertEqual(discover(self.handle), [])
        self.assertEqual(read_feed(self.handle), [])

    def test_missing_handle_is_an_empty_feed(self):
        self.assertEqual(read_feed(str(self.handle / 'does-not-exist')), [])
        self.assertEqual(read_feed(None), [])
        self.assertEqual(read_feed(''), [])

    def test_read_feed_relativizes_paths_under_project_root(self):
        self._write(self.handle, 'events.jsonl', [
            {'type': 'assistant', 'message': {'role': 'assistant', 'content': [
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': str(self.handle / 'a' / 'b.py')}}]}}])
        entries = read_feed(self.handle, project_root=str(self.handle))
        tool = next(e for e in entries if e['kind'] == 'tool')
        self.assertEqual(tool['text'], 'Read ' + os.path.join('a', 'b.py'))

    def test_read_feed_caps_total_bytes(self):
        from videobuilder import transcript
        original = transcript.MAX_BYTES
        transcript.MAX_BYTES = 10
        try:
            self._write(self.handle, 'events.jsonl', [{'type': 'result', 'num_turns': 1}] * 50)
            entries = read_feed(self.handle)  # must not raise, regardless of what survives the cap
            self.assertIsInstance(entries, list)
        finally:
            transcript.MAX_BYTES = original


class FakePeek:
    """A scripted peek(handle, file, after) -> (bytes, file, next): each call
    pops the next canned response, or raises it if it's an Exception."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, handle, file, after):
        self.calls.append((handle, file, after))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class LiveFeedTests(unittest.TestCase):
    def setUp(self):
        transcript._live_entries.clear()
        self.handle = '/fake/handle/' + self.id()

    def test_live_bytes_used_while_no_files_exist(self):
        peek = FakePeek((assistant(TEXT).encode() + b'\n', 'events.jsonl', 70))
        entries = read_feed(self.handle, peek=peek)
        self.assertEqual([e['text'] for e in entries], ['Building', 'Looking at the frame now.'])
        self.assertEqual(len(peek.calls), 1)

    def test_no_peek_given_is_an_empty_feed(self):
        self.assertEqual(read_feed(self.handle), [])

    def test_leg_change_starts_a_new_leg_and_keeps_the_old_ones_entries(self):
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0):
            peek = FakePeek(
                (assistant(TEXT).encode() + b'\n', 'events.jsonl', 10),
                (assistant(TOOL_READ).encode() + b'\n', 'events-review-1.jsonl', 10))
            read_feed(self.handle, peek=peek)
            entries = read_feed(self.handle, peek=peek, project_root='/proj')
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'leg'], ['Building', 'Review 1'])
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'text'], ['Looking at the frame now.'])
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'tool'], ['Read promo/film.py'])

    def test_partial_line_is_held_until_complete(self):
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0):
            full = assistant(TEXT).encode() + b'\n'
            peek = FakePeek((full[:20], 'events.jsonl', 20), (full[20:], 'events.jsonl', len(full)))
            first = read_feed(self.handle, peek=peek)
            self.assertEqual(first, [])  # the leg's only line is still incomplete: no header shown yet
            second = read_feed(self.handle, peek=peek)
        self.assertEqual([e['text'] for e in second], ['Building', 'Looking at the frame now.'])

    def test_cut_over_long_line_is_dropped(self):
        oversized = assistant({'type': 'text', 'text': 'x' * 100}).encode() + b'\n'
        good = assistant(TEXT).encode() + b'\n'
        cap = 40
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0), patch.object(transcript, 'PEEK_MAX', cap):
            peek = FakePeek(
                (oversized[:cap], 'events.jsonl', cap),             # capped at PEEK_MAX, no newline: oversized
                (oversized[cap:], 'events.jsonl', len(oversized)),  # the rest of the dropped line, up to its \n
                (good, 'events.jsonl', len(oversized) + len(good)))
            read_feed(self.handle, peek=peek)
            read_feed(self.handle, peek=peek)
            entries = read_feed(self.handle, peek=peek)
        self.assertEqual([e['text'] for e in entries], ['Building', 'Looking at the frame now.'])

    def test_second_poll_within_throttle_window_reuses_cache(self):
        peek = FakePeek((assistant(TEXT).encode() + b'\n', 'events.jsonl', 10))
        first = read_feed(self.handle, peek=peek)
        second = read_feed(self.handle, peek=peek)
        self.assertEqual(first, second)
        self.assertEqual(len(peek.calls), 1)

    def test_concurrent_polls_for_one_handle_run_only_one_peek(self):
        peek = FakePeek((b'', None, 0))
        results = []
        lock = threading.Lock()
        def worker():
            result = read_feed(self.handle, peek=peek)
            with lock:
                results.append(result)
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)
        self.assertEqual(len(results), 5)
        self.assertEqual(len(peek.calls), 1)

    def test_discover_finding_files_drops_the_live_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            handle = Path(tmp)
            peek = FakePeek((assistant({'type': 'text', 'text': 'live only, must not survive'}).encode() + b'\n',
                              'events.jsonl', 50))
            live_entries = read_feed(handle, peek=peek)
            self.assertEqual([e['text'] for e in live_entries if e['kind'] == 'text'],
                              ['live only, must not survive'])
            self.assertIn(str(handle), transcript._live_entries)
            (handle / 'events.jsonl').write_text(assistant(TEXT) + '\n')
            entries = read_feed(handle, peek=peek)
        self.assertEqual([e['text'] for e in entries if e['kind'] == 'text'], ['Looking at the frame now.'])
        self.assertNotIn(str(handle), transcript._live_entries)

    def test_failing_peek_is_logged_once_and_feed_keeps_working(self):
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0):
            peek = FakePeek(
                (assistant(TEXT).encode() + b'\n', 'events.jsonl', 10),
                ValueError('cluster unreachable'),
                ValueError('cluster unreachable'))
            with self.assertLogs('videobuilder.transcript', level='WARNING') as captured:
                first = read_feed(self.handle, peek=peek)
                second = read_feed(self.handle, peek=peek)
                third = read_feed(self.handle, peek=peek)
        self.assertEqual([e['text'] for e in first], ['Building', 'Looking at the frame now.'])
        self.assertEqual(second, first)
        self.assertEqual(third, first)
        self.assertEqual(len(captured.records), 1)

    def test_live_feed_matches_collected_feed_for_the_same_bytes(self):
        lines = [assistant(TEXT), assistant(TOOL_READ), RESULT]
        raw = ('\n'.join(lines) + '\n').encode()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'events.jsonl').write_text(raw.decode())
            collected = read_feed(Path(tmp), project_root='/proj')
        cuts = sorted({10, len(raw) // 2, len(raw)})
        chunks, start = [], 0
        for cut in cuts:
            chunks.append(raw[start:cut])
            start = cut
        with patch.object(transcript, '_LIVE_POLL_INTERVAL', 0):
            peek = FakePeek(*[(chunk, 'events.jsonl', cut) for chunk, cut in zip(chunks, cuts)])
            entries = None
            for _ in chunks:
                entries = read_feed(self.handle, project_root='/proj', peek=peek)
        self.assertEqual(entries, collected)


if __name__ == '__main__':
    unittest.main()
