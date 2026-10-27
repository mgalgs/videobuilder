"""Narration: a voiceover made once with text to speech, then loaded like any
other audio.

    python -m videobuilder say script.txt --out assets/narration.wav

`say` (needs `pip install 'videobuilder[speech]'` and the Kokoro model files)
synthesizes each phrase of the script with Kokoro, joins them with a short
gap, and writes the WAV plus two sidecars measured from that audio:
`narration.vtt` (one cue per phrase, for `vb.captions`) and `narration.json`
(the phrase times and the inputs that made them). Commit all three, and the
script beside them. Rendering never needs the model:

    VOICE = vb.speech.load('assets/narration.wav')
    VOICE.track            # a captions Track, one cue per phrase
    VOICE.sound(at=15)     # a vb.Sound starting on film frame 15
    VOICE.mouth(fps, at=15)  # per film frame: is the mouth open?

Pronunciation: `[Kokoro](/kəkˈɔːɹəʊ/)` in the script speaks the phonemes
between the slashes and captions the word in brackets (Kokoro's own syntax);
`--say Galgs=Gahlgz` or `--lexicon names.json` respell a word everywhere
(a value in slashes is phonemes). `say --phonemes` prints how each phrase
will be read, to copy from. Two-part sounds reach the voice as Kokoro's
single symbols (`ɔɪ` as `Y`, see `single_symbols`), typed or not. In English, 1100-1999 is read as a year.

`say --engine chatterbox` reads the same script's text with Chatterbox
instead (see `Chatterbox`): slower, phrased by the model, no phonemes.

`say --engine gemini` reads it with Gemini (see `Gemini`), over the
network: natural phrasing, a `--style` direction, and (unlike Chatterbox)
no seed, so unchanged phrases keep their committed audio instead of being
redone every run.
"""
import array
import base64
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RATE = 24000
DEFAULT_VOICE = 'af_heart'
MODEL_FILES = ('kokoro-v1.0.int8.onnx', 'kokoro-v1.0.onnx')
VOICES_FILE = 'voices-v1.0.bin'
MODEL_DIRS = ('/opt/kokoro', '~/.cache/kokoro')
MODEL_URL = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
INSTALL_HINT = ("text to speech needs the speech extra: pip install 'videobuilder[speech]' (kokoro-onnx), "
                f'plus the model files {MODEL_FILES[0]} and {VOICES_FILE} from {MODEL_URL} '
                'in $VIDEOBUILDER_KOKORO_DIR or ~/.cache/kokoro')

CHATTERBOX_PYTHON = '/opt/chatterbox/bin/python'
CHATTERBOX_REPO = 'ResembleAI/chatterbox'
CHATTERBOX_REVISION = '5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18'
CHATTERBOX_CACHE = '/opt/chatterbox/hf'
CHATTERBOX_WORKER = Path(__file__).with_name('chatterbox_worker.py')
CHATTERBOX_HINT = (
    'Chatterbox runs in its own Python: $VIDEOBUILDER_CHATTERBOX_PYTHON (default '
    f'{CHATTERBOX_PYTHON}). Make one with: uv venv --python 3.11 ~/.local/chatterbox && '
    'uv pip install --python ~/.local/chatterbox/bin/python chatterbox-tts==0.1.7 "setuptools<81" '
    '--extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match; '
    'then export VIDEOBUILDER_CHATTERBOX_PYTHON=~/.local/chatterbox/bin/python')

GEMINI_MODEL = 'gemini-3.8-flash-tts'
GEMINI_VOICE = 'Kore'
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
GEMINI_HINT = 'export GEMINI_API_KEY=... (an API key from https://aistudio.google.com/apikey)'
GEMINI_HTTP_RETRIES = 4
GEMINI_BACKOFF = 1.0
GEMINI_TIMEOUT = 120

# Kokoro voice ids start with a language letter, then f/m.
LANGS = {'a': 'en-us', 'b': 'en-gb', 'e': 'es', 'f': 'fr-fr', 'h': 'hi', 'i': 'it', 'j': 'ja', 'p': 'pt-br',
         'z': 'cmn'}


class SpeechUnavailable(RuntimeError):
    pass


# ---- the script ----
_SENTENCE = re.compile(r'(?<=[.!?…])["\'”’)\]]*\s+')
_INLINE = re.compile(r'\[([^\]]+)\]\(/([^/)]+)/\)')
# A period after these (or after an initial, "J. R. R.") doesn't end a sentence.
_ABBREV = re.compile(r'(?:mr|mrs|ms|dr|st|jr|sr|prof|mt|vs|e\.g|i\.e|cf|(?-i:[A-Z]))\.', re.IGNORECASE)
# `|` between words: a phrase break the voice hears (a comma in its phonemes) and nobody sees.
BREAK = '|'
_PUNCT = '.,!?;:…'
# A straight quote can open as well as close: it closes only when no space comes before it.
_BREAK_AT_EDGE = re.compile(r'^[\s|]*\||\s*\|[\s|]*(?=[.,!?;:…”’)\]]|$)|\s*\|(?:\s*\|)*(?=["\'])')
_BREAKS = re.compile(r'\s*\|[\s|]*')


