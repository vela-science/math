# Case 4 — Erdős 1074 EHS prefix

## Exact identity and evaluation result

- Problem/declaration: Erdős 1074,
  `Erdos1074.erdos_1074.variants.EHSNumbers_init`.
- Evaluated source:
  `google-deepmind/formal-conjectures@9c4d5821819656af53c5473ded2116ea14a7ff1c`,
  `FormalConjectures/ErdosProblems/1074.lean`.
- Source SHA-256:
  `72b74c90c3fbdf66fedcd744d6c90da05fdfc7e87673a016787ae4586c705c45`.
- Current FC `origin/main` `e13dd7284e72012a1616806d09cb6b8025e387af`
  has the same file SHA-256.
- Evaluator verdict: `qualified_candidate`, conversion-ready because an
  independent replay reproduced every factor, exponent, residue, witness,
  exclusion, reconstructed integer, and the final list
  `[8,9,13,14,15,16,17]`.

## Correct conversion form and owning repositories

Priority realization is a combination with two explicitly separate stages:

1. **Checked executable certificate.** Retain the deterministic program,
   exact stdout, exit code, hashes, source definition, and replay environment.
   This is already computational evidence and should remain labelled as such.
2. **Lean theorem realization.** In `williamjblair/lean-proofs` (MIT), prove
   the exact FC declaration or an exact-source theorem that compiles to it,
   including membership, exclusions below 18, increasing enumeration, and the
   `Nat.nth`/image bridge. Only a successful retained Lean build and axiom
   inspection can make this a checked theorem artifact.

The eventual source declaration is owned by
`google-deepmind/formal-conjectures` (Apache-2.0). No data/metadata correction
is indicated: the FC statement already names the correct prefix. Math stores
this bounded handoff only. Math Repository authority would own any later Vela
transaction; none is authorized here.

Reproduced computation must not be upgraded into a proof theorem. A later
Lean theorem is an additional artifact, not a rewrite of the certificate.

The realization handoff timing gate is satisfied: the existing Erdős 399
integration task reached terminal state with `lean-proofs` `origin/main` at
`62444861a41509b90c50499bc923e0ee4235df7d` (tree
`71f7bd5bd65ae3226f5e48a1c8773aa97333a349`) and reported green hosted main
CI. A refreshed exact-name/content search at that commit found no
`EHSNumbers` or `EHSNumbers_init` duplicate.

## Exact retained evidence and nonclaims

- Producer candidate SHA-256:
  `b7af4927edc477ce0a90bdb1c005812a03345ca03f8900d1578d271679195b89`.
- Producer receipt SHA-256:
  `4c6c96e1e660a8b4b527d0b6e8fe4d865156c7fb311d037ec8f9565b9c9621f2`.
- Producer commands/full-output SHA-256:
  `03bae4dc933435dd689bb81c5d98e8de80d6519c99ca39659251b4699e57deac`.
- Producer raw-stream SHA-256 retained in the receipt:
  `2bd4e7a6184f46918c1429ef92e47135b7226aa82572d8203893511b9888c35e`.
- Exact executable body: `case-4-ehs-prefix/certificate.py`.
- Exact retained stdout: `case-4-ehs-prefix/certificate.stdout.txt`.
- Original command and stdout remain addressable at producer commit path
  `results/2026-08-20-docker-batch-3/outputs/04-erdos-1074-ehs-init/tool-calls.json`.

The program proves only its finite computation assuming exact Python integer
semantics and the correctness of its trial-division algorithm. It is not
formally verified, is not a Lean proof, does not establish EHS infinitude, and
does not confer source adoption, Vela Check, Decision, or Standing.

## Required independent Check

For the certificate, independently rerun offline, compare stdout byte-for-
byte, verify every factorization reconstructs `m!+1`, primality/completeness of
the listed factors, residues, membership witnesses, and exclusions for every
`m = 0..17`.

For the Lean realization, use a clean `lean-proofs` branch pinned to its
current main and the exact FC source/toolchain. Retain the proof source, build
stdout, toolchain and dependency roots, exact theorem statement comparison,
and `#print axioms`. The independent checker must be separate from the proof
author and must not call that separation protocol independence by itself.

## Falsifiers

- Any listed factor is composite, any factorization fails to reconstruct
  `m!+1`, or trial division terminates before proving the remaining factor
  prime.
- A residue/witness/exclusion is wrong or another EHS member occurs below 18.
- `Nat.nth` does not enumerate these members as claimed, or the Lean bridge
  checks only membership without exclusions/order.
- Source definitions/hash changed or a current exact proof duplicate exists.
- Replay depends on network, unpinned third-party libraries, nondeterminism,
  or hidden state.
- Lean realization uses `sorryAx`, undeclared axioms, weakened definitions, or
  a statement not exactly matching the FC target.
- Certificate/proof bytes lack compatible explicit licensing.

## Integration gates

1. Preserve and independently replay the executable certificate and stdout.
2. Add explicit licence headers/statements to newly retained program and proof
   bytes; preserve FC Apache-2.0 attribution and lean-proofs MIT terms.
3. Refresh current Math/FC/lean-proofs duplicate and source-hash searches.
4. Implement the exact Lean prefix theorem in `lean-proofs`, including the
   finite-to-`Nat.nth` bridge.
5. Build under pinned dependencies and retain full stdout/digests/axioms.
6. Obtain independent semantic/build Check.
7. Only then decide separately whether to propose FC integration or a Vela
   conversion; this packet performs neither.
