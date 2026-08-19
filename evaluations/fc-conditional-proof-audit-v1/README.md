# Formal Conjectures conditional-proof audit

A deterministic, non-authoritative evaluation frozen on 2026-08-19. It asks one
question about someone else's corpus:

> How many of the external proofs Formal Conjectures links from a
> `formal_proof` attribute are conditional on hypotheses that are never
> inhabited by a closed term?

This directory creates no Problem, Result, Submission, Verification, Decision,
Event, or Standing. Nothing here changes scientific standing anywhere, and no
`vela` command was run to produce it. Every output carries
`authority_effect: none`.

## Why the question is worth asking

The gate the field runs on a formalisation is: it builds against its pinned
toolchain, it contains no `sorry`, and `#print axioms` on the target returns
only `propext`, `Classical.choice`, `Quot.sound`.

An artifact can pass all three and still not prove the theorem. If the
top-level theorem reads

```lean
theorem the_conjecture (X : SomeAssumptionPackage) : … := …
```

and `SomeAssumptionPackage` is never constructed anywhere, then what has been
proved is an implication whose antecedent is exactly the mathematics. A binder
is not an axiom, so an axiom audit cannot see it. A structure that is never
constructed emits no `sorry`. The build is genuinely green.

That is not hypothetical. The case that motivated this audit builds clean
across 7,663 jobs, has zero `sorry` and zero `axiom`, reports exactly the three
standard axioms, and its top-level theorems take an
`ExternalReconstructionSource` argument that is never closed-constructed in its
16,717 lines. That artifact is **not** in the population below — Formal
Conjectures does not link it — and it is used here only to calibrate the
detector. See `CALIBRATION.md`.

## A flag is not an accusation

The calibration artifact disclosed its own assumption layer, in its own audit
file, in prose, naming exactly which packages carried the assumption. It reads
as a formalisation methodology, not as deception. Stating an assumption as a
structure binder is a legitimate and common technique.

What this audit measures is narrower and is about the *reader*, not the author:
whether the ordinary gate is sufficient for a third party to tell a closed
proof from a conditional one. Every per-item output repeats this. Nothing here
should be quoted as a finding of misconduct against any repository or author.

## Population

`google-deepmind/formal-conjectures` at commit
`9f5ee773841921f460b4a26a3552f5eca4accaa0`, every `formal_proof` attribute
under `FormalConjectures/`. Occurrences under `FormalConjecturesTest/`,
`FormalConjecturesUtil/` and `docbuild/` are the attribute's own definition and
unit tests and are excluded.

`audit.json` records the verified population counts, and `results.json` records
one row per link. The counts differ from the working estimate this audit
started from; the numbers in `audit.json` are the ones that were actually
parsed out of the pinned tree.

Two facts about the attribute shape matter for the method:

- `formal_proof using <kind> at "<url>"` — the `<kind>` is the proof *system*
  (`formal_conjectures`, `lean4`, `other_system`), **not** a declaration name.
  The attribute never records which declaration in the linked repository
  discharges the Formal Conjectures statement. The target has to be recovered
  from the URL path and line anchor, or by name matching, and the recovery
  basis is recorded per link.
- Formal Conjectures already has a `conditional … assuming <decl>` form for a
  proof that assumes an unproved hypothesis. It is used, and the count of how
  often is in `report.json`. That vocabulary exists for hypotheses stated as
  Formal Conjectures declarations; it does not reach a hypothesis stated as a
  structure inside the linked repository.

## Method

Two tiers. Tier 1 does not build Lean — building 100+ Mathlib-dependent
projects is hours and many gigabytes, and the question does not require it.

**Tier 1**, over every link:

1. `fetch.py` shallow-clones each distinct (repository, revision) pair into a
   scratch directory, at the commit the link pins, else at the branch or
   default HEAD it names. Which of those applied, and the resolved SHA, are
   recorded per checkout. A repository that 404s and a revision that no longer
   exists are findings, not errors.
