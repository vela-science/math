# Vela Mathematics Program disposition

Status: **KEEP as a bounded authority; REDUCE future scope.**

This disposition is derived from the complete 927-path Phase 0 inventory in
[`OWNERSHIP.md`](OWNERSHIP.md). It does not close, archive, relocate, delete,
or rewrite this Repository.

## Exact basis

| Field | Exact value |
| --- | --- |
| Inventory commit | `b1f1a1decd565d9aa38303efaba22d2a54fdf0b8` |
| Inventory tree | `7c2fe41c80d2706f6709f3fce274e87b835f7e1d` |
| Repository id | `8115c538-7688-40b7-ab75-3c4765bf3c19` |
| Repository root at disposition | `sha256:ae41be4a91265d91967344459fa12583314ec05c5a0ebc74d8b0136195879511` |
| Inventory result | 927 paths classified; 0 `obsolete_unbound` |

The inventory contains 143 `authority_required` paths and 684
`historical_evidence` paths. Those 827 paths make archival or closure false:
the Repository still has replay, correction, custody, and explanation duties.
The remaining 100 paths are retained but future-owned elsewhere: 65
`source_owned_future`, 6 `core_conformance`, 4 `projection_owned`, and 25
`activity_owned`.

## KEEP

The Vela Mathematics Program retains only work that needs this authority
boundary:

- strict replay and correction of accepted local scientific state;
- exact Decision, Event, policy, keyset, and Standing custody;
- repair of replay or authority-safety defects;
- explanations and reassessments rooted in retained local history; and
- bounded program-specific evidence needed for one local Proposal or Decision.

These duties preserve the plural-authority architecture. This Repository is
one local authority; it is not Vela's mathematics integration hub and no hosted
service may exercise its scientific authority.

## REDUCE

Future writes follow the inventory classification, while every current byte
stays where history put it:

| Classification | Future write placement |
| --- | --- |
| `authority_required` | This Repository, only for bounded authority, replay, correction, or custody work |
| `historical_evidence` | No new development; retain exact bytes and correct only a custody or reproducibility defect |
| `source_owned_future` | The native source repository, with an Exact Reference back when this authority consumes it |
| `core_conformance` | Vela Core only after two maintained consumers prove the shared waist and extraction deletes more code than it adds |
| `projection_owned` | `vela-web` or another rebuildable read projection |
| `activity_owned` | A Workspace or native workbench, with attributed Agent, Activity, Entity, and Role provenance kept separate |
| `obsolete_unbound` | No current path; any future deletion requires a new exact reference scan and separate authorization |

The Phase 1 native integrations demonstrate shared document, root, inventory,
rights, availability, and Exact Reference mechanics. They do not demonstrate a
shared Lean, proof, review, audit, or statement-fidelity Profile. No such
Profile moves into Math or Core under this disposition.

## MATH-01R and MATH-02R result

MATH-01R is complete as a future-placement rule: new source integration work
goes to `lean-proofs` or the Formal Conjectures contributor fork; generic
structural conformance belongs to Core only under its extraction gate; read
presentation belongs to Web; mutable coordination belongs to a Workspace.

MATH-02R is **KEEP/REDUCE**, not archive. No independent responsibility has
been removed from this Repository's authority duties, and no retained byte is
authorized for destructive migration. A later archival proposal would need to
prove that authority history, replay, correction obligations, exact references,
and public consumers have all moved without changing their meaning.

## Nonclaims

This charter changes no Claim, Submission, Proposal, Verification Record,
Decision, Event, Standing, authority policy, authority keyset, or Protocol 1
object. A clean build, review, commit, or push is not scientific acceptance.
