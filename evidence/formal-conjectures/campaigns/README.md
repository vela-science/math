# Source-owned Math Campaign pilot

This directory contains one experimental product-layer Campaign record for the
closed Erdős 887 source-fidelity Work Offer. It is a read-only coordination
view, not a Protocol object, scientific Decision, funding instrument, or global
mechanism registry.

The record deliberately preserves the historical Completion Contract gap. The
scientific correction was accepted after an independently attributed AI-model
review, but the issued Work Offer had required a human review. Performer class
is now treated as provenance rather than a quality hierarchy; the old contract
is not rewritten retroactively.

The Campaign now links its remapped obligation to the separately issued
`erdos:887:proof-discharge` packet. The Campaign remains closed. The successor
offer has its own roots, contract, results, and authority boundary.

Build and verify it with:

```bash
python3 -B evidence/formal-conjectures/campaigns/build.py
python3 -B evidence/formal-conjectures/campaigns/build.py --check
python3 -B evidence/formal-conjectures/campaigns/test_build.py
```

The single embedded staged-open-work mechanism profile is experimental. A
reusable profile or registry should be extracted only after another materially
different Campaign demonstrates stable shared semantics.