def phrases(script):
    """The script's phrases: every non-empty line, split after each sentence."""
    out = []
    for line in script.splitlines():
        line = ' '.join(line.split())
        if not line or line.startswith('#'):
            continue
        at = 0
        for m in _SENTENCE.finditer(line):
            # Don't split inside [word](/phonemes/).
            if line.count('[', 0, m.start()) != line.count(']', 0, m.start()):
                continue
            words = line[at:m.start()].split()
            if words and _ABBREV.fullmatch(words[-1].lstrip('("\'“‘[')):
                continue
            if line[at:m.end()].strip(BREAK + ' '):
                out.append(line[at:m.end()].strip())
            at = m.end()
        if line[at:].strip(BREAK + ' '):
            out.append(line[at:].strip())
    return out


def unmarked(text):
    """`text` without its `|` breaks, spaced as if they were never typed."""
    if BREAK not in text:
        return text
    return _BREAKS.sub(' ', _BREAK_AT_EDGE.sub('', text)).strip()


def caption_text(phrase):
    """What the captions show: `[word](/phonemes/)` as just the word, and no `|`."""
    return unmarked(_INLINE.sub(r'\1', phrase))


def spoken_parts(phrase, lexicon=None):
    """The phrase as [(kind, text)], kind 'text', 'phonemes' or 'break' (a `|`,
    in the text, typed phonemes or a respelling), with `lexicon` ({word:
    respelling, or '/phonemes/'}, whole words, case-insensitive) applied to
    the plain text."""
    parts = []
    at = 0
    for m in _INLINE.finditer(phrase):
        parts.append(('text', phrase[at:m.start()]))
        parts.append(('phonemes', m.group(2)))
        at = m.end()
    parts.append(('text', phrase[at:]))
    if lexicon:
        # Lookarounds, not \b: \b never matches beside a key's own non-word edge ("C++").
        words = '|'.join(re.escape(w) for w in sorted(lexicon, key=len, reverse=True))
        pat = re.compile(r'(?<!\w)(' + words + r')(?!\w)', re.IGNORECASE)
        keys = {w.casefold(): v for w, v in lexicon.items()}
        out = []
        for kind, s in parts:
            if kind != 'text':
                out.append((kind, s))
                continue
            at = 0
            for m in pat.finditer(s):
                v = keys[m.group(1).casefold()]
                out.append(('text', s[at:m.start()]))
                out.append(('phonemes', v[1:-1]) if len(v) > 2 and v[0] == v[-1] == '/' else ('text', v))
                at = m.end()
            out.append(('text', s[at:]))
        parts = out
    if any(BREAK in s for _, s in parts):
        out = []
        for kind, s in parts:
            for i, piece in enumerate(s.split(BREAK)):
                out += [('break', ',')] * (i > 0) + [(kind, piece)]
        parts = out
    merged = []
    for kind, s in parts:
        if not s:
            continue
        if merged and merged[-1][0] == kind and kind in ('text', 'break'):
            merged[-1] = (kind, merged[-1][1] if kind == 'break' else merged[-1][1] + s)
        else:
            merged.append((kind, s))
    return merged


# ---- synthesis ----
def _find(name, model_dir=None):
    dirs = [model_dir] if model_dir else [os.environ.get('VIDEOBUILDER_KOKORO_DIR'), *MODEL_DIRS]
    for d in dirs:
        if d and Path(d).expanduser().joinpath(name).is_file():
            return Path(d).expanduser() / name
    return None


class Kokoro:
    """Kokoro through kokoro-onnx. The only part of this module that imports it."""

    def __init__(self, model=None, voices=None, model_dir=None):
        # find_spec, not import: listing voices (capabilities import time) must not pay for onnxruntime.
        loaded = sys.modules.get('kokoro_onnx', False)   # None there means "import refused"
        if loaded is None or (loaded is False and importlib.util.find_spec('kokoro_onnx') is None):
            raise SpeechUnavailable(INSTALL_HINT)
        self.voices_path = Path(voices) if voices else _find(VOICES_FILE, model_dir)
        self.model_path = Path(model) if model else next(
            (p for p in (_find(m, model_dir) for m in MODEL_FILES) if p), None)
        self._kokoro = None
        self._tokenizer = None

    def _need(self, *paths):
        missing = [p for p in paths if not p or not Path(p).is_file()]
        if missing:
            raise SpeechUnavailable(f'Kokoro model files not found. {INSTALL_HINT}')

    @property
    def kokoro(self):
        if self._kokoro is None:
            self._need(self.model_path, self.voices_path)
            from kokoro_onnx import Kokoro as K
            self._kokoro = K(str(self.model_path), str(self.voices_path))
        return self._kokoro

    @property
    def model_id(self):
        return f'{self.model_path.name}+{self.voices_path.name}' if self.model_path and self.voices_path else None

    def voices(self):
        self._need(self.voices_path)
        import numpy as np
        with np.load(self.voices_path) as v:
            return sorted(v.files)

    def phonemize(self, text, lang):
        """espeak's phonemes for `text`, as the tokenizer's own `phonemize`
        gives them but with each sound espeak counts as one tied by `^`
        (`t^ʃ` in "church", not the t + ʃ of "nutshell"; see `single_symbols`)."""
        if self._tokenizer is None:
            from kokoro_onnx.tokenizer import Tokenizer
            self._tokenizer = Tokenizer()   # also points phonemizer at its espeak
        import phonemizer
        out = phonemizer.phonemize(text.strip(), lang, preserve_punctuation=True, with_stress=True, tie=TIE)
        return ''.join(c for c in out if c in self._tokenizer.vocab or c == TIE).strip()

    def synth(self, phonemes, voice, speed, lang):
        """16-bit mono samples at RATE for a phoneme string."""
        import numpy as np
        k = self.kokoro
        if voice not in k.voices:
            raise ValueError(f'no voice {voice!r}; see `say --list-voices`')
        samples, rate = k.create(phonemes, voice=voice, speed=speed, lang=lang, is_phonemes=True)
        if rate != RATE:
            raise ValueError(f'Kokoro returned {rate} Hz, expected {RATE}')
        return array.array('h', (np.clip(samples, -1, 1) * 32767).round().astype('<i2').tobytes())


