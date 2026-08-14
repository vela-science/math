# Vela Mathematics Program — agent charter

Canonical state is Git history plus the current `.vela/repository.json` manifest. Producers may inspect exact Target briefings, submit signed evidence directly, and record scoped Verification. Only an authorized, attributed Decision changes scientific Standing. The performer may be human or agent; actor class, identity, session provenance, and the distinct Repository authority principal must remain explicit.

## Native integration freeze

This Repository is one optional local authority, not Vela's mathematics
integration hub. New generic integration contracts, reusable Profiles,
source-specific adapters or schemas, workbench machinery, review dashboards,
agent activity, and cross-domain experiments must go to their native source,
Vela Core after the two-consumer extraction gate, a Workspace, or a read
projection as classified in [`OWNERSHIP.md`](OWNERSHIP.md).

Authority maintenance, replay safety, correction duties, and bounded work that
is specific to the Vela Mathematics Program may continue here. The ownership
classification controls future placement only: it does not authorize moving,
deleting, or rewriting any retained byte, changing any historical root, or
changing scientific Standing. The current source-owned and historical packets
remain in place unless a separately authorized migration proves their exact
references, replay, roots, and public consumers remain valid.

An agent may invoke `vela review accept` or `vela review reject` only when the Repository has explicitly authorized the exact authority principal and the invocation records the agent's own `agent:` identity plus its source-owned session or checkpoint. Producer or verifier status never grants that capability. Agents must not impersonate a human, reuse another performer's identity, access undelegated credentials, hand-edit canonical records, or describe Verification as acceptance. A Verification method manifest must be tracked, clean, and retained in the current Git commit before `vela verification record`.

```bash
vela status . --json
vela claims . --json
vela submit --repo . --claim <bounded-claim> --type computational --replayability exact --artifact <path>:<kind> --caveat <limit> --as agent:<name> --json
vela verification record . <vpr_id> --profile <profile> --method <committed-method> --outcome <outcome> --does-not-establish <limit> --as verifier:<name> --json
vela review inbox . --json
vela replay . --json
```

Hand the rooted Decision Inbox entry to an authorized operator. If you are that explicitly authorized operator, decide the exact entry under your own attributed identity and session; otherwise do not decide it yourself.
