# Vela 0.977.4 Result Runner qualification

This directory is the active signed Vela pin for the maintained Result Runner.
It is non-scoring operational evidence and makes no scientific, comparative,
authority, or Standing claim.

`release/` retains the exact macOS arm64 release manifest, detached OpenSSH
signature, checksum sidecar, and source-owned `allowed_signers` preimage. The
signature verifies as `release@vela.space` in namespace `vela-release`; the
manifest binds tag `v0.977.4`, source commit `1a2e0328…3d45`, source tree
`1bd8ed4e…4803`, archive SHA-256 `023bf4d9…5d65`, and binary SHA-256
`06f912d1…d05e`.

The first two disposable lifecycle runs passed their signed Submission,
truthful failing Verification, rooted rejection, strict readback, and replay,
but exposed that Vela 0.977.4 now leaves disposable producer/verifier keys in
the isolated HOME unless the adapter removes that HOME. `PRE-FIX.json` retains
the typed operational failure. No secret bytes are retained.

The adapter cleanup was minimally extended inside its existing `finally` guard.
Runs 3 and 4 are the final repeated qualification: exact retained output passed
through Native, Graph, and separate disposable signed Vela lifecycles; both
ended with zero accepted Claims, `scientific_state_changed=false`, deleted
authority/private directories, deleted disposable HOME, and strict replay.
Their full command stdout/stderr/exit receipts are retained. The Docker dry
receipt binds a fresh clean clone of canonical Math merge `7a535164…2563`, the
unchanged accepted image, `/repo`, and read-only source/OAuth mounts. A separate
network-disabled, no-model stdin sentinel executed inside that exact image and
returned the mounted source commit/tree byte-exactly.

The historical one-request provider packet under `qualification-v1/` remains
byte-identical and valid for the unchanged model invocation. This repin made no
provider request and consumed no benchmark denominator.