2. `analyze.py` indexes every top-level declaration in each checkout, locates
   the target declaration, and computes four discriminators. `rubric.json`
   defines them and states, for each, what it would falsely flag and what it
   would miss.

**Tier 2**, on the highest-signal Tier-1 results only: attempt a real build and
read the target's axiom set. Where a build is infeasible inside the budget,
`tier2.json` says so exactly rather than guessing. Results are in `tier2.json`.

## The four discriminators

| | question | flag means |
|---|---|---|
| **D1** | does the target take a binder that does not occur in its own conclusion, whose type is declared in the linked repository, and which nothing closed-constructs? | the proof may be an implication whose antecedent is the mathematics |
| **D2** | does the repository declare `opaque`, and does the target reach one? | part of the argument is sealed from the kernel and invisible to an axiom audit |
| **D3** | `sorry` / `sorryAx` / `axiom` / `native_decide` / `Lean.ofReduceBool`, scoped to declaration, file and repository | the ordinary gate fires without any of this machinery |
| **D4** | structure fields whose type is `False` or ends in `→ False` | the structure asserts mathematics in its own inhabitation |

D1 and D2 are **heuristics with false positives and false negatives.** They
parse Lean text; they do not elaborate it. `rubric.json` enumerates the known
failure modes of each, and the Result section below reports the hand-checks.
D3 is a textual substitute for `#print axioms` and is not an equal of it.

D1 needs three conditions together, and dropping any one of them destroys it.

*Closure.* A naive "is this type ever constructed" check **passes** the
calibration artifact, because that artifact does contain a declaration
returning the assumption package — one that takes the two component assumption
packages as arguments. D1 instead takes the least fixpoint of *closed*
construction: a site counts only when its own binders are already discharged.

*Occurs-check.* "Local type, never closed-constructed" alone fires constantly
on ordinary mathematics. `theorem t (circles : Fin n → Circle2D) : … circles …`
quantifies over a datatype that nothing in its file explicitly constructs, and
that is exactly as it should be — the binder occurs in the conclusion, so the
statement is stronger for having it. The 887 shape is the opposite: the binder
occurs nowhere in what is asserted, so it can only be supplying the proof. In
the first pass of this audit, before the occurs-check was added, every flag but
none of the real ones survived hand-checking.

*Target location.* Reading every theorem in the linked file also manufactures
flags, because proof files carry dozens of auxiliary lemmas parameterised over
development structures. The locator returns one declaration and records how
confident that identification is; the headline rate uses high-confidence
targets only.

Under all three rules the calibration artifact's three conditional theorems
flag and the one theorem in it that genuinely does not take the package comes
out clear.

## Rights

Third-party Lean source is referenced by URL and commit and is never vendored
into this repository. Several linked repositories carry no LICENSE file —
`plby/lean-proofs`, which is the single largest source of links, is one of
them. `results.json` and `report.json` contain declaration names, type names,
counts, file paths and line numbers only. `evaluate.py` enforces that: it
rejects known body-copy fields and any retained string over 512 characters.

## Run

```bash
python3 evaluate.py verify
python3 evaluate.py report --output report.json
python3 -m unittest discover -s tests -v
```

`verify` re-derives the deterministic roots of the frozen inputs and rejects
schema drift, invented authority effects, population-count drift against
`audit.json`, retained third-party text, and any report cell not derived from
`results.json`. It needs no network and no checkouts.

Regenerating the frozen inputs needs both:

```bash
python3 fetch.py --fc <fc-checkout> --repos <scratch>/repos --output <scratch>/fetched.json
python3 analyze.py collect --fc <fc-checkout> --repos <scratch>/repos \
    --fetched <scratch>/fetched.json --output results.json
python3 analyze.py calibrate --checkout <erdos887-checkout> --output calibration.json
```

