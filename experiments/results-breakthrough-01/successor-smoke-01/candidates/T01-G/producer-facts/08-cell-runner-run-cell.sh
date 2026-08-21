#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 12 ]]; then
  echo "usage: run-cell.sh CELL ARM TARGET_CARD FACT_PACK ANSWER_SCHEMA WORK_ROOT AUTH_FILE MATH_DIR FC_DIR LEAN_DIR VELA_DIR START_RECEIPT" >&2
  exit 64
fi
cell=$1 arm=$2 card=$3 facts=$4 schema=$5 work_root=$6 auth=$7 math=$8 fc=$9 lean=${10} vela=${11} start_receipt=${12}
if [[ "$work_root" != /* ]]; then
  echo "work root must be an absolute host path: $work_root" >&2
  exit 64
fi
if [[ "$start_receipt" != /* ]]; then
  echo "start receipt must be an absolute host path: $start_receipt" >&2
  exit 64
fi
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
expected_start_receipt="$root/successor-smoke-01/launch/start-receipt.json"
if [[ "$start_receipt" != "$expected_start_receipt" ]]; then
  echo "unexpected start receipt path: $start_receipt" >&2
  exit 64
fi
if [[ -L "$start_receipt" ]] || [[ ! -f "$start_receipt" ]]; then
  echo "start receipt must be a non-symlink regular file: $start_receipt" >&2
  exit 64
fi
repo=$(git -C "$root/../.." rev-parse --show-toplevel)
image=$(python3 - "$start_receipt" "$root" "$root/scripts/run-cell.sh" "$repo" <<'PY'
import hashlib
import json
import pathlib
import re
import subprocess
import sys

receipt_path, root, runner, repo = map(pathlib.Path, sys.argv[1:])

def fail(message):
    raise SystemExit(f"invalid successor start receipt: {message}")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

try:
    value = json.loads(receipt_path.read_text())
except Exception as error:
    fail(f"unreadable JSON: {error}")

if value.get("run_id") != "RESULTS-BREAKTHROUGH-01-SUCCESSOR-SMOKE-01":
    fail("wrong run_id")
if value.get("launch_authorized") is not True:
    fail("launch_authorized must be true")
if value.get("consumable_by_run_cell") is not True:
    fail("consumable_by_run_cell must be true")
if value.get("not_a_launch_receipt") is not False:
    fail("not_a_launch_receipt must be false")
if value.get("candidate_generation_started") is not False:
    fail("candidate_generation_started must be false")
accepted_image = "sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e"
if value.get("accepted_image") != accepted_image or value.get("runtime_image") != accepted_image:
    fail("wrong accepted image")
runner_hash = sha(runner)
if value.get("runner_sha256") != runner_hash:
    fail("wrong runner hash")

reviewed = value.get("reviewed_producer")
if not isinstance(reviewed, dict):
    fail("missing reviewed producer")
commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()
if reviewed.get("commit") != commit or reviewed.get("tree") != tree:
    fail("wrong reviewed producer commit/tree")
review = value.get("independent_launch_review")
if not isinstance(review, dict) or review.get("verdict") != "PASS":
    fail("independent launch review is not PASS")
for field in ("evaluator_commit", "evaluator_tree"):
    if not re.fullmatch(r"[0-9a-f]{40}", str(review.get(field, ""))):
        fail(f"invalid review {field}")
for field in ("report_sha256", "verdict_sha256"):
    if not re.fullmatch(r"[0-9a-f]{64}", str(review.get(field, ""))):
        fail(f"invalid review {field}")

source_receipt_hash = "cbe3b821d9dcfefb5286d23fad64fbc52c2ca3da9e0d00ce3b3ced1b58c71bca"
stage2_aggregate = "d7fd89641e6ca83c21b4b615efedcfce3ff8174b79444a19cf1d08809df56ebd"
if value.get("source_mount_receipt_sha256") != source_receipt_hash:
    fail("wrong source receipt hash")
if value.get("stage2_held_out_aggregate_sha256") != stage2_aggregate:
    fail("wrong Stage2 aggregate")

files = {
    "answer_schema_sha256": root / "launch/inputs/result.schema.json",
    "assignments_sha256": root / "assignments.json",
    "derived_validation_sha256": root / "successor-harness/DERIVED-VALIDATION.json",
    "evaluator_lock_sha256": root / "EVALUATOR-LOCK.json",
    "preregistration_sha256": root / "successor-smoke-01/PREREGISTRATION.json",
    "runtime_parameters_sha256": root / "runtime/parameters.json",
    "sentinel_receipt_sha256": root / "successor-harness/stdin-sentinel/receipt.json",
    "source_lock_sha256": root / "SOURCE-LOCK.json",
    "source_mount_receipt_sha256": root / "launch/source-mount-receipt.json",
    "stage2_commitment_sha256": root / "stage2/COMMITMENT.json",
}
computed = {name: sha(path) for name, path in files.items()}

def aggregate(directory):
    lines = []
    for path in sorted(item for item in directory.iterdir() if item.is_file()):
        lines.append(f"{sha(path)}\t{path.relative_to(root)}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()

computed["fact_packs_aggregate_sha256"] = aggregate(root / "fact-packs")
computed["equivalence_aggregate_sha256"] = aggregate(root / "equivalence")
if value.get("frozen_launch_bindings") != computed:
    fail("wrong frozen launch bindings")
if value.get("preregistration_sha256") != computed["preregistration_sha256"]:
    fail("wrong preregistration hash")
if value.get("source_mount_receipt_sha256") != computed["source_mount_receipt_sha256"]:
    fail("source receipt bytes do not match")
if value.get("stage2_commitment_sha256") != computed["stage2_commitment_sha256"]:
    fail("wrong Stage2 commitment hash")
docker_stdin_segment = b"docker run --rm " + b"-i --name"
if runner.read_bytes().count(docker_stdin_segment) != 1:
    fail("qualified Docker stdin segment missing or duplicated")
print(accepted_image)
PY
)
case "$arm" in N|G|V) ;; *) exit 64 ;; esac
test "$(docker context show)" = desktop-linux
mount_receipt="$root/launch/source-mount-receipt.json"
test -f "$mount_receipt"
test "$(shasum -a 256 "$mount_receipt" | awk '{print $1}')" = cbe3b821d9dcfefb5286d23fad64fbc52c2ca3da9e0d00ce3b3ced1b58c71bca
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
set +e
docker run --rm -i --name "rb01-${cell,,}" \
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
