# Vela Result Runner

One maintained execution path for source-native Result candidates. It runs
Codex from a genuine, clean Git checkout, retains bounded structured output,
verifies that source bytes did not change, and records the exact output through
Native Git and JSON/SQLite graph routes.

The runner is execution software, not a scientific authority. It cannot accept
a Vela Proposal or change Standing. With `--disposable-vela`, it initializes a
new disposable Repository, records Submission and Verification, and always
rejects the qualification-only Proposal before strict replay. It never acts on
the source Repository or an existing authority.

```bash
python3 tools/result_runner/runner.py \
  --repo /absolute/path/to/clean/repository \
  --prompt /absolute/path/to/prompt.txt \
  --schema /absolute/path/to/output.schema.json \
  --output /absolute/new/output-directory \
  --image sha256:... \
  --auth /absolute/path/to/auth.json
```

The Docker context must be `desktop-linux`. Source and OAuth mounts are
read-only; Codex runs at `/repo`; the ephemeral container root and `/output`
remain writable. The output directory must not already exist.

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

The live reference qualification is commit
`5f993c5bafe834828c50bca60830e7bc8488d340`: one provider request completed
from `/repo` in ten seconds and the exact 86 output bytes traversed Native,
Graph, and disposable Vela routes without changing source bytes or Standing.
