#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 11 ]]; then
  echo "usage: run-cell.sh CELL ARM TARGET_CARD FACT_PACK ANSWER_SCHEMA WORK_ROOT AUTH_FILE MATH_DIR FC_DIR LEAN_DIR VELA_DIR" >&2
  exit 64
fi
cell=$1 arm=$2 card=$3 facts=$4 schema=$5 work_root=$6 auth=$7 math=$8 fc=$9 lean=${10} vela=${11}
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
case "$arm" in N|G|V) ;; *) exit 64 ;; esac
test "$(docker context show)" = desktop-linux
test -f "$root/launch/start-receipt.json"
python3 - "$root/launch/start-receipt.json" <<'PY'
import json, sys
v=json.load(open(sys.argv[1]))
assert v["candidate_generation_started"] is False
assert len(v["stage2_held_out_aggregate_sha256"]) == 64
assert v["independent_launch_review"] == "PASS"
assert len(v["source_mount_receipt_sha256"]) == 64
PY
mount_receipt="$root/launch/source-mount-receipt.json"
test -f "$mount_receipt"
expected_mount_receipt=$(python3 -c 'import json; print(json.load(open("'"$root"'/launch/start-receipt.json"))["source_mount_receipt_sha256"])')
test "$(shasum -a 256 "$mount_receipt" | awk '{print $1}')" = "$expected_mount_receipt"
verify_checkout() {
  local repo=$1 commit=$2 tree=$3
  test "$(git -C "$repo" rev-parse HEAD)" = "$commit"
  test "$(git -C "$repo" rev-parse HEAD^{tree})" = "$tree"
  test "$(git -C "$repo" rev-parse --is-shallow-repository)" = false
  test -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all)"
}
verify_checkout "$math" 5de716c896065c03c0a470d015ba2a328a527f73 56e37a5058c80e69f3c343b8ae624c08b5417229
verify_checkout "$fc" e13dd7284e72012a1616806d09cb6b8025e387af 7d2b7c17ff144393c2b4a39973ed212387b3e783
verify_checkout "$lean" accf62cb636c8909dd7e098e3f82b2140d3a192e 608ce332d1d5d8f14abc7d39349f4a29102f5aba
verify_checkout "$vela" 88fcc0105eba35ee22ed1816d3aabba3322bebc1 2cb85fe1e1c3525ba97ff2aec25945417ea7b372
test "$(shasum -a 256 "$schema" | awk '{print $1}')" = 62f7bbc908dbb9020ea39430307c0c685ee30fce2dee496e54b739e4b5a702b6
session="$work_root/$cell"
test ! -e "$session"
mkdir -p "$session/work" "$session/receipts"
python3 "$root/scripts/materialize-facts.py" --experiment-root "$root" --fact-pack "$facts" --output "$session/producer-facts"
python3 - "$root/prompts/common-objective.txt" "$card" "$root/prompts/arm-$arm.txt" "$session/prompt.txt" <<'PY'
import pathlib, sys
common, card, arm, output = map(pathlib.Path, sys.argv[1:])
output.write_bytes(common.read_bytes() + b"\n<producer_target_card>\n" + card.read_bytes() + b"</producer_target_card>\n<organization_only>\n" + arm.read_bytes() + b"</organization_only>\n")
PY
image=$(python3 -c 'import json; print(json.load(open("'"$root"'/launch/start-receipt.json"))["runtime_image"])')
set +e
docker run --rm --name "rb01-${cell,,}" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=1g \
  --mount "type=bind,src=$session/work,dst=/work" \
  --mount "type=bind,src=$math,dst=/inputs/math,readonly" \
  --mount "type=bind,src=$fc,dst=/inputs/fc,readonly" \
  --mount "type=bind,src=$lean,dst=/inputs/lean-proofs,readonly" \
  --mount "type=bind,src=$vela,dst=/inputs/vela,readonly" \
  --mount "type=bind,src=$card,dst=/inputs/target-card.json,readonly" \
  --mount "type=bind,src=$facts,dst=/inputs/fact-pack.json,readonly" \
  --mount "type=bind,src=$session/producer-facts,dst=/inputs/producer-facts,readonly" \
  --mount "type=bind,src=$schema,dst=/inputs/result.schema.json,readonly" \
  --mount "type=bind,src=$auth,dst=/root/.codex/auth.json,readonly" \
  --entrypoint /bin/bash "$image" -lc \
  'timeout 720 codex exec --ephemeral --ignore-user-config --ignore-rules -m gpt-5.6-sol -c model_reasoning_effort="high" -c service_tier="default" -s danger-full-access -C /work --output-schema /inputs/result.schema.json --json -o /work/result.json -' \
  < "$session/prompt.txt" > "$session/receipts/codex.stdout" 2> "$session/receipts/codex.stderr"
rc=$?
set -e
printf '%s\n' "$rc" > "$session/receipts/exit-code.txt"
python3 "$root/scripts/secret-scan.py" "$session" --receipt "$session/receipts/secret-scan.json"
if [[ -f "$session/work/result.json" ]] && [[ $(wc -c < "$session/work/result.json") -gt 8192 ]]; then
  echo 'result.json exceeds frozen 8192-byte scientific output allowance' > "$session/receipts/output-budget.stderr"
  exit 65
fi
exit "$rc"
