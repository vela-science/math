# Vela Mathematics Program ownership inventory

This document freezes future placement for the exact 927 tracked paths at the
Phase 0 baseline. It does not relocate, delete, rewrite, or re-root anything.

## Frozen baseline

| Field | Exact value |
| --- | --- |
| Git commit | `b1f1a1decd565d9aa38303efaba22d2a54fdf0b8` |
| Git tree | `7c2fe41c80d2706f6709f3fce274e87b835f7e1d` |
| Repository id | `8115c538-7688-40b7-ab75-3c4765bf3c19` |
| Repository root | `sha256:ae41be4a91265d91967344459fa12583314ec05c5a0ebc74d8b0136195879511` |
| Strict replay | `pass` |
| Tracked paths | `927` |

This inventory implements the following approved documents, read completely
before the packet was frozen:

| Governed document | SHA-256 |
| --- | --- |
| `VELA_CANONICAL_NATIVE_INTEGRATION_ARCHITECTURE_2026-08-13.md` | `3ac5740763db46c2c64a0d2154c6ab464def2cd8371e265d16a9be083f374ead` |
| `VELA_NATIVE_REPOSITORY_INTEGRATION_AND_AUTHORITY_PLAN_2026-08-13.md` | `4e499ed9703560bf8f859a709d4e8f9265980e1a089a4e3fe1427583c6a0836f` |

The classification is complete when
`python3 -B scripts/validate_ownership_inventory.py` reproduces the baseline
tree and the counts below. The checker reads the committed baseline tree, not
the mutable working directory. `OWNERSHIP.md` and its checker are Phase 0
`authority_required` repository-safety additions and are intentionally outside
the frozen 927-path count.

The root documentation uses the approved display identity **Vela Mathematics
Program**. The authority-bound `vela.toml` retains its historical name because
the current Profile, repository manifest, and origin bind that exact identity;
changing it in place would invalidate replay rather than perform a display-only
rename. Any authority-profile migration requires separate authorization.

## Classification semantics

| Classification | Meaning | Baseline paths |
| --- | --- | ---: |
| `authority_required` | Necessary to replay or explain a local Decision or Standing, or to operate this authority safely | 143 |
| `historical_evidence` | Retained exact evidence for an already recorded case or completed experiment | 684 |
| `source_owned_future` | Current bytes remain retained; future revisions belong in the native source repository | 65 |
| `core_conformance` | Generic behavior may move to Vela only after the two-consumer extraction gate | 6 |
| `projection_owned` | Future rebuildable read data belongs in `vela-web` or another projection | 4 |
| `activity_owned` | Future mutable work belongs in a Workspace or native workbench | 25 |
| `obsolete_unbound` | No live reference, authority history, or reproducibility duty | 0 |

The first six classifications are retention or future-placement decisions.
None authorizes deletion. No path is classified `obsolete_unbound`; therefore
this inventory authorizes no deletion at all.

The evidence-based repository disposition is recorded in
[`MATH_CHARTER.md`](MATH_CHARTER.md): **KEEP** the bounded authority and
**REDUCE** future scope. The 827 `authority_required` and
`historical_evidence` paths preserve live replay, correction, custody, and
explanation duties. The other 100 paths remain retained while future revisions
move to their classified owners.

## Complete path rules

These closed rules partition every path in the frozen tree. A trailing `/**`
means every tracked descendant at the baseline commit.

### `authority_required`

- `.gitattributes`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `README.md`, and
  `vela.toml`;
- `.vela/**`, `records/**`, and `continuity/**`;
- `evidence/erdos-321/definition-correspondence.v1.json` and
  `evidence/erdos-321/definition-correspondence.v2.json`;
- `evidence/erdos-321/correction-impact/**`;
- `evidence/erdos-321/terminal-variants/**`;
- `evidence/erdos-522/**`;
- `methods/erdos-321/**`, `methods/erdos-522/**`, `methods/erdos-887/**`, and
  `methods/review-provenance/**`;
- `evidence/formal-conjectures/work-offers/results/erdos-887-pilot-02-current-binding/**`.

