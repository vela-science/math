# Next-campaign hardening v1

This prospective layer fixes the concrete RESULTS-FIVE-01 execution failures
without changing that completed campaign. It adds no Vela Protocol object and
has no scientific-authority or Standing effect.

## Runtime and verification

`Dockerfile` builds one `linux/arm64` runtime from a digest-pinned Debian base.
It retains Codex 0.145.0, Lean/lake 4.27.0, and the complete dependency cache for
the exact Formal Conjectures commit in `PIN.json`. The source release, Lean
archive, toolchain file, Lake manifest, image, and platform are hash-bound.

Before a campaign can freeze, `runtime.py preflight` must run with
`--network none` and prove that the embedded checkout and mounted source have
the expected Git commit/tree/archive, `lake env lean` can compile a real source
file, Codex has the expected version, and the source remains clean.

Each proposed proof is then compiled before model evaluation. A proof Result
uses the closed `source-native-candidate-result.v1` shape and one of exactly
`checked_proof` or `proof_sketch`; unknown statuses fail before Docker. Its receipt
retains the exact command, image/toolchain/source identities, exit and elapsed
time, stdout/stderr hashes, generated artifact manifest/root, placeholder and
axiom audit, and clean before/after state. Failed or uncompiled proofs are
`invalid` or `proof_sketch`; successful proofs with placeholders or unsupported
axioms are `repairable`. Compilation satisfies only the compile gate and never
rewrites semantic status. None of those states can be conversion-ready. A reviewer correction
is a new rooted artifact that points back to the immutable submitted Result and
receipt; it never upgrades that submission.

Duplicate audits and supported typed non-results are valid non-conversion task
outcomes only when their closed evidence schemas bind exact current source
files, statements, commit/tree/archive, and Result bytes. Arbitrary evidence
files fail closed. Valid duplicate and non-result receipts are neither
infrastructure failures nor proof successes.

## One cell, one permit

Future five-case campaigns freeze exactly five candidate cells and five
independent evaluator cells. The authoritative path has no multi-run
auto-advance. A single-use permit binds one predetermined cell to exact
campaign/config/image/source/assignment/run roots. After consumption, a
terminal receipt—including a timeout or non-result—must be generated from the
actual bounded runner bundle and match those roots. An evaluator permit also
requires the complete source-native verification directory to replay against
the same immutable runtime and source. Hand-authored terminal or verification
JSON cannot advance custody or unlock evaluation.
The controller returns to `operator_hold`; only then may the next permit be
minted. There are zero retries and no substitution.

The neutral provider canary in `canary-spec.json` is a one-request calibration,
not a scientific target and not part of either denominator. A future campaign
cannot freeze until offline tests, that canary, and an independent exact-runtime
review all pass. Freeze validates the complete canary permit, runner execution,
compile, preflight, credential/teardown receipts and an independent PASS report
and verdict against the same image, configuration, source, runtime, and exact
canary root. Scalar or synthetic pass assertions fail closed. This patch does
not run the canary or authorize inference.

`correction-validation/` retains the bounded offline/container correction
evidence, including the first failed proof-check setup and the subsequent
successful exact Lean/lake receipt. It contains no provider or campaign run.
