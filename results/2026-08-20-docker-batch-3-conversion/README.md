# Batch 3 conversion handoff

This directory packages only independently conversion-ready Cases 1, 3, and
4 from Docker Result Factory Batch 3. It changes no source repository, Vela
record, authority state, Standing, or external registry.

Frozen evidence:

- producer commit/tree:
  `082a118ea6ce7c9ca6a62f72aa425373228f7efe` /
  `480aa298b947b144bdcd9e9574420dcb69b9b486`;
- evaluator commit/tree:
  `be883fe7808e1860373ce19d12d0cb38b409a687` /
  `4a607a4a4252e927b215c2bce55aff59d6b4d6f7`;
- evaluated FC commit/tree:
  `9c4d5821819656af53c5473ded2116ea14a7ff1c` /
  `4ccf4dbcb68d8cc097551213ed13b184f910f110`;
- Math base/current `origin/main`:
  `5de716c896065c03c0a470d015ba2a328a527f73`.

Current-state search on 2026-08-20:

- Formal Conjectures `origin/main` is
  `e13dd7284e72012a1616806d09cb6b8025e387af`, tree
  `7d2b7c17ff144393c2b4a39973ed212387b3e783`; the three assigned source files
  retain their evaluated SHA-256 values.
- `lean-proofs` `origin/main` is
  `62444861a41509b90c50499bc923e0ee4235df7d`, tree
  `71f7bd5bd65ae3226f5e48a1c8773aa97333a349`, after the Erdős 399
  integration reached terminal state with green hosted main CI.
- Exact target/correction searches found no proof or correction in current
  Math or `lean-proofs`; FC contains only the assigned declarations and its
  subset-index references.

Priority order:

1. Case 4: independently checked executable certificate, then a separate
   exact Lean realization; never call the reproduced computation a theorem.
2. Case 1: FC statement-translation correction plus checked `k = 0` bridge.
3. Case 3: FC docstring-domain correction only.

Each case packet lists its owning repository, evidence, nonclaims, falsifiers,
integration gates, licence boundary, and authority owner. No packet is a Vela
Submission, Verification, Decision, Check, independence claim, or Standing
change.
