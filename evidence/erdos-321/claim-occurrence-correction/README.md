# Erdős 321 occurrence correction preparation

This non-authoritative packet prepares MATH-CLAIM-01 without performing a Vela
write. It binds the accepted predecessor, the exact Web resolver bytes, the
canonical problem occurrence, two exact Formal Conjectures occurrences, the
full source commits, the `corrects` relation, and two scoped Verification
Methods.

The two JSON documents are bounded local evidence formats, not new source
schemas, shared Profiles, integration contracts, or Protocol 1 objects. Their
nested Exact References reuse the accepted Core value shape.

The predecessor remains accepted at repository root
`sha256:ae41be4a91265d91967344459fa12583314ec05c5a0ebc74d8b0136195879511`.
No successor Claim, Proposal, Verification Record, Decision, Event, or Standing
exists merely because this directory is committed.

## Check

```bash
python3 -B evidence/erdos-321/claim-occurrence-correction/build.py --check
python3 -B evidence/erdos-321/claim-occurrence-correction/build.py \
  --check --vela-web-repo ../vela-web
python3 -B evidence/erdos-321/claim-occurrence-correction/test_build.py
```

`occurrence-resolution.v1.json` is the selectively retained subject map.
`correction-plan.v1.json` binds the exact static command arguments and leaves
all signature- or transaction-derived identifiers explicitly unavailable.
The deterministic checker refuses rerooted drift, not only stale root strings.
Their content roots are respectively
`sha256:e1bd42900378d2cfff08be12b40e79ee005c8211477f8ce91a652ad06a65c80d`
and
`sha256:f2d8bd26ee37a0fb10679d215586f2cd5eb1abd0d3de7a1fa665315e907e30ca`.

## Authority boundary

The producer and verifier steps are non-authoritative but still write protocol
records, so they are intentionally not executed in this preparation tranche.
The final acceptance step additionally requires the exact live Decision Inbox
entry and the authorized Repository signer. Signer availability is not asserted
or inferred by this packet.

If the authority later accepts the exact correction, replay is expected to
derive the predecessor as `superseded` and the successor as `accepted`. The
Claim relation remains `corrects`; Protocol 1 does not derive a separate
`corrected` Standing.

## Accepted transition

The separately authorized transition was accepted on 2026-08-14 after two
attributed, scoped passing Verifications. The accepted successor is
`vcl_a618b77ab0f6a4b5b186133e37af555a22c6acb71a4746bab0b144b8973668a6`
at root
`sha256:8ea9f7150743ba0919a9d40aa0e632e1171b0a2ecdce20e76d6068e1427a647e`.
Strict replay derives repository root
`sha256:0e24fa1b13d7eda7b4e809564ec414eb1fda09f5dcf9aa8a6bcd6ae69ac96197`.
The predecessor remains retained with its original bytes and accepted-decision
history; the applied `claim.superseded` event retires it from the current
accepted Claim set. The source mapping still has authority effect none, and
the Decision does not establish proof, resolution, equivalence, adoption, or
Standing in any other Repository.
