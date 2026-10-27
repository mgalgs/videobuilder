"""Chatterbox (Resemble AI) as its own process, for `say --engine chatterbox`
and, for `say --engine gemini`, voice conversion (`--convert-to`) and the
transcript check (on by default; see speech.ChatterboxOps).

Chatterbox pins a torch that videobuilder's own Python can't install, so
speech.Chatterbox and speech.ChatterboxOps run this file with Chatterbox's
interpreter ($VIDEOBUILDER_CHATTERBOX_PYTHON). It imports only the stdlib,
torch, chatterbox (with the watermarker, numpy and hub client chatterbox
brings) and faster-whisper, never videobuilder:

    python chatterbox_worker.py --ops synth --repo ResembleAI/chatterbox --revision <sha> \\
        [--cache-dir D] [--voice clip.wav] --seed 0 --exaggeration 0.4 --cfg-weight 0.5
    python chatterbox_worker.py --ops convert --repo ResembleAI/chatterbox --revision <sha> \\
        [--cache-dir D] --convert-to clip.wav
    python chatterbox_worker.py --ops transcribe [--cache-dir D]
    python chatterbox_worker.py --ops convert,transcribe ... --convert-to clip.wav

`--ops` (comma-separated: synth, convert, transcribe) says which of the
three models to load -- only those it needs. It loads them once and prints
one JSON line, {"ready": true, "rate": 24000}. Then for each JSON line it
reads: {"text": "..."} answers {"samples": "<base64 PCM>"} (synth, seeding
first so a phrase's audio depends only on its text and the settings);
{"convert": "<base64 PCM, RATE Hz mono>"} answers {"samples": "<base64
PCM>"}, that audio spoken in the --convert-to voice; {"transcribe":
"<base64 PCM, RATE Hz mono>"} answers {"transcript": "..."}. A failure is
one line {"error": "...", "install": true if something needed isn't
installed}, then exit 1. Whatever the libraries print goes to stderr,
never into the protocol.
"""
import argparse
import base64
import io
import json
import os
import random
import sys
import wave

# Chatterbox's sampler draws a tqdm bar per phrase on stderr, which `say`
# passes through; set before chatterbox (and so tqdm) is imported.
os.environ.setdefault('TQDM_DISABLE', '1')

RATE = 24000
# What ChatterboxTTS.from_local reads: the English model and its built-in voice.
FILES = ('ve.safetensors', 't3_cfg.safetensors', 's3gen.safetensors', 'tokenizer.json', 'conds.pt')
# What ChatterboxVC.from_local reads: a subset -- no T3 text model needed for voice conversion.
VC_FILES = ('s3gen.safetensors', 'conds.pt')
WHISPER_MODEL = 'small.en'
OPS = ('synth', 'convert', 'transcribe')


class Missing(Exception):
    """Something this op needs isn't installed in this interpreter."""


def _check_perth(perth):
    if getattr(perth, 'PerthImplicitWatermarker', None) is None:
        # perth swallows the ImportError that left its watermarker out; show it.
        try:
            from perth.perth_net.perth_net_implicit.perth_watermarker import PerthImplicitWatermarker  # noqa: F401
            why = 'it imported as None'
        except ImportError as e:
            why = f'{type(e).__name__}: {e}'
        raise Missing(f"Chatterbox's Perth watermarker did not load ({why}); resemble-perth imports "
                      "pkg_resources, which only setuptools<81 has: install 'setuptools<81' beside it")


def _snapshot(a, files, snapshot_download):
    want = dict(repo_id=a.repo, revision=a.revision, cache_dir=a.cache_dir, allow_patterns=list(files))
    try:
        return snapshot_download(**want, local_files_only=True)
    except Exception:
        try:
            return snapshot_download(**want)
        except Exception as e:
            raise RuntimeError(f'the Chatterbox weights {a.repo}@{a.revision} are not in '
                               f'{a.cache_dir or "the Hugging Face cache"} and could not be downloaded: {e}') from None


def load_tts(a):
    try:
        import perth
        import torch
        from chatterbox.tts import ChatterboxTTS
        from huggingface_hub import snapshot_download
    except ImportError as e:
        raise Missing(f'{type(e).__name__}: {e}') from None
    _check_perth(perth)
    ckpt = _snapshot(a, FILES, snapshot_download)
    seed(a.seed)
    model = ChatterboxTTS.from_local(ckpt, 'cpu')
    if a.voice:
        model.prepare_conditionals(a.voice, exaggeration=a.exaggeration)
    torch.set_grad_enabled(False)
    return model


