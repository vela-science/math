# V Review Method correction re-review handoff

Review the single successor of producer commit
`161a9af0551b43f7c89aabedc3b7ea4316757741` / tree
`221f8c3c07a2046f96114f9ca6f4aa89615fd63e` on branch
`codex/results-breakthrough-01-prereg-2026-08-20`.

The controlling BLOCKED review is evaluator commit
`03855d5b4a0f7b88385d84df1cf2c3c79abdabfb` / tree
`ad2921579f888eadcc9c2e17d2cade2a7c3720b2`, report SHA-256
`220cebb44d252292057002ca62ec36e00591afab8d000690891790669e37cb28`,
and verdict SHA-256
`76f3ac97c47c7d41503eafdf095994268d9f31bf798d1782011508c9111d093e`.
It independently found every prior B1–B6 defect resolved and identified one
new executable blocker only. This delta does not revisit those resolved
surfaces.

## Sole correction

- `arms/V/blinded-review-method.json` is canonical JSON plus one LF and has
  SHA-256 `03c3add32ac7f33c01afa084233ee2f43b1efc8a1b81873db5b995be0c0bc4e3`.
- `arms/V/review-method.schema.json` is byte-identical to
  `vela@88fcc0105eba35ee22ed1816d3aabba3322bebc1:schemas/review-method.schema.json`,
  Git blob `36a185fb5dc4b3dbcb5365825383dfe449dd3ad9`, SHA-256
  `0b202272637dc5dc0219822116f87488f95c4993230654c5544d35c8a49bbe31`.
- The method truthfully binds profile `blinded-source-native`, registered
  property `Frozen blinded source-native adjudication`, AI reviewer
  `gpt-5.6-sol` / OpenAI, attesting actor `verifier:blinded-evaluator`, the
  blinded adjudication procedure, required output, and two exact nonclaims.
- `scripts/validate-review-method.py` checks the exact frozen schema, canonical
  framing, reviewer fields, CLI profile/property/actor/nonclaim bindings, and
  dependency disclosures. `arms/V/lifecycle.sh` runs it with retained
  stdout/stderr/exit/hashes before either `prepare` or `finalize` may invoke
  Vela, then validates the retained method again before Verification.
- Verification declares only execution-scoped checking of
  `agent:result-producer`. It separately discloses the shared OpenAI/model
  family, experiment owner, Docker host, source mounts, fact pack, answer
  schema, and campaign-local repository. Its method explicitly does not claim
  organizational, provider, model, operator, host, or source independence.
- Only the V adapter, frozen schema/method validator receipt, V equivalence
  manifests, evaluator lock, explanatory text/process observation, validator,
  and final hash bindings change. Candidate cards, fact packs/roots,
  assignments, N/G adapters/manifests/fixtures, Dockerfile, build context,
  source locks, and scientific inputs remain byte-identical.

## Deterministic validation

Run from a checkout of this exact successor with the four frozen clean source
clones and the exact evaluator repository:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/results-breakthrough-01/scripts/validate-prereg.py \
  --root experiments/results-breakthrough-01 \
  --math <exact-math-clone> \
  --fc <exact-formal-conjectures-clone> \
  --lean-proofs <exact-lean-proofs-clone> \
  --vela <exact-vela-clone> \
  --evaluator /Users/williamblair/Documents/Codex/2026-08-20/results-breakthrough-01
```

Expected summary:

```text
json_files=83
targets=10
cells=30
equivalence_manifests=30
independent_readers=2
frozen_review_method_validators=1
candidate_inference=false
validation=pass
```

`HASHES.tsv` binds every other experiment file by path, byte count, and
SHA-256; the successor Git tree binds that manifest. The exact successor
commit/tree, hash-manifest digest, V adapter digest, validator digest, and
remote equality accompany the task handoff.

## Prohibition and next gate

This correction does not build an image, execute a Vela lifecycle or V fixture,
create Stage 2, start candidate/evaluator inference, or mutate any source,
provider, canonical record, authority, or Standing. A PASS on this exact
successor may authorize only the already-frozen next steps; it does not itself
authorize candidate inference.
