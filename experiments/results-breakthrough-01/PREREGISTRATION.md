# RESULTS-BREAKTHROUGH-01 preregistration

Status: **frozen before candidate inference; execution blocked pending
independent review of the disposable Vela lifecycle preflight**.

This is a bounded precursor experiment. Its product is comparative evidence
about production of source-native mathematical Results, not workflow
architecture. It creates no Math Submission, Verification, Decision, Event,
or Standing and does not edit Formal Conjectures, lean-proofs, Vela, Palomar,
Web, Core, or Workbench.

## Hypothesis and unit of analysis

For the same mathematical target and information, test whether the native
repository workflow, a simplest-sufficient JSON/SQLite graph, or the signed
Vela lifecycle produces more independently qualified source-native Results
per unit resource without more false promotion.

The unit is one `target x arm` candidate session. All 30 assigned units remain
in the denominator once their model call starts. A target-level independent
evaluation session grades the three anonymized outputs separately. Results
are paired by target; no arm receives a different target slate.

## Frozen execution identity

- Docker Desktop context: exactly `desktop-linux`; any other context stops the
  run.
- Image:
  `vela-results-breakthrough-01@sha256:526fdb202378ca02eb5946c75bc4d319751336c0ad88162c671fbe89950d1750`.
- Base image:
  `vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01`.
