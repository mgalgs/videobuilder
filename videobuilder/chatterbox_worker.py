"""Chatterbox (Resemble AI) as its own process, for `say --engine chatterbox`.

Chatterbox pins a torch that videobuilder's own Python can't install, so
`speech.Chatterbox` runs this file with Chatterbox's interpreter
($VIDEOBUILDER_CHATTERBOX_PYTHON). It imports only the stdlib, torch and
chatterbox (with the watermarker, numpy and hub client chatterbox brings),
never videobuilder:

    python chatterbox_worker.py --repo ResembleAI/chatterbox --revision <sha> \\
        [--cache-dir D] [--voice clip.wav] --seed 0 --exaggeration 0.4 --cfg-weight 0.5

It loads the model once and prints one JSON line, {"ready": true, "rate":
24000}. Then for each JSON line {"text": "..."} it reads, it answers
{"samples": "<base64 of 16-bit little-endian mono>"}, seeding first so a
phrase's audio depends only on its text and the settings. A failure is one
line {"error": "...", "install": true if Chatterbox itself is missing},
then exit 1. Whatever the libraries print goes to stderr, never into the
protocol.
"""
import argparse
import base64
import io
import json
import os
import random
import sys

# What ChatterboxTTS.from_local reads: the English model and its built-in voice.
FILES = ('ve.safetensors', 't3_cfg.safetensors', 's3gen.safetensors', 'tokenizer.json', 'conds.pt')


class Missing(Exception):
    """Chatterbox, or something it needs, isn't installed in this interpreter."""


def load(a):
    try:
        import perth
        import torch
        from chatterbox.tts import ChatterboxTTS
        from huggingface_hub import snapshot_download
    except ImportError as e:
        raise Missing(f'{type(e).__name__}: {e}') from None
    if getattr(perth, 'PerthImplicitWatermarker', None) is None:
        # perth swallows the ImportError that left its watermarker out; show it.
        try:
            from perth.perth_net.perth_net_implicit.perth_watermarker import PerthImplicitWatermarker  # noqa: F401
            why = 'it imported as None'
        except ImportError as e:
            why = f'{type(e).__name__}: {e}'
        raise Missing(f"Chatterbox's Perth watermarker did not load ({why}); resemble-perth imports "
                      "pkg_resources, which only setuptools<81 has: install 'setuptools<81' beside it")
    want = dict(repo_id=a.repo, revision=a.revision, cache_dir=a.cache_dir, allow_patterns=list(FILES))
    try:
        ckpt = snapshot_download(**want, local_files_only=True)
    except Exception:
        try:
            ckpt = snapshot_download(**want)
        except Exception as e:
            raise RuntimeError(f'the Chatterbox weights {a.repo}@{a.revision} are not in '
                               f'{a.cache_dir or "the Hugging Face cache"} and could not be downloaded: {e}') from None
    seed(a.seed)
    model = ChatterboxTTS.from_local(ckpt, 'cpu')
    if a.voice:
        model.prepare_conditionals(a.voice, exaggeration=a.exaggeration)
    torch.set_grad_enabled(False)
    return model


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


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--repo', required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--cache-dir')
    p.add_argument('--voice', help='a reference clip to speak in (default: the built-in voice)')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--exaggeration', type=float, default=0.4)
    p.add_argument('--cfg-weight', type=float, default=0.5)
    a = p.parse_args(argv)
    # The protocol owns the real stdout; fd 1 (and sys.stdout) become stderr for everyone else.
    out = io.open(os.dup(1), 'w', encoding='utf-8')
    os.dup2(2, 1)
    sys.stdout = sys.stderr

    def send(**msg):
        out.write(json.dumps(msg) + '\n')
        out.flush()

    try:
        model = load(a)
    except Missing as e:
        send(error=str(e), install=True)
        return 1
    except Exception as e:
        send(error=f'{type(e).__name__}: {e}')
        return 1
    send(ready=True, rate=model.sr)
    for line in io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8'):
        if not line.strip():
            continue
        try:
            samples = synth(model, json.loads(line)['text'], a)
        except Exception as e:
            send(error=f'{type(e).__name__}: {e}')
            return 1
        send(samples=base64.b64encode(samples).decode('ascii'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
