# Disposable Vela lifecycle fixture evidence

Outcome: **FAILED, retained, zero retries**.

Exactly one network-disabled no-model fixture container was started against
the corrected image digest
`sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e`.
It exited `1` in under one second. Outer stdout/stderr SHA-256 are
`7087ba6fb79b337661eb8181d5a4e7573616ec33b91754bcd7c633dc0bdf438b` /
`d926b83b50e87b8c4306aa9f5117cd5bf148b6d0dd2b943fc3b0f45623d99bb6`.

The frozen Review Method passed its schema/binding validator before the first
Vela command. The synthetic no-model `invalid` verdict independently passed
the frozen evaluator verdict schema. Vela `init` then exited `1` and retained
this exact JSON diagnostic in `session/organization-only/pre-verdict/receipts/init.stdout`:

```json
{
  "schema": "vela.error.v1",
  "ok": false,
  "command": "init",
  "error": {
    "kind": "domain",
    "code": null,
    "message": "refusing to initialize non-empty directory .",
    "hint": null
  }
}
```

The direct cause is the frozen adapter ordering: `prepare` copies
`result.json` and `artifacts/` into `session/repo` before invoking `vela init
.`, while Vela correctly requires an empty initialization directory. This is
a different harness defect from the repaired missing-machine-ID failure. The
machine-ID correction and failure-path JSON retention both worked as reviewed.

Because initialization did not complete, no Submission, Verification,
Decision, replay, status/readback, bundle, or provider-loss reconstruction
exists. Claiming those gates passed would be false. The provider-loss step is
`not_run` because there is no initialized repository or signed history to
reconstruct.

Denominator/accounting:

- corrected image rebuilds: 1 of 1;
- no-model Vela lifecycle fixture attempts: 1 of 1;
- retries: 0;
- Vela CLI calls reached: 1 (`init`);
- model, evaluator-model, provider, OAuth, and credit-relevant sessions: 0;
- candidate inference: false;
- authority effect: none outside the disposable incomplete directory.

The disposable keypair generated before `init` was fingerprinted and removed.
The post-cleanup credential scan examined 21 files, found zero credential
patterns, and passed. Pre/post source and canonical-state receipts are
byte-identical (stdout SHA-256
`fa9c76c04cd6c3e823b85d1daf7220a16da929246fd76c99de7142d1987121c1`):
all four complete source clones remain clean at their frozen commits/trees,
and canonical `.vela`/`records`/`evidence`/`methods` state has an empty diff.

Smallest next handoff: independent review should confirm this retained
denominator and, in a later separately authorized delta, move repository
initialization before copying retained packet bytes. This commit does not make
that correction and does not authorize another fixture run.
