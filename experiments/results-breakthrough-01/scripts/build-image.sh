#!/usr/bin/env bash
set -euo pipefail

usage() { echo "usage: build-image.sh --approval-receipt FILE --vela-repo DIR" >&2; exit 64; }
approval=
vela_repo=
while [[ $# -gt 0 ]]; do
  case "$1" in
    --approval-receipt) approval=$2; shift 2 ;;
    --vela-repo) vela_repo=$2; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$approval" && -n "$vela_repo" ]] || usage

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python3 - "$approval" <<'PY'
import json, sys
value = json.load(open(sys.argv[1]))
required = value.get("authorizations", {})
if value.get("verdict") != "PASS" or required.get("image_rebuild") is not True or required.get("no_model_vela_fixture") is not True:
    raise SystemExit("independent receipt does not authorize the bounded rebuild and fixture")
PY
test "$(docker context show)" = desktop-linux
test "$(git -C "$vela_repo" rev-parse 88fcc0105eba35ee22ed1816d3aabba3322bebc1^{tree})" = 2cb85fe1e1c3525ba97ff2aec25945417ea7b372
python3 "$root/scripts/verify-vela-context.py" \
  --vela-repo "$vela_repo" \
  --commit 88fcc0105eba35ee22ed1816d3aabba3322bebc1 \
  --manifest "$root/build/vela-context.tsv"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git -C "$vela_repo" archive 88fcc0105eba35ee22ed1816d3aabba3322bebc1 | tar -x -C "$tmp"
docker build --pull=false --no-cache \
  --file "$root/Dockerfile" \
  --tag vela-results-breakthrough-01:approved-machine-id \
  "$tmp"
docker image inspect vela-results-breakthrough-01:approved-machine-id --format '{{.Id}}'
