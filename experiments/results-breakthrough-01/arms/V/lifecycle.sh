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
review_method_source="$script_dir/arms/V/blinded-review-method.json"
review_method_schema="$script_dir/arms/V/review-method.schema.json"
review_method_validator="$script_dir/scripts/validate-review-method.py"
review_method_schema_commit=88fcc0105eba35ee22ed1816d3aabba3322bebc1
review_method_schema_git_blob=36a185fb5dc4b3dbcb5365825383dfe449dd3ad9
review_method_schema_sha256=0b202272637dc5dc0219822116f87488f95c4993230654c5544d35c8a49bbe31
verification_profile=blinded-source-native
verification_property='Frozen blinded source-native adjudication'
verification_actor=verifier:blinded-evaluator
verification_nonclaims=(
  'Canonical mathematical truth, scientific acceptance, source-owner approval, or Standing.'
  'Organizational, provider, model, operator, host, or source independence.'
)
verification_independent_of=(agent:result-producer)
verification_shared_dependencies=(
  'Same OpenAI provider and GPT-5.6 Sol model family as candidate production.'
  'Same experiment owner, Docker Desktop host, frozen source mounts, producer fact pack, answer schema, and campaign-local repository.'
)

case "$phase" in
  prepare)
    [[ $# -eq 3 ]] || exit 64
    packet=$1 session=$2 vela_bin=$3
    ;;
  finalize)
    [[ $# -eq 3 ]] || exit 64
    verdict=$1 session=$2 vela_bin=$3
    ;;
  *)
    echo "unknown phase: $phase" >&2
    exit 64
    ;;
esac

validate_review_method() {
  local method=$1 receipt_prefix=$2 rc
  local args=(
    --schema "$review_method_schema"
    --schema-source-commit "$review_method_schema_commit"
    --schema-git-blob "$review_method_schema_git_blob"
    --schema-sha256 "$review_method_schema_sha256"
    --method "$method"
    --expected-profile "$verification_profile"
    --expected-property "$verification_property"
    --expected-actor "$verification_actor"
    --expected-reviewer-kind ai_model
    --expected-reviewer-identifier gpt-5.6-sol
    --expected-reviewer-provider OpenAI
  )
  local nonclaim
  for nonclaim in "${verification_nonclaims[@]}"; do
    args+=(--expected-nonclaim "$nonclaim")
  done
  local actor dependency
  for actor in "${verification_independent_of[@]}"; do
    args+=(--declared-independent-of "$actor")
  done
  for dependency in "${verification_shared_dependencies[@]}"; do
    args+=(--shared-dependency "$dependency")
  done
  mkdir -p "$(dirname "$receipt_prefix")"
  set +e
  python3 "$review_method_validator" "${args[@]}" \
    > "$receipt_prefix.stdout" 2> "$receipt_prefix.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$receipt_prefix.exit-code.txt"
  {
    shasum -a 256 "$receipt_prefix.stdout"
    shasum -a 256 "$receipt_prefix.stderr"
  } > "$receipt_prefix.sha256"
  [[ $rc -eq 0 ]] || return "$rc"
}

# The frozen schema, canonical bytes, and CLI cross-bindings fail closed before
# either prepare or finalize can invoke Vela.
validate_review_method "$review_method_source" \
  "$session/organization-only/preflight/review-method-$phase"

load_authority() {
  local key=$1
  eval "$(ssh-agent -s)" >/dev/null
  ssh-add "$key" >/dev/null
  trap 'ssh-agent -k >/dev/null 2>&1 || true' EXIT
  git config --global user.name 'RESULTS-BREAKTHROUGH-01 disposable authority'
  git config --global user.email 'results-breakthrough-01@invalid.local'
}

if [[ "$phase" == prepare ]]; then
  repo="$session/repo"
  receipts="$session/organization-only/pre-verdict/receipts"
  blind="$session/blind-bundle"
  key="$session/private/authority-key"
  mkdir -p "$repo" "$receipts" "$blind" "$(dirname "$key")"
  cp "$packet/result.json" "$blind/result.json"
  if [[ -d "$packet/artifacts" ]]; then cp -R "$packet/artifacts" "$blind/artifacts"; fi
  if [[ -d "$packet/commands" ]]; then cp -R "$packet/commands" "$blind/commands"; fi

  ssh-keygen -q -t ed25519 -N '' -f "$key"
  chmod 0600 "$key"
  load_authority "$key"
  "$runner" "$receipts/init" "$repo" "$vela_bin" init . \
    --name "RESULTS-BREAKTHROUGH-01 disposable session" \
    --scope "Record one bounded experiment cell without canonical authority effect" --json
  cp "$blind/result.json" "$repo/result.json"
  if [[ -d "$blind/artifacts" ]]; then cp -R "$blind/artifacts" "$repo/artifacts"; fi
  if [[ -d "$blind/commands" ]]; then cp -R "$blind/commands" "$repo/commands"; fi
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
  repo="$session/repo"
  receipts="$session/organization-only/post-verdict/receipts"
  key="$session/private/authority-key"
  proposal=$(tr -d '\n' < "$session/proposal-id.txt")
  mkdir -p "$receipts" "$repo/methods" "$repo/evidence"
  load_authority "$key"
  cp "$verdict" "$repo/evidence/blinded-verdict.json"
  cp "$review_method_source" "$repo/methods/blinded-review.json"
  validate_review_method "$repo/methods/blinded-review.json" \
    "$session/organization-only/pre-verdict/retained-review-method"
  git -C "$repo" add -- methods/blinded-review.json evidence/blinded-verdict.json
  git -C "$repo" commit -q -m 'Retain locked blinded evaluation evidence and method'
  verdict_name=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verdict"])' "$verdict")
  case "$verdict_name" in qualified_result|valid_non_result) outcome=pass ;; needs_correction) outcome=inconclusive ;; *) outcome=fail ;; esac
  verification_args=(
    --profile "$verification_profile"
    --method methods/blinded-review.json
    --property "$verification_property"
    --outcome "$outcome"
  )
  for nonclaim in "${verification_nonclaims[@]}"; do
    verification_args+=(--does-not-establish "$nonclaim")
  done
  for actor in "${verification_independent_of[@]}"; do
    verification_args+=(--independent-of "$actor")
  done
  for dependency in "${verification_shared_dependencies[@]}"; do
    verification_args+=(--shared-dependency "$dependency")
  done
  verification_args+=(
    --output evidence/blinded-verdict.json
    --as "$verification_actor"
    --json
  )
  "$runner" "$receipts/verification" "$repo" "$vela_bin" verification record . "$proposal" \
    "${verification_args[@]}"
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
