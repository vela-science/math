# Independent re-review: Result Runner next-campaign hardening

## Verdict

**PASS** for producer commit
`8eca684f02db097ccd25f4e0de0a451bcf7f68eb` and tree
`27f814e77a2afab2c5b4c31fd8e058b3f419573c` only.

The four findings in independent review
`6ce4bfbcfeab4428cdec9e3726471d9d7064d9ba` are resolved within the frozen
scope. This is implementation qualification for the prospective Result Runner
custody layer. It is not a canary, campaign-freeze, inference, merge,
conversion, scientific-acceptance, Vela authority, or Standing authorization.

## Frozen protocol and subject

- The review protocol was committed before producer inspection at
  `66dd5412761f3f6a1502ce987060de9ef1d95eec`.
- Repository: `https://github.com/vela-science/math.git`.
- Live `origin/main`: `6fea63f2e7882fd9de0398868984cd88a17898f1`,
  tree `79e9482b9abe6999d36d63b1cfc62f6f964bda53`.
- Prior producer: `033ff587142f23f67e2b7fb281821c2f6395839f`.
- Corrective producer: `8eca684f02db097ccd25f4e0de0a451bcf7f68eb`,
  tree `27f814e77a2afab2c5b4c31fd8e058b3f419573c`.
- The corrective delta is exactly 27 paths under
  `tools/result_runner/next_campaign_v1/` plus its maintained test file. It does
  not touch any completed RESULTS-FIVE-01 path.
- The live-main merge tree is clean and equals the reviewed producer tree
  `27f814e77a2afab2c5b4c31fd8e058b3f419573c`.

## Finding closure

### RRH-01: terminal and verification custody — resolved

`record_terminal` no longer accepts a terminal assertion. It requires a
consumed exact permit and opens the maintained runner bundle with a closed file
set. It recomputes assignment and run roots, semantic invocation identity,
image, source snapshot, runner implementation, execution and stream receipts,
structured Result, credential scan, runner receipt, Native and Graph Result
bindings, usage, and one bounded runner invocation. The generated terminal is
root-bound into the completed ledger and returns the controller to hold.

Evaluator permits additionally require the complete source-native verification
directory. Proof verification recomputes the closed Result, retained proof,
target statement, audited Lean preimage, streams, generated-artifact manifest,
axiom and placeholder audits, source/runtime identities, classification, and
conversion flag. Non-conversion verification recomputes its closed Result and
typed source evidence. A direct hand-authored terminal fixture failed with
`path_missing`; an incomplete verification fixture did not unlock an evaluator.

### RRH-02: canary and independent-review custody — resolved

Plan freeze opens the exact canary receipt and binds the committed canary-spec
bytes. It independently validates the permit, complete runner execution,
source-native compile directory, network-disabled preflight, credential result,
and teardown receipt, then compares their recomputed roots with the canary
receipt. The canary remains excluded from both scientific denominators.

The independent review receipt is a closed object bound to producer
commit/tree, runtime verifier and pin, image, configuration, source, exact
canary receipt, and the exact report and machine-verdict bytes. The verdict must
be `PASS`. A scalar canary assertion failed with `closed_schema`; mutation of a
linked review or teardown preimage failed its exact digest/invariant check. The
nominal fixed plan retained exactly five candidate and five evaluator cells,
zero retries, fixed order, and default operator hold.

### RRH-03: duplicate and non-result schemas — resolved

Duplicate and non-result Results use a closed candidate schema and closed
status set. Their evidence is typed and binds exact source commit, tree,
archive, repository, source-file bytes, target statement, and Result bytes.
Duplicate evidence requires equality of exact target statement bytes;
non-result evidence requires a closed reason code and sorted, unique,
hash-checked reviewed sources. Both outcomes remain valid non-conversions with
`conversion_ready: false`. Arbitrary JSON failed with `closed_schema`, and
source-root and extra-field mutations failed closed.

