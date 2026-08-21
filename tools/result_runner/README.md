# Vela Result Runner

One maintained execution path for source-native Result candidates. It runs
Codex from the exact root of a genuine, clean Git checkout, retains bounded
structured output, verifies that source and image identities do not change,
and records one canonical result/provenance payload through Native Git and
JSON/SQLite graph routes.

The runner is execution software, not a scientific authority or proof-editing
engine. Its read-only source mount means it cannot edit or test source changes.
It cannot accept a Vela Proposal or change Standing. With
`--disposable-vela`, it initializes a new disposable Repository, records a
truthful failing Verification, and always makes a rooted rejection Decision
before strict status/readback/replay. It never acts on the source Repository or
an existing authority.

```bash
python3 tools/result_runner/runner.py \
  --repo /absolute/path/to/clean/repository \
  --expected-repository-id https://github.com/owner/repository.git \
  --expected-commit <40-hex-commit> \
  --expected-tree <40-hex-tree> \
  --expected-archive-sha256 <64-hex-archive-digest> \
  --prompt /absolute/path/to/prompt.txt \
  --schema /absolute/path/to/output.schema.json \
  --output /absolute/new/output-directory \
  --image sha256:... \
  --auth /absolute/path/to/auth.json
```

The Docker context must be `desktop-linux`, and `--image` must be its exact
`sha256:<64-hex>` image ID. `--repo` must be an absolute canonical top level
with an in-tree `.git` directory; subdirectories, path aliases, symlinks,
gitfiles, and linked worktrees are rejected. The binding covers clean tracked
Git bytes through repository identity, commit, tree, and `git archive` digest;
ignored bytes are outside that claim and a checkout containing any untracked
bytes is rejected.

Source and OAuth mounts are read-only; Codex runs at `/repo`; the ephemeral
container root and `/output` remain writable. The output directory must not
already exist. Wall time, prompt/schema/result bytes, captured streams, runtime
file count, and runtime bytes have explicit hard ceilings. The supported output
schema subset is a closed object with string properties and only `const`,
`enum`, `minLength`, and `maxLength` constraints; every other type or keyword,
including `pattern`, is rejected before inference. This avoids claiming that a
second Python regular-expression validator is equivalent to the JSON Schema
evaluator inside the pinned container.

Native Git bytes and canonical `graph.json` bytes are reproducible from the
same payload. `sqlite-projection.json` binds the Python implementation/version,
SQLite version/source ID, database byte digest, and a canonical logical-content
root. SQLite byte equality is claimed only under that exact recorded serializer
environment; portable replay checks database integrity and the canonical
logical-content root rather than cross-version database bytes.

Run the focused regression suite with:

```bash
python3 -m unittest discover -s tools/result_runner/tests -v
```

Exercise the signed disposable Vela integration explicitly:

```bash
VELA_TEST_BIN=/absolute/path/to/vela \
VELA_TEST_SHA256=<approved-binary-sha256> \
python3 -m unittest discover -s tools/result_runner/tests -v
```

The active signed Vela pin is `v0.977.4` for macOS arm64, binary SHA-256
`06f912d107d29e4ce1dadd19bf7ef849ec42d7e62cbc9332c9807e6b8c9bd05e`.
Exact tag/source, release-manifest, detached-signature, platform, and repeated
non-scoring lifecycle receipts are retained in
[`qualification-v0.977.4/`](qualification-v0.977.4/). The older Vela 0.977.3
objects under `qualification-v1/` remain historical preimages and are not
rewritten by the active pin.

The retained qualification is
[`qualification-v1/`](qualification-v1/). Exactly one provider request
completed from `/repo` in 11.622 seconds under runner SHA-256 `ef2ce961…3561`.
Its exact 100 output bytes traversed the Native and Graph recorders plus a
disposable Vela Submission, failing Verification, rooted rejection Decision,
strict status/readback, and replay. The four subsequent bounded corrections do
not change that model invocation or its const-only output schema; they are
covered without another provider request by hostile bounds/schema/key tests,
exact retained-output recorder replay, and signed disposable-Vela integration.
The retained SQLite file is an exact historical byte receipt; current replay
treats its logical rows as portable and binds future serializer bytes to their
recorded implementation. Source bytes and accepted Standing remained unchanged.
The earlier
`5f993c5…` qualification is retained only as predecessor evidence; it did not
execute this corrected runner and does not qualify this head.

The prospective Lean-aware campaign layer is documented in
[`next_campaign_v1/`](next_campaign_v1/). It requires an exact pinned
Lean/lake runtime, source-native verification receipts, and one single-use
permit per fixed candidate or evaluator cell. It is not campaign-ready until
its neutral provider canary and an independent exact-runtime review pass; this
patch itself performs no provider inference and changes no scientific state.