def _chatterbox_python(python=None):
    python = python or os.environ.get('VIDEOBUILDER_CHATTERBOX_PYTHON') or CHATTERBOX_PYTHON
    if not (Path(python).is_file() and os.access(python, os.X_OK)):
        raise SpeechUnavailable(f'no Chatterbox interpreter at {python}. {CHATTERBOX_HINT}')
    return python


def _chatterbox_cache_dir(cache_dir=None):
    cache = os.environ.get('VIDEOBUILDER_CHATTERBOX_CACHE')
    return cache_dir or cache or (CHATTERBOX_CACHE if Path(CHATTERBOX_CACHE).is_dir() else None)


def _worker_reply(proc):
    line = proc.stdout.readline()
    if not line:
        raise SpeechUnavailable(f'the Chatterbox worker exited ({proc.wait()}) without answering; '
                                'its own message, if any, is above')
    try:
        msg = json.loads(line)
    except ValueError:
        raise SpeechUnavailable(f'the Chatterbox worker said {line.strip()[:200]!r}, not JSON') from None
    if 'error' in msg:
        raise SpeechUnavailable(f"Chatterbox: {msg['error']}" + (f'. {CHATTERBOX_HINT}' if msg.get('install') else ''))
    return msg


class Chatterbox:
    """Chatterbox (Resemble AI) through chatterbox_worker.py, run in its own
    interpreter ($VIDEOBUILDER_CHATTERBOX_PYTHON): one process per `say`,
    loading the model once for all its phrases. It reads text, not phonemes,
    and speaks English in its built-in voice, or in the voice of `voice` (a
    reference clip)."""
    speaks_text = True
    engine_name = 'Chatterbox'
    model_id = f'{CHATTERBOX_REPO}@{CHATTERBOX_REVISION}'

    def __init__(self, voice=None, seed=0, exaggeration=0.4, cfg_weight=0.5, python=None, cache_dir=None):
        if voice is not None and not Path(voice).is_file():
            raise ValueError(f'no voice clip {voice!r}: with --engine chatterbox, --voice is a .wav of the voice '
                             "to speak in (default: Chatterbox's built-in voice), not a Kokoro voice name")
        self.python = _chatterbox_python(python)
        self.cache_dir = _chatterbox_cache_dir(cache_dir)
        self.voice = voice
        self.voice_sha256 = hashlib.sha256(Path(voice).read_bytes()).hexdigest() if voice else None
        self.seed, self.exaggeration, self.cfg_weight = seed, exaggeration, cfg_weight

    def settings(self):
        """What, beside the text, decides the audio: `say`'s inputs."""
        return {'engine': 'chatterbox', 'model': self.model_id, 'seed': self.seed,
                'exaggeration': self.exaggeration, 'cfg_weight': self.cfg_weight,
                'voice': Path(self.voice).as_posix() if self.voice else None, 'voice_sha256': self.voice_sha256}

    def synth_all(self, texts):
        """16-bit mono samples at RATE for each text, in order."""
        cmd = [self.python, str(CHATTERBOX_WORKER), '--repo', CHATTERBOX_REPO, '--revision', CHATTERBOX_REVISION,
               '--seed', str(self.seed), '--exaggeration', repr(self.exaggeration),
               '--cfg-weight', repr(self.cfg_weight)]
        if self.cache_dir:
            cmd += ['--cache-dir', str(self.cache_dir)]
        if self.voice:
            cmd += ['--voice', str(Path(self.voice).resolve())]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
        except OSError as e:
            raise SpeechUnavailable(f'could not run {self.python}: {e}. {CHATTERBOX_HINT}') from None
        out = []
        with proc:
            try:
                ready = _worker_reply(proc)
                if ready.get('rate') != RATE:
                    raise SpeechUnavailable(f"Chatterbox makes {ready.get('rate')} Hz, expected {RATE}")
                for i, text in enumerate(texts):
                    print(f'chatterbox {i + 1}/{len(texts)}: {text}', file=sys.stderr, flush=True)
                    proc.stdin.write(json.dumps({'text': text}, ensure_ascii=False) + '\n')
                    proc.stdin.flush()
                    s = array.array('h', base64.b64decode(_worker_reply(proc)['samples']))
                    out.append(s if sys.byteorder == 'little' else _swapped(s))
            finally:
                proc.stdin.close()
                if proc.poll() is None and len(out) < len(texts):
                    proc.kill()
        return out