### RRH-04: closed proof status and no proof-sketch promotion — resolved

Proof status is exactly `checked_proof` or `proof_sketch`; an unknown status
failed with `candidate_status` before Docker. The candidate proof, declaration,
target statement, exact source-owned statement/file identities, and artifact
digest are validated before compilation. A successfully compiling declared
proof sketch remains `proof_sketch` with `conversion_ready: false`. Failed
compilation, placeholders, incomplete axiom audit, and unsupported axioms also
remain non-conversion states. Reviewer corrections are retained separately and
cannot upgrade the submitted Result.

## Reproduced gates

- Focused correction suite: 11/11 passed in the review checkout and again from
  a second fresh detached clone.
- Full maintained suite: 28 passed; the unchanged signed-Vela integration test
  remained the single explicit opt-in skip.
- Python 3.11.2, Ruff 0.5.4 check and format, `compileall`, and `git diff
  --check`: PASS.
- Pinned Docker context/image: `desktop-linux`, `linux/arm64`,
  `sha256:eec93eef374618d394269ae1108c0bbe6d247ecc7efdd39eb1a4ba5aec548397`.
- Runtime pin SHA-256:
  `0c42682ca4b8e77b76c04088fe04adc9baf5e8e1ed72398d43e38a380e51eb71`.
- Runtime verifier SHA-256:
  `5f954a638a9c5e0f0451a10865a009a1f7fc1b3a2405172356f0d10bc118f5e5`.
- Exact Formal Conjectures source: commit
  `9cbe1d3c12998c786b7c2cd99ce28a21b6631f66`, tree
  `afc1a5d149d5434089aabe705f3ce450ebfbc244`, archive SHA-256
  `ba47fe3d14126eda45870d40ea951fdaa14a5135dafcf449f8b28f49c53cf6fa`;
  clean before and after.
- Network-disabled preflight passed. Retained receipt SHA-256
  `5638ae45fe9b8f61a63c9dac3d5aa46e1ccf1541859053de982a0d247a3db01e`
  and root
  `adf51e9a24aab93179930012814586ba25ea7c20447f253522cacc35dfee3a93`
  recomputed. Fresh replay reproduced stdout SHA-256
  `3ab10b8ac25d64132bc28d3b90e5f64dbd565c6f9d5a37e68a676539f56a3f4a`
  and stderr SHA-256
  `d47a06d59aba2814c3fb7460049fc2ccbfc834196c956d6c6558e8be8b079e24`.
- Checked proof passed with retained receipt SHA-256
  `e7888ba566ce34f2c0160dd996f9b4f5bd0c65d192ca774f9922abf288360555`,
  verification root
  `ef9fae1891dc0d3fb584935af2e66ed88953a1aa167a023f54f8028528a0d402`,
  and generated-artifact root
  `8b4cd73516c222e318743bbab0bfbd9e3dbe5cf0b1dc7d277ee4d3e9dd5ed8e7`.
  Fresh replay reproduced the OLean SHA-256
  `aaba07269991599e97eb9017ac7ac0cf64102b36bd0bc5b7da60eaaf9cf894e1`,
  proof stdout SHA-256
  `425c790f5b58acc1da16366de354be262cb1d8f7bd5132f69c95e10268046913`,
  empty stderr, checked classification, and no unsupported axioms. Full receipt
  bytes differ as expected because they retain absolute host paths and elapsed
  time; deterministic artifacts and semantic roots match.
- Credential scan: zero findings across all 27 corrective paths.
- Completed RESULTS-FIVE-01 bytes and denominator evidence are unchanged.

## Claim ceiling

The exact producer bytes qualify the corrected prospective custody and
verification implementation for a separately authorized neutral canary and
future exact campaign-freeze review. No model, canary, candidate, evaluator,
campaign, scientific conversion, merge, Vela authority, or Standing action was
performed by this review.