`fetch.py` pulls about 2.5 GB of shallow checkouts and `analyze.py collect`
takes roughly half an hour on the resulting tree, most of it in the handful of
very large repositories. Neither writes anything into this repository except
`results.json`.

## Result

### The headline is negative

**The Erdős 887 pattern does not appear in the corpus Formal Conjectures
links.** D1 flags zero of the 396 links whose target could be located. Not one
linked target takes a binder that fails to occur in its own conclusion, whose
type is declared in that repository, and which nothing closed-constructs.

That is worth stating as plainly as the opposite would have been. This audit
was built expecting to find the shape and did not find it. On this evidence the
calibration artifact is an outlier, not a symptom.

The supporting negatives are equally clean. **D2 is zero**: not one of the 143
checkouts declares `opaque` anywhere, so the sealed-arithmetic-core technique
that hides nine declarations from `#print axioms` in the calibration artifact is
absent here. **D4 is zero on any target**: eight checkouts contain a structure
with a field whose type ends in `False`, but no such type is a binder on any
linked target, and in each case it is the ordinary Lean spelling of a negation
(`IsNextPrime`, `PromiseProblem`).

### Counts

| | |
|---|---|
| `formal_proof` attributes at the pinned commit | **415** |
| distinct GitHub repositories | **81** |
| distinct (repository, revision) pairs fetched | **143** |
| dead repositories | **0** |
| vanished revisions | **0** |
| links naming a branch, tag or bare repository root instead of a commit | **142 of 415 (34%)** |
| links that are not a GitHub repository at all | **16** |
| links whose target could be located | **396 of 399 assessed** |
| links located at HIGH confidence (exact name or line anchor) | **267** |
| **D1 flags** | **0** |
| **D2 checkouts declaring `opaque`** | **0** |
| **D3 targets tripping `sorry`/`axiom`/`native_decide`/`ofReduceBool`** | **1** |
| **D4 targets carrying a `False`-field type** | **0** |
| repositories with no LICENSE file | **15 of 81** |
| repositories with no Lean project manifest anywhere | **5 of 81** |

### What did turn up

**A third of the links are not pinned.** 139 name a branch or tag, 3 name only
a repository root. The evidence behind those claims can change without the
claim changing, and a reader cannot tell whether what they see is what was
checked. This is the largest defect in the corpus and the cheapest to fix.

**The attribute does not name what it points at.** 129 of the 399 assessed
links could only be located at medium or low confidence, and 3 not at all —
those point at repository roots (`FormalizedFormalLogic/Foundation`,
`jcreedcmu/Noperthedron`) or at a path that no longer exists
(`math-inc/Sphere-Packing-Lean`).

**Nothing on the Formal Conjectures side is checked.** All 415 Formal
Conjectures declarations carrying a `formal_proof` are `sorry` in their own
proof body, and no workflow clones or builds any linked repository. That is
Formal Conjectures working as designed, and it is exactly why the link carries
the whole weight.

**One target does not have the standard axiom set.** `Erdos418.erdos_418` in
`plby/lean-proofs`, located by exact name match, discharges `m_BS ≠ 0` with
`native_decide`. Tier 2 built the project at its own pinned toolchain and read
the axioms:

```text
'Erdos418.erdos_418' depends on axioms:
  [propext, Classical.choice, Lean.ofReduceBool, Lean.trustCompiler, Quot.sound]
```

This is the one place in the population where the ordinary gate's third clause
fails, and nothing in Formal Conjectures runs that clause. It is a disclosure
point rather than an error: compiled evaluation of a concrete numeric non-zero
check is a reasonable choice and the repository is not hiding it.

**Three links use Formal Conjectures' own `conditional` marker** — `erdos_750`,
`erdos_1141`, `erdos_427`. The vocabulary exists, it is well designed, and it is
used honestly where it applies.

### False positives: what the detector did before it was correct

This is the part to read before anyone quotes the count. Three successive
versions of D1 were run over the same corpus. The first two produced flags.
**Every one was a false positive**, and each was retired by reading the file.

