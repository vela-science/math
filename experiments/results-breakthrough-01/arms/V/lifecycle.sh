#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: lifecycle.sh prepare COMMON_PACKET SESSION_DIR VELA_BIN | finalize VERDICT_JSON SESSION_DIR VELA_BIN" >&2
  exit 64
fi
phase=$1
shift
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
runner="$script_dir/scripts/run-json-command.sh"

load_authority() {
  local key=$1
  eval "$(ssh-agent -s)" >/dev/null
  ssh-add "$key" >/dev/null
  trap 'ssh-agent -k >/dev/null 2>&1 || true' EXIT
  git config --global user.name 'RESULTS-BREAKTHROUGH-01 disposable authority'
  git config --global user.email 'results-breakthrough-01@invalid.local'
}

if [[ "$phase" == prepare ]]; then
  [[ $# -eq 3 ]] || exit 64
  packet=$1 session=$2 vela_bin=$3
  repo="$session/repo"
  receipts="$session/organization-only/pre-verdict/receipts"
  blind="$session/blind-bundle"
  key="$session/private/authority-key"
  mkdir -p "$repo" "$receipts" "$blind" "$(dirname "$key")"
  cp "$packet/result.json" "$blind/result.json"
  if [[ -d "$packet/artifacts" ]]; then cp -R "$packet/artifacts" "$blind/artifacts"; fi
  if [[ -d "$packet/commands" ]]; then cp -R "$packet/commands" "$blind/commands"; fi
  cp "$blind/result.json" "$repo/result.json"
  if [[ -d "$blind/artifacts" ]]; then cp -R "$blind/artifacts" "$repo/artifacts"; fi
  if [[ -d "$blind/commands" ]]; then cp -R "$blind/commands" "$repo/commands"; fi

  ssh-keygen -q -t ed25519 -N '' -f "$key"
  chmod 0600 "$key"
  load_authority "$key"
  "$runner" "$receipts/init" "$repo" "$vela_bin" init . \
    --name "RESULTS-BREAKTHROUGH-01 disposable session" \
    --scope "Record one bounded experiment cell without canonical authority effect" --json
  git -C "$repo" add -- result.json
  if [[ -d "$repo/artifacts" ]]; then git -C "$repo" add -- artifacts; fi
  if [[ -d "$repo/commands" ]]; then git -C "$repo" add -- commands; fi
  git -C "$repo" commit -q -m 'Retain candidate result and supporting evidence'

  claim=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposed_result"])' "$packet/result.json")
  claim_type=$(python3 - "$packet/result.json" <<'PY'
import json, sys
status = json.load(open(sys.argv[1]))["result_status"]
print("computational" if status == "computational_certificate" else "theoretical")
PY
)
  artifact_args=(--artifact result.json:result-packet)
  while IFS= read -r path; do
    rel=${path#"$repo/"}
    artifact_args+=(--artifact "$rel:supporting-evidence")
  done < <(find "$repo/artifacts" "$repo/commands" -type f 2>/dev/null | LC_ALL=C sort)
  "$runner" "$receipts/submit" "$repo" "$vela_bin" submit --repo . \
    --claim "$claim" --type "$claim_type" --replayability exact \
    "${artifact_args[@]}" \
    --caveat "Experiment-local candidate; no truth, source-owner acceptance, or canonical Standing" \
    --requires-verification "Frozen blinded source-native adjudication" \
    --source-run "RESULTS-BREAKTHROUGH-01" --as agent:result-producer --json
  python3 - "$receipts/submit.stdout" "$session/proposal-id.txt" <<'PY'
import json, pathlib, sys
value = json.load(open(sys.argv[1]))
for key in ("proposal_id", "vpr_id", "id"):
    if isinstance(value, dict) and isinstance(value.get(key), str) and value[key].startswith("vpr_"):
        pathlib.Path(sys.argv[2]).write_text(value[key] + "\n"); raise SystemExit(0)
raise SystemExit("proposal id absent")
PY
  exit 0
fi

if [[ "$phase" == finalize ]]; then
  [[ $# -eq 3 ]] || exit 64
  verdict=$1 session=$2 vela_bin=$3
  repo="$session/repo"
  receipts="$session/organization-only/post-verdict/receipts"
  key="$session/private/authority-key"
  proposal=$(tr -d '\n' < "$session/proposal-id.txt")
  mkdir -p "$receipts" "$repo/methods" "$repo/evidence"
  load_authority "$key"
  cp "$verdict" "$repo/evidence/blinded-verdict.json"
  python3 - "$repo/methods/blinded-review.json" <<'PY'
import pathlib, sys
pathlib.Path(sys.argv[1]).write_text('{"schema":"vela.review-method.v1","reviewer":{"kind":"agent","display_name":"RESULTS-BREAKTHROUGH-01 blinded adjudicator","provider":"OpenAI","version":"frozen-stage-1","attesting_actor":"verifier:blinded-evaluator"},"environment":{"inputs_are_exact_bytes":true,"network_required":false,"shared_dependencies":["frozen source and fact pack"]}}\n')
PY
  git -C "$repo" add -- methods/blinded-review.json evidence/blinded-verdict.json
  git -C "$repo" commit -q -m 'Retain locked blinded evaluation evidence and method'
  verdict_name=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verdict"])' "$verdict")
  case "$verdict_name" in qualified_result|valid_non_result) outcome=pass ;; needs_correction) outcome=inconclusive ;; *) outcome=fail ;; esac
  "$runner" "$receipts/verification" "$repo" "$vela_bin" verification record . "$proposal" \
    --profile blinded-source-native --method methods/blinded-review.json \
    --outcome "$outcome" --does-not-establish "Canonical truth or source-owner acceptance" \
    --output evidence/blinded-verdict.json --as verifier:blinded-evaluator --json
  "$runner" "$receipts/inbox" "$repo" "$vela_bin" review inbox . --json
  entry_root=$(python3 - "$receipts/inbox.stdout" "$proposal" <<'PY'
import json, sys
value = json.load(open(sys.argv[1])); proposal = sys.argv[2]
def walk(v):
    if isinstance(v, dict):
        if proposal in v.values():
            for key in ("entry_root", "root"):
                if isinstance(v.get(key), str) and v[key].startswith("sha256:"):
                    print(v[key]); raise SystemExit(0)
        for child in v.values(): walk(child)
    elif isinstance(v, list):
        for child in v: walk(child)
walk(value); raise SystemExit("entry root absent")
PY
)
  if [[ "$verdict_name" == qualified_result || "$verdict_name" == valid_non_result ]]; then decision=accept; else decision=reject; fi
  "$runner" "$receipts/decision" "$repo" "$vela_bin" review "$decision" . "$proposal" \
    --if-entry-root "$entry_root" --reason "Apply frozen blinded pilot verdict: $verdict_name" \
    --as agent:experiment-owner --session-ref RESULTS-BREAKTHROUGH-01 --json
  "$runner" "$receipts/show" "$repo" "$vela_bin" review show . "$proposal" --json
  "$runner" "$receipts/status" "$repo" "$vela_bin" status . --json
  "$runner" "$receipts/replay" "$repo" "$vela_bin" replay . --json
  rm -f "$key" "$key.pub"
  exit 0
fi

echo "unknown phase: $phase" >&2
exit 64
