"""The builder transcript reader, formatter and redaction (videobuilder/transcript.py)."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from videobuilder.transcript import discover, format_transcript, read_feed, redact


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


class RedactionTests(unittest.TestCase):
    def test_anthropic_key(self):
        self.assertEqual(redact('key is sk-ant-abc123def456ghi789'), 'key is [redacted]')

    def test_openai_key(self):
        self.assertEqual(redact('export OPENAI=sk-abcdefghijklmnopqrstuvwx'), 'export OPENAI=[redacted]')

    def test_github_token(self):
        self.assertEqual(redact('token ghp_abcdefghijklmnopqrstuv'), 'token [redacted]')
        self.assertEqual(redact('token github_pat_abcdefghijklmnopqrstuv'), 'token [redacted]')

    def test_slack_token(self):
        self.assertEqual(redact('xoxb-123456-abcdefghijklmnop'), '[redacted]')

    def test_aws_key(self):
        self.assertEqual(redact('AKIA' + 'Q' * 16), '[redacted]')

    def test_jwt(self):
        jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dQw4w9WgXcQ_abc123'
        self.assertEqual(redact(f'Authorization: {jwt}'), 'Authorization: [redacted]')

    def test_bearer_token(self):
        self.assertEqual(redact('curl -H "Authorization: Bearer abc.def-123_xyz"'),
                         'curl -H "Authorization: Bearer [redacted]"')

    def test_long_hex_or_base64_after_equals_colon_or_token(self):
        self.assertEqual(redact('export X=' + 'a1b2' * 8), 'export X=[redacted]')
        self.assertEqual(redact('digest: ' + 'A1b2'.ljust(32, 'z')), 'digest: [redacted]')
        self.assertEqual(redact('token ' + 'Zz19' * 8), 'token [redacted]')
        self.assertEqual(redact('short=abc123'), 'short=abc123')

    def test_name_equals_value_rule(self):
        self.assertEqual(redact('ANTHROPIC_API_KEY=sk-ant-xyz'), 'ANTHROPIC_API_KEY=[redacted]')
        self.assertEqual(redact('DB_PASSWORD=hunter2'), 'DB_PASSWORD=[redacted]')
        self.assertEqual(redact('my_secret_token=zzz'), 'my_secret_token=[redacted]')
        self.assertEqual(redact('FORMAT=1x1'), 'FORMAT=1x1')

    def test_bash_command_with_api_key_env_assignment(self):
        text = 'ANTHROPIC_API_KEY=sk-ant-xyz some-command --flag'
        result = redact(text)
        self.assertNotIn('sk-ant-xyz', result)
        self.assertNotIn('ANTHROPIC_API_KEY=sk', result)
        self.assertIn('[redacted]', result)

    def test_home_path(self):
        self.assertEqual(redact('/home/mitch/clone/videobuilder/film.py'), '~/clone/videobuilder/film.py')

    def test_non_string_passthrough(self):
        self.assertIsNone(redact(None))
        self.assertEqual(redact(42), 42)


if __name__ == '__main__':
    unittest.main()
