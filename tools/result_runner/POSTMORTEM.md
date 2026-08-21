# Runner postmortem

`RESULTS-BREAKTHROUGH-01` closed with zero scientific evidence because its
runner was frozen before the real end-to-end candidate entrypoint worked. The
full append-only incident history remains on commit
`38b8d91b5f1cc6451ab96ca023d23aaddcbf7c2a`; it is historical evidence, not a
template for future campaigns.

## Keep

- Exact source commit/tree and clean before/after checks.
- Read-only source and OAuth mounts.
- Bounded structured output and exact command receipts.
- Clear separation between producer evidence, Verification, and Decision.
- Disposable Vela lifecycle qualification with no scientific Standing.

## Change

- Qualify the exact complete command before assigning a scientific denominator.
- Maintain one runner implementation independently of experiment inputs.
- Generate committed-evidence manifests from Git; generate runtime receipts
  only from explicit files.
- Treat ordinary setup failures as retained operational incidents that can be
  corrected once, not as reasons to redesign the experiment.
- Use canonical Vela schemas and actionable container preflight diagnostics.

## Delete

- Copied per-cell runner scripts and duplicated fact roots.
- Repeated no-model gates that do not execute the real candidate command.
- Self-referential seals, hand-written evidence inventories, and review cycles
  whose only purpose is validating other review machinery.
- Any artifact unused by execution, adjudication, or replay.

The successor qualification at commit
`5f993c5bafe834828c50bca60830e7bc8488d340` proved the corrected path: one
provider request completed from `/repo` in ten seconds, exact output traversed
Native, Graph, and disposable Vela routes, and source bytes remained unchanged.
