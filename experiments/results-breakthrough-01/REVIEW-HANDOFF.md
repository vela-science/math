# Corrected immutable preregistration re-review handoff

Review the single successor commit containing this file on branch
`codex/results-breakthrough-01-prereg-2026-08-20`. Its predecessor is exactly
`0bbf3b8578417c928fe2b62ee9912f2c7918e9d5` / tree
`5f71bffbfad364d628abf8ba70003e91a2dcd643`. The blocking evaluator evidence is
exactly `43c51f9f893a6919428a290421a8344a11c5f5f4` / tree
`4069ae9ed804fec3178c548ecc4475179f3568ba`, with report SHA-256
`93765f10bc011971aac413ecb854b8e641f7630fc3e8a2ceb9f0e74e25de27a6`
and verdict SHA-256
`16ecb8fe09d50693b67db1fbbdd892c30ff117397162b3aadcb873ffaac0da7a`.

`HASHES.tsv` binds every other file in this experiment directory. The Git tree
binds both this handoff and that hash manifest. `EVALUATOR-LOCK.json` binds the
normative Stage 1 freeze/receipt/rubric/analysis bytes; `SOURCE-LOCK.json` binds
all source/evaluator bundles, commits, trees, archive hashes, licenses, and
tool identities.

## Corrections presented for exact re-review

1. The five frozen verdicts, usable definition, scientific recovery,
   30-assignment ITT denominator, smoke gate, paired summaries, NO-VALUE graph
   falsifier, and 40–60 scale gate are restored without a competing contract.
2. T02 is no longer called novel. The duplicate index records three exact Math
   occurrence/provenance metadata matches for
   `Erdos138.monoAPNumber_two_two`; neither linked external proof commit is in
   the frozen FC object database. T02 remains only an independent proof
   realization target and may not claim theorem novelty. All ten targets were
   reindexed against exact Math and lean-proofs commits.
3. Both Docker `FROM` inputs are digest-pinned. The proposed build uses only a
   verified archive of Vela commit `88fcc0105eba35ee22ed1816d3aabba3322bebc1`
   / tree `2cb85fe1e1c3525ba97ff2aec25945417ea7b372`, bound by a 412-file context
   manifest. The deterministic experiment-only machine ID is exactly 32
   lowercase hex characters plus newline and remains a proposed, unbuilt
   post-review delta.
4. Ten producer cards, ten supplied-order fact roots, 30 fixed assignments, a
   byte-identical common arm wrapper, three minimal adapters, 30 equivalence
   manifests, mount/materialization/isolation/credential scripts, and N/G
   no-model receipts are frozen. The source-mount fixture recomputed all four
   exact Git archive hashes. Two independent readers report PASS with no
   discrepancies and no candidate-output access.
5. `PROCESS-LOG.md` retains observed failures and corrections append-only. It
   is evidence only, adds no gate, and will receive its keep/change/delete
   retrospective at experiment end.

## Deterministic local validation

Run from a checkout of this exact commit with the four bundle-reconstructed,
detached, clean source repositories and the exact evaluator repository:

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

Expected terminal summary:

```text
json_files=80
targets=10
cells=30
equivalence_manifests=30
independent_readers=2
candidate_inference=false
validation=pass
```

## Current prohibition and smallest next authorization

No corrected image was built, no Vela lifecycle fixture ran, and no candidate
inference or scientific/canonical mutation occurred in this correction turn.
A PASS on this exact commit may authorize only the already bounded next steps:
create evaluator-held Stage 2 bytes, rebuild the exact proposed image once, run
one corrected disposable no-model signed Vela lifecycle with retained
stdout/stderr/exit/hashes, and return those receipts for the frozen launch
review. Only the later launch PASS may authorize the six T01/T02 smoke cells.
