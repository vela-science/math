FROM rust:1.97.1-bookworm@sha256:0e2bcaef56d041a486784e54104a81aebe0da44bd03019bd70bc0401e42e4a97 AS vela-builder

WORKDIR /src
COPY . .
RUN cargo build --locked --release -p vela-cli

FROM vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01

# Proposed post-review compatibility delta. This is experiment-specific and
# deterministic; the host machine identity is never mounted or copied.
RUN printf '%s\n' 'af94b40fa642620275e6d617be97a542' > /etc/machine-id

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=vela-builder /src/target/release/vela /usr/local/bin/vela

WORKDIR /work
CMD ["bash"]
