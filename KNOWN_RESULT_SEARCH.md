# Known-result and duplicate search

Searching for a prior result is a scoped Check, not a decision. It is recorded
with `vela verification record` against a pending Proposal, under the method
manifest
[`methods/current/known-result-and-duplicate-search.v1.json`](methods/current/known-result-and-duplicate-search.v1.json)
(`vela.verification-method.v1`, profile `coh-00-known-result-and-duplicate-search-v1`,
property `known_result_and_duplicate_search`).

This adds no Core object and no Protocol surface. It is the existing
Verification mechanism pointed at a question we were answering informally.

## What the Check answers

Was the declared source scope searched for a prior result covering this Claim,
and did that search find one?

The manifest names the sources, the exact query string or command for each, the
locator form to retain, and the rights boundary for each. It requires the
searcher to declare the scope — terms, date bound, and what was deliberately
not searched — before searching, and to record every source it names, including
the ones that were unavailable, not applicable, or not searched.

## Register the requirement on the Submission

A producer who wants this Check to gate acceptance registers it at submission
time:

```bash
vela submit --repo . \
  --claim "<bounded assertion>" \
  --type <claim-type> --replayability <class> \
  --artifact evidence/current/<packet>.json:<kind> \
  --caveat "<limit>" \
  --requires-verification known_result_and_duplicate_search \
  --as agent:<name> --json
```

Note the `vpr_...` in the result. Without `--requires-verification`, the Check
can still be recorded, with `--property known_result_and_duplicate_search` named
explicitly or with `--complementary`, but it does not become an acceptance
requirement.

## Perform and record the Check

Run the exact queries the manifest names, write the search log in the shape its
`required_output` block requires, and retain the log as a tracked repository
file. The method manifest and the log must both be tracked, clean, and present
in the current Git commit before recording — `vela verification record` binds
the manifest bytes as `method.environment_root` and the log bytes as a
content-addressed output Artifact.

```bash
git add -- evidence/current/<claim>-known-result-search.v1.json
git commit -m "Retain known-result search log"

vela verification record . <vpr_id> \
  --profile coh-00-known-result-and-duplicate-search-v1 \
  --method methods/current/known-result-and-duplicate-search.v1.json \
  --property known_result_and_duplicate_search \
  --outcome pass \
  --output evidence/current/<claim>-known-result-search.v1.json \
  --independent-of agent:<producer> \
  --does-not-establish "Novelty. A search that finds no covering prior result is bounded by its declared terms, sources, and observation time, and does not establish that the Claim is new." \
  --does-not-establish "Authority. A found prior result is evidence; only an authorized, attributed Repository Decision changes Standing." \
  --does-not-establish "Standing. A source's own status token — registered, solved, open, retracted, accepted, or withdrawn — is never Vela Standing." \
  --does-not-establish "Mathematical equivalence or priority between the Claim and any locator recorded. Coverage here is the searcher's bounded judgement, not a proof of statement identity." \
  --does-not-establish "Correctness of the Claim, or of any prior result found." \
  --does-not-establish "Provider-independent, durable, or reproducible results. Every source may change, restrict access, or disappear after the recorded observation time." \
  --does-not-establish "Scientific acceptance, a Decision, or Standing." \
  --as verifier:<name> --json
```

`--outcome fail` when the search found a prior result covering the Claim,
`inconclusive` when an applicable source was unavailable or rights-restricted
such that the declared scope was not reached, `error` when the search could not
be run as declared.

Repeat every nonclaim in the manifest's `does_not_establish` block on the
command line. This shape is `vela.verification-method.v1`, which Core does not
type-check, so nothing copies those nonclaims into the Record for you; a Record
that drops one is a Record that claims more than the method allows.

`--method` and `--output` are resolved against the process working directory,
so run this from inside the repository.

## When the search finds a duplicate

A `fail` outcome is evidence. It changes what the reviewer knows and it appears
as an acceptance blocker on the Proposal. It is not a rejection, it does not
withdraw the Proposal, and it changes nothing about Standing. Nothing happens
automatically.

What it motivates is a corrected Submission that names the prior result and
narrows the assertion to what remains:

```bash
vela submit --repo . \
  --claim "<narrowed assertion citing the prior result>" \
  --type <claim-type> --replayability <class> \
  --artifact evidence/current/<packet>.json:<kind> \
  --caveat "<limit>" \
  --corrects <full accepted vcl_ id> --target-root sha256:<full root> \
  --as agent:<name> --json
```

Use `--supersedes` instead when the prior result replaces rather than corrects
the accepted Claim. Both bind one full accepted Claim ID and its full root, and
neither decides the Proposal.

If the covering result arrived after the Claim was accepted, the correction is
still a Submission. An authorized operator then makes the exact Decision on the
successor through `vela review accept|reject`; the Check does not.

The reverse direction has the same boundary. A `pass` outcome is bounded by its
declared terms, sources, and observation time. It is not a novelty certificate,
and an accepted Claim carrying a passing search remains open to a later
correction when a source that was silent at the observation time is not silent
later.

## Rehearsal

The Check was rehearsed end to end in a disposable repository on 2026-08-19
against the manifest bytes retained here
(`sha256:42e00706140c3079282a0b04fe9e352d5be740235533e5a2527f96be189850a0`). The
rehearsal searched the declared sources for a claim about Wallace's question,
found two covering prior results — arXiv `2608.17317v1` and Palomar entry
`PALOMAR-2026-08-19-000004` — and recorded outcome `fail`. The failing Check
registered as an acceptance blocker on the Proposal and changed no Standing.
That repository was disposable and is not retained.