def load_vc(a):
    try:
        import perth
        import torch
        from chatterbox.vc import ChatterboxVC
        from huggingface_hub import snapshot_download
    except ImportError as e:
        raise Missing(f'{type(e).__name__}: {e}') from None
    _check_perth(perth)
    ckpt = _snapshot(a, VC_FILES, snapshot_download)
    model = ChatterboxVC.from_local(ckpt, 'cpu')
    model.set_target_voice(a.convert_to)
    torch.set_grad_enabled(False)
    return model


def load_whisper(a):
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise Missing(f'{type(e).__name__}: {e}') from None
    return WhisperModel(WHISPER_MODEL, device='cpu', compute_type='int8', download_root=a.cache_dir)


def seed(n):
    import numpy
    import torch
    random.seed(n)
    numpy.random.seed(n)
    torch.manual_seed(n)


def synth(model, text, a):
    """16-bit little-endian mono samples at model.sr for one phrase."""
    import torch
    seed(a.seed)
    wav = model.generate(text, exaggeration=a.exaggeration, cfg_weight=a.cfg_weight)
    pcm = (wav.reshape(-1).clamp(-1, 1) * 32767).round().to(torch.int16)
    return pcm.numpy().astype('<i2').tobytes()


def _wav_buffer(pcm, rate=RATE):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    buf.seek(0)
    return buf


def convert(model, pcm):
    """16-bit little-endian mono samples at model.sr: `pcm` (RATE Hz mono),
    spoken in the --convert-to voice `load_vc` set as the target."""
    import torch
    wav = model.generate(_wav_buffer(pcm))
    samples = (wav.reshape(-1).clamp(-1, 1) * 32767).round().to(torch.int16)
    return samples.numpy().astype('<i2').tobytes()


def transcribe(model, pcm):
    """The words faster-whisper hears in `pcm` (RATE Hz mono), as one string."""
    segments, _ = model.transcribe(_wav_buffer(pcm))
    return ' '.join(s.text.strip() for s in segments).strip()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--ops', default='synth', help='comma-separated: synth, convert, transcribe')
    p.add_argument('--repo')
    p.add_argument('--revision')
    p.add_argument('--cache-dir')
    p.add_argument('--voice', help='synth: a reference clip to speak in (default: the built-in voice)')
    p.add_argument('--convert-to', help='convert: the reference clip every phrase is converted to')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--exaggeration', type=float, default=0.4)
    p.add_argument('--cfg-weight', type=float, default=0.5)
    a = p.parse_args(argv)
    ops = {o.strip() for o in a.ops.split(',') if o.strip()}
    if ops - set(OPS):
        p.error(f'--ops: unknown {sorted(ops - set(OPS))}')
    if ('synth' in ops or 'convert' in ops) and not (a.repo and a.revision):
        p.error('--repo and --revision are required for --ops synth or convert')
    if 'convert' in ops and not a.convert_to:
        p.error('--convert-to is required for --ops convert')
    # The protocol owns the real stdout; fd 1 (and sys.stdout) become stderr for everyone else.
    out = io.open(os.dup(1), 'w', encoding='utf-8')
    os.dup2(2, 1)
    sys.stdout = sys.stderr

    def send(**msg):
        out.write(json.dumps(msg) + '\n')
        out.flush()

    models = {}
    try:
        if 'synth' in ops:
            models['synth'] = load_tts(a)
        if 'convert' in ops:
            models['convert'] = load_vc(a)
        if 'transcribe' in ops:
            models['transcribe'] = load_whisper(a)
    except Missing as e:
        send(error=str(e), install=True)
        return 1
    except Exception as e:
        send(error=f'{type(e).__name__}: {e}')
        return 1
    rate = models['synth'].sr if 'synth' in models else models['convert'].sr if 'convert' in models else RATE
    send(ready=True, rate=rate)
    for line in io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8'):
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            if 'text' in req:
                reply = {'samples': base64.b64encode(synth(models['synth'], req['text'], a)).decode('ascii')}
            elif 'convert' in req:
                pcm = base64.b64decode(req['convert'])
                reply = {'samples': base64.b64encode(convert(models['convert'], pcm)).decode('ascii')}
            elif 'transcribe' in req:
                pcm = base64.b64decode(req['transcribe'])
                reply = {'transcript': transcribe(models['transcribe'], pcm)}
            else:
                raise ValueError(f'unknown request: {line.strip()[:200]!r}')
        except Exception as e:
            send(error=f'{type(e).__name__}: {e}')
            return 1
        send(**reply)
    return 0


if __name__ == '__main__':
    sys.exit(main())
