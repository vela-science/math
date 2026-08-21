#!/usr/bin/env bash
set -euo pipefail

experiment_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
source_runner="$experiment_root/scripts/run-cell.sh"
scratch=$(mktemp -d)
scratch=$(cd "$scratch" && pwd -P)
trap 'rm -rf "$scratch"' EXIT
repo="$scratch/repo"
copy_root="$repo/experiments/results-breakthrough-01"
mkdir -p "$repo/experiments"
cp -R "$experiment_root" "$copy_root"
git -C "$repo" init -q
git -C "$repo" config user.name "RESULTS-BREAKTHROUGH-01 validator"
git -C "$repo" config user.email "validator@invalid.local"
git -C "$repo" add -- experiments
GIT_AUTHOR_DATE=2000-01-01T00:00:00Z GIT_COMMITTER_DATE=2000-01-01T00:00:00Z \
  git -C "$repo" commit -qm fixture

runner="$copy_root/scripts/run-cell.sh"
expected="$copy_root/successor-smoke-01/launch/start-receipt.json"
base="$scratch/base-receipt.json"
runner_sha=$(shasum -a 256 "$runner" | awk '{print $1}')
script_sha=$(shasum -a 256 "${BASH_SOURCE[0]}" | awk '{print $1}')

python3 - "$copy_root" "$repo" "$runner_sha" "$base" <<'PY'
import hashlib, json, pathlib, subprocess, sys
root, repo, runner_sha, output = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], pathlib.Path(sys.argv[4])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def aggregate(directory):
    lines = [f"{sha(path)}\t{path.relative_to(root)}\n" for path in sorted(item for item in directory.iterdir() if item.is_file())]
    return hashlib.sha256("".join(lines).encode()).hexdigest()
bindings = {
    "answer_schema_sha256": sha(root / "launch/inputs/result.schema.json"),
    "assignments_sha256": sha(root / "assignments.json"),
    "derived_validation_sha256": sha(root / "successor-harness/DERIVED-VALIDATION.json"),
    "evaluator_lock_sha256": sha(root / "EVALUATOR-LOCK.json"),
    "preregistration_sha256": sha(root / "successor-smoke-01/PREREGISTRATION.json"),
    "runtime_parameters_sha256": sha(root / "runtime/parameters.json"),
    "sentinel_receipt_sha256": sha(root / "successor-harness/stdin-sentinel/receipt.json"),
    "source_lock_sha256": sha(root / "SOURCE-LOCK.json"),
    "source_mount_receipt_sha256": sha(root / "launch/source-mount-receipt.json"),
    "stage2_commitment_sha256": sha(root / "stage2/COMMITMENT.json"),
    "fact_packs_aggregate_sha256": aggregate(root / "fact-packs"),
    "equivalence_aggregate_sha256": aggregate(root / "equivalence"),
}
value = {
    "accepted_image": "sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e",
    "runtime_image": "sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e",
    "run_id": "RESULTS-BREAKTHROUGH-01-SUCCESSOR-SMOKE-01",
    "launch_authorized": True,
    "consumable_by_run_cell": True,
    "not_a_launch_receipt": False,
    "candidate_generation_started": False,
    "runner_sha256": runner_sha,
    "reviewed_producer": {
        "commit": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "tree": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip(),
    },
    "independent_launch_review": {
        "verdict": "PASS",
        "evaluator_commit": "1" * 40,
        "evaluator_tree": "2" * 40,
        "report_sha256": "3" * 64,
        "verdict_sha256": "4" * 64,
    },
    "source_mount_receipt_sha256": "cbe3b821d9dcfefb5286d23fad64fbc52c2ca3da9e0d00ce3b3ced1b58c71bca",
    "stage2_held_out_aggregate_sha256": "d7fd89641e6ca83c21b4b615efedcfce3ff8174b79444a19cf1d08809df56ebd",
    "stage2_commitment_sha256": bindings["stage2_commitment_sha256"],
    "preregistration_sha256": bindings["preregistration_sha256"],
    "frozen_launch_bindings": bindings,
}
output.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
PY

fakebin="$scratch/fakebin"
mkdir -p "$fakebin"
printf '%s\n' '#!/usr/bin/env bash' ': > "$DOCKER_MARKER"' 'exit 99' > "$fakebin/docker"
chmod +x "$fakebin/docker"
results="$scratch/results.tsv"
: > "$results"

