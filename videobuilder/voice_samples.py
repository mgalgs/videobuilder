"""A short, fixed-sentence sample of a Kokoro voice, for the editor's voice
picker: rendered once per (voice, speed, engine) with the same `speech.say`
path narration itself uses, then cached on disk under the editor's state
dir, so previewing a voice never re-synthesizes it on every click. Never
used by the builder's render path -- see video_api.py's
GET /api/narration/voice-sample, the only caller.
"""
import hashlib
import threading
from pathlib import Path

from . import speech

SAMPLE_TEXT = 'This is how this voice sounds, read at a steady, natural pace.'


class UnknownVoice(KeyError):
    pass


class VoiceSamples:
    """`path(voice, speed)` is this sample's .wav, rendered and cached on
    first request. A lock per cache key makes two concurrent first requests
    for the same voice render once, the second simply waiting for the
    first's file."""

    def __init__(self, state_dir, engine_factory=None):
        self.dir = Path(state_dir) / 'voice-samples'
        self._engine_factory = engine_factory or speech.Kokoro
        self._lock = threading.Lock()
        self._key_locks = {}

    def _key_lock(self, key):
        with self._lock:
            return self._key_locks.setdefault(key, threading.Lock())

    def path(self, voice, speed):
        """Raises `UnknownVoice` for a voice this engine doesn't have, or
        `speech.SpeechUnavailable` when there is no engine at all."""
        engine = self._engine_factory()
        if voice not in engine.voices():
            raise UnknownVoice(voice)
        key = hashlib.sha256(f'{voice}|{speed}|{engine.model_id}'.encode()).hexdigest()[:24]
        out = self.dir / f'{key}.wav'
        with self._key_lock(key):
            self.dir.mkdir(parents=True, exist_ok=True)
            speech.say(SAMPLE_TEXT, out, engine, voice=voice, speed=speed)
        return out
