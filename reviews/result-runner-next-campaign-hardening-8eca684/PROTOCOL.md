# Frozen independent re-review protocol

Frozen before inspecting producer commit
`8eca684f02db097ccd25f4e0de0a451bcf7f68eb`.

## Subject and scope

- Repository: `https://github.com/vela-science/math.git`.
- Base: `6fea63f2e7882fd9de0398868984cd88a17898f1`.
- Prior producer: `033ff587142f23f67e2b7fb281821c2f6395839f`.
- Prior independent review: `6ce4bfbcfeab4428cdec9e3726471d9d7064d9ba`.
- Corrective producer: `8eca684f02db097ccd25f4e0de0a451bcf7f68eb`,
  expected tree `27f814e77a2afab2c5b4c31fd8e058b3f419573c`.
- Re-review is limited to RRH-01 through RRH-04 and regression of the
  previously passing runtime, receipt, denominator, credential, and preserved
  RESULTS-FIVE-01 boundaries.

## Mandatory gates

1. **RRH-01 terminal and verification custody.** Terminal and source-native
   verification receipts must be runner-generated, closed-schema, root-bound,
   and linked to retained invocation, streams, usage, source, image/config,
   result, route, credential-scan, and execution evidence. Missing, fabricated,
   extra, or drifted fields must fail closed before an evaluator permit exists.
2. **RRH-02 canary and review custody.** The fixed five-candidate plus
   five-evaluator plan may freeze only from real, exact-byte-linked canary and
   independent-review receipts bound to the producer commit/tree, runtime
   implementation/pin/image, and referenced evidence. Scalar assertions or
   absent preimages must not unlock the plan.
3. **RRH-03 duplicate and non-result evidence.** Duplicate and non-result
   outcomes must use closed Result and source-native evidence schemas with exact
   occurrence/declaration/source roots and typed reasons. Arbitrary JSON or text
   must fail closed. Both remain non-conversion outcomes in the denominator.
4. **RRH-04 closed Result status and target fidelity.** Candidate Result status
   must be a closed enum. Unknown statuses fail before Docker. Successful
   compilation cannot promote a proof sketch or a declaration not bound to the
   frozen scientific target to conversion-ready.

## Reproduction

- Verify remote commit/tree/base and changed-path scope.
- Run focused correction tests, the full maintained suite, and the focused suite
  from a fresh detached clone.
- Reproduce Ruff/compile checks, the exact pinned network-disabled Docker/Lean
  preflight and checked-proof receipts, and the credential scan.
- Confirm completed RESULTS-FIVE-01 evidence is unchanged from the base.
- Add direct benign adversaries for each prior fail-open family rather than
  relying only on nominal producer tests.

## Verdict rule

Return `PASS` only if every mandatory gate and claimed retained gate reproduces
against the exact producer bytes. Otherwise return `BLOCKED` with exact
reproduction evidence. Neither verdict authorizes inference, a canary, a
campaign, merge, Vela protocol or authority action, Standing, or scientific
acceptance.
