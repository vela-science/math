# Vela Mathematics — agent charter

Canonical state is Git history plus the current `.vela/repository.json` manifest. Producers may inspect exact Target briefings, submit signed evidence directly, and record scoped Verification. Only an authorized human Decision changes scientific standing.

Agents must not invoke `vela review accept` or `vela review reject`, access repository-authority credentials, hand-edit canonical records, or describe Verification as acceptance. A Verification method manifest must be tracked, clean, and retained in the current Git commit before `vela verification record`.

```bash
vela status . --json
vela next . --limit 1 --json
vela start <target> --json
vela submit --repo . --claim <bounded-claim> --type computational --replayability exact --artifact <path>:<kind> --caveat <limit> --as agent:<name> --json
vela verification record . <vpr_id> --profile <profile> --method <committed-method> --outcome <outcome> --does-not-establish <limit> --as verifier:<name> --json
vela review inbox . --json
vela replay . --json
```

Hand the rooted Decision Inbox entry to the authorized operator; do not decide it yourself.
