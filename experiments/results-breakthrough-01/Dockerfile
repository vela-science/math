FROM rust:1.97.1-bookworm AS vela-builder

WORKDIR /src
COPY . .
RUN cargo build --locked --release -p vela-cli

FROM vela-math-result-candidate:2026-08-20

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=vela-builder /src/target/release/vela /usr/local/bin/vela

WORKDIR /work
CMD ["bash"]
