# Attributed review methods

These canonical `vela.review-method.v1` profiles make the performer behind a
source-fidelity review explicit while keeping the signed Verification Record,
human Decision, and Math Standing separate.

- `statement-fidelity-gpt-5.6-sol.v1.json` is an AI-model review profile. The
  model performs the bounded comparison; `agent:codex-review` attests the
  resulting Verification Record.
- `statement-fidelity-william-blair.v1.json` is a human review profile. The
  named human performs and attests the bounded comparison.

Neither file claims that a review ran. An outcome exists only when a signed
Verification Record binds one of these exact method files and the exact
Proposal inputs.

Validate the profiles without network access:

```bash
python3 -B methods/review-provenance/test_review_methods.py
```

The governing contract is published by Vela at
`schemas/review-method.schema.json`; the Math test holds the source-owning
profiles to the same closed fields, performer rules, and authority nonclaims.
