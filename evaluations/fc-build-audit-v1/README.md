# Formal Conjectures build audit

A deterministic, non-authoritative evaluation. It does the expensive half of a
question the static audit next door deliberately left open:

> Of the external proofs Formal Conjectures marks a statement solved by, how
> many still build at the revision the link points at, and what axiom set does
> the linked declaration actually carry?

Formal Conjectures marks 415 statements solved by `formal_proof` links into 81
other repositories. Its CI builds none of them. This directory builds them.

This creates no Problem, Result, Submission, Verification, Decision, Event or
Standing. Nothing here changes scientific standing anywhere, and no `vela`
command was run to produce it. Every output carries `authority_effect: none`.

## What this extends

`../fc-conditional-proof-audit-v1/` resolved every `formal_proof` attribute at
`google-deepmind/formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`
into 415 links, 81 repositories and 143 (repository, revision) pairs, and
located a target declaration for each link — all by parsing Lean text. It never
elaborated any of it. Its `sorry` and `native_decide` signals were textual, and
its target locations were name and anchor matches carrying an explicit
confidence.

This audit reuses that work unchanged. The population is not re-derived, the
locator is not re-run, and every link's `target_locator_confidence` is carried
through verbatim — `evaluate.py` rejects the file if a single one has been
altered. What is new is that the kernel now runs.

## Method

For each of the 143 checkouts, in descending order of link count:

1. Fetch at the SHA the static audit resolved, so both audits mean the same
   bytes.
2. Find every directory carrying both a Lake manifest and a `lean-toolchain`,
   and group the links by which of those projects owns the linked file.
3. Per project: install the pinned toolchain through elan, `lake exe cache get`
   where the manifest names Mathlib, and `lake build` the linked modules.
4. Where it builds, elaborate `#print axioms` on each located target
   declaration, one command per declaration.
5. Delete the `.lake` tree.

Step 5 is not housekeeping. A Mathlib build tree is several gigabytes and 143
of them do not fit on any ordinary disk, so the run deletes each one before
starting the next and stops cleanly if free space drops below its floor. The
shared Mathlib olean cache is pruned under pressure rather than every time: 97
of the 143 checkouts pin the same toolchain, and dropping the tarballs after
each build would spend the entire budget re-downloading them.

`rubric.json` defines the closed outcome vocabulary and states, for each
outcome, exactly what it does and does not mean.

### Why a repository is built as several projects

A repository is not always one Lake project, and its links do not all land in
the same one. `plby/lean-proofs@main` keeps a directory per Lean version, and
its 104 links split 81 / 21 / 2 across `src/v4.29.1`, `src/v4.24.0` and
`src/latest` — three toolchains, three Mathlib revisions, three cache fetches.
Building only the busiest would have reported `target_not_found` for 23 links
that are fine. The wall-clock cap is therefore per project, capped at three
projects' worth per repository, and the repository's headline outcome is its
busiest project's rather than its best one's.

## Run

```bash
python3 evaluate.py verify
python3 evaluate.py report --output report.json
python3 -m unittest discover -s tests -v
```

`verify` re-derives the deterministic roots of the frozen inputs and rejects
schema drift, invented authority effects, outcome vocabularies outside the
rubric, drift against the static audit, axiom flags that do not follow from the
axiom sets they claim to summarise, a finding that names no link, a flagged
link with no finding, a claim of clean axioms on a checkout nobody built, and
retained third-party text. It needs no network, no toolchain and no checkouts.

Regenerating the frozen inputs needs a machine with elan, a fast link and a lot
of patience:

```bash
python3 build.py fetch --repos <scratch>/repos --state <scratch>/state.json
python3 build.py run   --repos <scratch>/repos --state <scratch>/state.json \
    --timeout 2700 --budget-seconds 24000 --min-free-gb 15
python3 build.py collect --state <scratch>/state.json --output builds.json
```

`run` checkpoints after every repository and is resumable: a crash costs one
repository, not the batch.

## Rights

