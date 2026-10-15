"""The builder's prompt: the review-request markdown written beside each note."""
import json


def render(note, payload, image):
    """The exact text written to `<state>/sessions/<slug>/<note-id>.md`, the file
    the submitted payload's `note_file` points the builder at. `payload` is the
    note merged with its context and session fields (see NoteStore._submit);
    `image` is the frame path exposed to the runner (through /attachments), or
    None.
    """
    lines = ['# Review request', '', *([note['rejection']] if note.get('rejection') else []), note['text'], '']
    if note.get('time') is not None:
        t = note['time']
        lines += [f'At {int(t // 60)}:{int(t % 60):02d} (frame {note["frame"]}, segment {json.dumps(note.get("segment"))})', '']
    if note.get('attachments'):
        lines += ['Attachments (read-only reference files):']
        for item in note['attachments']:
            lines.append(f'- /attachments/{item["name"]} ({item["type"]}, {item["size"]} bytes)')
        lines += ['Use them as reference. To include one in the video, copy it into the video assets directory and commit it there. Never write into /attachments.', '']
    for key in ('video', 'film', 'format', 'frame', 'segment', 'beat', 'time', 'image', 'draft'):
        lines.append(f"{key}: {image if key == 'image' else payload.get(key)}")
    asking_enabled = not (note.get('no_questions') or note.get('automatic'))
    if not asking_enabled:
        lines += ['', '## No more questions', '',
                  'This note already settles any open choice (either with answers, or by asking '
                  'you to use your best judgement). Do not ask clarifying questions about it: '
                  'go ahead and build it.']
    else:
        lines += ['', '## Ask first if truly unclear', '',
                  'Before doing any work, check whether this note leaves open a choice that '
                  'would substantially change the result, and that nothing already here (this '
                  'note, the pinned frame, any attachments, or the video itself) settles. If so, '
                  'stop and ask the director 1 to 3 short questions instead of building: ask '
                  'before changing anything, and commit nothing. Keep each question short, in '
                  'plain language (never a file, function or parameter name), and either give it '
                  '2 to 4 short choices or leave it as free text. End your reply with a line '
                  'containing only ```questions, then one line of JSON {"questions": '
                  '[{"text": "...", "choices": ["...", "..."]}]} (omit or empty "choices" for '
                  'free text), then a line containing only ```, and nothing after it: if you '
                  'ask, that block is the very end of your reply, with no Summary line. You may '
                  'put one short line of plain text before the block as a lead-in. If the note '
                  'is already clear enough, never ask: just build it as usual.']
    lines += ['', '## Look at your work', '',
              'Before each distinct step of your work, write one line in your own message '
              'that starts with "Step: " and says what you are about to do and why, in plain '
              'words for the director (for example, "Step: make the logo arrive faster in the '
              'intro"). One line per step, never inside a tool call.',
              'The director is a creator, not a programmer. In every Step line and in your '
              'reply, describe what changes on screen in plain language: no file names, function '
              'or parameter names, code, frame counts or easing names.',
              'You can see images: open a PNG with the Read tool. When `image` is set it is '
              'the frame the director was looking at; open it before anything else.',
              'For anything about how the video looks, iterate visually: `still` the frames the '
              'note is about and open them, change the code, `still` them again and open them, '
              'and repeat until the problem is plainly gone when you look, not just in the code. '
              'A change you can only see side by side has not fixed it. For motion, '
              '`sheet --frames` around the moment.',
              'Open your final frames before you reply, and say in the reply what you saw wrong '
              'and what it looks like now.',
              '', f"Change files only under {payload.get('directory', payload.get('video'))}.",
              'Commit only changes to the video. Never commit a reply or notes file: '
              'end with a short answer for the reviewer as your final message, '
              'and it is shown to them as your reply.',
              'Continue the supplied draft, or start from main when draft is null.',
              'End your reply with Summary: <one line> — unless you are asking clarifying '
              'questions instead of building, in which case end with the ```questions block '
              'as described above and do not add a Summary line.'
              if asking_enabled else 'End your reply with Summary: <one line>.']
    return '\n'.join(lines) + '\n'
