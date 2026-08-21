# Maintained Math Result Runner review

Verdict: **BLOCKED**

Reviewed state:

- repository `/Users/williamblair/personal/math`
- branch `codex/result-runner-v1`
- commit `1e7ca3ec4821651c0697c8952fce7d29d616eb52`
- tree `fc4d629215a66e65027fdff0b8ed602e0eefbe2f`
- base `origin/main` at
  `5de716c896065c03c0a470d015ba2a328a527f73`
- remote branch equal to the reviewed commit

The branch establishes one maintained Python runner and exposes it from the
root README. It removes the copied-experiment pattern and discloses read-only
source operation. The implementation still has six merge-blocking contract
gaps. They can recreate the prior non-repository failure, permit unbounded
execution, accept outputs that the declared schema rejects, emit
nondeterministic Native evidence, record the wrong Vela Verification outcome,
and present an unbound qualification PASS.

## Reproduced checks

- Exact branch commit/tree/base and signed remote equality: PASS.
- Exact delta: one root README edit plus ten files under
  `tools/result_runner`, 992 added lines: PASS.
- Focused tests without Vela: 5 pass, 1 skip.
- Focused tests with Vela 0.977.3 at SHA-256
  `3a1173918bdcb887155bab681411bf5e9ff64d925fe1b50369ac37ab020b94ad`:
  6 pass.
- Ruff 0.5.4 check and format check: PASS.
- Python 3.11.2 compileall: PASS.
- `git diff --check`: PASS.
- Credential-pattern scan of the ten maintained-runner files: zero findings.
- Docker context `desktop-linux`; accepted image resolves to exact ID
  `sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e`
  on `linux/arm64`.
- Independent disposable Vela replay: Submission, passing Verification,
  rooted reject Decision, rejected status, strict replay, accepted claims zero,
  and private/public key deletion all reproduced. This proves the current code
  path; it also exposes the required-outcome mismatch in finding RR-05.
- Two identical recorder runs produced byte-identical graph JSON and SQLite
  hashes and identical Native trees. Native commit hashes differed after two
  seconds because Git commit dates remain uncontrolled.

## Findings

### RR-01 [P1] The host Git check can mount a non-repository at `/repo`

`runner.py:294-306` resolves the supplied path, then accepts any directory for
which Git reports `--is-inside-work-tree=true`. A repository subdirectory
passes that check. Docker mounts only that subdirectory at `/repo`, so the
container receives no `.git` and Codex fails its repository preflight. An
independent fixture reproduced the condition: `git_snapshot(repo/sub)` passed
while `repo/sub/.git` was absent. A linked worktree has the same risk because
its `.git` file can point outside the mounted directory.

The code also resolves prompt, schema, OAuth, Vela, and repository paths before
checking `is_symlink()`. A direct symlink becomes its target and passes the
advertised non-symlink check. Relative paths become absolute and pass despite
the CLI contract. Docker `--mount` values do not reject commas, and the image
argument does not require a `sha256:<64-hex>` digest.

Smallest correction:

1. Reject non-absolute or symlink CLI paths before calling `resolve()`.
2. Require the physical `git rev-parse --show-toplevel` path to equal `--repo`.
   Require an in-tree `.git` directory, or add and test an explicit linked-
   worktree mount design.
3. Reject Docker-mount delimiter characters. Require an exact image digest,
   inspect it, and record the resolved ID and platform.
4. Add expected commit, tree, and archive digest inputs and compare them before
   execution and after it. State that the binding covers tracked Git bytes, or
   mount a clean archive so ignored files cannot influence the model.

### RR-02 [P1] “Bounded” covers only the final result after execution

`runner.py:53-60` captures stdout and stderr into unbounded memory.
`runner.py:340-355` sets no timeout, reads an unbounded prompt, lets the
container write `result.json` without a quota, and checks the result size only
after Docker exits. A stalled process can run without limit; a noisy process
can exhaust host memory or disk. The runner also retains stdout/stderr without
a credential scan.

Smallest correction: add an explicit wall-time limit, prompt/schema byte
limits, bounded stdout/stderr capture, and a write-time output limit. Retain a
failure receipt on timeout or overflow. Scan retained output and receipts for
credential patterns before producing the success manifest.

### RR-03 [P1] The independent schema check silently accepts unsupported types

`runner.py:137-143` validates only properties whose declared type is `string`.
An `integer`, `boolean`, array, nested object, enum, or constrained string rule
falls through without validation. The function therefore accepts values that
the supplied schema rejects.

Smallest correction: use the repository's pinned canonical JSON Schema
validator, or reject every schema keyword and property type outside a
documented supported subset. Add negative tests for each allowed type and for
unsupported rules. Convert JSON decode and schema errors into bounded
`RunnerError` receipts.

### RR-04 [P1] Native evidence is nondeterministic and both routes omit source provenance

