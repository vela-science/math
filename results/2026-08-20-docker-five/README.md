# Five Docker Result attempts — 2026-08-20

Five source-native candidate sessions ran exactly once each. They produced
three bounded proposed Results and two typed non-results. These are candidate
artifacts for independent evaluation; they are not Verifications, Decisions,
Standing changes, or source-owner acceptance.

| # | Case | Outcome | Elapsed | Completed shell calls |
|---|---|---|---:|---:|
| 1 | Erdős 321 status conflict | Typed non-result: conflict established, scope unresolved | 50.08 s | 4 |
| 2 | Erdős 750 conditional dependency | Proposed conditional implication; universe fidelity unresolved | 102.14 s | 7 |
| 3 | Erdős 56 trust/axiom/licence | Proposed exact-byte trust disclosure; policy and rights unresolved | 56.04 s | 4 |
| 4 | Erdős 94 sum-multiplicity proof | Proposed mathematical proof reconstruction; no independent Lean build | 106.64 s | 8 |
| 5 | Erdős 887 negative control | Typed non-result: repair/replay contains no number-theory proof | 73.13 s | 6 |

## Exact execution boundary

- Git base: `5de716c896065c03c0a470d015ba2a328a527f73`
  (`origin/main` when the branch was created).
- Branch: `codex/docker-result-attempts-2026-08-20`.
- Docker context: `desktop-linux`; server version `28.3.2`.
- Image:
  `vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01`.
- Base image:
  `debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818`.
- Candidate CLI: `codex-cli 0.145.0`, using the existing ChatGPT OAuth file
  through a read-only bind mount. No provider key was added or logged.
- Repository mount: read-only. Output mount: one writable directory per case.
- Attempts/retries: `5/0`. Every assigned case remains in the denominator.

Each case directory contains `candidate.json`, the compact source-native
Result packet; `receipt.json`, the elapsed time and exact artifact hashes; and
`tool-calls.json`, the completed observable shell calls and exit codes. The
full raw event streams were reduced to that projection after a credential
pattern scan so the retained packet stays compact.

## Smallest handoff

An independent evaluator should inspect the five `candidate.json` files at
this exact commit, then run only the `smallest_independent_check` named by each
candidate. The proof candidate in case 4 and the explicit non-result in case 5
are the clearest first pair for discriminating mathematical throughput from
mere record inspection. No current Math authority action is in scope.
