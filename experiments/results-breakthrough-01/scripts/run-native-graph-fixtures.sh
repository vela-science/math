#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
image='vela-results-breakthrough-01@sha256:526fdb202378ca02eb5946c75bc4d319751336c0ad88162c671fbe89950d1750'
test "$(docker context show)" = desktop-linux
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

docker run --rm --network none \
  -e GIT_AUTHOR_DATE=2026-08-20T00:00:00Z -e GIT_COMMITTER_DATE=2026-08-20T00:00:00Z \
  --mount "type=bind,src=$root,dst=/experiment,readonly" \
  --mount "type=bind,src=$tmp,dst=/out" \
  --entrypoint /bin/bash "$image" \
  /experiment/arms/N/record.sh /experiment/fixtures/common /out/native
docker run --rm --network none \
  --mount "type=bind,src=$root,dst=/experiment,readonly" \
  --mount "type=bind,src=$tmp,dst=/out" \
  --entrypoint /usr/bin/python3 "$image" \
  /experiment/arms/G/record.py /experiment/fixtures/common /out/graph

python3 - "$root" "$tmp" <<'PY'
import hashlib, json, pathlib, shutil, sys
root, tmp = map(pathlib.Path, sys.argv[1:])
for arm in ("native", "graph"):
    source = tmp / arm
    destination = root / "fixtures" / arm
    if destination.exists(): shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(p for p in source.rglob("*") if p.is_file() and ".git" not in p.parts):
        rel = path.relative_to(source)
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    files = []
    for path in sorted(p for p in destination.rglob("*") if p.is_file()):
        data = path.read_bytes()
        files.append({"path": path.relative_to(destination).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    receipt = {
        "schema": "results-breakthrough-no-model-fixture.v1",
        "arm": "N" if arm == "native" else "G",
        "model_sessions": 0,
        "network": "none",
        "runtime_image": "sha256:526fdb202378ca02eb5946c75bc4d319751336c0ad88162c671fbe89950d1750",
        "common_result_sha256": hashlib.sha256((root / "fixtures/common/result.json").read_bytes()).hexdigest(),
        "files": files,
        "outcome": "pass",
        "scientific_claim": False,
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
PY
