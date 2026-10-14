# Build from the repository root: docker build -f deploy/Dockerfile .
ARG BASE=debian:trixie-slim
FROM ${BASE} AS runtime
USER root
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-setuptools python3-cairo python3-gi python3-gi-cairo \
    python3-pil python3-yaml gir1.2-pango-1.0 ffmpeg fonts-dejavu-core fontconfig \
    bubblewrap tini git openssh-client ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*
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
RUN python3 -m unittest discover -s . -t . && \
    python3 -m videobuilder frames --hash --check deploy/frames.sha256 examples/tour.py examples/benchmark.py

# The capabilities page's clips and posters render here, from exactly this image's
# videobuilder, so a built clip can never show something the running version can't do.
FROM runtime AS capabilities
USER root
RUN python3 -m videobuilder capabilities build --out /opt/videobuilder-capabilities

FROM runtime
COPY --from=gated /opt/videobuilder/deploy/Dockerfile /opt/videobuilder/deploy/Dockerfile
COPY --from=capabilities /opt/videobuilder-capabilities /opt/videobuilder-capabilities
USER 1000:1000
