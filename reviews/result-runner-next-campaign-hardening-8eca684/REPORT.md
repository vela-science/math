# Independent re-review: Result Runner next-campaign hardening

## Verdict

**BLOCKED** for corrective producer commit `8eca684f02db097ccd25f4e0de0a451bcf7f68eb` and tree `27f814e77a2afab2c5b4c31fd8e058b3f419573c`.

The correction closes the minimal malformed-JSON cases and fixes proof-status handling. Three paths still accept evidence that does not establish the claimed event: the terminal gate does not reconstruct the maintained runner invocation, the verification gate does not replay Lean or validate the compile command, and the duplicate gate accepts the target as its own duplicate. Those paths can unlock an evaluator or freeze a plan.

## Frozen scope

- Corrective branch: `origin/codex/result-runner-next-campaign-hardening-v1`, remote-equal at the commit and tree above.
- Parent reviewed producer: `033ff587142f23f67e2b7fb281821c2f6395839f`.
- Controlling review: `6ce4bfbcfeab4428cdec9e3726471d9d7064d9ba`.
- Corrective delta: 27 paths under `tools/result_runner/next_campaign_v1/` plus `tools/result_runner/tests/test_next_campaign_v1.py`. Completed RESULTS-FIVE-01 and historical qualification files remain byte-identical.
- Runtime implementation SHA-256: `5f954a638a9c5e0f0451a10865a009a1f7fc1b3a2405172356f0d10bc118f5e5`.
- Runtime pin SHA-256: `0c42682ca4b8e77b76c04088fe04adc9baf5e8e1ed72398d43e38a380e51eb71`.
- Image: `sha256:eec93eef374618d394269ae1108c0bbe6d247ecc7efdd39eb1a4ba5aec548397`, `linux/arm64` under `desktop-linux`.

## Reproduced passing evidence

- Corrective regressions: 11/11 pass in the retained worktree and a fresh local clone.
- Full suite: 28 pass; the unchanged opt-in signed-Vela integration test skips. Ruff 0.5.4 format/check and Python 3.11.2 `compileall` pass.
- Network-disabled preflight: pass. Replayed stdout and stderr match `3ab10b8a…` and `d47a06d5…`; source root is `a8d18248…`. The retained receipt is `5638ae45fe9b8f61a63c9dac3d5aa46e1ccf1541859053de982a0d247a3db01e`, and its three-file root recomputes as `adf51e9a24aab93179930012814586ba25ea7c20447f253522cacc35dfee3a93`.
- Checked proof: pass. The replay produced OLean `aaba07269991599e97eb9017ac7ac0cf64102b36bd0bc5b7da60eaaf9cf894e1`, output root `8b4cd73516c222e318743bbab0bfbd9e3dbe5cf0b1dc7d277ee4d3e9dd5ed8e7`, and the same stdout/stderr hashes. The retained proof receipt is `e7888ba566ce34f2c0160dd996f9b4f5bd0c65d192ca774f9922abf288360555`; the complete verification directory recomputes as `ef9fae1891dc0d3fb584935af2e66ed88953a1aa167a023f54f8028528a0d402`.
- Validation packet: `7f1ec0486905ccc96bd05e4b5bda8efbd31c3d38be56b19f2b195e9e9ca3db10`; its retained roots recompute.
- Credential scan: zero findings across all 27 corrective paths.
- The controller still fixes five candidate and five evaluator cells, records zero retries, consumes one active permit once, and returns to `operator_hold` after each terminal cell.
- No provider, canary, campaign, inference, Vela, authority, Standing, scientific, or source action occurred in this review.

## Four-finding disposition

### RRH-01: BLOCKED, terminal and verification provenance remains fail-open

The code rejects the prior four-field verification JSON and a terminal file without a runner bundle. The stronger benign fixture below still passes:

1. Create a complete shaped runner bundle with valid hashes and semantic fields.
2. Set `invocation.argv` to `["not-the-maintained-runner"]` and recompute only `host_argv_sha256`.
3. `record_terminal` accepts the bundle as `completed` because `_validate_runner_bundle` hashes the supplied argv but never reconstructs the expected runner command.
4. Copy a shaped proof-verification directory, set `command` to `["not-lean"]`, replace `Submitted.olean` with an empty file, and recompute the generated manifest/root.
5. `_validate_source_verification_directory` classifies it as `checked_proof`; `bind_source_verification` records it; `mint_permit` issues evaluator permit `E1`.

The fixture ran no Docker, Lean, provider, or model process. The accepted empty OLean proves that the validator checks file presence, stdout text, and receipt fields rather than the compile event.

Minimal correction: reconstruct and compare the exact maintained-runner argv from the frozen semantic invocation, assignment, run spec, and image before accepting a terminal. Before binding a source verification, run the exact network-disabled Lean check into a fresh directory or compare against a fresh verifier-produced semantic projection; require a non-empty generated artifact and the exact compile argv. Add this five-step fixture as a negative test.

### RRH-02: BLOCKED, a complete synthetic canary can freeze the plan

The scalar-only synthetic canary now fails. A complete shaped canary assembled by the test helpers still passes `validate_canary` and `freeze_cell_plan` without executing the maintained runner, Docker, Lean, or a provider. It freezes a 5+5, zero-retry plan while its stored canary argv is only `["docker", "run", "--rm", "-i", <image>]`.

The canary inherits RRH-01 because it uses the same runner-bundle and proof-directory validators. The gate also hashes `canary-spec.json` without validating its closed schema and neutral fields.

Minimal correction: apply the corrected runner-command and Lean-replay checks to the canary packet, then validate the canary spec's exact schema, neutral target, one-request ceiling, zero retries, and denominator exclusion before plan freeze.

### RRH-03: BLOCKED, the duplicate evidence permits self-duplication

Closed Result and evidence schemas now reject arbitrary files, altered fields, and mismatched source hashes. A duplicate packet still passes when its `duplicate` target equals its `target` byte-for-byte. The validator checks equal statement bytes but never requires a distinct prior occurrence or Claim.

Minimal correction: require the duplicate binding to identify a distinct source occurrence or retained prior Result/Claim root. Reject equal `(source_repository, source_commit, source_path, declaration)` identities and add a self-duplicate negative test. Keep valid duplicates and typed non-results in the denominator and non-conversion.

### RRH-04: PASS

The candidate Result uses a closed status enum. Unknown values fail before Docker. A compiled `proof_sketch` remains `proof_sketch` with `conversion_ready: false`; compilation cannot promote it. The checked-proof path also binds the submitted proof, target statement bytes, declaration, source snapshot, audit output, and generated artifact root.

## Receipt determinism

The replayed proof artifacts, streams, classifications, source roots, and semantic verification root match the retained packet. Full receipt JSON remains execution-specific because it includes elapsed seconds and absolute host mount paths. The fresh proof receipt SHA is `93d8bba0e5b406dfbd0c2cf0e7a9219614a4779c529d172493509b51bbbc9344`; the fresh preflight receipt SHA is `712d58ebc53d232d92083121c0b7a8cdf87ac4f1ebf36b6420d43af25eda4c25`. The documentation states that distinction.

## Handoff

Retain the source pin, image, preflight, proof-status schema, 5+5 denominator, zero-retry state machine, and closed non-result schema. Correct RRH-01 through RRH-03 and rerun the focused offline/container gates. Do not run the canary or freeze a scientific campaign until a new immutable head receives independent review.