The last packet contains exact evidence used to explain current local history.
Its native source may own future work, but these bound bytes remain here.

### `historical_evidence`

- `.github/workflows/terminal-variant-evidence.yml`;
- `evidence/erdos-321/external-workbench-return/**`,
  `evidence/erdos-321/translation/**`, and
  `evidence/erdos-321/workbench-compatibility/**`;
- `evidence/formal-conjectures/agent-evaluation/**` and
  `evidence/formal-conjectures/reviews/**`;
- `evidence/formal-conjectures/work-offers/execution/**`;
- the closed repair paths
  `evidence/formal-conjectures/work-offers/lifecycle/erdos-887-pr-1237-fidelity-repair.v1.json`,
  `evidence/formal-conjectures/work-offers/packets/erdos-887-pr-1237-fidelity-repair.v1.json`,
  and `evidence/formal-conjectures/work-offers/results/erdos-887-pilot-01/**`;
- `sources/gpt_erdos/**` and `sources/wiki/**`.

Completed studies and compatibility experiments stay exact and reproducible.
They receive no new generic development here.

### `source_owned_future`

- `.github/workflows/formal-conjectures-phase-0.yml`;
- `sources.yaml` and `sources.lock.json`;
- `evidence/formal-conjectures/audit-pilot/**` and
  `evidence/formal-conjectures/source-adapter/**`;
- `methods/formal-conjectures/**`.

These exact versions remain historical inputs and may still be needed by
current consumers. New Formal Conjectures integration and audit revisions
belong in the contributor fork. Other source revisions belong with their
native owners.

### `core_conformance`

- `evidence/formal-conjectures/conformance/**`;
- `methods/source-adapters/**`.

These prototypes do not move into Vela Core during Phase 0 or Phase 1. The two
native integrations must first prove shared behavior and an extraction must
delete more maintained duplication than it adds.

### `projection_owned`

- `evidence/formal-conjectures/campaigns/**`.

The retained Campaign is historical. Future rebuildable presentation belongs
in a read projection and has no authority effect.

### `activity_owned`

- `evidence/formal-conjectures/work-offers/README.md`, `build.py`,
  `test_build.py`, and `index.v1.json`;
- `evidence/formal-conjectures/work-offers/packets/erdos-887-proof-discharge.v1.json`;
- `evidence/formal-conjectures/work-offers/proof-discharge/**`;
- `evidence/formal-conjectures/work-offers/results/erdos-887-proof-discharge-attempt-01/**`.

The issued offer and bounded attempt remain retained. Future coordination and
attempts belong in a Workspace or source-owned workbench. Neither an attempt
nor a Workspace changes Standing.

### `obsolete_unbound`

No baseline path. A future deletion proposal requires a separate exact scan of
canonical records, Git history, replay, roots, documentation, tests,
projections, and public consumers. Git cleanliness or a future owner alone is
not zero-reference proof.

## Freeze

Math may continue authority maintenance, replay safety, correction duties, and
bounded program-specific work. It must not receive new generic adapters,
shared Profiles, source-specific schemas, general Lean infrastructure,
workbench machinery, review dashboards, agent activity, source registries, or
cross-domain experiments.

Future placement never changes historical custody. No existing Decision may be
rewritten to point elsewhere, no historical root may be regenerated, and no
source-owned integration may claim to be the historical origin of bytes first
retained here. Only an exact authorized Decision can change this Repository's
Standing.

## Post-baseline authority additions

The following paths were added after the frozen 927-path baseline and are
`authority_required`; they do not change the baseline count:

- `MATH_CHARTER.md`;
- `.github/workflows/math-authority-maintenance.yml`;
- `evidence/erdos-321/claim-occurrence-correction/**`; and
- `methods/erdos-321/claim-revision-fidelity.v1.json` and
  `methods/erdos-321/subject-occurrence-mapping.v1.json`.

They implement future-write placement, the KEEP/REDUCE disposition, and one
bounded correction-preparation duty. The generated packet has authority effect
none and performs no Vela write. Its future Claim, Proposal, Verification,
Decision, Event, and Standing identities remain unavailable until their exact
authenticated operations occur.
