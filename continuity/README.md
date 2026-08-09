# Protocol continuity

This directory retains non-canonical, machine-readable inventories at protocol
generation boundaries. Git history remains the exact source of the predecessor
records and signatures.

`v0.971.0-predecessor.json` anchors the last replay-verified Vela 0.971.0 state
before the repository moves to the current Vela protocol waist. It records the
exact Git commit and tree, repository and authority roots, counts, accepted
Claim, and Decision roots. A consumer can check out that commit and replay it
with the named Vela release.

The accompanying recovery package contains
`math-v0.971.0-predecessor.bundle` and its detached SSH signature. Verify them
without a hosting provider:

```bash
ssh-keygen -Y verify -f continuity/allowed_signers -I bundle@vela.space \
  -n vela-bundle -s continuity/math-v0.971.0-predecessor.bundle.sig \
  < continuity/math-v0.971.0-predecessor.bundle
git bundle verify continuity/math-v0.971.0-predecessor.bundle
```

The inventory does not import or confer Standing. Re-genesis creates a new
repository identity and authority history. Any continuing scientific assertion
must enter the new generation through a fresh authenticated Submission, scoped
Verification, and an authorized human Decision.
