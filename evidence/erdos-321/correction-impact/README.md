# Erdős 321 correction impact

This package describes one historical correction already reviewed by the Math
Repository's human authority. It does not create or replay that Decision.

The record binds the rejected predecessor, the corrected accepted successor,
their Verifications and Decision events, four exact replay states, and a bounded
relation slice. Every relation in the slice is marked affected, unaffected,
unresolved, incomplete-basis, or out-of-scope. The open terminal-variant repair
obligation remains non-authoritative and undecided.

Build and verify it offline from the retained Git history:

```bash
python3 evidence/erdos-321/correction-impact/build.py --check
python3 evidence/erdos-321/correction-impact/test_build.py
python3 evidence/erdos-321/correction-impact/cold_reader.py --verify
```

`correction-impact.v1.json` is a source-local package with
`authority_effect: none`. It is not a Claim, Verification, Decision, Event, or
Standing transition.

`cold-reader-result.v1.json` records one matched internal rehearsal using two
ephemeral, context-free Codex CLI sessions. It is agent usability evidence, not
a human-participant result or independent validation. Both arms answered all
eight scored items correctly; the treatment used more time and input tokens.
`cold-reader-evaluation.v1.json` therefore retains the interface source-locally
and does not claim comprehension or efficiency lift.
