# `math-result-candidate-erdos-321-status-conflict-2026-08-20`

## Bounded assertion

At the exact current source heads checked on 2026-08-20, the source-owned
status of Erdős problem 321 is inconsistent across repositories:

- [`teorth/erdosproblems@931e7db4.../data/problems.yaml`](https://github.com/teorth/erdosproblems/blob/931e7db4ee3c97705598f802e8358a201b9e422c/data/problems.yaml#L5210-L5223)
  records both `informal_status.state` and `status.state` as `solved`, with
  `formal_status.state` still `unformalized`.
- [`google-deepmind/formal-conjectures@9f5ee773.../321.lean`](https://github.com/google-deepmind/formal-conjectures/blob/9f5ee773841921f460b4a26a3552f5eca4accaa0/FormalConjectures/ErdosProblems/321.lean#L39-L80)
  marks the exact-answer, `IsTheta`, `IsBigO`, and `IsLittleO` occurrences
  `research open` and says a solution is not known.
- The official Formal Conjectures status script reports problem 321 as
  `lean_status: open`, `yaml_status: solved`, and existing issue
  [#4444](https://github.com/google-deepmind/formal-conjectures/issues/4444)
  remains open.
- Math's accepted Claim
  `vcl_b9c6915de55e15c69d06b9aeed786b0e632986374a347d77ff447ad244f67a2e`
  at
  [`records/claims/sha256/58f97ba8...json`](../../records/claims/sha256/58f97ba8a90d23d4655c4b71051c6bdd4723c0454f31f4ed3cb3e95b0a6c8b15.json)
  carries the caveat “Erdos problem 321 remains open.”

This establishes a current status conflict. It does **not** establish that the
problem is solved, that the accepted Math Claim's mathematical assertion is
false, or that the `solved` status applies to any particular Formal
Conjectures occurrence.

## Observable facts available to every comparison condition

The numbered list is a quick summary. Every condition receives this entire
public packet, including the evidence and uncertainty, required Check and
authority, draft message, and next action below.

1. The two exact upstream heads and file locators named above.
2. Erdős Problems records informal and overall status `solved` and formal
   status `unformalized`.
3. Formal Conjectures marks four named occurrences `research open`.
4. Its official status script returns `lean_status: open` and
   `yaml_status: solved` for problem 321.
5. Existing Formal Conjectures issue #4444 is open with no source-owner scope
   resolution.
6. The current accepted Math Claim and root are named above, including its
   “remains open” caveat.
7. The current Math profile includes Erdős 321, but no new Submission,
   Verification, or Decision exists for this conflict.

## Explicit nonclaims

- The YAML label does not prove the exact-answer or any asymptotic occurrence.
- The mismatch script does not perform a literature or statement-fidelity
  review.
- The existing accepted Claim's mathematical assertion is not shown false.
- In-scope Repository authority is not permission to decide before the source
  scope is resolved.

## Answerable questions

1. **E321-Q1:** What exact source-status conflict exists?
2. **E321-Q2:** Does the status script establish that problem 321 is solved?
3. **E321-Q3:** Which owner controls each of source status, Lean category, and
   Math Standing?
4. **E321-Q4:** Which exact Formal Conjectures occurrences are affected?
5. **E321-Q5:** What, if anything, does the conflict establish about the
   accepted Math Claim?
6. **E321-Q6:** Is the current Math authority in scope, and is a Decision
   justified now?
7. **E321-Q7:** What is the single next human action?

Expected answers are held out. Their public byte commitment is in
[`ADJUDICATION_COMMITMENT.md`](ADJUDICATION_COMMITMENT.md).

## Same-information baseline views that can be constructed later

- **Git/source only:** the entire public packet's information through exact
  source files, heads, official mismatch output, and plain-text Check,
  authority, uncertainty, and next-action facts.
- **Native FC/registry presentation:** that same complete information set
  through the Formal Conjectures file, status-sync issue, and Erdős Problems
  status presentation, without adding keyed answers.
- **Vela package:** that same complete information set as one source-bound
  artifact and non-authoritative Check input; no Standing change or extra
  source facts.

## Exact evidence and uncertainty

- Known-result Check method:
  [`methods/current/known-result-and-duplicate-search.v1.json`](../../methods/current/known-result-and-duplicate-search.v1.json),
  file SHA-256 and method root
  `sha256:42e00706140c3079282a0b04fe9e352d5be740235533e5a2527f96be189850a0`.
- Status source: `teorth/erdosproblems`, commit
  `931e7db4ee3c97705598f802e8358a201b9e422c`.
- Formal statement source: `google-deepmind/formal-conjectures`, commit
  `9f5ee773841921f460b4a26a3552f5eca4accaa0`, declarations
  `Erdos321.erdos_321`, `Erdos321.erdos_321.variants.isTheta`,
  `Erdos321.erdos_321.variants.isBigO`, and
  `Erdos321.erdos_321.variants.isLittleO`.
- Existing Math Standing is recoverable from `.vela/repository.json`; the
  current accepted Claim root is
  `sha256:58f97ba8a90d23d4655c4b71051c6bdd4723c0454f31f4ed3cb3e95b0a6c8b15`.

The unresolved uncertainty is semantic scope. A source-level `solved` label
may refer to the informal problem, an asymptotic answer, or a result that does
not prove the exact Lean occurrence. This pass did not locate and review a
source-owner-endorsed solution against those four Lean statements.

## Required independent Check and intended authority

1. The `teorth/erdosproblems` owner identifies the literature/result behind
   `solved` and states which formulation it resolves.
2. An independent mathematical reviewer compares that result with each exact
   Formal Conjectures occurrence and records match, partial match, or mismatch.
3. Re-run `python3 scripts/check_erdos_status.py` at the two exact source heads
   and the current known-result/duplicate search for the bounded assertion.

If the review confirms a scope match, Formal Conjectures maintainers own the
source correction and Vela Math Repository authority may review a new
corrected Claim that supersedes the accepted caveat. If it does not, the
`teorth/erdosproblems` owner owns the status correction. No Math authority
action is justified before this split is resolved.

## Exact draft for existing issue #4444 — not posted

> At current heads `formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`
> and `teorth/erdosproblems@931e7db4ee3c97705598f802e8358a201b9e422c`,
> the mismatch remains. Before changing the four `research open` annotations,
> could the Erdős Problems source owner identify the result behind the YAML
> `solved` status and say whether it resolves the exact `R N = answer(...)`
> occurrence, an asymptotic occurrence, or another interpretation? Math's
> current accepted candidate only asserts a two-sided asymptotic bound and
> explicitly does not claim resolution, so a status-only edit would collapse
> the scope distinction.

The one human action is to obtain that source-owner scope decision on the
existing issue. No new issue or comment was posted by this task.