Third-party Lean source is referenced by URL and commit and is never vendored
into this repository. Several linked repositories carry no LICENSE file —
`plby/lean-proofs`, the single largest source of links, is one of them.
`builds.json` contains declaration names, axiom names, module names, toolchain
versions, timings, and build failure excerpts capped at 400 characters.
`evaluate.py` enforces that: it rejects known body-copy fields and any retained
string over 512 characters.

## Coverage, stated plainly

This is a **partial** audit and its coverage is part of its result.

| | |
|---|---|
| `formal_proof` links at the pinned Formal Conjectures commit | **415** |
| links that point at a GitHub repository at all | **399** |
| links with no GitHub checkout (nothing to build) | **16** |
| distinct (repository, revision) pairs | **143** |
| checkouts attempted | **20** |
| **links inside the attempted checkouts** | **260 of 399 — 65.2%** |
| checkouts not attempted | **123** |
| measured build compute | **2.37 hours** |

The cap is a budget decision, not a finding. Measured on this host a
Mathlib-dependent Lake project costs 3 to 45 minutes end to end, and the 143
checkouts declare 135 projects between them, so the full set is 20 to 28 hours.
The 20 attempted are the 20 with the most links. Every one of them reached a
terminal outcome — the run stopped because the work was finished, not because
it hit the wall-clock budget or the disk floor.

**A `not_attempted` row says nothing about the repository it names.** The 123
of them are recorded with their link counts in `builds.json`, not dropped.

## Result

### Nothing failed to build

**Zero build failures. Zero timeouts. Zero unavailable toolchains.** All 15
checkouts that contain a Lake project compiled at the toolchain they pin,
across five Lean versions from v4.27.0 to v4.32.0, at a pinned revision and at
an unpinned one alike.

That is not what was expected. These projects were written months apart against
a Lean and a Mathlib that both make breaking changes on a weeks-to-months
cadence, and some fraction failing to build today would have been the ordinary
result. In this sample the fraction is none. It is a positive finding about the
corpus and it is worth saying first.

`findings.json` states each of these zeros and `evaluate.py verify` recomputes
every one of them from `builds.json`, rejecting the file on a mismatch. A
negative result nobody re-checks is a sentence, not a finding.

### 204 declarations read at the kernel

| axiom closure | declarations |
|---|---|
| `propext, Classical.choice, Quot.sound` | **199** |
| `propext, Quot.sound` | 1 |
| `propext` | 1 |
| `propext, Classical.choice, Lean.ofReduceBool, Lean.trustCompiler, Quot.sound` | **2** |
| `propext, Classical.choice, Erdos750.stiebitz_lower_bound, Quot.sound` | **1** |

201 of 204 are the standard three or a proper subset of them. Three are not.

### The three that are not

**`Erdos418.erdos_418`** (`plby/lean-proofs`, HIGH confidence, exact name
match) carries `Lean.ofReduceBool` and `Lean.trustCompiler` — the `native_decide`
route. The static audit already found this one by reading the source. The build
confirms it at the kernel.

**`Erdos56.erdos_56`** (`plby/lean-proofs`, HIGH confidence, exact name match)
carries the same two axioms, and **the static audit did not find it and could
not have.** There is no `native_decide` token anywhere inside the declaration;
its per-declaration token count was empty. The dependency is transitive,
through a lemma the theorem uses. This is the case that justifies building
rather than reading: a text-level audit is structurally blind to it, and
grepping the file instead would flag every declaration in a file that uses
`native_decide` anywhere — a different and much noisier claim. The closure
answers the actual question, did *this* theorem's proof depend on it, and the
answer is yes.

**`Erdos750.erdos_750_FC`** (`Shashi456/erdos-formalizations`, MEDIUM
confidence) carries a locally declared `axiom`, `Erdos750.stiebitz_lower_bound`.
The proof assumes Stiebitz's lower bound rather than proving it — and
**Formal Conjectures already says so**: this is one of the three links using its
own `conditional … assuming` form, naming `erdos_750.variants.stiebitz`. That
vocabulary is working exactly as designed, and the build corroborates it
independently. It is listed because it is an axiom-clause failure by the
mechanical definition and because it shows what a closure looks like when an
assumption really is load-bearing.

