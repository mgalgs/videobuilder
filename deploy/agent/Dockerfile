# The builder agent's base: the editor image plus ManimGX for 3D shots and
# Chatterbox for narration.
# fork-sandbox's build-sandbox-image.sh --base layers the agent tooling on
# top of this, and needs the image to end as root.
#
#   docker build --build-arg BASE=<editor base image> -f deploy/agent/Dockerfile deploy/agent
#
# ManimGX's wheels are GPL-3 (they bundle x264), so it stays out of the
# editor image: only authors render shots; films read the committed MP4.
ARG BASE
FROM ${BASE}
USER root
# rsvg-convert renders gathered or uploaded SVGs to PNG at any size.
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-bin \
    && rm -rf /var/lib/apt/lists/* && rsvg-convert --version
RUN python3 -m venv --system-site-packages /opt/manimgx \
    && /opt/manimgx/bin/pip install --no-cache-dir manimgx==0.1.1 \
    && /opt/manimgx/bin/python -c 'import manimgx'
# Chatterbox, `say --engine chatterbox`'s voice, in its own venv at
# /opt/chatterbox (speech.CHATTERBOX_PYTHON): it pins a torch videobuilder's
# Python doesn't share. CPU-only torch, from PyTorch's own index first so
# chatterbox-tts finds it already satisfied. setuptools<81 because
# resemble-perth's watermarker imports pkg_resources, and without it perth
# leaves the watermarker out without a word. The weights come now, at the
# revision speech.py pins, into /opt/chatterbox/hf (speech.CHATTERBOX_CACHE):
# the builder has no network at run time. The last step loads the model the
# way `say` does, with HF_HUB_OFFLINE=1, so a broken watermarker or a
# missing weight fails the build, not a narration.
RUN python3 -m venv /opt/chatterbox \
    && /opt/chatterbox/bin/pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0 torchaudio==2.6.0 \
    && /opt/chatterbox/bin/pip install --no-cache-dir chatterbox-tts==0.1.7 'setuptools<81' \
    && set -- $(python3 -c 'from videobuilder import speech as s; print(s.CHATTERBOX_WORKER, s.CHATTERBOX_REPO, s.CHATTERBOX_REVISION, s.CHATTERBOX_CACHE)') \
    && env -u HF_HUB_OFFLINE /opt/chatterbox/bin/python "$1" --repo "$2" --revision "$3" --cache-dir "$4" </dev/null >/dev/null \
    && ready="$(HF_HUB_OFFLINE=1 /opt/chatterbox/bin/python "$1" --repo "$2" --revision "$3" --cache-dir "$4" </dev/null)" \
    && echo "$ready" && test "$ready" = '{"ready": true, "rate": 24000}' \
    && chmod -R a+rX "$4"