class ChatterboxOps:
    """Voice conversion and transcript checking for `say --engine gemini`
    (`--convert-to`, the transcript check), through chatterbox_worker.py run
    with `--ops` set to whichever of convert/transcribe it is asked for: one
    process for the whole `say` call, each model loaded once, started lazily
    on first use so a `say` that needs neither starts no worker at all."""

    def __init__(self, convert_to=None, transcribe=False, python=None, cache_dir=None):
        self.convert_to = convert_to
        self.ops = [op for op, on in (('convert', convert_to is not None), ('transcribe', transcribe)) if on]
        self._python_arg, self._cache_dir_arg = python, cache_dir
        self.proc = None

    def _start(self):
        if self.proc is not None:
            return
        python = _chatterbox_python(self._python_arg)
        cmd = [python, str(CHATTERBOX_WORKER), '--ops', ','.join(self.ops)]
        if 'convert' in self.ops:
            cache_dir = _chatterbox_cache_dir(self._cache_dir_arg)
            cmd += ['--repo', CHATTERBOX_REPO, '--revision', CHATTERBOX_REVISION,
                   '--convert-to', str(Path(self.convert_to).resolve())]
            if cache_dir:
                cmd += ['--cache-dir', str(cache_dir)]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
        except OSError as e:
            raise SpeechUnavailable(f'could not run {python}: {e}. {CHATTERBOX_HINT}') from None
        ready = _worker_reply(proc)
        if 'convert' in self.ops and ready.get('rate') != RATE:
            proc.stdin.close()
            raise SpeechUnavailable(f"Chatterbox's voice converter makes {ready.get('rate')} Hz, expected {RATE}")
        self.proc = proc

    def _call(self, **req):
        self._start()
        self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + '\n')
        self.proc.stdin.flush()
        return _worker_reply(self.proc)

    def convert(self, samples):
        """`samples` (16-bit mono at RATE), spoken in the --convert-to voice."""
        pcm = samples.tobytes() if sys.byteorder == 'little' else _swapped(samples).tobytes()
        reply = self._call(convert=base64.b64encode(pcm).decode('ascii'))
        s = array.array('h', base64.b64decode(reply['samples']))
        return s if sys.byteorder == 'little' else _swapped(s)

    def transcribe(self, samples):
        """The words faster-whisper hears in `samples` (16-bit mono at RATE)."""
        pcm = samples.tobytes() if sys.byteorder == 'little' else _swapped(samples).tobytes()
        return self._call(transcribe=base64.b64encode(pcm).decode('ascii'))['transcript']

    def close(self):
        if self.proc is not None:
            self.proc.stdin.close()
            if self.proc.poll() is None:
                self.proc.wait()
            self.proc = None


_GEMINI_UNSUPPORTED = re.compile(r'speech.?metadata|\bstyle\b', re.IGNORECASE)
_GEMINI_RATE = re.compile(r'rate=(\d+)')


def _gemini_context(previous):
    """The style direction's context clause for the phrase after `previous`
    (its own spoken text), so the model hears the sentence before the one it
    reads; never spoken itself. None for the first phrase."""
    if previous is None:
        return None
    return f"This continues straight on from the narrator's previous sentence: \"{previous}\""


def _gemini_style(style, previous):
    """`style` with `_gemini_context(previous)` appended, or `style` alone
    for the first phrase (`previous` is None)."""
    ctx = _gemini_context(previous)
    if ctx is None:
        return style or ''
    return f'{style} {ctx}' if style else ctx


def _gemini_error(code, payload, model):
    try:
        msg = json.loads(payload)['error']['message']
    except (ValueError, KeyError, TypeError):
        msg = payload.decode('utf-8', 'replace')[:300] if isinstance(payload, bytes) else str(payload)[:300]
    if code == 400 and _GEMINI_UNSUPPORTED.search(msg):
        return SpeechUnavailable(f'{model} does not support a style direction (--style): {msg}')
    return SpeechUnavailable(f'Gemini ({model}): {msg}')