None of the three is an accusation. Compiled evaluation of a concrete numeric
check is a reasonable engineering choice; stating an assumption as an axiom and
declaring the result conditional is honest practice. What the three show is
that the ordinary gate's third clause is a real check that links in this corpus
can fail, that nothing in Formal Conjectures runs it, and that one of the three
cannot be surfaced by reading source at all.

### The second surface: propositional hypotheses

All 204 declarations also got a hypothesis reading — **zero `unavailable`**, so
the metaprogram elaborated on every toolchain in the sample.

| Prop binders on the declaration's own type | declarations |
|---|---|
| 0 | 124 |
| 1 | 50 |
| 2 | 17 |
| 3 | 9 |
| 4 | 3 |
| 5 | 1 |

80 of 204 linked targets prove an implication rather than their conclusion
outright. **This is not a defect count.** Formal Conjectures statements carry
hypotheses of their own and a linked proof that mirrors them is exactly right;
the ones inspected are ordinary side conditions (`3 ≤ k`, `1 < n`, a
Cauchy-type functional condition). It is recorded because `#print axioms`
cannot see it — a hypothesis parameter never appears in an axiom closure, the
same way `Erdos56`'s transitive `native_decide` never appears in its source
text. Reading one surface and calling it a verdict is how both get missed.

The two surfaces are recorded separately for a reason stated in `rubric.json`:
a clean closure is **necessary and not sufficient**. `@[csimp]` can substitute
an unverified implementation without adding anything to the closure
(lean4#7463, open), and the `Lean.ofReduceBool` route was shown unsound in 2023
(Carneiro).

### What could not be read

| | links |
|---|---|
| target elaborated and axioms read | **212** |
| repository has no Lake project at all | 15 |
| project built, target not elaborable under the recorded name | 13 |

**`Woett/Lean-files` contains no Lake project.** Neither checkout has any
directory carrying both a Lake manifest and a `lean-toolchain`, so there is
nothing to build and no way to reach the linked declarations by the ordinary
route. Formal Conjectures links **15 statements** to this repository across two
revisions. This is not drift and not a build failure — publishing Lean files
without a Lake package is legitimate and predates any expectation of
buildability. But a minimal `lakefile.toml` plus `lean-toolchain` would make all
15 machine-checkable, and it is the cheapest single change available anywhere
in this corpus.

The other 13 are a **locator** result, not a repository defect. The
`formal_proof` attribute records a URL and at most a line anchor; it never
records which declaration discharges the statement, so the name is always
reconstructed. Where the reconstruction is wrong the honest output is
`not_found`, and no claim is made about those proofs in either direction. This
is the same defect the static audit named as its largest, seen from the other
side.

### The honest summary

The corpus builds. Where its proofs can be reached, they are overwhelmingly
clean: 199 of 204 declarations return exactly the three standard axioms and
nothing in the sample contains `sorryAx`. The problems are not soundness
problems — they are reachability problems. A third of the links are unpinned,
the attribute never names its target, 15 links point at a repository with no
build, and Formal Conjectures checks none of it. Every one of those is cheaper
to fix than what this audit went looking for, and one of the three axiom
findings could not have been found without doing the expensive thing.

## What this does not establish

- It does not establish that any linked proof is wrong. A build failure months
  after the fact is ordinary toolchain drift.
- `#print axioms` reports the axiom set, not the statement. A clean axiom set on
  a declaration that does not state the conjecture is worth nothing, and
  statement fidelity is not checked here.
- An axiom reading is only as attached to the intended target as the static
  audit's locator was. Where that confidence is medium or low, the reading is a
  fact about the declaration the locator picked.
- A build result is a statement about one host, one network and one date.
- Nothing here is a Submission, Verification, Decision, Event or Standing.
