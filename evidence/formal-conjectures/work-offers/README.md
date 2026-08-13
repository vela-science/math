# Formal Conjectures source-local work offer

This directory retains one closed Math Work Offer: repair the answer-slot scope
defect in the exact retained head of Formal Conjectures PR 1237 for Erdős 887.
The source audit reported `needs_revision` even though the exact head built
successfully. That separation remains the point of the exercise.

The offer is a source-local activity packet, not a Vela protocol object. It
cannot create a Verification, Decision, Event, or change to Math Standing.
The Web activity plane may retain the exact Target identifier and packet root,
but it cannot sign or decide scientific state.

The packet explicitly forbids upstream comments or reviews without separate
authorization. Its proof and source artifacts may be public, while participant
private data is forbidden from the public packet.

The immutable issued packet is restored at its exact executed root
`sha256:a2cfe3df...bfd057`. Its producer profile, verifier capsule, result
contract, execution result, and attributed review remain independently rooted.
The source-owned lifecycle record closes the offer as `superseded`, not
completed: the issued contract required independent human review, while the
retained qualifying review was performed by an independent AI-model reviewer.
Later performer-neutral packet rebindings were not fresh executed issuances.
The scientific Decision remains valid and separately attributed; it does not
retroactively satisfy the source-owned completion contract.

Build, verify, and inspect the exact offer:

```bash
python3 -B evidence/formal-conjectures/work-offers/build.py
python3 -B evidence/formal-conjectures/work-offers/build.py --check --print-roots
python3 -B evidence/formal-conjectures/work-offers/build.py \
  --check \
  --print-target erdos:887
python3 -B evidence/formal-conjectures/work-offers/test_build.py
python3 -B \
  evidence/formal-conjectures/work-offers/execution/erdos-887-pr-1237-fidelity-repair/verify_binding.py
```

The retained result has bounded attributed source-fidelity reviews. Human and
AI-model method examples are retained under
[`methods/review-provenance/`](../../../methods/review-provenance/README.md);
the historical human-specific guide remains at
[`results/erdos-887-pilot-02-current-binding/HUMAN_REVIEW.md`](results/erdos-887-pilot-02-current-binding/HUMAN_REVIEW.md).
The committed method keeps the semantic question and the execution-binding
check separate. A named reviewer chooses and signs the outcome; this repository
does not infer it from Lean success or rank reviewer kinds by type.

`index.v1.json`, the packet, and the lifecycle record use canonical JSON plus
one trailing LF. The index binds the current Math projection, the immutable
issued packet, its complete execution binding, and the lifecycle root. The
lifecycle binds the exact result, independent attributed review, scientific
Decision and applied Event, explicit absence of program/deployment Decisions,
retired administrative rebindings, and the next identified but unoffered
Obligation. `--print-roots` prints the complete execution binding, lifecycle
root, and index root.

The retained `erdos-887-pilot-01` result predates the execution-component
extension. Its verifier reconstructs and checks the former packet preimage. No
historical result is rebound to a later packet, and the closed index publishes
no next command or open Work Offer.
