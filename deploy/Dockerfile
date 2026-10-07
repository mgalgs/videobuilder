# Build from the repository root: docker build -f deploy/Dockerfile .
ARG BASE=debian:bookworm-slim
FROM ${BASE} AS runtime
USER root
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-setuptools python3-cairo python3-gi \
    python3-pil python3-yaml gir1.2-pango-1.0 ffmpeg fonts-dejavu-core fontconfig \
    bubblewrap tini git openssh-client ca-certificates && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /opt/videobuilder
COPY . .
RUN python3 -m pip install --break-system-packages --no-deps --no-build-isolation . && \
    mkdir -p /var/tmp/claude-scratch /home/editor/src && \
    chown -R 1000:1000 /var/tmp/claude-scratch /home/editor
ENV HOME=/home/editor
USER 1000:1000
ENTRYPOINT ["tini", "--"]
CMD ["python3", "-m", "videobuilder", "editor", "/home/editor/src/project"]

FROM runtime AS frames
USER root
RUN python3 -m videobuilder frames --hash examples/tour.py examples/benchmark.py > /frames.sha256
FROM scratch AS frames-export
COPY --from=frames /frames.sha256 /frames.sha256

FROM runtime AS gated
USER root
RUN python3 -m unittest discover -s . -t . && \
    python3 -m videobuilder frames --hash --check deploy/frames.sha256 examples/tour.py examples/benchmark.py

FROM runtime
COPY --from=gated /opt/videobuilder/deploy/Dockerfile /opt/videobuilder/deploy/Dockerfile
USER 1000:1000
