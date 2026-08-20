# Stage 2 held-out freeze

This directory contains only encrypted held-out material, its public
commitment, the content-independent permutation generator, and deterministic
validation. Plaintext check cards and the duplicate index remain outside the
Math producer workspace under the evaluator custodian; the concealed arm map
and its key remain under a separate neutral-custodian boundary.

The scientific evaluator receives the evaluator key only. The `X/Y/Z` mapping
key is withheld until all first-pass verdicts and correction notices are
locked. Candidate sessions receive neither key and the frozen runner does not
mount this directory.

Validate public bytes from the repository root:

```bash
python3 experiments/results-breakthrough-01/stage2/scripts/validate-stage2.py
```

The independent Stage 2 reviewer may additionally validate decrypted bytes by
supplying the two external key paths and the frozen check-card schema:

```bash
python3 experiments/results-breakthrough-01/stage2/scripts/validate-stage2.py \
  --evaluator-key /absolute/evaluator-key \
  --custodian-key /absolute/custodian-key \
  --check-card-schema /absolute/check-card.schema.json
```

Passing this freeze does not authorize inference. It supplies only the
commitment required for a separate exact launch review.
