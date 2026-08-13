# Erdős 887 current-binding repair result

This directory retains a new execution of the current public `erdos:887` work
offer. It does not overwrite or rebind `erdos-887-pilot-01`. The result carries
the complete `vela.execution-binding.v1` published by the current index and is
rooted to its packet, producer profile, verifier capsule, and result contract.
`target-packet.v1.json` and `work-offer-index.v1.json` retain the exact offer
bytes that were current for this execution. Later Repository writes may advance
the live offer; the result remains verifiable against these retained inputs and
must then be classified as historical rather than silently rebound.

The producer used a fresh detached local checkout of Formal Conjectures commit
`288608562e684a2f3c97ba0ce960a2649a71370b`, applied `repair.patch`, and checked
the repaired file with Lean 4.22.0:

```bash
git apply --check --unidiff-zero repair.patch
git apply --unidiff-zero repair.patch
lake env lean FormalConjectures/ErdosProblems/887.lean
```

The successful target check used a fresh exact source checkout and a local
materialization of the public package source checkouts named by
`lake-manifest.json`. `capture_execution.py` independently reads every package
HEAD, tree, and worktree status and refuses any checkout that already contains
a `.lake/build` directory or registry barrel. Two exact public compiled inputs
are selectively retained: the LeanSearchClient Reservoir barrel and the
ProofWidgets v0.0.68 GitHub release archive. Their URLs, revisions, toolchains,
byte roots, sizes, and canonical normalized acquisition-command metadata are rooted in
`public-cache-snapshot.v1.json`; raw Lake traces are excluded because they embed
runtime-local private paths. HTTP status and final redirect URL were not retained;
the record establishes byte custody, not authenticated HTTP provenance.

Both snapshots are materialized locally using validated Python standard-library
tar extraction. The narrow
`lake --no-cache build +FormalConjectures.Util.ProblemImports:olean` prerequisite
and target check run under `sandbox-exec` with network denied.
This is exact public compiled-cache replay evidence, not a from-source dependency
build or an independent reproduction.

Lean elaborated the repaired source with the four expected `sorry` warnings.
The result remains pending an attributed human semantic review. It creates no
Vela Verification, Decision, Event, or Math Standing, and no upstream action
was taken.

Re-execute from a fresh exact source checkout and an exact local package-source
set. `FC_SOURCE` may be the public repository or a local mirror of it;
`EXACT_PACKAGES` is a directory populated from the public package URLs at the
manifest commits. The capture refuses any package HEAD or dirty-worktree drift:

```bash
SOURCE_CHECKOUT="$(mktemp -d)/formal-conjectures"
git clone --no-checkout "$FC_SOURCE" "$SOURCE_CHECKOUT"
git -C "$SOURCE_CHECKOUT" checkout --detach \
  288608562e684a2f3c97ba0ce960a2649a71370b
mkdir -p "$SOURCE_CHECKOUT/.lake"
ln -s "$EXACT_PACKAGES" "$SOURCE_CHECKOUT/.lake/packages"
python3 -B capture_execution.py --source-checkout "$SOURCE_CHECKOUT"
```

To reconstruct the package source set directly from public origins instead,
run `lake update` in the exact checkout before capture. It must leave
`lake-manifest.json` byte-identical.

Regenerate the derived check/result and verify the frozen bytes:

```bash
python3 -B build_result.py --check --print-roots
python3 -B test_result.py
python3 -B ../../execution/erdos-887-pr-1237-fidelity-repair/verify_binding.py \
  --result result.v1.json
```
