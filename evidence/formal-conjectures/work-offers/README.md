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

Build, verify, and inspect the exact offer:

```bash
python3 -B evidence/formal-conjectures/work-offers/build.py
python3 -B evidence/formal-conjectures/work-offers/build.py --check --print-roots
python3 -B evidence/formal-conjectures/work-offers/build.py \
  --check \
  --print-target erdos:887
python3 -B evidence/formal-conjectures/work-offers/test_build.py
```

`index.v1.json` and the packet use canonical JSON plus one trailing LF. The
index binds the exact Math repository manifest root, the source-adapter commit
and tree, the source projection and record roots, and the packet's canonical
root, raw-file SHA-256, and byte length.
