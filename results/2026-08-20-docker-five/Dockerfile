FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git nodejs npm ripgrep \
    && npm install --global @openai/codex@0.145.0 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.codex /out

WORKDIR /work

