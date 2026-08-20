# RESULTS-BREAKTHROUGH-01 disposable session

Record one bounded experiment cell without canonical authority effect

This is a Vela repository. Git stores exact Claims, Submissions, Verification Records, Decisions, and authority history. Derived views are rebuildable.

## Operator loop

```bash
vela status . --json
vela submit --repo . --claim "<bounded result>" --type computational --replayability exact --artifact <path>:<kind> --caveat "<limit>" --as agent:<producer> --json

# Verification binds method bytes already retained at the current Git commit.
git add -- verification/method.json
git commit -m "Retain verification method"
vela verification record . <vpr_id> --profile <profile> --method verification/method.json --outcome pass --does-not-establish "Scientific acceptance." --independent-of agent:<producer> --as verifier:<name> --json

vela review inbox . --json
# An eligible human or agent may perform the exact rooted Decision. --as records
# the performer; Repository policy and the authority signer authorize it.
vela review accept . <vpr_id> --reason "<reason>" --if-entry-root sha256:... --as agent:<reviewer> --session-ref <source-owned-ref> --json
vela replay . --json
```
