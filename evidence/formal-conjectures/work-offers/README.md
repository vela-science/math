# Formal Conjectures source-local Work Offers

Math owns two related records for Erdős 887:

- `erdos:887` is the closed source-fidelity repair. It corrected the answer-slot
  scope defect found in Formal Conjectures PR 1237.
- `erdos:887:proof-discharge` is the open mathematical obligation for the
  corrected `Erdos887.erdos_887.parts.ii` declaration at upstream commit
  `158727e...`.

The offer is a source-local activity packet, not a Vela protocol object. It
cannot create a Verification, Decision, Event, or change to Math Standing.
The Web activity plane may retain the exact Target identifier and packet root,
but it cannot sign or decide scientific state.

Both packets forbid upstream writes without separate authorization. Proof and
source artifacts may be public. Participant private data may not enter these
records.

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
  evidence/formal-conjectures/work-offers/results/erdos-887-pilot-02-current-binding/test_result.py
```

The retained repair result has attributed source-fidelity review. Human and
AI-model method examples live under
[`methods/review-provenance/`](../../../methods/review-provenance/README.md);
the historical human-specific guide remains at
[`results/erdos-887-pilot-02-current-binding/HUMAN_REVIEW.md`](results/erdos-887-pilot-02-current-binding/HUMAN_REVIEW.md).
Current policy treats agent, human, organization, and deterministic-tool performers as
peer provenance classes. Each result records the performer, method, inputs,
dependencies, independence, output, and limits. Performer class does not rank
the evidence.

## Proof-discharge offer

Build and inspect the open packet:

```bash
python3 -B evidence/formal-conjectures/work-offers/proof-discharge/build.py
python3 -B evidence/formal-conjectures/work-offers/proof-discharge/build.py \
  --check \
  --print-roots
python3 -B evidence/formal-conjectures/work-offers/proof-discharge/test_build.py
```

Prepare a clean public checkout at the packet's exact upstream commit:

```bash
python3 -B evidence/formal-conjectures/work-offers/proof-discharge/run_attempt.py
```

The first bounded attempt is retained under
`results/erdos-887-proof-discharge-attempt-01/`. It records an agent performer,
the exact 4.27 toolchain and source, a same-machine compatible cache disclosure,
the current `sorryAx` dependency, and the terminal goal left by exhaustive
`aesop`. Its terminal state is `not_proved_within_declared_bounds`. The offer
stays open because one bounded attempt neither proves the theorem nor exhausts
other methods.

Verify that result with:

```bash
python3 -B evidence/formal-conjectures/work-offers/proof-discharge/capture_result.py \
  --check \
  --output evidence/formal-conjectures/work-offers/results/erdos-887-proof-discharge-attempt-01
```

`index.v1.json`, packets, results, and the closed lifecycle use canonical JSON
plus one trailing LF. The index binds the closed repair and the open proof
offer, including all four execution roots and the first attempt root.

The retained `erdos-887-pilot-01` result predates the execution-component
extension. Its verifier reconstructs and checks the former packet preimage. No
historical result is rebound to a later packet. Only the proof-discharge offer
publishes a next command.
