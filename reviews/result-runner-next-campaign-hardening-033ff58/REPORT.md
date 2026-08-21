# Independent review: Result Runner next-campaign hardening

## Verdict

**BLOCKED** for producer commit `033ff587142f23f67e2b7fb281821c2f6395839f` and tree `92bdb75914359cfe40c2f93255b169f2dbcd4a1f`.

The pinned Lean runtime and proof compiler work. The permit controller does not yet prove that a candidate cell ran or that a source-native verifier produced the receipt used to unlock an evaluator. The canary and non-result gates also trust assertions without validating their evidence. These gaps prevent campaign freeze or inference authorization.

## Frozen scope

- Base: `origin/main` at `6fea63f2e7882fd9de0398868984cd88a17898f1`.
- Feature: `origin/codex/result-runner-next-campaign-hardening-v1` at the producer commit and tree above; remote equality reproduced.
- Delta: 19 paths, confined to `tools/result_runner/README.md`, `tools/result_runner/next_campaign_v1/`, and `tools/result_runner/tests/test_next_campaign_v1.py`. No campaign or RESULTS-FIVE-01 path changed.
- Runtime pin: `0c42682ca4b8e77b76c04088fe04adc9baf5e8e1ed72398d43e38a380e51eb71`.
- Runtime implementation: `5070b7995bf4008ba1aa96dfeb03951b1dec3814a01067bda227b21dd49bf5f1`.
- Image: `sha256:eec93eef374618d394269ae1108c0bbe6d247ecc7efdd39eb1a4ba5aec548397`, resolved as `linux/arm64` under `desktop-linux`.

## Checks that passed

- Python 3.11.2: 28 tests passed; the unchanged opt-in signed-Vela integration test skipped. Ruff 0.5.4 format and check passed. `compileall` passed.
- A clean-clone, network-disabled preflight passed against Formal Conjectures commit `9cbe1d3c12998c786b7c2cd99ce28a21b6631f66`, tree `afc1a5d149d5434089aabe705f3ce450ebfbc244`, and archive root `ba47fe3d14126eda45870d40ea951fdaa14a5135dafcf449f8b28f49c53cf6fa`. Replayed stdout and stderr matched retained hashes `3ab10b8a…` and `d47a06d5…`.
- The checked-proof replay passed with no axioms. `Submitted.olean` reproduced byte-for-byte at `6aa84a751eed98807ecf18c03127e7cbb5b1d40ea7e06629996230d168964bb9`; stdout and stderr matched `4d270842…` and `e3b0c442…`; the generated artifact root matched `19b64487cc00f5fb4dc0b0c4e737558028a27d17425cf19800e357c43b3d0ed8`.
- The fixed plan constructor requires five candidate and five evaluator assignments and records zero retries. Permit state starts and returns to `operator_hold`, advances in fixed ordinal order, and rejects reuse of one active permit.
- The candidate and evaluator denominators exclude the neutral canary in both the canary spec and plan schema.
- The feature credential scan reproduced zero findings across the claimed 18 files.
- No provider, canary, inference, Vela, authority, Standing, scientific, or source mutation occurred during this review.

## Blocking findings

### RRH-01: evaluator permits accept hand-authored verification receipts

`record_terminal` checks shared root fields and `terminal: true`, but it requires no execution status, result file, runner receipt, model identity, usage, or provider-call count. `bind_source_verification` then checks only a repeated result digest and one of two type strings. A benign fixture recorded a candidate terminal with no execution fields, supplied a four-field JSON object labeled `source-native-proof-verification-v1`, and minted evaluator permit `E1`.

The existing unit test demonstrates the same weakness at `test_next_campaign_v1.py:489-497`: it creates the accepted verification receipt by hand with no verifier, runtime, source, compilation, evidence, or conversion checks.

Minimal correction: define strict terminal schemas per role and bind them to the maintained runner's complete execution receipt, exact result bytes, provider/session accounting, and permit root. Validate the full source-native receipt schema and its runtime pin, verifier hash, source snapshot, candidate bytes, classification invariants, and referenced evidence before recording it or minting an evaluator permit. Add negative tests for missing and fabricated fields.

### RRH-02: synthetic canary and review assertions can freeze a plan

`validate_canary` accepts scalar status fields and three well-formed digest strings. It does not open or hash the named permit, output, compile, preflight, credential-scan, or teardown evidence. It does not bind `canary-spec.json`. The independent-review gate accepts `status: pass` plus the runtime-pin digest without binding a reviewed producer commit/tree or report/verdict preimages.

A local fixture with no canary or review execution supplied those assertions and froze a ten-cell plan. The fixture made no provider or external call.

Minimal correction: make the canary receipt bind the canary-spec digest and validate each referenced receipt from exact bytes. Bind the independent review to the producer commit/tree, runtime implementation, pin, image, report, and verdict. Reject missing, extra, unlinked, and inconsistent evidence.

### RRH-03: arbitrary files become valid non-results or duplicates

`verify_nonconversion` checks that two paths are regular files, hashes them, and emits `task_outcome_valid: true`. It does not parse a Result schema or validate a duplicate occurrence, source comparison, typed non-result reason, or evidence method. The committed test passes `{}` and the text `exact source audit` as sufficient evidence. A second benign fixture reproduced `valid_non_result` from `{}` and an untyped assertion.

Minimal correction: require a closed Result status/schema and a closed source-native evidence schema for each kind. Recompute exact occurrence/declaration/source roots and require the evidence fields that establish a duplicate or support a non-result. Keep both outcomes non-conversion and in the denominator.

### RRH-04: unknown Result status can become conversion-ready

`verify_proof` requires only that `result_status` is a string. `_proof_classification` returns `checked_proof, true` for any declared value when compilation and the axiom audit pass. A direct fixture with `result_status: unsupported-value` reproduced that result. The verifier also compiles the submitted declaration without checking that its type matches the frozen scientific target.

Minimal correction: validate the complete candidate Result schema and status enum before Docker. Bind the expected target declaration/type or an exact source-owned statement root, and require statement fidelity before setting `conversion_ready: true`.

## Receipt determinism and path handling

The proof artifact, stdout, stderr, source identities, classification, and generated-artifact root reproduced. The receipt JSON did not reproduce byte-for-byte because it records host-specific absolute mount paths and elapsed seconds; the replay receipt SHA was `e3d092fd668d7a950d40b0fadf8a82b47676a193eefb3d642719dce1aa3e0129`, while the retained receipt SHA is `60abc7b7e7c0d5cdbd439ad5426812bb3abf20de7f2d9e76e450b1e0978feff3`. Documentation should call the rooted artifacts and semantic projection deterministic, and call each full receipt an exact execution receipt.

Canonical absolute paths fail closed. A relative `--pin` invocation exits before Docker, but the CLI prints an uncaught `RunnerError` traceback because `main` catches only `HardeningError`. Catching the base runner error would preserve a bounded typed failure; this defect did not weaken the absolute-path guard.

## Handoff

Retain the runtime image, pin, network-disabled preflight, proof compiler, fixed denominator, and hold state. Correct RRH-01 through RRH-04 and add hostile tests that reproduce these exact fixtures. Do not run the neutral canary or freeze a scientific campaign until a new immutable head receives independent review.
