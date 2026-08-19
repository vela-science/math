# Vela Mathematics Program

Which bounded assertions about Erdős 321, Erdős 94, and Erdős 887 are admitted on exact evidence?

This is a Vela repository. Git stores exact Claims, Submissions, Verification Records, Decisions, and authority history. Derived views are rebuildable.

The current prelaunch state is a compact Submission v3 repository with three
accepted Claims and no pending review. See [`MIGRATION.md`](MIGRATION.md) for
the exact retained current-state inventory.

Current strict replay and deterministic projection use signed Vela 0.977.3
(`sha256:3a1173918bdcb887155bab681411bf5e9ff64d925fe1b50369ac37ab020b94ad`).

## Evaluation material

[`evaluations/time-frozen-replay/erdos-321-occurrence-v1/`](evaluations/time-frozen-replay/erdos-321-occurrence-v1/)
contains one non-Protocol epistemic replay pilot. It exports only exact bytes
available before the historical Erdős 321 occurrence correction, keeps the
later outcome scorer-only, and records an internal deterministic baseline. Its
scores have no authority effect and make no general model-quality claim.

[`evaluations/far-probxiv-result-boundary-v1/`](evaluations/far-probxiv-result-boundary-v1/)
is a rights-safe, non-Protocol comparison of FAR, ProbXiv, and this
Repository's current Result evaluation and correction boundary. It retains
only primary-source locators, small factual labels, and digests; it creates no
scientific record or Standing.

## Operator loop

```bash
vela status . --json
vela submit --repo . --claim "<bounded result>" --type computational --replayability exact --artifact <path>:<kind> --caveat "<limit>" --as agent:<name> --json

# Verification binds method bytes already retained at the current Git commit.
git add -- verification/method.json
git commit -m "Retain verification method"
vela verification record . <vpr_id> --profile <profile> --method verification/method.json --outcome pass --does-not-establish "Scientific acceptance." --as verifier:<name> --json

vela review inbox . --json
# Only an authorized operator may make the exact accept or reject Decision.
vela review accept . <vpr_id> --reason "<reason>" --if-entry-root sha256:... --json
vela replay . --json
```
