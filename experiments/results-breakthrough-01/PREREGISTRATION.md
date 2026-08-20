# RESULTS-BREAKTHROUGH-01 corrected preregistration

Status: **frozen before candidate inference; blocked pending exact independent
re-review**.

This is the single corrected successor to producer commit
`0bbf3b8578417c928fe2b62ee9912f2c7918e9d5` / tree
`5f71bffbfad364d628abf8ba70003e91a2dcd643`, which independent review blocked
at evaluator commit `43c51f9f893a6919428a290421a8344a11c5f5f4` / tree
`4069ae9ed804fec3178c548ecc4475179f3568ba`. No candidate generation, answer
drafting, tool-using candidate model session, corrected image build, Vela
lifecycle fixture, source mutation, or authority mutation has begun.

The pilot produces comparative evaluation evidence only. It creates no Math
Submission, Verification, Decision, Event, or Standing and changes no Formal
Conjectures, lean-proofs, Vela, Palomar, Web, Core, Workbench, upstream source,
or canonical authority.

## Normative evaluator commitment

`EVALUATOR-LOCK.json` binds the Stage 1 freeze, receipt, independent review,
rubric, analysis plan, information-equivalence procedure, held-out procedure,
producer requirements, commitment, and the BLOCKED review of the predecessor.
Those frozen bytes are normative. Nothing in this producer packet replaces or
loosens them.

Every one of the 30 target-arm cells receives exactly one primary verdict:

1. `qualified_result`;
2. `valid_non_result`;
3. `needs_correction`;
4. `duplicate`; or
5. `invalid`.

Primary `usable = 1` only for `qualified_result` or `valid_non_result`; all
others have `usable = 0`. `recovered` means an initial `needs_correction` cell
becomes one of those two usable verdicts after exactly one symmetric bounded
correction round using only the original fact pack and the adjudicator's
locked minimal defect notice. Receipt reconstruction is reported separately
as provenance completeness and is not recovery.

The fixed intention-to-treat denominator is **30 cells from assignment**, not
from model start. A failed-to-start assigned cell remains in the denominator
as `invalid`, `infrastructure_failure:true`, `usable:0`; a pre-inference
failure is not a model attempt. The two historical global Vela setup failures
predate cell assignment and remain infrastructure evidence outside the 30.
There are no silent retries, target substitutions, cell deletions, or
treatment-specific rescues.

## Trial, arms, and exact inputs

The paired block is one target. The ten targets and smoke IDs T01/T02 are
frozen in `TARGETS.md`; candidate-facing exact public cards are in `cards/`.
The cards are not the evaluator's held-out check cards. Exact source commits,
trees, bundles, toolchains, licenses, answer schema, runtime, and evaluator
bundle are in `SOURCE-LOCK.json`.

Each target has one canonical `fact-packs/Txx.json`. Its
`scientific_fact_root` is SHA-256 over supplied-order canonical JSON lines containing
only `(fact_id,payload_sha256,byte_length,role)`. The same complete source
mounts, fact pack, producer card, common objective, model, parameters, tools,
time limit, output budget, retry rule, and answer schema go to all three arms.
Only these organization bytes differ:

- **N:** ordinary session-local files and Git commit;
- **G:** the same files plus the simplest deterministic JSON/SQLite graph;
- **V:** the same files through the current signed Vela lifecycle in a wholly
  disposable campaign-local repository.

Exact organization wrappers/adapters live in `prompts/arm-*.txt` and `arms/`.
They add no mathematical fact. `G` has only objects, edges, and events; it has
no inference, signing, authority, standards mapping, ORM, or hidden retrieval.
Vela uses actual public `0.977.3` CLI semantics and never Math credentials or
canonical state. Its Submission and Verification are not acceptance; its
experiment-local Decision/readback is not mathematical truth, independence,
source-owner approval, or canonical Standing.

The fixed candidate execution order is `assignments.json`. It balances arm
order without concealing treatment from the producer. The evaluator-owned
X/Y/Z permutation, target-specific held-out check cards, duplicate-control
index, and aggregate commitment remain absent from producer bytes by design.