| detector version | flags | true positives | what went wrong |
|---|---|---|---|
| local type, never closed-constructed | 8 | 0 | ordinary datatypes the theorem quantifies over |
| + occurs-check on the conclusion | 2 | 0 | locator pointed at auxiliary lemmas, not the theorem |
| + locator prefers the final theorem and reads the declaration containing a line anchor | 0 | — | |

1. **Datatype binders.** `Erdos1121.erdos_1121 (circles : Fin n → Circle2D)`.
   Nothing constructs a `Circle2D` and nothing should: the theorem quantifies
   over all of them, and `circles` occurs throughout the conclusion. Six of the
   eight first-round flags were this.
2. **Auxiliary lemmas.** `Erdos639.erdos639_pre (A : AFrame C)` and
   `Erdos775.tree_from_many_clique_sizes`. Both are internal steps; the final
   theorems `erdos639` and `erdos_problem_775` are unconditional.
3. **Anchors read forward instead of around.** The link for
   `bounded_gap_legendre` anchors at `#L48`, inside that theorem's own proof.
   Taking the first declaration *after* the anchor walked past it into
   `legendre_conjecture.ferreira_large_n`, an unrelated `sorry` in the same
   file, and reported a `sorry` finding about a link that has none.

**False-positive estimate for the current detector: undetermined, because it
produced no flags to check.** What can be said is that the three prior versions
had a false-positive rate of 100% at 8 and 2 flags, that all ten were retired by
hand, and that each fix was made because a hand-check found the error rather
than because the count looked wrong. `tier2.json` records each retirement.

### False negatives: what a zero would hide

1. **A hypothesis over Mathlib types is invisible.** D1 requires the binder's
   type to be declared in the linked repository. `theorem t (h : ∀ n, P n) : …`
   with `P` built from Mathlib is exactly as conditional and is not flagged.
   This is the largest gap and nothing here bounds it.
2. **Low-confidence targets.** 51 links were located only as "the last theorem
   in the file", and 1 by an anchor landing before the file's first
   declaration. For `openai/ten-proofs` that file has 656 theorems over 18,500
   lines and the locator picked `not_erdos_146` where the intended target is
   `twoDegenerateExtremalCounterexample`. Both are unconditional, and exactly
   one of those 656 theorems carries an unused unclosed local binder, so the
   miss hides nothing here — but the mechanism is real.
3. **`variable` lines and section binders** are not part of the parsed
   signature.
4. **Lean 3.** `b-mehta/unit-fractions` is a Lean 3 project read by a Lean 4
   parser. Its row is approximate.
5. **Imported assumptions.** A package constructed in a dependency reads as
   closed here; one assumed by a dependency reads as absent.

Partly bounding (2): a stratified sample of 24 `clear` verdicts across all three
confidence tiers was drawn, and six were read in full signature detail —
`conjecture1`, `alpha_le_one_not_isGoodPair`, `erdos_379`, `not_erdos_1037`,
`ErdosProblem16`, `erdos45`. All six are closed statements whose binders either
occur in the conclusion or mirror hypotheses present in the Formal Conjectures
statement. No false negative was found in the sample.

### The honest summary

Formal Conjectures' external-proof corpus is in better shape than the
motivating case suggested. The conditional-on-uninhabited pattern is not there.
What is there is a provenance problem rather than a soundness problem: a third
of the links are unpinned, none names the declaration it points at, and Formal
Conjectures' own CI checks none of it. Those are worth fixing, and they are far
easier to fix than what this audit went looking for.

## What this does not establish

- It does not establish that any linked proof is wrong. D1 flags a *shape*.
- It does not establish that any flagged repository is unsound, incomplete, or
  presented in bad faith.
- It does not measure mathematical correctness, novelty, or difficulty.
- Where a repository cannot be assessed statically the row is `undetermined`,
  and `undetermined` rows are excluded from rates rather than counted as clear.
