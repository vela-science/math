# Calibration

D1 is a heuristic. Before applying it to someone else's corpus it has to be
shown to separate a known-conditional artifact from an unconditional statement
inside that same artifact. This file records that check. `calibration.json` is
the machine-readable form, produced by:

```bash
python3 analyze.py calibrate --checkout <erdos887-checkout> --output calibration.json
```

## The artifact

`jarekkoch-hub/erdos887-lean` at `230bf2cd0bc15f971ad9d0e36f36f2056dd9d8b7`.

It is **not** part of the population this audit measures. Formal Conjectures
does not link it from any `formal_proof` attribute at the pinned commit. It is
here only because it is a case where the answer is already known by hand, which
is what a detector needs to be calibrated against.

## What the ordinary gate says about it

- builds clean across 7,663 jobs
- `sorry`: 0
- `axiom`: 0
- `#print axioms` on the top-level theorems: exactly `propext`,
  `Classical.choice`, `Quot.sound`

Every gate the field runs is green.

## What it actually proves

Three of its four Formal-Conjectures-mirroring theorems take an argument:

```lean
theorem erdos_887_parts_ii (X : ExternalCanonicalExtraction.ExternalReconstructionSource) : …
```

`ExternalReconstructionSource` has exactly one construction site in the
repository, `externalReconstructionSource_of_components`, and that site takes
`CanonicalExtractionSource` and `RootBandSurvivorReconstructionSource` as
arguments. Neither of those has any construction site at all. So the package is
never closed-constructed, and the three theorems are implications whose
antecedent is the mathematics.

A binder is not an axiom. Nine `opaque` declarations additionally seal the
arithmetic core, and `opaque` is likewise invisible to `#print axioms`.

## What D1 says about it

| declaration | D1 |
|---|---|
| `erdos_887_parts_i_answer_four` | `flagged_conditional_construction` |
| `erdos_887_parts_ii` | `flagged_conditional_construction` |
| `erdos_887_variants_rosenfeld_4_paper_recurring_form` | `flagged_conditional_construction` |
| `erdos_887_variants_rosenfeld_infinite` | `clear` |

The fourth theorem genuinely does not take the package — it is discharged from
a constructed Rosenfeld source with `C = 64` — and D1 passes it. That
separation, inside one file, is the calibration.

## Why the closure rule is necessary

A naive "is this type ever constructed anywhere" check **passes** this
artifact, because `externalReconstructionSource_of_components` exists and
returns the type. Under that rule the detector reports nothing and the audit is
worthless.

D1 instead takes the least fixpoint of *closed* construction: a construction
site counts only when its own binders are already discharged. That is what
makes the difference between `conditional_construction_only` and
`closed_construction`, and it is the difference between seeing this artifact
and not.

## Not an accusation

The artifact's own audit file states, in prose, that
`ExternalReconstructionSource` is a record package and not the statement that
no counterexamples exist, and names the two component packages that carry the
assumption. The author disclosed the assumption layer. This reads as a
formalisation methodology, not as deception.

The failure being measured is on the reader's side: the gate the community
runs, and the badge it produces, does not distinguish this from a closed proof.
