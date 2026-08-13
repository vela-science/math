# Attributed review methods

These canonical `vela.review-method.v1` profiles make the performer behind a
source-fidelity review explicit while keeping the signed Verification Record,
Repository Decision, and Math Standing separate. Human, AI-model,
organization, and deterministic-tool reviewers are peer evidence producers.
Their records are evaluated by exact method, inputs, outputs, independence,
limitations, and provenance rather than by a human-over-AI type hierarchy.

- `statement-fidelity-gpt-5.6-sol.v1.json` is an AI-model review profile. The
  model performs the bounded comparison; `agent:codex-review` attests the
  resulting historical, same-task-lineage Verification Record.
- `statement-fidelity-gpt-5.6-sol-peer.v1.json` is the independently dispatched
  AI-model peer-review profile. It additionally requires task/dependency and
  blinding disclosures; `agent:codex-review-independent` attests the result.
- `statement-fidelity-william-blair.v1.json` is a human review profile. The
  named human performs and attests the bounded comparison.

No method file claims that a review ran. An outcome exists only when a signed
Verification Record binds one of these exact method files and the exact
Proposal inputs.

Separate reviewer records stay separate. A synthesis or judge output is
another attributed review record; it does not erase disagreement and is not a
Repository Decision. Only an authorized Repository Decision can change
Standing.

Validate the profiles without network access:

```bash
python3 -B methods/review-provenance/test_review_methods.py
```

The governing contract is published by Vela at
`schemas/review-method.schema.json`; the Math test holds the source-owning
profiles to the same closed fields, performer rules, and authority nonclaims.
