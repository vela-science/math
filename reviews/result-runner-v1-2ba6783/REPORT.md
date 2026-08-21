# Corrected Math Result Runner re-review

Verdict: **BLOCKED**

Reviewed producer state:

- branch `codex/result-runner-v1`
- commit `2ba67830a42e657567bd30755f560183e767c26c`
- tree `7e6ec37b2e7eb94be789949abf4a78aba33d3f86`
- parent `1e7ca3ec4821651c0697c8952fce7d29d616eb52`
- remote branch equal to the reviewed commit

The correction closes RR-01 and RR-06. It adds fail-closed keyword/type
checks, canonical provenance, and failing Vela semantics. Four implementation
defects block merge: a post-exit output-limit race, unbound regex and SQLite
dependencies, and authority-key cleanup that starts after key creation.

## Findings

### RR-02 [P1] The output monitor can miss files written in the final polling interval

`runner.py:214-241` calls the runtime monitor only while `process.poll()` is
`None`. `execute()` does not run the monitor after Docker exits
(`runner.py:1035-1072`). A container can write an oversized or excess file,
exit during the 20 ms polling interval, and reach result validation and the
unbounded final credential scan.

An independent five-run fixture delayed 5 ms, wrote a 1,000,000-byte file
against a 10-byte limit, and exited. Four runs returned `status=completed`;
the same monitor reported `runtime_total_size_exceeded` when called after the
process. This contradicts the advertised write-time runtime bound.

Smallest correction: invoke the same monitor once after process and stream
joins, before reading or copying any output. Convert a violation to the
existing failure receipt. Add a regression fixture that writes a valid small
`result.json` plus an oversized sibling in the final polling interval.

### RR-03 [P1] `pattern` uses an unbound regex dialect

The closed schema subset delegates `pattern` compilation and matching to
Python `re` (`runner.py:518-528` and `runner.py:571-575`). The schema passed to
Codex is JSON Schema, but the runner neither pins a matching validator nor
restricts patterns to a proven common grammar. The host accepted a Python-only
named group `(?P<named>pass)` and accepted the Arabic digit `١` for `^\d$`.
Those outcomes do not establish equivalence with the container's JSON Schema
evaluator.

The retained qualification schema uses only `const`, so this defect does not
invalidate its 100 output bytes. It does invalidate the maintained runner's
claim that supported `pattern` constraints receive an exact independent host
check.

Smallest correction: remove `pattern` from the supported subset, or validate
with the exact pinned dialect used by the accepted Codex image. Add dialect
boundary tests that run both validators.

### RR-04 [P1] SQLite bytes depend on an unrecorded library version

Replaying the retained result and provenance reproduced Native commit
`501e058abf304fb363e629508af051bce4154de5`, Native tree
`ba38c2fb7bb4cf79137d7f57e1dae3d67550cae7`, and Graph JSON SHA-256
`f301129777dbe45f686986dc9b44120e0304c28774c766b0bcee179f6ff95bc1`.
The SQLite replay produced SHA-256
`12bd395fa5acfa3c9091a6fd408ce0fbffd88af53e15f5f69840f4057e9e33d2`,
not retained SHA-256
`f7a8b51fb039341d9e0d4cc1f2d0e79b69faeb220c734a822b1f9036c1c66501`.

The databases have identical length, integrity, rows, and payloads. Only
header bytes 99 and 100 differ. The retained file records SQLite 3.51.0; the
replay used the repository's stated Python 3.11.2 with SQLite 3.39.4.
`record_graph()` does not bind or pin SQLite (`runner.py:718-789`). The
twice-run test proves determinism within one ambient library version, not from
the retained source and provenance.

Smallest correction: serialize SQLite with a pinned runtime and bind that
runtime digest/version in provenance, or scope the byte-determinism claim to
one recorded runtime and treat logical SQLite replay plus canonical Graph JSON
as the portable check. A merge-quality exact-byte claim requires the pinned
route.

### RR-05 [P1] Key cleanup does not cover setup failure

`record_disposable()` creates the private/public authority key inside
`_agent_environment()` at `vela_disposable.py:324`, then enters its cleanup
`try/finally` at line 325. If `ssh-keygen` succeeds and `ssh-add` fails, control
never reaches the key-deletion block at lines 530-534.

An injected `ssh-add` failure reproduced both retained files:
`private/authority-key` and `private/authority-key.pub`. The successful live
integration deletes both keys, but the AGENTS contract requires cleanup on
failure too.

Smallest correction: enter `try/finally` before agent/key setup, initialize
the environment and agent state defensively, and delete both key files for
every exit. Add a regression test for failure after key generation and before
`ssh-add` returns.

## RR-01 through RR-06 disposition

- **RR-01 PASS.** The runner rejects relative, aliased, symlink, subdirectory,
  linked-worktree, mount-delimiter, output-collision, and stale-source inputs.
  It requires a physical top-level repository with in-tree `.git`, exact
  repository/commit/tree/archive identities, `desktop-linux`, and an exact
  local image ID. The focused Docker dry path reproduced the frozen source and
  image before/after receipt.
- **RR-02 BLOCKED.** Wall time, streams, prompt/schema/result sizes, and process
  tree cancellation pass. The final output-limit race remains.
- **RR-03 BLOCKED.** Unsupported types and keywords fail closed; const, enum,
  and length checks pass. `pattern` lacks evaluator equivalence.
- **RR-04 BLOCKED.** Canonical provenance, Native commit/tree, Graph JSON, and
  same-runtime twice-run tests pass. Portable SQLite byte replay fails because
  the serializer runtime is absent from provenance.
- **RR-05 BLOCKED.** The retained and live exact-digest lifecycles show one
  failing Verification, rooted reject, strict readback/replay, zero accepted
  Claims, and `scientific_state_changed=false`. Key deletion fails on the
  pre-`try` setup path.
- **RR-06 PASS.** The retained qualification is coherent and
  source-bound. All 35 non-manifest portable files, sizes, and hashes
  recompute. `QUALIFICATION.json`, invocation, execution, result, provenance,
  route, method, source, image, and Vela identities agree. The 51-file clean
  clone credential scan returns zero findings.

## Reproduced checks

- commit/tree/parent and remote equality: PASS
- runner, Vela adapter, method, qualification, result, and manifest hashes:
  PASS
- focused suite: 15 pass plus one expected Vela skip
- exact Vela 0.977.3 integration at SHA-256
  `3a1173918bdcb887155bab681411bf5e9ff64d925fe1b50369ac37ab020b94ad`:
  PASS
- Ruff 0.5.4 check/format, Python 3.11.2 compileall, `git diff --check`, and
  clean checkout: PASS
- Docker dry path against image
  `sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e`
  on `linux/arm64`: PASS
- retained Vela receipt hashes/exits and lifecycle semantic assertions: PASS
- retained Graph SQLite integrity and logical rows: PASS
- independent exact Graph SQLite byte reconstruction: FAIL
- post-exit output bound and pre-agent-failure key deletion: FAIL

## Merge gate

Do not merge `2ba67830a42e657567bd30755f560183e767c26c`. Return one correction limited
to RR-02, RR-03, RR-04, and RR-05 plus focused regression tests. The retained
qualification remains truthful for its exact simple `const` schema and
successful execution. A new provider request is unnecessary if the producer
does not change candidate invocation, scientific inputs, or result-routing
semantics. Re-run the deterministic/security suite, exact Vela integration,
and one no-model Docker dry path before another independent review.
