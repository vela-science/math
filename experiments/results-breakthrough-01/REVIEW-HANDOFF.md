# Independent preregistration review handoff

Review only the head commit of
`codex/results-breakthrough-01-prereg-2026-08-20`. Candidate inference is
prohibited until the reviewer returns a commit-bound pass. This packet creates
no scientific authority effect.

## Review inputs

- `PREREGISTRATION.md`: hypothesis, common objective, arms, fixed schedule,
  metrics, denominators, stopping rules, isolation, rights, and standards gate.
- `TARGETS.md`: the frozen ten-target slate and prior-case exclusions.
- `SOURCE-LOCK.json`: exact commits, trees, complete-clone checks, bundle
  digests, image/tool identities, model configuration, and answer contract.
- `Dockerfile`: the complete minimal derivative image recipe. Its SHA-256 is
  `299151c8e683fb3b1a5eae0e384273c34fac2b12b659fc1cb7eba9bf9b478b67`.
- Existing answer schema, unmodified:
  `082a118ea6ce7c9ca6a62f72aa425373228f7efe:results/2026-08-20-docker-batch-3/result.schema.json`,
  SHA-256
  `62f7bbc908dbb9020ea39430307c0c685ee30fce2dee496e54b739e4b5a702b6`.

## Required review findings

Return a pass/fail finding bound to the reviewed Git commit and tree for each:

1. all ten targets are new against the frozen Math/lean-proofs state and the
   three earlier Result Factory batches;
2. each arm receives information-equivalent source bytes, tools, objective,
   answer schema, time cap, retry count, and model configuration;
3. source mounts and Math canonical authority are read-only and arm state is
   mutually isolated;
4. Native and JSON/SQLite no-model fixture receipts are complete;
5. the exact signed Vela lifecycle can complete in disposable state with no
   Math authority effect;
6. the OAuth mount remains read-only and no credential bytes enter retained
   evidence;
7. session ceilings are 30 candidate, 10 evaluator, 40 total, with the first
   stage limited to six candidate sessions over T01/T02 and two target-level
   evaluator sessions;
8. no current-pilot standards adapter, fourth arm, new answer schema, source
   change, or canonical scientific record exists.

## Exact blocker to resolve or confirm

Two no-model disposable preflight attempts used the frozen Docker image,
isolated in-container `ssh-agent`, a fresh loaded Ed25519 key, and (on the
corrected second attempt) configured Git identity. Both `vela init --json`
processes exited 1 after retaining the repository Profile/scaffold and before
creating `.vela/origin.json` or `.vela/repository.json`. No model session or
signed lifecycle record started.

The reviewer may identify and verify **one smallest correction** using this
same image and disposable state, then re-run the complete no-model lifecycle
fixture once. The reviewer must not construct a new harness, weaken the Vela
arm to unsigned data, reuse Math authority, or infer a pass from partial
scaffold retention. If the blocker cannot be resolved within that bounded
check, return a commit-bound blocked verdict and do not authorize inference.

The supervisor's current diagnosis is specific: the frozen image has no
`/etc/machine-id` or `/var/lib/dbus/machine-id`, while Vela's post-Profile Linux
authority path requires `local_device_identifier()`. The proposed bounded fix
is a documented deterministic experiment-only value of 32 lowercase hex
characters plus newline at `/etc/machine-id`; the host value must never be
mounted. Review must also require the fixture to write Vela JSON output to a
retained file and display/hash it on either exit path, replacing the prior
command substitution that swallowed the failure diagnostic. Approval of this
proposal authorizes one new image build and one corrected no-model fixture,
not candidate inference. Their new digest and receipt must return for review.

## Pass output

A valid pass names the reviewed commit/tree, exact Docker image digest, all
source commits, schema digest, fixture commands and redacted stdout hashes,
pre/post canonical Math commit/tree/manifest identity, disposable Vela origin
and repository identities, signature/replay outcome, and secret-scan outcome.
It authorizes only the six-session candidate smoke plus two evaluator sessions.
Continuation to T03-T10 still requires the preregistered post-smoke gate.
