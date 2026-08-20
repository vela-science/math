#!/usr/bin/env bash
set -u

if [[ $# -lt 3 ]]; then
  echo "usage: run-json-command.sh RECEIPT_PREFIX WORKDIR COMMAND..." >&2
  exit 64
fi

prefix=$1
workdir=$2
shift 2
mkdir -p "$(dirname "$prefix")"

start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
start_epoch=$(date +%s)
set +e
(cd "$workdir" && "$@") >"${prefix}.stdout" 2>"${prefix}.stderr"
rc=$?
set -e
end_epoch=$(date +%s)
end=$(date -u +%Y-%m-%dT%H:%M:%SZ)

stdout_sha=$(shasum -a 256 "${prefix}.stdout" | awk '{print $1}')
stderr_sha=$(shasum -a 256 "${prefix}.stderr" | awk '{print $1}')
python3 - "$prefix" "$start" "$end" "$((end_epoch - start_epoch))" "$rc" "$stdout_sha" "$stderr_sha" "$@" <<'PY'
import json
import pathlib
import sys

prefix, start, end, elapsed, rc, stdout_sha, stderr_sha, *command = sys.argv[1:]
receipt = {
    "schema": "results-breakthrough-command-receipt.v1",
    "command": command,
    "started_at": start,
    "ended_at": end,
    "elapsed_seconds": int(elapsed),
    "exit_code": int(rc),
    "stdout_sha256": stdout_sha,
    "stderr_sha256": stderr_sha,
}
pathlib.Path(prefix + ".json").write_text(
    json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY

printf 'exit_code=%s\nstdout_sha256=%s\nstderr_sha256=%s\n' "$rc" "$stdout_sha" "$stderr_sha"
exit "$rc"
