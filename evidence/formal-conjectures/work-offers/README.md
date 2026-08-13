# Formal Conjectures source-local work offer

This directory publishes one current, bounded Math work offer: repair the
answer-slot scope defect in the exact retained head of Formal Conjectures PR
1237 for Erdős 887. The source audit reports `needs_revision` even though the
exact head built successfully. That separation is the point of the exercise.

The offer is a source-local activity packet, not a Vela protocol object. It
cannot create a Verification, Decision, Event, or change to Math Standing.
The Web activity plane may retain the exact Target identifier and packet root,
but it cannot sign or decide scientific state.

The packet explicitly forbids upstream comments or reviews without separate
authorization. Its proof and source artifacts may be public, while participant
private data is forbidden from the public packet.

The live offer also publishes three independently rooted public execution
components under `execution/erdos-887-pr-1237-fidelity-repair/`: an eligible
producer profile, a network-independent verifier capsule, and a positive result
contract. The packet binds their schemas, paths, canonical roots, raw-file
digests, and sizes. The index combines those roots with the completed packet
root as the closed `vela.execution-binding.v1` object a producer may copy into
an unsigned Submission. These activity-plane records all carry
`authority_effect: none`.

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

The current result is ready for a bounded, attributed source-fidelity review.
Human and AI-model examples are retained under
[`methods/review-provenance/`](../../../methods/review-provenance/README.md);
the historical human-specific guide remains at
[`results/erdos-887-pilot-02-current-binding/HUMAN_REVIEW.md`](results/erdos-887-pilot-02-current-binding/HUMAN_REVIEW.md).
The committed method keeps the semantic question and the execution-binding
check separate. A named reviewer still chooses and signs the outcome; this
repository does not infer it from Lean success or rank reviewer kinds by type.

`index.v1.json` and the packet use canonical JSON plus one trailing LF. The
index binds the exact Math repository manifest root, the source-adapter commit
and tree, the source projection and record roots, and the packet's canonical
root, raw-file SHA-256, and byte length. `--print-roots` prints the complete
execution binding and index root.

The retained `erdos-887-pilot-01` result predates the execution-component
extension. Its verifier reconstructs and checks the former packet preimage; it
is intentionally not rebound to the new live packet root. A new Submission or
result must use the full binding now published by the index.