`runner.py:197-208` creates a Git commit with ambient author and committer
timestamps. Independent replay produced two commit IDs for the same result;
only the tree matched. Native stores only `result.json`. Graph stores a generic
run node and a result digest, but no source commit/tree/archive, prompt/schema
digest, image, model, or runner identity. Neither route can establish which
execution produced the bytes.

Smallest correction: create one canonical provenance JSON object from the
before/after source snapshot and invocation bindings. Store the same bytes in
Native and Graph, and copy the result into both routes. Set fixed Git identity,
timestamps, initial branch, and file modes. Add a twice-run test requiring
byte-identical Native commit/tree, graph JSON, SQLite, result, and provenance.

### RR-05 [P1] The disposable Vela lifecycle records a passing Verification

`vela_disposable.py:214-243` records
`--outcome pass` for “Exact disposable Result Runner output retention.” The
review requirement calls for a failing Verification before rooted rejection.
The live integration confirmed `outcome: pass`, followed by a valid rooted
reject and zero accepted claims.

The function checks command exit codes but returns hard-coded
`decision: reject` and `scientific_state_changed: false` without asserting the
semantic response. It does not fail if the Decision response, show/status, or
replay omits the expected reject Standing, accepted-claim count zero, or strict
PASS. Its general receipt also omits the approved Vela binary and method
digests.

Smallest correction: define a property for which `fail` is truthful, record
that failing Verification, and assert exact Submission, Verification, rooted
Decision, show, status, and replay semantics before returning success. Bind the
binary and method digests in the route receipt. Keep the fresh destination and
key-deletion `finally` block. Pass a minimal environment to Vela instead of the
full host environment.

### RR-06 [P1] `QUALIFICATION.json` is not bound to retained evidence

The branch file reports a 63-byte GPT-5.4-mini output with SHA-256
`9bec86e4…76322`, source commit `e19da725…`, Native commit `5e820e3a…`, graph
hashes `bd5a7fdb…` / `9c1a5a05…`, and Vela Proposal `vpr_ddcab99597d014ae`.
Those Git objects and output bytes are absent from every fetched branch, so an
independent reader cannot reproduce the claimed hashes or IDs.

Both runner READMEs instead identify retained qualification commit
`5f993c5bafe834828c50bca60830e7bc8488d340`. That exact commit reports an
86-byte GPT-5.6 Sol output with SHA-256 `b6a44156…1d83`, different Native/Graph
IDs, a different Vela binary digest, and one ten-second provider request. Its
raw receipts reproduce the 86-byte claim. The README and postmortem are correct
for `5f993c5`; `QUALIFICATION.json` describes a different, unretained run.

Smallest correction: retain one compact qualification directory on a named
commit with the exact result bytes, invocation, source before/after receipt,
route receipts or bundles, credential scan, and manifest. Point
`QUALIFICATION.json`, both READMEs, and the postmortem to that commit and one
consistent set of hashes. If the 63-byte run cannot be retained, remove its
PASS and use the reproducible 86-byte run only as historical predecessor
evidence; qualify this maintained implementation after RR-01 through RR-05.

## Checks that pass or need wording only

- Subprocess calls use argv arrays and never invoke a shell.
- Docker uses `-i`, mounts source/schema/OAuth read-only, keeps `/output`
  writable, and leaves the ephemeral container root writable under `--rm`.
- Source status, commit, tree, shallow flag, and Git archive digest are captured
  before and after. The exact expected identity and ignored-file boundary need
  RR-01's correction.
- Graph JSON and SQLite bytes were deterministic in the two-run check. SQLite
  integrity and row counts passed the focused tests.
- Vela uses a fresh output destination, verifies the caller-supplied binary
  digest, roots the reject against the inbox entry, runs show/status/replay,
  and deletes both key files in `finally`. It never points at an existing
  authority path.
- Root and tool READMEs describe execution software with a read-only source
  mount. They do not claim proof editing. Add one sentence stating that the
  current runner cannot edit or test source changes and is not a proof-editing
  engine.
- The directory is a maintained implementation, not copied experiment
  bureaucracy: one runner, one optional adapter, one focused test directory,
  a compact method, and a postmortem that deletes the old campaign machinery.

## Merge gate

No merge authorization at `1e7ca3e`. Return one bounded correction commit that
addresses RR-01 through RR-06 without adding a campaign framework. Re-run:

1. focused unit and exact-digest Vela integration tests;
2. Ruff check/format, compileall, and diff hygiene;
3. adversarial path tests for relative paths, symlinks, repository
   subdirectories, linked worktrees, mount delimiters, output collisions, and
   stale source identities;
4. timeout, stream/output-bound, schema-negative, credential-retention, and
   deterministic twice-run recorder tests;
5. one retained non-scoring provider qualification on the exact corrected
   runner, followed by Native, Graph, failing Verification, rooted reject,
   status, and replay; and
6. independent commit-bound review of that correction and qualification.

These gates authorize one tiny qualification request, not a candidate campaign
or scientific validation. They do not authorize merge, Standing, source edits,
or external contact.
