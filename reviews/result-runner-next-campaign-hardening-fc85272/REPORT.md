# Independent stricter re-review: Result Runner next-campaign hardening

## Verdict

**BLOCKED** for producer commit `fc852724304896ae8b472f2a76785c4d6562557d`
and tree `6d92fea4c71bc21f6b5313b31a9db1d0ddf2d134`.

RRH-01, RRH-03, and RRH-04 pass. RRH-02 retains one fail-open path:
`_validate_independent_review` accepts an untracked `review.json`. A future plan
can therefore freeze from a handoff whose report and verdict are committed but
whose protocol receipt bytes are not.

## Frozen scope

- Remote `upstream-review/codex/result-runner-next-campaign-hardening-v1`
  equals the producer commit. The producer tree matches the supplied tree.
- The delta from blocked producer `8eca684f02db097ccd25f4e0de0a451bcf7f68eb`
  contains 17 paths under `tools/result_runner/next_campaign_v1/` and its focused
  test file.
- Runtime SHA-256: `81550fb85d4e03f90b855811a071b227c6a96d6c1744ca8b0618ed8e5c432001`.
- Runtime pin SHA-256: `0c42682ca4b8e77b76c04088fe04adc9baf5e8e1ed72398d43e38a380e51eb71`.
- The RESULTS-FIVE-01 and retained qualification paths have no delta from the
  controlling producer.

## Reproduced gates

- Focused suite: 12 passed.
- Full suite: 30 tests ran, 29 passed, and the opt-in signed-Vela integration
  test skipped. A clean local clone produced the same count. The handoff phrase
  "30 PASS, 1 skipped" overcounts by one; committed `VALIDATION.json` records
  `29` passed and `1` skipped.
- Ruff 0.5.4 format and repository-style check with E402 excluded passed.
  Python `compileall`, JSON parsing, and `git diff --check` passed.
- Formal Conjectures remained clean at commit
  `9cbe1d3c12998c786b7c2cd99ce28a21b6631f66`, tree
  `afc1a5d149d5434089aabe705f3ce450ebfbc244`, and archive SHA-256
  `ba47fe3d14126eda45870d40ea951fdaa14a5135dafcf449f8b28f49c53cf6fa`.
- Docker used `desktop-linux`. Image
  `sha256:eec93eef374618d394269ae1108c0bbe6d247ecc7efdd39eb1a4ba5aec548397`
  resolved as `linux/arm64`.
- The network-disabled preflight passed again with source root
  `a8d18248ed4760eb9f90f21f5eb272f172c526fdbb39cb8d461f0f8c370c211a`
  and the retained stdout/stderr hashes. The fresh receipt and three-file root
  differ because the receipt retains elapsed time. The retained receipt/root
  remain `66e83cba7d2fa1847857afcce9a612161400aa615f21457da07ba46d38c1d9e0`
  and `8d7de7c67be9963cb866617c90e64dadad7cf6006cedfb7b8cf5cab3a2687ffe`.
- The exact stricter validator replayed the retained proof through Docker and
  Lean. It reproduced proof-artifact root
  `e5144509579b777fb1474ed0ee5d0e766c66c892a54089b3a30caab778b8ea83`,
  complete verification root
  `42838c49cd288b9ddeb9f9697bef296736eee061af66a669023a3eb3e613a333`,
  receipt SHA-256
  `168cd5611bbb7e7c105bf6577dd418ce26d99a3c59994cf5da77c4b6964d5e0d`,
  and nonempty OLean SHA-256
  `aaba07269991599e97eb9017ac7ac0cf64102b36bd0bc5b7da60eaaf9cf894e1`.
- The credential scan found zero findings in the 17-path delta.

## Finding disposition

### RRH-01: PASS

The terminal path reconstructs the maintained runner's complete Docker/Codex
argv from closed assignment, run, and semantic inputs. It rejects the prior
non-runner argv fixture. Candidate verification binds the terminal and execution
roots, the approved network-disabled Lean command, the sole nonempty OLean, the
proof-artifact root, and the full verification-directory root. Evaluator permit
issuance triggers a fresh byte-identical Lean replay.

### RRH-02: BLOCKED

The canary side now validates the generated terminal, execution, compile,
preflight, teardown, protocol root, producer identity, and committed canary
receipt. Copied or uncommitted canary bytes fail.

The independent-review side does not apply the same committed-blob check to its
protocol receipt. The isolated reproducer did this:

1. Commit `REPORT.md` and `verdict.json` in a fresh review repository.
2. Generate `review.json` with `record_independent_review_receipt`.
3. Leave `review.json` untracked. `git status --porcelain=v1` reports
   `?? review.json`.
4. Call `_validate_independent_review`. It returns `status: pass`.

The repository's positive freeze test uses this same sequence: it commits the
report and verdict, generates an untracked review receipt, then freezes the
five-candidate/five-evaluator plan. The validator checks committed report and
verdict blobs at lines 2033-2034 of `runtime.py`; it never calls
`_tracked_blob_matches` for `review_path`.

Minimal correction: keep the embedded review commit/tree as the commit that
contains the report and verdict, commit the generated receipt in one descendant
commit, and bind that descendant commit/tree as the receipt identity. Freeze
must require `review.json` to match its exact committed blob while resolving the
report and verdict from the embedded review commit. Add a negative test where an
untracked generated receipt fails and a committed descendant receipt passes.

### RRH-03: PASS

Duplicate evidence uses a closed schema, recomputes both occurrence roots, and
requires different repository/commit/path/declaration identities. The retained
self-duplicate fixture fails. Non-results retain closed reason and source-review
bindings.

### RRH-04: PASS

The Result status enum remains closed. Unknown proof statuses fail during Result
validation, before compilation. A compiled `proof_sketch` stays a non-conversion
with `conversion_ready: false`.

## Boundary

This review made no model request, canary or campaign execution, Vela action,
scientific change, authority action, Standing change, or merge. Do not freeze a
campaign, run the canary, or merge this producer head until RRH-02 receives the
bounded correction above and another commit-bound review.