## Common objective and execution controls

The exact common candidate prompt is `prompts/common-objective.txt`; the runner
appends the byte-exact producer card and one organization-only arm wrapper.
The normalized scientific prompt hash excludes only that arm wrapper and is
identical within each target. `runtime/parameters.json` and
`runtime/tool-allowlist.json` bind:

- Docker Desktop context `desktop-linux` only;
- model `gpt-5.6-sol`, reasoning `high`, service tier `default`, using existing
  ChatGPT OAuth only;
- one initial non-interactive `codex exec` per assigned cell, 12-minute wall
  cap, zero initial-generation retries, identical 8,192-UTF-8-byte `result.json`
  scientific output allowance, identical tools/mounts/network policy, and no
  cross-arm sharing;
- maximum 30 unique candidate sessions and 10 unique target-evaluator sessions,
  hence **40 experimental OAuth sessions**;
- one `codex exec resume` of the same candidate session ID only when the locked
  first-pass verdict is `needs_correction`; this is the frozen recovery round,
  not a replacement cell or silent retry. It receives only the original fact
  pack and minimal defect notice, uses the same 12-minute cap, and its extra
  provider call/time/tokens/cost are reported. No second resume is permitted.

The two preregistration equivalence-reader tasks are review evidence, not
candidate or target-evaluator sessions, and do not access candidate answers.
All model/provider time, calls, tokens, and provider-reported cost that the
experiment can observe are retained. If OAuth receipts expose no incremental
USD, cost-derived rates are `not estimable`, never zero or infinite.

`scripts/run-cell.sh` fails closed unless an append-only start receipt binds a
PASS independent launch review, this corrected preregistration commit, a
nonblank Stage 2 held-out aggregate hash, and the newly built runtime digest.
Immediately before each cell it verifies all four complete source checkouts'
exact commits, trees, non-shallow status, cleanliness, and the launch mount
receipt. It materializes every producer-local fact at a digest-checked mounted
path, mounts source and OAuth bytes read-only, gives the candidate only its
session workspace, exposes no Docker socket, retains stdout/stderr/exit, and
runs the credential scan. All three arm wrappers are byte-identical, hence have
identical tokenizer input under the common model, and the runner rejects any
`result.json` larger than the common allowance. A detected secret quarantines raw output, retains a
non-secret hash/failure receipt, counts an assigned cell as ITT failure, and
stops the stage.

## Image reconstruction and current block

The current verified image remains
`vela-results-breakthrough-01@sha256:526fdb202378ca02eb5946c75bc4d319751336c0ad88162c671fbe89950d1750`.
It is not launchable because it lacks `/etc/machine-id`. The predecessor also
discarded Vela failure JSON through shell command substitution.

The proposed post-review Dockerfile now:

- digest-pins both `FROM` images;
- copies only the complete exact Vela Git tree
  `88fcc0105eba35ee22ed1816d3aabba3322bebc1` reconstructed and verified against
  all 412 entries in `build/vela-context.tsv`;
- writes deterministic experiment-only machine ID
  `af94b40fa642620275e6d617be97a542` plus newline; and
- keeps Vela stdout, stderr, exit code, elapsed time, and hashes on every path
  through `scripts/run-json-command.sh`.

`build/BUILD-LOCK.json` and `scripts/build-image.sh` bind the exact recipe and
fail closed without a commit-bound independent PASS authorizing one build and
one Vela no-model lifecycle fixture. The Dockerfile is frozen proposed input,
not evidence that an image was built. No corrected image digest exists yet.

The N/G adapter-only fixtures in `fixtures/native/` and `fixtures/graph/` ran
network-disabled in the current pinned image with zero model sessions. They
establish byte retention and deterministic graph reconstruction only. They are
not scientific Results and do not substitute for the still-prohibited Vela
lifecycle fixture or final three-arm launch equivalence receipt.

