# Vela Mathematics Program — agent charter

Canonical state is Git history plus the current `.vela/repository.json` manifest. Producers may submit signed evidence directly and record scoped Verification. Only an authorized, attributed Decision changes scientific standing; human and agent performers use the same exact-root and replay checks.

Agents must not copy or export repository-authority credentials, hand-edit canonical records, or describe Verification as acceptance. An agent selected to decide uses `vela review accept|reject --as agent:<name>` and may bind a source-owned `--session-ref`; Repository authority signs the transaction. A Verification method manifest must be tracked, clean, and retained in the current Git commit before `vela verification record`.

```bash
vela status . --json
vela submit --repo . --claim <bounded-claim> --type computational --replayability exact --artifact <path>:<kind> --caveat <limit> --as agent:<name> --json
vela verification record . <vpr_id> --profile <profile> --method <committed-method> --outcome <outcome> --does-not-establish <limit> --as verifier:<name> --json
vela review inbox . --json
vela review accept . <vpr_id> --if-entry-root sha256:... --reason <reason> --as agent:<name> --session-ref <ref> --json
vela replay . --json
```
