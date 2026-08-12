# Stock Buzz external-workbench execution

This evidence freezes one same-experimenter run of the unmodified Buzz source at
commit `397796c5f343db4251198f44505b1afebe88223f` (tree
`aa2867f523032a0b87bfc8c70b152d6e117c9696`). The stock locked release build,
relay, administration binary, CLI, migrations, and selected stock Compose
services executed locally. The experiment operator authored the target packet,
scientific decomposition, and result. Two ephemeral Buzz activity identities
then created and read a channel, established owner/member membership, and used
stock Buzz to transport, store, and read those exact bytes through three native
signed channel messages with a root/reply chain. Buzz performed no scientific
reasoning, proof construction, or result evaluation.

The retained aggregate evidence root is
`sha256:0271f0d9d385b2c834ccf461a8e004165ad579e6b12f2ab2f2f44e824e68f625`.
It binds:

- exact canonical Git directory/worktree, clean source commit/tree, absence of
  sparse/skip-worktree/assume-unchanged/shallow/partial/promisor/alternate/
  replacement state, and mode/type/blob equality for all 3,862 tracked entries
  used by the build, including the exact Apache-2.0 license, `Cargo.lock`,
  Rust-toolchain, and Compose blobs;
- exact `buzz`, `buzz-relay`, and `buzz-admin` release-binary roots;
- Docker, Rust, Cargo, Bun, Python, OS/architecture, and resolved container
  image identifiers/digests;
- an allowlisted 34-command exit/stdout/stderr root ledger;
- channel metadata, membership, accepted write receipts, normalized CLI
  readback, and full signed database event readback;
- a cross-implementation pinned `nostr-tools@2.23.12` signature verifier, its
  Bun lock, and its exact three-event result;
- before/after proof that the disposable Buzz containers, network, and volumes
  are absent; every Compose call used the verified tracked file and fixed
  `vela-stock-buzz-proof` project with ambient `COMPOSE_*` stripped; and
  `.vela`, `records`, `methods`, and `continuity` did not change.

The raw relay log stayed inside the disposable external build directory; its
mode, size, and root are bound while the file itself is removed before success.
Three ephemeral private keys were passed only through the stock Buzz child
process environments. The harness scanned the complete raw relay log for all
three values before hashing and removal; no key was serialized or retained. No
participant, evaluator, private-build, or Repository-authority input was used.
The same experimenter operated both activity identities, no candidate artifact
was produced, and `authority_effect` is `none`. Therefore the result proves
stock Buzz can transport, store, and read back this operator-authored
Vela-shaped packet and result; it does **not** establish Buzz scientific
reasoning, independent adoption, a Vela Submission, Verification,
Decision, Event, Standing, scientific implication, or scientific equivalence.

Verify the frozen evidence offline:

```bash
python3 -B evidence/erdos-321/workbench-compatibility/verify.py \
  --expected-root sha256:0271f0d9d385b2c834ccf461a8e004165ad579e6b12f2ab2f2f44e824e68f625
python3 -B evidence/erdos-321/workbench-compatibility/test_verify.py
cd evidence/erdos-321/workbench-compatibility
bun install --frozen-lockfile
bun run verify-nostr.mjs
```

With an ordinary full checkout of the exact Buzz commit, run the source-custody
and cleanup-ownership hostile tests too:

```bash
python3 -B evidence/erdos-321/workbench-compatibility/test_run.py \
  --buzz-repo /absolute/path/to/exact/buzz-checkout
```

`run.py` is the frozen operator harness. It requires an ordinary, full, clean,
canonical checkout of the exact Buzz commit, refuses sparse/index-flag/shallow/
partial/promisor/alternate/replacement object state, compares every tracked
worktree entry used by the build to its exact pinned-tree type/mode/blob,
and requires an empty Buzz Docker inventory. It
rebuilds and executes the experiment, replaces the runtime-dependent evidence
files, and destroys only the disposable Compose resources started by that run
before success. Rerunning
changes activity identifiers/timestamps and therefore requires review and a new
aggregate evidence root; it is not part of ordinary CI.