## Held-out Stage 2 and launch order

After this exact commit passes re-review, and before any inference:

1. the independent evaluator creates ten target-specific check cards,
   duplicate-control index, and concealed balanced X/Y/Z mapping without
   reading future answers;
2. it commits their per-file hashes and aggregate Stage 2 hash while retaining
   the held-out bytes outside the producer workspace;
3. the approved Dockerfile is built exactly once and the new digest, complete
   Vela signed lifecycle fixture, N/G/V equivalence receipts, source/canonical
   pre/post identities, signature/replay result, and secret scan return for
   commit-bound review; and
4. only a PASS produces append-only `launch/start-receipt.json` with
   `candidate_generation_started:false` immediately before T01-N.

No diagnosis, Dockerfile edit, adapter fixture, reader report, or Stage 2 hash
alone authorizes inference.

## Smoke gate

Run only the six T01/T02 cells, lock blinded first-pass verdicts, conduct the
single symmetric recovery round for eligible cells, and continue to T03–T10
only if every frozen Stage 1 condition holds:

1. information equivalence passes for all six cells;
2. all six bundles are independently checkable, except a single shared
   pre-inference outage repaired under the symmetric policy;
3. zero false promotions and zero authority-confusion events;
4. zero unplanned source mutation and zero treatment-specific fact leakage;
5. blind packaging and verdict locking replay deterministically;
6. at least four of six final cells are usable, with at least one usable cell
   on each target; and
7. no arm requires a schema or protocol change.

Otherwise stop. Scientific difficulty does not relax the gate, and fixing
pilot infrastructure requires a new preregistration rather than patching this
run.

## Frozen analysis and workload verdict

For each arm, report all five verdicts, usable components, every frozen defect
flag, source-native realization, recovery, exact-check pass, false promotion,
authority confusion, time/tool/model/token/cost receipts, artifact/adapter
bytes, reproducibility, disagreement, and blindness breaches. For `V-G`,
`V-N`, and `G-N`, report all ten target-level differences for the frozen
outcomes plus paired mean, paired median where defined, win/tie/loss, and an
exact two-sided paired sign/randomization test. No significance or general
performance claim is permitted from ten targets.

Apply the Stage 1 **NO VALUE** simple-graph falsifier exactly. G materially
matches V when usable and source-native realization differ by at most one
target, V has no unique recovered usable cell or disposition-changing
detection, no categorical reproducibility advantage, and no preregistered 20%
Vela overhead improvement without guardrail regression. If it holds, stop the
Vela and standards-integration program for this workload.

A fresh 40–60-target trial is eligible only under every frozen scale condition:
zero Vela false promotion/unresolved authority confusion; at least +2/10 usable
versus G, or +1/10 with one independently verified unique recovery/detection;
source-native realization no worse than -1/10; no extra arm-specific
infrastructure failures; no material equivalence/blinding breach; gains not
solely duplicates/restatements/metadata; median wall time and artifact/adapter
bytes each at most 2× G; and all paired outcomes/receipts/costs/exclusions
reported before new target selection. Guardrail failure yields
`BOUNDED_FOLLOW_UP`; indecision yields `STUDY`; neither authorizes integration.

This pilot has no RO-Crate, Workflow Run RO-Crate, SWHID, nanopublication
adapter, or fourth arm. Only a material Vela win under that exact scale gate,
without higher false promotion, makes a separate standards-composed successor
eligible. Eligibility is not adoption.

## Rights, authority, and process evidence

Formal Conjectures and Vela inputs retain Apache-2.0 identity; lean-proofs
retains MIT. Candidate artifacts must declare compatible inspection,
execution, and redistribution rights before qualification. External linked
proof bytes not present in the frozen mounts are unavailable dependencies, not
facts candidates may infer or fetch.

`PROCESS-LOG.md` is append-only observational evidence about failures and
simplification opportunities. It creates no gate or authorization. At the end
of the experiment it receives a short measured keep/change/delete
retrospective; until then it must not delay scientific execution.
