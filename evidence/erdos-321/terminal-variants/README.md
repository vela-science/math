# Erdős 321 terminal-variant comparison v0.1

This directory is a source-local, read-only evidence unit. It compares the
pinned terminal theorem in `williamjblair/lean-proofs` with the fixed lower and
upper variants already retained from Formal Conjectures. It creates no Vela
protocol object, changes no Submission, Verification, Decision, Event, or
Standing, and has `authority_effect: none` throughout.

The Star Fleet theorem bytes are not copied here. The pinned upstream NOTICE
says those files are not covered by the repository MIT license, remain the
author's copyright, and are hosted in `lean-proofs` with permission while a
portable license is pending. This unit therefore retains exact Git-object and
SHA-256 references only. The rights classification is evidence, not a license
grant.

The comparison establishes only that:

- `extremalSize` and `R` denote the same extremal quantity under the already
  retained corrected correspondence;
- the terminal and fixed statements occupy an overlapping iterated-log scale
  family; and
- the terminal theorem is not the same statement as either fixed variant, and
  no implication or equivalence is proved in either direction by these
  retained artifacts.

The pinned project has no committed `lake-manifest.json`, and its historical CI
recipe used mutable runner, action, installer, and cache inputs. This unit roots
the full upstream Git tree plus the theorem, definition, toolchain, direct
dependency, audit-script, workflow, NOTICE, and LICENSE objects consumed by the
comparison. It is not a fresh Lean run or an exact reconstruction of the
historical CI environment.

## Files

- `source-lock.v0.1.json` roots the exact upstream and inherited Math commits,
  trees, key proof/CI/rights blobs, dependency revisions, and handling boundary.
- `comparison.v0.1.json` contains the bounded statement comparison.
- `plan.v0.1.json` preregisters a future public-instrument cold-reader study.
  It binds a common participant-facing packet and a separate
  `reader-instrument.v0.1.json`, which freezes matched source-only and
  source-plus-comparison arms, the pre-enrollment assignment schedule,
  append-only observed-ledger schema, deterministic scoring, custody, stopping,
  first-period analysis, and null `not_measured` observations. Classification
  choices are cued and are reported as such; selected material differences
  require participant-authored explanations and exact evidence locators.
- `participant-packet.v0.1.json` is the exact common delivery subset for both
  arms. It contains the neutral prompt and response form, but no scoring key.
- `reader_scorer.py` is the pure 11-component deterministic scorer. Eligible
  readers must attest that they had not seen the instrument, scorer, or answer
  text before their first period; the public study is not blinded.
- `reader_protocol.py` fixes the append-only event-chain, enrollment,
  assignment, completion, timing, and custody-root algorithms; its literal
  vectors are in `reader_protocol_test.py`.
- `reader_run.py` is the operator for the frozen study. It initializes a
  private custody directory, assigns eligible readers, records rooted raw
  responses and timing, audits every retained byte, and computes only the
  preregistered first-period estimator. `reader_run_test.py` exercises a full
  two-reader crossover plus withdrawal and hostile custody files.
- `evidence_rooting.py` is the small shared canonical JSON/rooting subset.
- `build.py` reads only pinned local Git objects and emits deterministic JSON.
- `test_build.py` exercises determinism, roots, rights, and refusal boundaries.

## Reconstruct

The exact `a8c2872a...` object must already be present in a local
`lean-proofs` object store. The builder performs no fetch or network access.

```bash
python3 -B evidence/erdos-321/terminal-variants/build.py \
  --lean-proofs-repo ../lean-proofs \
  --mathlib-repo /path/to/mathlib4 \
  --pnt-repo /path/to/PrimeNumberTheoremAnd --check
VELA_LEAN_PROOFS_REPO=../lean-proofs \
VELA_MATHLIB_REPO=/path/to/mathlib4 \
VELA_PNT_REPO=/path/to/PrimeNumberTheoremAnd \
  python3 -B evidence/erdos-321/terminal-variants/test_build.py
python3 -B evidence/erdos-321/terminal-variants/build.py \
  --lean-proofs-repo ../lean-proofs \
  --mathlib-repo /path/to/mathlib4 \
  --pnt-repo /path/to/PrimeNumberTheoremAnd --print-root
```

All three local object stores must be complete, non-shallow, non-promisor
repositories with the exact pinned objects and canonical origin URLs. The
builder performs no fetch or lazy object acquisition.

`.github/workflows/terminal-variant-evidence.yml` acquires those complete
public object stores before invoking the otherwise offline builder and tests.

To generate the three retained outputs rather than checking them, omit
`--check` and `--print-root`. `--print-root` is read-only.

No participant or evaluator run is authorized by these files. The frozen run
targets 12 eligible human readers before the stated cutoff; model observations
are excluded from that run and may never be pooled with human evidence.
Because the instrument is public, later observations must exclude prior
authors/reviewers, retain access and timing provenance, and never be described
as blinded or held-out.

## Operate the preregistered run

The custodian uses a fresh parent-owned directory. `init` creates the run at
mode `0700`; attestations, raw responses, period records, and the append-only
ledger remain mode `0600`. The exact pinned `lean-proofs` object store is read
only to verify the terminal source bytes supplied during each period.

```bash
python3 -B evidence/erdos-321/terminal-variants/reader_run.py init \
  /private/custody/erdos-321-reader-run --custodian 'custodian:<id>'

python3 -B evidence/erdos-321/terminal-variants/reader_run.py enroll \
  /private/custody/erdos-321-reader-run \
  --participant-id human-001 --attestation /private/intake/human-001.txt \
  --occurred-at 2026-08-15T12:00:00Z

python3 -B evidence/erdos-321/terminal-variants/reader_run.py opened-materials \
  /private/custody/erdos-321-reader-run --participant-id human-001 \
  --opened-at 2026-08-15T12:05:00Z > /private/intake/human-001-opened.json

python3 -B evidence/erdos-321/terminal-variants/reader_run.py record-period \
  /private/custody/erdos-321-reader-run --participant-id human-001 \
  --response /private/intake/human-001-response.json \
  --opened-materials /private/intake/human-001-opened.json \
  --lean-proofs-repo /path/to/lean-proofs \
  --timer-started-at 2026-08-15T12:05:00Z \
  --timer-stopped-at 2026-08-15T12:25:00Z \
  --monotonic-started-ns 1000000000 --monotonic-stopped-ns 1200000000000 \
  --occurred-at 2026-08-15T12:25:00Z

python3 -B evidence/erdos-321/terminal-variants/reader_run.py audit \
  /private/custody/erdos-321-reader-run --lean-proofs-repo /path/to/lean-proofs
python3 -B evidence/erdos-321/terminal-variants/reader_run.py analyze \
  /private/custody/erdos-321-reader-run --lean-proofs-repo /path/to/lean-proofs \
  --as-of 2026-10-08T00:00:00Z
```

The participant response is the exact JSON shape in
`participant-packet.v0.1.json`. Scoring occurs only after raw response custody.
The result keeps second-period answers outside the primary estimator and makes
no acceptance, adoption, scientific-lift, or reviewer-efficiency claim.
