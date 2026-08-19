# Disposition

What this audit changes, and what it explicitly does not.

## Adopt now

- **Treat "builds, no `sorry`, clean `#print axioms`" as necessary and not
  sufficient.** It is the gate the field runs and it is a good gate. It cannot
  see a hypothesis carried in a binder, and it cannot see an `opaque`. Any
  Vela Verification that cites a Lean build must say which of those it checked
  and must not describe a green build as acceptance.

- **Record the target declaration, not just the repository.** The single
  largest obstacle to auditing this corpus is that `formal_proof using <kind>
  at "<url>"` names a proof system and a URL and never names the declaration
  that discharges the statement. Anything Vela emits about an external formal
  proof should carry the declaration's fully qualified name alongside the
  repository, the commit, and the file path.

- **Pin the commit.** A third of the links in this population name a branch
  rather than a commit, so the evidence can change under the claim without the
  claim changing. A Vela evidence artifact pointing at external source must
  carry a resolved SHA, and a branch reference should fail closed.

- **Make "conditional" a first-class outcome, not an exception.** Formal
  Conjectures already has `conditional formal_proof … assuming <decl>`, and it
  is well designed: it refuses `assuming` without `conditional` and refuses
  `conditional` without `assuming`. Its reach stops where the hypothesis stops
  being a Formal Conjectures declaration. A Verification Record that reports on
  an external Lean artifact should carry the binder list of the target and say
  explicitly which binders are discharged by a closed term.

## Offer upstream, if anyone wants it

The cheapest useful change to Formal Conjectures is an optional declaration
name in the attribute — `formal_proof using lean4 at "<url>" proving <name>`.
That alone would turn every audit of this corpus from a heuristic into an exact
check, because the target would be unambiguous and its signature could be read
directly. Nothing else here needs Formal Conjectures to change.

A second, smaller one: the existing `research open` warning fires when a
`formal_proof` is attached to an open problem. The same machinery could warn on
a link with a branch reference rather than a commit.

## Do not do

- **Do not publish a list of flagged repositories as a list of bad proofs.**
  D1 flags a signature shape. The hand-checks in `README.md` show how much of
  the raw signal is ordinary mathematics quantifying over a datatype, and the
  first version of this detector, before the occurs-check, was almost entirely
  false positives. Any public statement must carry the false-positive estimate
  next to the count.

- **Do not treat the calibration artifact as representative.** It is one case,
  it is not in this population, and it disclosed its own assumption layer. The
  measured rate in the corpus Formal Conjectures actually links is what this
  directory reports; the calibration artifact is only evidence that the
  detector can see the shape at all.

- **Do not build a Formal Conjectures crawler, a proof-checking service, or a
  ranked "conditionality" leaderboard.** This is one frozen evaluation. If it
  needs to run again it runs again from the pinned commit.

- **Do not vendor third-party Lean source.** Fifteen of the linked repositories
  have no LICENSE file, including the one carrying the most links.

## Monitor

- Whether Formal Conjectures adopts a target-declaration field, and whether
  `conditional … assuming` usage grows past the three links now using it.
- Whether the linked repositories that name branches move to pinned commits.
- Whether any linked repository starts using `opaque` or `native_decide` in a
  proof path, which the ordinary gate also cannot see.