write_case() {
  local mutation=$1
  rm -rf "$expected"
  mkdir -p "$(dirname "$expected")"
  cp "$base" "$expected"
  python3 - "$expected" "$mutation" <<'PY'
import json, pathlib, sys
path, mutation = pathlib.Path(sys.argv[1]), sys.argv[2]
value = json.loads(path.read_text())
if mutation == "wrong_run_id": value["run_id"] = "RESULTS-BREAKTHROUGH-01"
elif mutation == "launch_authorized_false": value["launch_authorized"] = False
elif mutation == "consumable_false": value["consumable_by_run_cell"] = False
elif mutation == "not_a_launch_receipt_true": value["not_a_launch_receipt"] = True
elif mutation == "wrong_image": value["accepted_image"] = "sha256:" + "0" * 64
elif mutation == "wrong_runner_hash": value["runner_sha256"] = "0" * 64
elif mutation == "wrong_reviewed_identity": value["reviewed_producer"]["commit"] = "0" * 40
elif mutation == "review_not_pass": value["independent_launch_review"]["verdict"] = "BLOCKED"
elif mutation == "wrong_source_hash": value["source_mount_receipt_sha256"] = "0" * 64
elif mutation == "wrong_stage2_aggregate": value["stage2_held_out_aggregate_sha256"] = "0" * 64
elif mutation == "wrong_frozen_bindings": value["frozen_launch_bindings"]["assignments_sha256"] = "0" * 64
elif mutation == "wrong_preregistration_hash": value["preregistration_sha256"] = "0" * 64
else: raise SystemExit(f"unknown mutation: {mutation}")
path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
PY
}

run_case() {
  local name=$1 expected_rc=$2 expected_text=$3 receipt=$4 arg_mode=${5:-full}
  local work="$scratch/work-$name" stdout="$scratch/$name.stdout" stderr="$scratch/$name.stderr" marker="$scratch/$name.docker"
  rm -rf "$work" "$marker"
  set +e
  if [[ "$arg_mode" == missing ]]; then
    DOCKER_MARKER="$marker" PATH="$fakebin:$PATH" "$runner" T01-N N /card /facts /schema "$work" /auth /math /fc /lean /vela >"$stdout" 2>"$stderr"
  else
    DOCKER_MARKER="$marker" PATH="$fakebin:$PATH" "$runner" T01-N N /card /facts /schema "$work" /auth /math /fc /lean /vela "$receipt" >"$stdout" 2>"$stderr"
  fi
  rc=$?
  set -e
  if [[ $rc -ne $expected_rc ]] || ! grep -F "$expected_text" "$stderr" >/dev/null || [[ -e "$work" ]] || [[ -e "$marker" ]]; then
    echo "negative check failed: $name rc=$rc expected_rc=$expected_rc" >&2
    sed 's/^/stderr: /' "$stderr" >&2
    exit 1
  fi
  normalized=$(python3 - "$stderr" "$scratch" <<'PY'
import pathlib, sys
print(pathlib.Path(sys.argv[1]).read_text().replace(sys.argv[2], "<TMP>").rstrip("\n"))
PY
)
  normalized_sha=$(printf '%s\n' "$normalized" | shasum -a 256 | awk '{print $1}')
  printf '%s\t%s\t%s\t%s\n' "$name" "$rc" "$normalized_sha" "$normalized" >> "$results"
}

run_case missing_arg 64 "usage: run-cell.sh" unused missing
run_case relative_path 64 "start receipt must be an absolute host path" relative.json
run_case predecessor_path 64 "unexpected start receipt path" "$copy_root/launch/start-receipt.json"
run_case unexpected_path 64 "unexpected start receipt path" "$scratch/unexpected.json"
rm -rf "$expected"; ln -s "$base" "$expected"
run_case symlink_receipt 64 "start receipt must be a non-symlink regular file" "$expected"
rm -rf "$expected"; mkdir -p "$expected"
run_case nonregular_receipt 64 "start receipt must be a non-symlink regular file" "$expected"

for mutation in wrong_run_id launch_authorized_false consumable_false not_a_launch_receipt_true wrong_image wrong_runner_hash wrong_reviewed_identity review_not_pass wrong_source_hash wrong_stage2_aggregate wrong_frozen_bindings wrong_preregistration_hash; do
  write_case "$mutation"
  case "$mutation" in
    wrong_run_id) message="wrong run_id" ;;
    launch_authorized_false) message="launch_authorized must be true" ;;
    consumable_false) message="consumable_by_run_cell must be true" ;;
    not_a_launch_receipt_true) message="not_a_launch_receipt must be false" ;;
    wrong_image) message="wrong accepted image" ;;
    wrong_runner_hash) message="wrong runner hash" ;;
    wrong_reviewed_identity) message="wrong reviewed producer commit/tree" ;;
    review_not_pass) message="independent launch review is not PASS" ;;
    wrong_source_hash) message="wrong source receipt hash" ;;
    wrong_stage2_aggregate) message="wrong Stage2 aggregate" ;;
    wrong_frozen_bindings) message="wrong frozen launch bindings" ;;
    wrong_preregistration_hash) message="wrong preregistration hash" ;;
  esac
  run_case "$mutation" 1 "$message" "$expected"
done

python3 - "$results" "$runner_sha" "$script_sha" <<'PY'
import json, pathlib, sys
rows=[]
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    name, exit_code, stderr_sha256, stderr = line.split("\t", 3)
    rows.append({"case": name, "docker_invoked": False, "exit_code": int(exit_code), "normalized_stderr": stderr, "normalized_stderr_sha256": stderr_sha256, "state_created": False})
print(json.dumps({"case_count": len(rows), "cases": rows, "docker_or_model_execution": False, "outcome": "pass", "runner_sha256": sys.argv[2], "validator_sha256": sys.argv[3]}, sort_keys=True, separators=(",", ":")))
PY
