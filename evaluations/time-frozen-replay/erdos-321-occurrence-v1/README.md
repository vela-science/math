# Erdős 321 time-frozen replay pilot

This is a non-Protocol, task-relative evaluation of one historical Math
transition. It asks whether a candidate given only an exact `t0` view can
propose the bounded occurrence-identity correction that was later admitted at
`t1`, or can refuse for an explicit bounded reason.

The pilot does not create a Claim, Submission, Verification, Decision, Event,
Standing, benchmark authority, or model-quality claim. A passing score says
only that one response matched the protected fields this fixture can compare.
It does not establish mathematical correctness, semantic equivalence,
scientific acceptance, general capability, or external validation.

## Why this split

The current compact Submission v3 genesis is the source-owned current state,
but its migration retained the later correction evidence before replaying the
predecessor. It is therefore unsuitable as a historical clock. This pilot uses
the original chronological Git history instead:

- `t0`: `dba7cc9a0532138109af87d01b3517f7b071c95a`, immediately before
  occurrence-correction preparation began;
- `t1`: `7efcbe8cf48544d393c3ca102fdf24e2051b8c73`, after the exact correction,
  two scoped checks, and authorized acceptance.

The signed Vela 0.976.1 reader replays those historical Submission v2 commits.
They are evaluation archaeology only. The current repository remains
Submission v3 and is replayed by Vela 0.977.1.

## Separation contract

`candidate/task.json` lists every Git object exported to a candidate.
`protected/adjudication.json` lists the later bytes used only by the scorer.
`protected/replay/` records the exact signed historical-reader outputs that
bind the declared `t0` and `t1` Repository roots to their commits and trees;
the verifier checks their byte identities and rejects a merely well-formed
substitute root. These frozen receipts make the fixture self-checking; they do
not replace independent verification of the release signature or rerunning
the historical reader when requalifying the fixture.
`pilot.py export` creates a new directory containing only the task, response
schema, and pinned `t0` objects. It refuses unexpected or changed bytes and
scans the result for protected identifiers. The tests prove that the export
contains no `t1` path or protected token and that a relative attempt to open
`protected/adjudication.json` from the exported bundle fails.

The export directory is the candidate path. Give only that directory to an
external candidate environment; do not mount this repository, its Git object
database, or `protected/`. The internal deterministic baseline runs on the same
host and therefore shares the repository and evaluator implementation. That
dependency is disclosed and is why the baseline is not an isolation or
external-validation result.

## Commands

From this directory:

```bash
python3 pilot.py verify

candidate_dir="$(mktemp -d)/candidate"
python3 pilot.py export --output "$candidate_dir"

python3 baseline.py \
  --bundle "$candidate_dir" \
  --response baseline/candidate-output.json \
  --provenance baseline/provenance.json

python3 pilot.py evaluate \
  --bundle "$candidate_dir" \
  --response baseline/candidate-output.json \
  --provenance baseline/provenance.json \
  --output baseline/score.json

python3 -m unittest discover -s tests -v
```

The committed baseline files are one internal deterministic-tool run. The
response and each scoring dimension are deterministic from the frozen input.
The exact score bytes and root additionally bind the recorded provenance, so
they reproduce only with the same provenance and environment bytes. Provenance
records performer, tool, model absence, environment, command, shared
dependencies, and limitations separately from the scientific records.

## Supplying another domain fixture

Another source-owning repository can reuse the pattern without adopting this
Math rubric:

1. choose a genuine chronological `t0` before the outcome work and an admitted
   `t1` after it;
2. enumerate exact `t0` inclusions and omissions, with commit, tree,
   Repository, record, source, and evidence roots;
3. keep `t1` bytes in a protected scorer-only manifest and export only `t0`;
4. define domain-owned response fields and only those comparisons supported by
   the protected outcome;
5. retain run provenance outside scientific authority and publish limitations.

The exporter/evaluator may be copied or deleted. Its JSON formats are local
evaluation contracts, not Vela Protocol objects or a universal scientific
scoring model.
