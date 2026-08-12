# External-workbench return boundary

This directory is the source-owned receiving boundary for a future, separately
operated workbench response to the rooted Erdős 321 target packet. It does not
contain an external observation and does not authorize an operator, publish
private Mathematics source, or change a Vela Submission, Verification,
Decision, Event, or Standing.

`return-contract.v0.1.json` binds the existing target packet's canonical root
and raw SHA-256, the exact result and operator-attestation fields, bounded
input sizes, required nonclaims, and the receipt semantics. A candidate return
must carry at least one artifact root and an activity event. The operator must
attest that a separately controlled workbench was used without Repository
authority credentials or scientific Decision authority.

`verify_return.py` reads the returned result and operator attestation as strict,
bounded, no-symlink inputs. It emits a rooted receipt that classifies a returned
candidate only as `unverified_candidate`. The tool validates byte custody,
schema, roots, and required nonclaims. It cannot establish that the attesting
operator is independent, that an artifact is scientifically correct, that the
work has been adopted, or that a human accepts it. Those facts require separate
attributed evidence and ordinary Vela review.

An external operator needs authorized access to the exact private Mathematics
source named by the target packet or a separately reviewed, rights-safe source
handoff. This directory does not widen source rights and must not be used to
redistribute the reference-only Star Fleet theorem bytes.

Capture a returned result without promoting it:

```bash
python3 -B evidence/erdos-321/external-workbench-return/verify_return.py \
  --result /private/intake/workbench-result.json \
  --operator-attestation /private/intake/operator-attestation.json \
  --received-at 2026-08-20T12:01:00Z \
  --custodian custodian:vela \
  > /private/custody/external-workbench-receipt.json
```

The result must use `vela.workbench-result.v1`; the attestation must use
`vela.external-workbench-operator-attestation.v1`. Their exact required fields
and required nonclaims are in the rooted contract. Run the hostile tests with:

```bash
python3 -B evidence/erdos-321/external-workbench-return/test_verify_return.py
```