- Candidate runner: Codex CLI `0.145.0`, binary SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`.
- Model: `gpt-5.6-sol`, reasoning effort `high`, service tier `default`, via
  the already logged-in ChatGPT OAuth path only.
- Vela: `0.977.3` built from `vela-science/vela@88fcc0105eba35ee22ed1816d3aabba3322bebc1`,
  container binary SHA-256
  `59cc91e9d277d733a8f5b2892653cf5b540778ce26ac794521c63bba0036103b`.
- Source repositories, trees, dependency locks, licences, verified Git
  bundles, and tool hashes: `SOURCE-LOCK.json`.
- Candidate answer contract: the unmodified Batch 3 schema at
  `082a118e:results/2026-08-20-docker-batch-3/result.schema.json`, SHA-256
  `62f7bbc908dbb9020ea39430307c0c685ee30fce2dee496e54b739e4b5a702b6`.

The four complete clones are mounted read-only at their exact commits in every
arm. `git rev-parse --is-shallow-repository` is false and `git fsck --full`
passes for each. Candidate workspaces are fresh, arm-local, writable scratch
clones/checkouts made from the same retained bundles. No Docker socket is
mounted.

## Common candidate objective

Each arm receives this identical objective before its arm-specific recording
instructions:

> Using only the exact mounted sources, attempt the strongest truthful
> source-native Result for the assigned exact target: checked proof,
> executable certificate, counterexample, precise statement/status correction,
> dependency/trust finding, or typed non-result. Search all mounted current
> Math, Formal Conjectures, and lean-proofs bytes for duplicates and related
> files before claiming novelty. Distinguish checked Lean from a proof sketch
> and computation from theorem proof. Preserve exact source identities,
> commands, stdout, assumptions, dependencies, nonclaims, elapsed time, and
> artifact digests. Do not use outreach, live literature search, external
> posts, or source mutations. Return only the common schema-valid JSON.

The exact target-specific paragraph is frozen in `TARGETS.md`. Arm wrapper
text may describe only how to retain the same result; it may not add
mathematical facts, hints, examples, source paths, or evaluation criteria.

## Equal budgets and tools

- One non-interactive `codex exec` per assigned candidate unit.
- Zero retries and zero follow-up model turns.
- Candidate wall cap: 12 minutes from process start; timeout is retained as
  the assigned result.
- Evaluator wall cap: 12 minutes, one session per target, grading all three
  anonymized outputs independently against one rubric.
- Same image, model, reasoning effort, OAuth path, prompt objective, source
  mounts, writable byte allowance, shell tools, Lean tooling, Python stdlib,
  Git, network policy, and answer schema across arms.
- Network exists only because ChatGPT OAuth inference requires it. Prompts
  forbid source discovery or downloads; all mathematical inputs must come from
  the retained mounts. Network access outside the provider path is a protocol
  violation and stops the stage.
- Maximum candidate sessions: 30.
- Maximum evaluator sessions: 10.
- Maximum OAuth sessions: **40**. Tool calls inside a session do not increase
  this count. Any additional model start is prohibited.

Codex does not expose a reliable hard token cap in this path. Equal budget is
therefore enforced by identical single-session/run configuration and wall cap,
not by inventing token totals that cannot be observed.

## Arms

### N — Native repository workflow

The candidate works in an ordinary scratch Git repository containing the
common target packet and read-only source mounts. It retains `result.json`,
artifacts, commands/stdout, and a receipt, stages only those files, and makes
one ordinary local Git commit. Git hashes and file SHA-256 values are the
provenance/readback mechanism.

### J — Conventional JSON/SQLite graph

The candidate has the same files and tools. The same result/artifact/receipt
bytes are retained in ordinary files and represented, without inference or
enrichment, in both:

- `graph.json`: objects plus directed relations;
- `graph.sqlite`: `objects(id, kind, sha256, payload_json)`,
  `edges(src, dst, relation)`, and
  `events(seq, kind, actor, object_id, receipt_json)`.

Python's standard-library `sqlite3` is sufficient. IDs are ordinary assigned
session IDs; hashes are file SHA-256 values. The graph may record only facts
already present in the common packet or candidate output. There is no ORM,
adapter framework, new scientific schema, signing layer, standards mapping,
or hidden retrieval. JSON/SQLite is the simplest-sufficient falsifier.

### V — Vela lifecycle

The candidate has the same files and tools. Each V unit uses a newly created,
campaign-local repository and dedicated disposable Ed25519 authority identity;
it never copies, exports, or invokes Math's canonical authority identity.

Required actual CLI sequence, with all JSON stdout retained, is:

1. `vela init` the disposable repository and retain its signed origin.
2. Commit the candidate artifact and exact method bytes.
3. `vela submit` the candidate result as a pending Proposal, with exact
   artifact, caveats, source-run identity, and required verification property.
4. After the actor-separated target evaluation, record its exact observation
   with `vela verification record`; a Verification is not acceptance.
5. Read `vela review inbox --json`, bind the exact entry root, and have the
   attributed experiment-owner performer `accept` only an independently
   qualified output or `reject` every other output.
6. Retain `vela review show`, `vela status`, and `vela replay` JSON readback.

The Vela repository, trust anchor, authority key, and records live only in the
V session directory outside canonical Math. The private key is mode 0600,
never logged or committed, and is deleted after terminal readback; signed
records and the public key remain replayable. Actor separation is recorded
truthfully but is not called protocol independence.

Unsigned Vela-like JSON, hand-authored records, use of Math authority, or a
skipped Decision/readback is an arm failure, not an acceptable approximation.

## Assignment order

The smoke order is frozen as:

1. T01-N
2. T02-J
3. T01-V
4. T02-N
5. T01-J
6. T02-V

If smoke passes, the remaining candidate order is:

1. T03-V, T04-N, T05-J, T06-V, T07-N, T08-J, T09-V, T10-N
2. T03-N, T04-J, T05-V, T06-N, T07-J, T08-V, T09-N, T10-J
3. T03-J, T04-V, T05-N, T06-J, T07-V, T08-N, T09-J, T10-V

This is a fixed cyclic block order, not an outcome-responsive schedule. Target
evaluators receive the three candidate packets under a pre-frozen random label
permutation with arm receipts withheld until scientific grading is committed.

## Staged gates

Before the first candidate model call, independent review must confirm:

1. this preregistration commit and all source/image/schema hashes;
2. source clones are complete, exact, read-only, and information-equivalent;
3. the OAuth file is mounted read-only and `codex login status` reports only
   `Logged in using ChatGPT`;
4. native, graph, and Vela work/state paths cannot overlap;
5. one no-model fixture roundtrip for each arm produces complete receipts;
6. the Vela fixture completes the actual signed lifecycle and replay without
   canonical authority effect;
7. the redaction scan reports no credential bytes.

Run only T01/T02 across all three arms. Continue to T03-T10 only if every arm
has the same source-root list, target bytes, tool permissions, answer schema,
and complete receipt, and all source/canonical repositories have identical
pre/post commit, tree, manifest hash, and clean status. A scientific
non-result is not a smoke failure. Missing inputs, isolation drift, secret
exposure, unsigned Vela state, or incomplete receipts are failures.

## Current preflight blocker

The image, Vela version/hash, OpenSSH tools, Python SQLite, and read-only OAuth
probe passed. Two no-model, materially identical disposable Vela initialization
attempts then exited 1. In both:

- an isolated in-container `ssh-agent` was started;
- a fresh Ed25519 key was generated and `ssh-add` returned success;
- Git identity was configured before the corrected attempt;
- `vela init --json` retained deterministic scaffold files and `vela.toml`;
- the retained repo had no commit and no `.vela/origin.json` or
  `.vela/repository.json`;
- no Submission, Verification, Decision, model call, or canonical write
  occurred.

Observed blocker: **container Vela `0.977.3` exits 1 after retaining the Profile
but before signed authority initialization, even with one disposable Ed25519
identity loaded.** The first attempt had no Git identity; configuring it did
not change the failure. Because this is the second materially identical setup
failure, setup stops here. The smoke cannot begin until independent review
identifies and verifies one smallest correction. The Vela arm will not be
weakened or replaced.

Supervisor diagnosis, received after this stop and before inference: the exact
image has neither `/etc/machine-id` nor `/var/lib/dbus/machine-id`. After the
Profile write, Vela's Linux `local_device_identifier()` requires
`/etc/machine-id`, so authority initialization exits before either signed
repository file exists. The container otherwise ran as root with a valid home,
repository ownership, loaded SSH identity, and corrected Git identity. The
preflight shell also captured `vela init --json` in command substitution and
printed only `INIT_FAILED rc=1`, so it failed to retain the diagnostic JSON.
This narrows the blocker to an image-compatibility and receipt defect; it does
not establish that the proposed correction works.

The smallest proposed correction, still prohibited until the independent
preregistration review approves it, is to add a documented deterministic
experiment-specific valid machine ID (exactly 32 lowercase hexadecimal
characters plus newline) to `/etc/machine-id` in the Dockerfile, never mount
the host machine ID, rebuild and pin the resulting digest, and write Vela JSON
stdout/stderr to retained files whose hashes are emitted on both success and
failure. Exactly one corrected no-model disposable signed-lifecycle fixture is
then allowed. A pass returns to the frozen review gate; a distinct failure is
preserved and handled by these stopping rules. No candidate inference may
start merely from this diagnosis.

The two preflight attempts are not scoring denominator entries because no
candidate assignment or model call started. Their existence and failure remain
part of the infrastructure receipt.

## Metrics and adjudication

An evaluator result is `qualified` only when the exact source-native assertion
is supported by retained evidence and its claimed check modality. A sketch is
not a checked proof; a reproduced computation is not a theorem; build success
is not scientific acceptance.

Primary metrics, reported per arm with paired target differences and raw
counts, are:

1. **Qualified Results per dollar:** qualified candidate units divided by
   provider-reported incremental USD cost. ChatGPT OAuth currently exposes no
   per-session USD charge; if receipts still omit it, this metric is reported
   `not estimable`, never zero-cost or infinite. Session count remains visible.
2. **Qualified Results per hour:** qualified units divided by the sum of
   candidate wall-clock hours from assigned process start to terminal receipt.
3. **False-promotion rate:** candidate `proposed_result` units that the blinded
   evaluator does not qualify, divided by all candidate `proposed_result`
   units. This is based on candidate assertion, not the later storage Decision.
4. **Valid non-results:** `typed_non_result` units whose scope and evidence the
   evaluator confirms.
5. **Corrections:** qualified exact statement, status, metadata, identity, or
   dependency corrections, with source bug/translation bug/metadata issue/no
   bug distinguished.
6. **Duplicate work:** units whose proposed result was already established by
   exact reachable current sources at launch.
7. **Recovery:** failed/aborted units that still retain enough exact receipt,
   source, tool, and event information to reconstruct the failure without a
   retry. Report both count and completeness rate.
8. **Provenance completeness:** fraction of required fields present and valid:
   source commit/tree/path/hash, exact question, result/non-result, evidence,
   check outcome, assumptions/dependencies, elapsed time, observable tool
   calls, artifact digests, arm readback, and nonclaims.

Secondary metrics are candidate/evaluator elapsed time, tool-call count,
artifact bytes, protocol operations, and human/owner handling time. No metric
is silently replaced when unavailable.

## Denominators, failures, and stopping

- Once a candidate model process starts, its unit remains assigned and in the
  denominator even on timeout, invalid JSON, tool failure, provider loss,
  credential quarantine, or empty output.
- There are no silent retries, substitutions, repair turns, or post-hoc target
  exclusions.
- Evaluator failure is retained as inconclusive; it does not upgrade or erase
  the candidate.
- A source change, arm-information mismatch, write outside session state,
  credential exposure, or invalid Vela signature/replay stops the current
  stage.
- Two materially identical setup failures stop setup. That stop has already
  fired for disposable `vela init` and is the current execution state.
- The run stops at 30 candidate and 10 evaluator sessions even if targets are
  unresolved.

## Credentials and receipts

The ChatGPT OAuth file is mounted read-only at the exact Codex login path. It is
never copied into workspaces, images, prompts, stdout, artifacts, Git, JSON,
SQLite, or Vela. Logs are scanned before retention for access/refresh tokens,
authorization headers, private keys, and known credential shapes. A match
quarantines the raw ephemeral log, retains only a non-secret hash/failure
receipt, counts the unit as an infrastructure failure if assigned, and stops
the stage. No credential string is printed while diagnosing.

Every terminal unit retains invocation, image/source roots, start/end/elapsed,
exit/timeout, stdout/stderr after secret scan, candidate JSON or typed absence,
tool calls when observable, artifact hashes, and arm-specific readback. Raw
provider event streams are retained only when the secret scan passes.

## Provider-loss reconstruction

Verified Git bundles in `SOURCE-LOCK.json` reconstruct all exact source trees
without GitHub. The Docker image digest and Dockerfile/source locks reconstruct
the execution environment while its base/builder images remain available.
Receipts bind the model/config/prompt and any output already returned. They do
not claim that an unavailable proprietary model can be regenerated from local
bytes. Provider loss before a terminal response is an assigned infrastructure
failure with no retry.

## Rights and authority

Formal Conjectures inputs retain Apache-2.0 identity; lean-proofs retains MIT;
Vela retains Apache-2.0. Candidate-created code/evidence must declare a
compatible licence before conversion. Source excerpts remain bounded to what
is needed for evaluation.

Experiment-owner acceptance inside a disposable Vela repository is only the
predeclared arm readback. It is not Formal Conjectures adoption, mathematical
truth, Vela protocol independence, Math authority, or canonical Standing.

## Post-pilot standards gate

This pilot adds no RO-Crate, Workflow Run RO-Crate, SWHID, or nanopublication
adapter and no fourth arm. Only if Vela materially beats the JSON/SQLite arm on
qualified Results per hour (and per dollar when estimable) **without a higher
false-promotion rate** may a successor preregistration compare Vela with a
standards-composed baseline: RO-Crate/Workflow Run RO-Crate for
objects/execution, nanopublications for assertions, and optional SWHID for
software identity. If JSON/SQLite matches Vela, stop the standards-integration
program. This is a post-pilot decision gate, not permission for current code or
schema work.
