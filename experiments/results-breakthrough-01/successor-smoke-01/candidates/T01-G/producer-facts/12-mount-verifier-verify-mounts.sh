#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then echo "usage: verify-mounts.sh RECEIPT MATH FC LEAN_PROOFS VELA" >&2; exit 64; fi
receipt=$1 math=$2 fc=$3 lean=$4 vela=$5
verify_repo() {
  local name=$1 repo=$2 commit=$3 tree=$4 archive=$5
  test "$(git -C "$repo" rev-parse HEAD)" = "$commit"
  test "$(git -C "$repo" rev-parse HEAD^{tree})" = "$tree"
  test "$(git -C "$repo" rev-parse --is-shallow-repository)" = false
  test -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all)"
  test "$(git -C "$repo" archive --format=tar HEAD | shasum -a 256 | awk '{print $1}')" = "$archive"
  printf '%s\t%s\t%s\t%s\n' "$name" "$commit" "$tree" "$archive"
}
tmp=$(mktemp)
{
  verify_repo math "$math" 5de716c896065c03c0a470d015ba2a328a527f73 56e37a5058c80e69f3c343b8ae624c08b5417229 f3b983aba2ea5c8056b82e039204ec973246fe7f7c66a7b250b238a9fe4e6779
  verify_repo formal_conjectures "$fc" e13dd7284e72012a1616806d09cb6b8025e387af 7d2b7c17ff144393c2b4a39973ed212387b3e783 6a929b14796348e84badc6972524640688d98eac40fbbc91eadd0d744f39d647
  verify_repo lean_proofs "$lean" accf62cb636c8909dd7e098e3f82b2140d3a192e 608ce332d1d5d8f14abc7d39349f4a29102f5aba b28285a85b08e472cc5183c4dfeebaea821127f0c65baa3a4eb865daf5ed6ee9
  verify_repo vela "$vela" 88fcc0105eba35ee22ed1816d3aabba3322bebc1 2cb85fe1e1c3525ba97ff2aec25945417ea7b372 05a87f07789e0c8d77d85665c25504712cd70bea328b2c0f9e7ce57dc5b01c24
} > "$tmp"
python3 - "$tmp" "$receipt" <<'PY'
import json,pathlib,sys
records=[]
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    name,commit,tree,archive=line.split("\t"); records.append({"name":name,"commit":commit,"tree":tree,"git_archive_tar_sha256":archive})
pathlib.Path(sys.argv[2]).write_text(json.dumps({"schema":"results-breakthrough-mount-receipt.v1","outcome":"pass","repositories":records},sort_keys=True,separators=(",",":"))+"\n")
PY
