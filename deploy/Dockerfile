# Build from the repository root: docker build -f deploy/Dockerfile .
ARG BASE=debian:trixie-slim
# The stage the final image waits on. `gated` runs the tests first; `runtime`
# skips them, to ship now and run `--target gated` on the same tree afterwards.
ARG GATE=gated
FROM ${BASE} AS runtime
USER root
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-setuptools python3-cairo python3-gi python3-gi-cairo \
    python3-pil python3-yaml gir1.2-pango-1.0 ffmpeg fonts-dejavu-core fontconfig \
    bubblewrap tini git openssh-client ca-certificates curl \
    chromium fonts-liberation fonts-noto-color-emoji && \
    rm -rf /var/lib/apt/lists/*
# Text to speech for `videobuilder say` (the speech extra) and the Kokoro model
# it reads from /opt/kokoro. Only authors run it; films load the WAV it wrote.
# The int8 model: a third the size of the fp32 one, close in quality.
ARG KOKORO_URL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
RUN python3 -m pip install --break-system-packages --no-cache-dir kokoro-onnx==0.4.7 && \
    mkdir -p /opt/kokoro && \
    curl -fsSL -o /opt/kokoro/kokoro-v1.0.int8.onnx "$KOKORO_URL/kokoro-v1.0.int8.onnx" && \
    curl -fsSL -o /opt/kokoro/voices-v1.0.bin "$KOKORO_URL/voices-v1.0.bin" && \
    printf '%s  %s\n' \
        6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb /opt/kokoro/kokoro-v1.0.int8.onnx \
        bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d /opt/kokoro/voices-v1.0.bin \
        | sha256sum -c - && \
    python3 -c 'import kokoro_onnx'
ENV VIDEOBUILDER_KOKORO_DIR=/opt/kokoro
# Sound effects for `vb.sfx`: earshot's bank (MIT), rendered once to Opus as
# vb-sfx-1.tar. Its sha256 is pinned in videobuilder/sfx-pack.sha256, the file
# `python -m videobuilder sfx fetch` checks against too; all zeros there means
# the pack isn't published yet, and the build stops to say so.
ARG SFX_URL=https://github.com/mgalgs/videobuilder/releases/download/sfx-bank-1
COPY videobuilder/sfx-pack.sha256 /tmp/vb-sfx/
RUN cd /tmp/vb-sfx && \
    if grep -q '^0\{64\} ' sfx-pack.sha256; then \
        echo 'videobuilder/sfx-pack.sha256 is a placeholder: put the published vb-sfx-1.tar sha256 in it' >&2; \
        exit 1; \
    fi && \
    curl -fsSL -o vb-sfx-1.tar "$SFX_URL/vb-sfx-1.tar" && \
    sha256sum -c sfx-pack.sha256 && \
    mkdir -p /opt/vb-sfx && tar -xf vb-sfx-1.tar -C /opt/vb-sfx && \
    cd / && rm -rf /tmp/vb-sfx
ENV VIDEOBUILDER_SFX_DIR=/opt/vb-sfx
WORKDIR /opt/videobuilder
COPY . .
# ssh refuses to run for a uid with no passwd entry.
RUN python3 -m pip install --break-system-packages --no-deps --no-build-isolation . && \
    groupadd --gid 1000 editor && \
    useradd --uid 1000 --gid 1000 --home-dir /home/editor --no-create-home --shell /bin/sh editor && \
    mkdir -p /var/tmp/claude-scratch /home/editor/src && \
    chown -R 1000:1000 /var/tmp/claude-scratch /home/editor
ENV HOME=/home/editor
USER 1000:1000
ENTRYPOINT ["tini", "--"]
CMD ["/opt/videobuilder/deploy/start-editor.sh"]

FROM runtime AS frames
USER root
RUN python3 -m videobuilder frames --hash examples/tour.py examples/benchmark.py > /frames.sha256
FROM scratch AS frames-export
COPY --from=frames /frames.sha256 /frames.sha256

FROM runtime AS gated
USER root
RUN python3 -m tests.run_parallel && \
    python3 -m videobuilder frames --hash --check deploy/frames.sha256 examples/tour.py examples/benchmark.py

# The capabilities page's clips and posters render here, from exactly this image's
# videobuilder, so a built clip can never show something the running version can't do.
FROM runtime AS capabilities
USER root
RUN python3 -m videobuilder capabilities build --out /opt/videobuilder-capabilities

# Same idea for the compendium vote feed: every component and recipe preview, plus
# index.json's loop windows, built from exactly this image's videobuilder.
FROM runtime AS compendium
USER root
RUN python3 -m videobuilder compendium build --out /opt/videobuilder-compendium

FROM ${GATE} AS gate

FROM runtime
COPY --from=gate /opt/videobuilder/deploy/Dockerfile /opt/videobuilder/deploy/Dockerfile
COPY --from=capabilities /opt/videobuilder-capabilities /opt/videobuilder-capabilities
COPY --from=compendium /opt/videobuilder-compendium /opt/videobuilder-compendium
USER 1000:1000
