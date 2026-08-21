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
`enum`, `minLength`, `maxLength`, and `pattern` constraints; every other
type or keyword is rejected before inference.

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

The retained qualification is
[`qualification-v1/`](qualification-v1/). Exactly one provider request
completed from `/repo` in 11.622 seconds. Its exact 100 output bytes traversed
deterministic Native and Graph recorders plus a disposable Vela Submission,
failing Verification, rooted rejection Decision, strict status/readback, and
replay. Source bytes and accepted Standing remained unchanged. The earlier
`5f993c5…` qualification is retained only as predecessor evidence; it did not
execute this corrected runner and does not qualify this head.
