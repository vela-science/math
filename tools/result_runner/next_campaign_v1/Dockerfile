FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ARG TARGETARCH
ENV LEAN_ROOT=/opt/lean-4.27.0-linux_aarch64
ENV PATH="/opt/lean-4.27.0-linux_aarch64/bin:${PATH}"

RUN test "${TARGETARCH}" = "arm64" \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates curl git nodejs npm openssh-client ripgrep zstd \
    && npm install --global @openai/codex@0.145.0 \
    && rm -rf /var/lib/apt/lists/* \
    && curl --fail --location --silent --show-error \
      https://github.com/leanprover/lean4/releases/download/v4.27.0/lean-4.27.0-linux_aarch64.tar.zst \
      --output /tmp/lean.tar.zst \
    && printf '%s  %s\n' \
      b256eec276baaaccc3eb3fa64d7ccff64f710b7caa074f305ba95e0013ad31e7 \
      /tmp/lean.tar.zst | sha256sum --check --strict \
    && tar --use-compress-program=unzstd -xf /tmp/lean.tar.zst -C /opt \
    && rm /tmp/lean.tar.zst \
    && lean --version \
    && lake --version \
    && codex --version | grep -F 'codex-cli 0.145.0'

RUN git init -q /opt/formal-conjectures \
    && git -C /opt/formal-conjectures remote add origin \
      https://github.com/google-deepmind/formal-conjectures.git \
    && git -C /opt/formal-conjectures fetch --depth=1 origin \
      9cbe1d3c12998c786b7c2cd99ce28a21b6631f66 \
    && git -C /opt/formal-conjectures checkout -q --detach FETCH_HEAD \
    && test "$(git -C /opt/formal-conjectures rev-parse HEAD)" = \
      9cbe1d3c12998c786b7c2cd99ce28a21b6631f66 \
    && test "$(git -C /opt/formal-conjectures rev-parse HEAD^{tree})" = \
      afc1a5d149d5434089aabe705f3ce450ebfbc244 \
    && test "$(git -C /opt/formal-conjectures archive --format=tar HEAD | sha256sum | cut -d' ' -f1)" = \
      ba47fe3d14126eda45870d40ea951fdaa14a5135dafcf449f8b28f49c53cf6fa \
    && test "$(sha256sum /opt/formal-conjectures/lean-toolchain | cut -d' ' -f1)" = \
      e695e6e5d8e7a8be4d6cf159dfb995847993d26c6cc450353a86f387279025b9 \
    && test "$(sha256sum /opt/formal-conjectures/lake-manifest.json | cut -d' ' -f1)" = \
      5b99b5f4f807cbba67bbcd22e5e486c17d6a8d970ea218de08d05830ab350c26

WORKDIR /opt/formal-conjectures
RUN lake update \
    && test "$(sha256sum lake-manifest.json | cut -d' ' -f1)" = \
      5b99b5f4f807cbba67bbcd22e5e486c17d6a8d970ea218de08d05830ab350c26 \
    && lake exe cache get

RUN lake build FormalConjecturesUtil \
    && lake env lean --version \
    && lake env lean FormalConjectures/ErdosProblems/1052.lean \
      -o /tmp/preflight.olean \
    && rm -f /tmp/preflight.olean \
    && test -z "$(git status --porcelain=v1 --untracked-files=all)"

WORKDIR /repo
CMD ["bash"]