class Gemini:
    """Gemini (Google), text to speech over the network: REST generateContent
    on v1beta, stdlib urllib only, needs $GEMINI_API_KEY. Reads text, like
    Chatterbox: no phonemes, `--say`/`--lexicon` don't apply. `style` is a
    natural-language direction for how to read the script (sent beside the
    text, never spoken); every phrase after the first also carries the
    previous phrase's own text as context (see `_gemini_style`), so the
    model hears the sentence before the one it reads. Gemini can't be
    seeded, so `say` keeps an unchanged phrase's committed audio rather than
    asking for a new, different-sounding take of it every run (see
    `_say_gemini`)."""
    speaks_text = True
    engine_name = 'Gemini'

    def __init__(self, voice=None, model=None, style=None, api_key=None):
        self.voice = voice or GEMINI_VOICE
        self.model = model or GEMINI_MODEL
        self.model_id = self.model
        self.style = style or ''
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise SpeechUnavailable(f'say --engine gemini needs $GEMINI_API_KEY. {GEMINI_HINT}')
        self.url = (os.environ.get('VIDEOBUILDER_GEMINI_URL') or GEMINI_URL).format(model=self.model)

    def settings(self):
        """What, beside the text, decides the audio: `say`'s inputs."""
        return {'engine': 'gemini', 'model': self.model, 'voice': self.voice, 'style': self.style}

    def synth_one(self, text, style):
        """16-bit mono samples at RATE for one phrase, `style` already
        carrying any previous-phrase context (see `_gemini_style`)."""
        part = {'text': text}
        if style:
            part['speech_metadata'] = {'style': style}
        body = {
            'contents': [{'parts': [part]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': self.voice}}},
            },
        }
        reply = self._post(body)
        return self._audio(reply)

    def _post(self, body):
        data = json.dumps(body).encode('utf-8')
        headers = {'Content-Type': 'application/json', 'x-goog-api-key': self.api_key}
        for attempt in range(GEMINI_HTTP_RETRIES):
            req = urllib.request.Request(self.url, data=data, headers=headers, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=GEMINI_TIMEOUT) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                payload = e.read()
                retryable = e.code == 429 or 500 <= e.code < 600
                if retryable and attempt < GEMINI_HTTP_RETRIES - 1:
                    time.sleep(GEMINI_BACKOFF * (2 ** attempt))
                    continue
                raise _gemini_error(e.code, payload, self.model) from None
            except urllib.error.URLError as e:
                raise SpeechUnavailable(f'Gemini: could not reach {self.url}: {e.reason}') from None

    def _audio(self, reply):
        try:
            parts = reply['candidates'][0]['content']['parts']
            inline = next(p['inlineData'] for p in parts if 'inlineData' in p)
            mime, data = inline['mimeType'], inline['data']
        except (KeyError, IndexError, StopIteration, TypeError):
            raise SpeechUnavailable(f'Gemini ({self.model}) returned no audio: '
                                    f'{json.dumps(reply)[:300]}') from None
        m = _GEMINI_RATE.search(mime)
        if not m or int(m.group(1)) != RATE:
            raise SpeechUnavailable(f'Gemini ({self.model}) returned {mime}, expected {RATE} Hz 16-bit PCM')
        samples = array.array('h', base64.b64decode(data))
        return samples if sys.byteorder == 'little' else _swapped(samples)


def voice_options(engine=None):
    """Every voice `engine` (default a fresh `Kokoro()`) actually has, as
    settings.Option (see `say --list-voices`, which lists the same thing) --
    never a hardcoded list. Falls back to one option for `DEFAULT_VOICE`
    when there's no engine at all (no model files installed), so this never
    needs Kokoro to be present."""
    from .capabilities.settings import Option
    try:
        voices = (engine or Kokoro()).voices()
    except SpeechUnavailable:
        voices = (DEFAULT_VOICE,)
    out = []
    for v in voices:
        lang = LANGS.get(v[:1], '?')
        sex = 'female' if v[1:2] == 'f' else 'male' if v[1:2] == 'm' else ''
        # The settings card's play button, at the editor's own
        # api/narration/voice-sample (video_api.py); relative, like
        # director.js's api(), so it still resolves under a library's
        # /v/<name>/ prefix. Speed isn't part of this URL, so a preview
        # always auditions the voice at its natural pace.
        out.append(Option(f"{v}  ({lang}{', ' + sex if sex else ''})", v,
                          preview=f'api/narration/voice-sample?voice={v}'))
    return tuple(out)


@lru_cache(maxsize=None)
def narration_settings():
    """The settings narration shares everywhere it's offered (the
    `narration` and `voiceover` capabilities, see capabilities/sound/narration.py
    and capabilities/sound/voiceover.py) --
    one definition, so the two can't drift: voice (this installation's own
    Kokoro voices) and speed (`say`'s own 0.5 to 2.0 range). Cached: called
    from more than one place, and real voices never change mid-process."""
    from .capabilities.settings import Choice, Number
    return (Choice('voice', 'Voice', options=voice_options(), default=DEFAULT_VOICE),
            Number('speed', 'Speed', min=0.5, max=2.0, step=0.1, default=1.0))


_ONES = ('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen '
         'sixteen seventeen eighteen nineteen').split()
_TENS = ('', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety')
# 1100-1999 standing alone: not inside a longer number ("1,863", "1863.5"), a word ("1860s") or money.
_YEAR = re.compile(r'(?<![\w$£€.,])(1[1-9]\d\d)(?![\w%]|[.,]\d)')


def _two_digits(n):
    return _ONES[n] if n < 20 else _TENS[n // 10] + (f'-{_ONES[n % 10]}' if n % 10 else '')


def year_words(year):
    """A year the way it is said in English: 1863 "eighteen sixty-three",
    1805 "eighteen oh five", 1900 "nineteen hundred"."""
    hi, lo = divmod(year, 100)
    return _two_digits(hi) + (' hundred' if lo == 0 else f' oh {_ONES[lo]}' if lo < 10 else ' ' + _two_digits(lo))


def spoken_years(text):
    """`text` with each standalone 1100-1999 read as a year, not a cardinal
    ("one thousand eight hundred..."). Read as a count it is still natural:
    "1500 eels" becomes "fifteen hundred eels". Later years stay as written,
    since "2024 eels" is not "twenty twenty-four eels"."""
    return _YEAR.sub(lambda m: year_words(int(m.group(1))), text)


# Kokoro v1.0 was trained on one symbol for each of these two-part sounds,
# but espeak (and IPA copied from a dictionary) writes them as two, which the
# voice reads apart: "Freud" as "fried". A stress mark always comes before
# the vowel, never between the parts, so a plain replace is enough -- except
# that espeak also writes the t + ʃ of "nutshell" as `tʃ`, so its output is
# merged only where espeak tied the two (`TIE`), the way Kokoro's own G2P does.
SINGLE_SYMBOLS = (('eɪ', 'A'), ('aɪ', 'I'), ('aʊ', 'W'), ('ɔɪ', 'Y'), ('oʊ', 'O'), ('əʊ', 'Q'),
                  ('tʃ', 'ʧ'), ('dʒ', 'ʤ'))
TIE = '^'


def single_symbols(phonemes, tied=False):
    """`phonemes` with each two-part sound as Kokoro's single symbol. `tied`:
    espeak's output, where only a pair joined by `TIE` is one sound (any
    other tie, such as `ɛ^ɹ`, is dropped); otherwise typed IPA, with no ties."""
    for two, one in SINGLE_SYMBOLS:
        phonemes = phonemes.replace(two[0] + TIE + two[1] if tied else two, one)
    return phonemes.replace(TIE, '') if tied else phonemes


def phonemes_for(engine, parts, lang):
    """One phoneme string for a phrase's spoken parts, espeak's and the
    writer's alike, with Kokoro's single symbols (see `single_symbols`). A
    break is a comma, as if typed, but only between two sounds that have no
    punctuation between them already."""
    out = ''
    pause = False
    for kind, s in parts:
        if kind == 'break':
            pause = True
            continue
        if kind == 'text' and lang.startswith('en'):
            s = spoken_years(s)
        p = (single_symbols(s.strip()) if kind == 'phonemes'
             else single_symbols(engine.phonemize(s, lang), tied=True).strip())
        if p:
            if pause and out and out[-1] not in _PUNCT and p[0] not in _PUNCT:
                out += ','
            out += p if not out or p[0] in _PUNCT else ' ' + p
            pause = False
    return out


def _audible(samples, rate, floor_db=-45, window=0.01):
    """(first, last) sample of the audible span: 10 ms windows louder than
    `floor_db` dBFS. (0, 0) for silence."""
    n = max(1, int(rate * window))
    floor = (10 ** (floor_db / 20) * 32767) ** 2 * n
    loud = [i for i in range(0, len(samples), n) if sum(v * v for v in samples[i:i + n]) >= floor]
    if not loud:
        return 0, 0
    return loud[0], min(len(samples), loud[-1] + n)


@dataclass(frozen=True)
class _Reused:
    """A phrase's samples straight from the old committed WAV (see
    `_say_gemini`): already trimmed and faded by a previous `_assemble_with_bounds`
    call, so this one must place them as-is, with no further trim or fade --
    an unchanged phrase's bytes never move. `inner` is (start, end), the
    audible span's offset into `samples`, for the new cue span."""
    samples: array.array
    inner: tuple


def _assemble_with_bounds(chunks, rate, gap=0.35, margin=0.03, fade=0.005):
    """`assemble`, and also each piece's (start, end) sample bounds on the
    joined clock -- where its bytes sit in the output, pad and fade
    included -- so a later run can reuse an unchanged phrase's exact bytes
    (see `_Reused`, `_say_gemini`)."""
    out = array.array('h')
    spans, bounds = [], []
    pad, ramp = int(margin * rate), max(1, int(fade * rate))
    for i, s in enumerate(chunks):
        if isinstance(s, _Reused):
            piece, (inner_a, inner_z) = s.samples, s.inner
        else:
            a, z = _audible(s, rate)
            if z <= a:
                raise ValueError(f'phrase {i + 1} came out silent')
            a0, z0 = max(0, a - pad), min(len(s), z + pad)
            piece = array.array('h', s[a0:z0])
            # Kokoro's phrase edges aren't always at a zero crossing: a few ms of fade keeps the join from clicking.
            for k in range(min(ramp, len(piece))):
                g = k / ramp
                piece[k] = int(piece[k] * g)
                piece[-1 - k] = int(piece[-1 - k] * g)
            inner_a, inner_z = a - a0, z - a0
        if i:
            out.extend(array.array('h', bytes(2 * round(gap * rate))))
        base = len(out)
        spans.append(((base + inner_a) / rate, (base + inner_z) / rate))
        bounds.append((base, base + len(piece)))
        out.extend(piece)
    return out, spans, bounds


def assemble(chunks, rate, gap=0.35, margin=0.03, fade=0.005):
    """Join each phrase's samples, trimmed to its audible span plus `margin`
    s, with `gap` s of silence between. Returns (samples, [(start, end)] in
    seconds): each phrase's audible span on the joined clock."""
    samples, spans, _ = _assemble_with_bounds(chunks, rate, gap, margin, fade)
    return samples, spans


def _ts(t):
    ms = round(t * 1000)
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}'


def vtt(cues):
    """WebVTT text for [(text, start, end)]: one cue per phrase."""
    lines = ['WEBVTT', '']
    for text, a, z in cues:
        lines += [f'{_ts(a)} --> {_ts(z)}', text, '']
    return '\n'.join(lines)


def _write_wav(path, samples, rate):
    tmp = f'{path}.{os.getpid()}.tmp'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes() if sys.byteorder == 'little' else _swapped(samples).tobytes())
    os.replace(tmp, path)


def _swapped(samples):
    s = array.array('h', samples)
    s.byteswap()
    return s


def _write_text(path, s):
    tmp = f'{path}.{os.getpid()}.tmp'
    Path(tmp).write_text(s, encoding='utf-8')
    os.replace(tmp, path)


def sidecars(out):
    out = Path(out)
    return out.with_suffix('.vtt'), out.with_suffix('.json')


def say(script, out, engine, voice=DEFAULT_VOICE, speed=1.0, lang=None, gap=0.35, lexicon=None, force=False):
    """Synthesize `script` to `out` (.wav) and its .vtt/.json sidecars, and
    return the sidecar's dict. With the same inputs as the committed sidecar
    and the WAV present, writes nothing (returns it with 'unchanged': True),
    so a re-run never churns the repo even where Kokoro's floating point
    differs between machines."""
    out = Path(out)
    if out.suffix.lower() != '.wav':
        raise ValueError(f'{out}: say writes a .wav')
    reads_text = getattr(engine, 'speaks_text', False)
    if reads_text and speed != 1.0:
        raise ValueError(f"speed {speed}: {getattr(engine, 'engine_name', 'this engine')} has no speed setting")
    if not 0.5 <= speed <= 2.0:
        raise ValueError(f'speed {speed} is out of range: Kokoro takes 0.5 to 2.0')
    if isinstance(engine, Gemini):
        return _say_gemini(engine, script, out, gap, force)
    lang = lang or LANGS.get(voice[:1], 'en-us')
    items = phrases(script)
    if not items:
        raise ValueError('the script has no phrases: write one phrase or sentence per line')
    if reads_text:
        # The text the voice reads is the captions' own: `|` and phonemes have no meaning there.
        texts = [caption_text(p) for p in items]
        if lexicon or any(_INLINE.search(p) for p in items):
            print("say: Chatterbox reads text, not phonemes: [word](/phonemes/) speaks the word as written, "
                  'and --say/--lexicon respellings do not apply', file=sys.stderr)
        inputs = {'phrases': texts, 'gap': gap, **engine.settings()}
    else:
        inputs = {'phrases': items, 'voice': voice, 'speed': speed, 'lang': lang, 'gap': gap,
                  'lexicon': dict(sorted((lexicon or {}).items())), 'model': getattr(engine, 'model_id', None)}
    vtt_path, json_path = sidecars(out)
    if not force and out.is_file() and vtt_path.is_file() and json_path.is_file():
        try:
            old = json.loads(json_path.read_text(encoding='utf-8'))
        except ValueError:
            old = {}
        if old.get('inputs') == inputs:
            return {**old, 'unchanged': True}
    if reads_text:
        chunks = engine.synth_all(texts)
    else:
        chunks = []
        for p in items:
            ph = phonemes_for(engine, spoken_parts(p, lexicon), lang)
            chunks.append(engine.synth(ph, voice, speed, lang))
    samples, spans = assemble(chunks, RATE, gap=gap)
    cues = [(caption_text(p), round(a, 3), round(z, 3)) for p, (a, z) in zip(items, spans)]
    doc = {'audio': out.name, 'captions': vtt_path.name, 'seconds': round(len(samples) / RATE, 3),
           'phrases': [{'text': t, 'start': a, 'end': z} for t, a, z in cues], 'inputs': inputs,
           'sha256': hashlib.sha256(samples.tobytes()).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out, samples, RATE)
    _write_text(vtt_path, vtt(cues))
    _write_text(json_path, json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    return doc


def _reuse(old_samples, old_cue, bounds):
    """An unchanged phrase's `_Reused` chunk, sliced straight out of the old
    committed WAV at `bounds` (that phrase's (start, end) sample bounds, see
    `_assemble_with_bounds`); `old_cue` (that phrase's old {'start', 'end'})
    locates its audible span inside the slice. None where there is nothing
    to reuse (no prior run, or `bounds` no longer fits the old WAV)."""
    if not bounds or old_cue is None or old_samples is None:
        return None
    b, e = bounds
    if not (0 <= b <= e <= len(old_samples)):
        return None
    inner = round(old_cue['start'] * RATE) - b, round(old_cue['end'] * RATE) - b
    return _Reused(array.array('h', old_samples[b:e]), inner)


def _say_gemini(engine, script, out, gap, force):
    """`say` for `Gemini`: unlike Kokoro and Chatterbox, Gemini can't be
    seeded, so a changed phrase can't just be redone with the same take as
    last time -- every call gives a different one. Instead, each phrase is
    cached on its own: `doc['phrase_cache']` records what decided its audio
    (its text, its style with context, and the engine's settings), and a
    phrase whose record is still exactly that is sliced straight out of the
    old committed WAV (`_reuse`) instead of asked for again. Editing one
    phrase changes its own record and, because the next phrase's style
    quotes it as context, the next phrase's record too -- so exactly those
    two are redone, and nothing else moves."""
    items = phrases(script)
    if not items:
        raise ValueError('the script has no phrases: write one phrase or sentence per line')
    texts = [caption_text(p) for p in items]
    if any(_INLINE.search(p) for p in items):
        print(f'say: {engine.engine_name} reads text, not phonemes: [word](/phonemes/) speaks the word as '
              'written, and --say/--lexicon respellings do not apply', file=sys.stderr)
    styles, previous = [], None
    for t in texts:
        styles.append(_gemini_style(engine.style, previous))
        previous = t
    settings = engine.settings()
    # settings() has its own 'style' (the raw --style, no context): text/style must win, so they
    # come after it, or an unchanged phrase whose context changed would wrongly look unchanged.
    keys = [{**settings, 'text': t, 'style': s} for t, s in zip(texts, styles)]
    inputs = {'phrases': texts, 'gap': gap, **settings}
    vtt_path, json_path = sidecars(out)
    old = {}
    if not force and out.is_file() and vtt_path.is_file() and json_path.is_file():
        try:
            old = json.loads(json_path.read_text(encoding='utf-8'))
        except ValueError:
            old = {}
        if old.get('inputs') == inputs:
            return {**old, 'unchanged': True}
    old_cache, old_cues = old.get('phrase_cache') or [], old.get('phrases') or []
    old_samples = read_samples(out)[0] if old_cache and out.is_file() else None
    chunks = []
    for i, (text, style, key) in enumerate(zip(texts, styles, keys)):
        reused = None
        if old_samples is not None and i < len(old_cache) and old_cache[i].get('key') == key:
            reused = _reuse(old_samples, old_cues[i] if i < len(old_cues) else None, old_cache[i].get('bounds'))
        chunks.append(reused if reused is not None else engine.synth_one(text, style))
    samples, spans, bounds = _assemble_with_bounds(chunks, RATE, gap=gap)
    cues = [(t, round(a, 3), round(z, 3)) for t, (a, z) in zip(texts, spans)]
    doc = {'audio': out.name, 'captions': vtt_path.name, 'seconds': round(len(samples) / RATE, 3),
           'phrases': [{'text': t, 'start': a, 'end': z} for t, a, z in cues], 'inputs': inputs,
           'phrase_cache': [{'key': k, 'bounds': list(b)} for k, b in zip(keys, bounds)],
           'sha256': hashlib.sha256(samples.tobytes()).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out, samples, RATE)
    _write_text(vtt_path, vtt(cues))
    _write_text(json_path, json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    return doc


# ---- at render time: no model, just the committed files ----
def read_samples(path, rate=None):
    """(mono 16-bit samples, rate) of an audio file: a 16-bit WAV directly,
    anything else (or a resample to `rate`) through ffmpeg."""
    path = str(path)
    if path.lower().endswith('.wav') and rate is None:
        try:
            with wave.open(path, 'rb') as w:
                if w.getsampwidth() == 2:
                    ch, r = w.getnchannels(), w.getframerate()
                    s = array.array('h', w.readframes(w.getnframes()))
                    if sys.byteorder != 'little':
                        s.byteswap()
                    return (s if ch == 1 else array.array('h', s[::ch])), r
        except wave.Error:
            pass
    rate = rate or RATE
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(rate), '-'],
                         capture_output=True, check=True).stdout
    s = array.array('h', raw)
    if sys.byteorder != 'little':
        s.byteswap()
    return s, rate


def levels(samples, rate, fps):
    """RMS level per video frame, in dB relative to the loudest frame (0 at
    the loudest, -120 for silence)."""
    import math
    per = rate / fps
    out = []
    for f in range(math.ceil(len(samples) / per)):
        a, z = round(f * per), min(len(samples), round((f + 1) * per))
        ms = sum(v * v for v in samples[a:z]) / max(1, z - a)
        out.append(ms)
    peak = max(out, default=0)
    return [10 * math.log10(ms / peak) if ms > 0 and peak > 0 else -120.0 for ms in out]


def flaps(db, open_db=-24.0, close_db=-30.0, dip_db=5.0, hold=2, max_open=6):
    """Mouth open per frame from `levels`. It opens above `open_db` and
    stays open above `close_db` (the hysteresis), but only near a syllable's
    peak: within `dip_db` of the loudest of the last three frames, so it
    shuts in the dips between syllables. Looking back only, so it opens on
    the frame the sound rises, not when the peak comes. Every open or shut lasts at least `hold`
    frames, so it never flickers, and a long vowel shuts for `hold` frames
    after `max_open` frames open, so a held sound still reads as talking."""
    out, state, held = [], False, hold
    for i, v in enumerate(db):
        peak = max(db[max(0, i - 2):i + 1])
        want = v >= (close_db if state else open_db) and v >= peak - dip_db
        if state and held >= max_open:
            want = False
        if want != state and held >= hold:
            state, held = want, 0
        out.append(state)
        held += 1
    return out


def mouth(path, fps, at=0, frames=None, **kw):
    """Per film frame (0..`frames`), whether a mouth saying the audio at
    `path`, starting on frame `at`, is open. `kw` tunes `flaps`."""
    s, r = read_samples(path)
    m = flaps(levels(s, r, fps), **kw)
    frames = at + len(m) if frames is None else frames
    return tuple(0 <= n - at < len(m) and m[n - at] for n in range(frames))


def holds(opened, open_pose='talk', shut_pose='idle'):
    """`Puppet.pose_at` holds from a per-frame `mouth`: a hold at every change."""
    out = []
    for n, o in enumerate(opened):
        pose = open_pose if o else shut_pose
        if not out or out[-1][1] != pose:
            out.append((n, pose))
    return out or [(0, shut_pose)]


@dataclass(frozen=True)
class Phrase:
    text: str
    start: float
    end: float


class Narration:
    """A `say` output: the WAV and its sidecars, read once."""

    def __init__(self, path):
        from . import captions
        self.path = str(path)
        vtt_path, json_path = sidecars(path)
        doc = json.loads(Path(json_path).read_text(encoding='utf-8'))
        self.phrases = tuple(Phrase(p['text'], p['start'], p['end']) for p in doc['phrases'])
        self.seconds = doc['seconds']
        self.track = captions.load(vtt_path)
        self._mouth = {}

    def frames(self, fps):
        import math
        return math.ceil(self.seconds * fps)

    def sound(self, at, fps=30, gain_db=0.0):
        """The narration as a `vb.Sound` starting on film frame `at`."""
        from .film import Sound
        return Sound(self.path, at=at, start=0.0, frames=self.frames(fps), gain_db=gain_db,
                     fade_in_frames=0, fade_out_frames=0)

    def track_at(self, at, fps=30):
        """The captions on the film's clock, for narration starting on frame `at`."""
        return self.track.shift(at / fps)

    def mouth(self, fps, at=0, frames=None, **kw):
        key = (fps, at, frames, tuple(sorted(kw.items())))
        if key not in self._mouth:
            self._mouth[key] = mouth(self.path, fps, at, frames, **kw)
        return self._mouth[key]


def load(path):
    return Narration(path)
