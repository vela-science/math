# Vela Mathematics

Which mathematical assertions has this authority admitted on exact, reproducible evidence, and what remains unresolved?

This is a Vela repository. Git stores exact Claims, Submissions, Verification Records, Decisions, and authority history. Derived views are rebuildable.

## Operator loop

```bash
vela status . --json
vela claims . --json
vela submit --repo . --claim "<bounded result>" --type computational --replayability exact --artifact <path>:<kind> --caveat "<limit>" --as agent:<name> --json

# Verification binds method bytes already retained at the current Git commit.
git add -- verification/method.json
git commit -m "Retain verification method"
vela verification record . <vpr_id> --profile <profile> --method verification/method.json --outcome pass --does-not-establish "Scientific acceptance." --as verifier:<name> --json

vela review inbox . --json
# Only an authorized operator may make the exact accept or reject Decision.
vela review accept . <vpr_id> --reason "<reason>" --if-entry-root sha256:... --json
vela replay . --json
```

## Source-local experiments

- [Erdős 321 translation](evidence/erdos-321/translation/README.md) retains exact
  Lean source snapshots and derives W3C Web Annotations, a rooted semantic fact
  diff, an explicit loss report, and a Workflow Run RO-Crate. It is
  non-canonical evidence and has no authority effect.
- [Erdős 321 terminal-variant comparison](evidence/erdos-321/terminal-variants/README.md)
  roots the pinned terminal theorem, proof environment, rights boundary, and a
  bounded comparison with the retained fixed variants. It is non-canonical
  evidence, preregisters an unrun cold-reader measurement, and has no authority
  effect. Generated bundle root:
  `sha256:bd7b7eee6eb5e2e8f654898207bf05168ea6e7dd1d72f3a1a46a685a64f8f322`.
- [Buzz external-workbench compatibility](evidence/erdos-321/workbench-compatibility/README.md)
  freezes an exact-source locked build and native CLI/relay execution at Buzz
  commit `397796c5f343db4251198f44505b1afebe88223f`, including channel/member
  readback, three cross-implementation signature checks, exact runtime roots,
  and complete disposable teardown. The scientific packet, decomposition, and
  result were authored by the experiment operator; Buzz transported, stored,
  and read back the bytes and performed no scientific reasoning. Aggregate evidence root:
  `sha256:0271f0d9d385b2c834ccf461a8e004165ad579e6b12f2ab2f2f44e824e68f625`.
  Both identities were operated by the same experimenter, so this is execution
  compatibility evidence, not independent adoption or scientific authority.
- [External-workbench return boundary](evidence/erdos-321/external-workbench-return/README.md)
  strictly retains a future separately operated result as an unverified,
  non-authoritative receipt. Schema conformance does not establish operator
  independence, scientific correctness, adoption, or human acceptance.

## Protocol continuity

- [Vela 0.971.0 predecessor inventory](continuity/v0.971.0-predecessor.json)
  anchors the last replay-verified prior-generation state. The inventory is
  provenance, not Standing; current assertions still require the full operator
  loop in the new generation.
