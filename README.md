# Vela Mathematics Program

Which bounded assertions about Erdős 321, Erdős 94, and Erdős 887 are admitted on exact evidence?

This is a Vela repository. Git stores exact Claims, Submissions, Verification Records, Decisions, and authority history. Derived views are rebuildable.

The current prelaunch state is a compact Submission v3 genesis. See
[`MIGRATION.md`](MIGRATION.md) for the exact retained state and rollback ref.

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
