# Independent final re-review: Result Runner next-campaign hardening

## Verdict

**PASS** for producer commit `cf6d76687b205a39e2515e9fec7087c819454d2f`
and tree `f8e9e8d3b99226ed6bba62026396d5f17ea9351e`.

The three-file correction closes the remaining RRH-02 path. The validator now
rejects a generated but untracked independent-review receipt, accepts the same
bytes after a strict descendant commit, and returns separate artifact and
receipt commit/tree identities. Plan freeze records both identities.

## Frozen scope

- Remote `origin/codex/result-runner-next-campaign-hardening-v1` equals the
  producer commit and supplied tree.
- Parent: `fc852724304896ae8b472f2a76785c4d6562557d`.
- Controlling review: `898039a8bb4dfe5305dcfc60d537a9f8c45f61a4`,
  tree `beb69454ee8004f60166bdf536d76c43ea614a97`.
- The delta contains three modified files: `runtime.py`, its focused test, and
  the next-campaign README.
- Runtime SHA-256:
  `34b0f677e07b987dfdd7a64094a54fbd744d50ba32936210ed36b79ede53ce05`.
- Runtime pin and retained qualification paths have no delta. RESULTS-FIVE-01
  has no delta.

## RRH-02 result

`record_independent_review_receipt` preserves the commit and tree that contain
`REPORT.md` and `verdict.json`. `_validate_independent_review` now:

1. Resolves the live review-repository HEAD as the receipt commit and tree.
2. Requires `review.json` to match the exact tracked blob at that commit.
3. Resolves the embedded artifact commit and verifies its tree.
4. Requires the receipt commit to be a strict descendant of the artifact
   commit.
5. Verifies the report and verdict bytes against the embedded artifact commit.

The isolated fixture produced these outcomes:

- Generated, untracked `review.json`: rejected with `immutable_evidence`.
- The same receipt committed in a descendant: accepted with `status: pass`.
- Returned artifact and receipt commits differ, and freeze records
  `review_receipt_commit` plus `review_receipt_tree` alongside the artifact
  commit/tree and protocol root.

The positive five-candidate/five-evaluator freeze test now commits the receipt
before freeze. Copied receipt paths and mutated artifact bytes still fail.

## Reproduced gates

- Focused suite: 12 passed.
- Full suite: 30 tests ran, 29 passed, and the opt-in signed-Vela integration
  test skipped. A clean clone at the producer commit and tree produced the same
  count.
- Ruff 0.5.4 format and repository-style check passed. Python `compileall` and
  `git diff --check` passed.
- Formal Conjectures remained clean at commit
  `9cbe1d3c12998c786b7c2cd99ce28a21b6631f66`, tree
  `afc1a5d149d5434089aabe705f3ce450ebfbc244`, and archive SHA-256
  `ba47fe3d14126eda45870d40ea951fdaa14a5135dafcf449f8b28f49c53cf6fa`.
- Docker used `desktop-linux`. Image
  `sha256:eec93eef374618d394269ae1108c0bbe6d247ecc7efdd39eb1a4ba5aec548397`
  resolved as `linux/arm64`.
- The current-runtime network-none preflight passed. Stdout and stderr retained
  SHA-256 values `3ab10b8ac25d64132bc28d3b90e5f64dbd565c6f9d5a37e68a676539f56a3f4a`
  and `d47a06d59aba2814c3fb7460049fc2ccbfc834196c956d6c6558e8be8b079e24`.
- Current-runtime proof validation classified the fixture as `checked_proof`.
  Fresh Lean replay reproduced OLean SHA-256
  `aaba07269991599e97eb9017ac7ac0cf64102b36bd0bc5b7da60eaaf9cf894e1`
  and proof-artifact root
  `e5144509579b777fb1474ed0ee5d0e766c66c892a54089b3a30caab778b8ea83`.
- The three-file credential scan found zero findings.

## Other findings

- RRH-01 remains PASS. The correction does not change runner argv, terminal,
  verification-root, or fresh Lean replay logic.
- RRH-03 remains PASS. The correction does not change duplicate or non-result
  schemas and occurrence-root validation.
- RRH-04 remains PASS. The correction does not change the closed status enum or
  proof-sketch classification.

## Authorization boundary

This PASS authorizes merge of the exact reviewed producer commit and tree. It
does not authorize a canary, campaign freeze, model inference, scientific
conversion, Vela action, authority action, or Standing change. This review did
not perform any of those actions and did not merge the branch.
