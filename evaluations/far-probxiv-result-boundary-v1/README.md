# FAR / ProbXiv Result-boundary comparison

This is a deterministic, non-authoritative evaluation frozen on 2026-08-19.
It asks a narrow question: after FAR or ProbXiv finds, attempts, checks, or
retracts a candidate, what additional scientific-state boundary does Vela
actually provide?

The answer is deliberately mixed. FAR is stronger at literature-scale
discovery and effort allocation. ProbXiv already separates attempts from
machine and formal checks, states important fidelity limitations, and
preserves a retracted page. Those are not unique Vela capabilities. The
current Math Repository additionally demonstrates content-addressed source and
Result scope, authenticated performer/checker/authority axes, attributed
Decision and Event admission, exact Standing, correction replay, and
provider-independent reconstruction from Git.

This directory does not import any external proof or page body. It creates no
Problem, Result, Submission, Verification, Decision, Event, or Standing. Every
FAR/ProbXiv mapping is explanatory and has `authority_effect: none`.

## Frozen inputs

- FAR paper: arXiv `2608.16977v1`, submitted 2026-08-17, CC BY-NC-SA 4.0.
- FAR code: `zeyu-zheng/FAR` commit
  `0f498a7e9252affd478cbfe324f51ea6d0119331`, Apache-2.0.
- ProbXiv: live anonymous pages observed 2026-08-19; no public content license,
  API, export, source repository, or reconstruction contract was observed.
- Quipu: arXiv `2608.16813v1`, submitted 2026-08-17, CC BY 4.0. It supplies
  test questions about valid time and transaction time, not a Vela failure.
- Vela baseline: this Math Repository at
  `cf46d6f98b053714d16f113587c23a39d3e8bc8b`, replayed by signed Vela
  `0.977.3`.

See `audit.json` for exact source digests and `candidates.json` for the five
rights-safe comparison cases. The ProbXiv digests commit only to normalized
rendered `<main>` text observed during the audit; the text itself is not
redistributed. `vela-baseline.json` records the signed-reader replay and the
exact current correction events used by the comparison.

## Run

```bash
python3 evaluate.py verify
python3 evaluate.py report --output report.json
python3 -m unittest discover -s tests -v
```

`verify` rejects changed candidate IDs, missing dimensions, invented authority
effects, known body-copy fields, oversized retained strings/records, and
aggregate-score fields. This is a bounded structural rights guard, not a
copyright classifier. `report` derives every matrix cell from the same closed
two-criterion rubric and produces counts, not a leaderboard.

## Internal comparison result

The frozen matrix contains nine questions and three systems. It supports four
bounded conclusions:

1. FAR is the only system in this set satisfying both frozen
   discovery/allocation criteria; Vela should consume its selected artifacts
   only as external evidence.
2. ProbXiv falsifies any Vela claim of unique evidence-axis separation,
   statement-fidelity caveats, or preserved retraction.
3. The additional demonstrated Vela boundary is attributable admission,
   consequence-complete correction/replay, exact source custody, and Git-only
   reconstruction—not better search or proof generation.
4. Neither FAR nor ProbXiv candidate is admitted here. Their machine labels,
   human-review prose, and status projections do not become Vela authority.

The comparison is internally authored and reviewed. It is not an independent
scientific evaluation. `EXTERNAL_PILOT.md` is the bounded outside-review packet.

## Temporal finding

`TEMPORAL_FINDING.md` distinguishes source observation time from Vela
admission/Event time. The current scientific question is answerable without a
bitemporal Core schema: the external observation is retained in this derived
evaluation, while Git, Decisions, Events, corrections, and strict replay
answer what the Repository admitted and when. This does not make Vela a
general valid-time database.
