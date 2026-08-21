#!/usr/bin/env bash
set -euo pipefail

base=/qualification
session=$base/routes/V
repo=$session/repo
receipts=$session/receipts
runner=/existing/scripts/run-json-command.sh
vela=/usr/local/bin/vela
key=$session/private/authority-key

test ! -e "$repo"
mkdir -p "$repo" "$receipts" "$(dirname "$key")"
ssh-keygen -q -t ed25519 -N '' -f "$key"
chmod 0600 "$key"
eval "$(ssh-agent -s)" >/dev/null
ssh-add "$key" >/dev/null
trap 'ssh-agent -k >/dev/null 2>&1 || true' EXIT
git config --global user.name 'Runner qualification disposable authority'
git config --global user.email 'runner-qualification@invalid.local'

"$runner" "$receipts/init" "$repo" "$vela" init . \
  --name 'Runner E2E qualification disposable session' \
  --scope 'Record one non-scoring execution fixture without scientific or canonical authority effect' --json

mkdir -p "$repo/methods" "$repo/evidence"
cp "$base/common/result.json" "$repo/result.json"
cp "$base/review-method.json" "$repo/methods/runner-e2e.json"
cp "$base/verification-output.json" "$repo/evidence/verification-output.json"
git -C "$repo" add -- result.json methods/runner-e2e.json evidence/verification-output.json
git -C "$repo" commit -q -m 'Retain non-scoring runner qualification bytes'

"$runner" "$receipts/submit" "$repo" "$vela" submit --repo . \
  --claim 'Non-scoring runner qualification fixture completed; no scientific assertion.' \
  --type theoretical --replayability exact --artifact result.json:qualification-output \
  --caveat 'Disposable runner qualification only; no scientific truth, utility, canonical authority, or Standing.' \
  --requires-verification 'Exact non-scoring qualification output retention' \
  --source-run RUNNER-E2E-QUALIFICATION-2026-08-21 --as agent:runner-qualification --json

python3 - "$receipts/submit.stdout" "$session/proposal-id.txt" <<'PY'
import json, pathlib, sys
value=json.load(open(sys.argv[1]))
for key in ("proposal_id","vpr_id","id"):
    if isinstance(value,dict) and isinstance(value.get(key),str) and value[key].startswith("vpr_"):
        pathlib.Path(sys.argv[2]).write_text(value[key]+"\n"); raise SystemExit(0)
raise SystemExit("proposal id absent")
PY
proposal=$(tr -d '\n' < "$session/proposal-id.txt")

"$runner" "$receipts/verification" "$repo" "$vela" verification record . "$proposal" \
  --profile runner-e2e-qualification --method methods/runner-e2e.json \
  --property 'Exact non-scoring qualification output retention' --outcome pass \
  --does-not-establish 'Any scientific claim, mathematical truth, benchmark result, comparative utility, source-owner approval, canonical authority, or Standing.' \
  --does-not-establish 'Organizational, operator, host, provider, model, or source independence.' \
  --shared-dependency 'Same operator and Docker Desktop host as candidate execution; this is an end-to-end path check, not an independence claim.' \
  --output evidence/verification-output.json --as verifier:runner-qualification --json

"$runner" "$receipts/inbox" "$repo" "$vela" review inbox . --json
entry_root=$(python3 - "$receipts/inbox.stdout" "$proposal" <<'PY'
import json, sys
value=json.load(open(sys.argv[1])); proposal=sys.argv[2]
def walk(item):
    if isinstance(item,dict):
        if proposal in item.values():
            for key in ("entry_root","root"):
                if isinstance(item.get(key),str) and item[key].startswith("sha256:"):
                    print(item[key]); raise SystemExit(0)
        for child in item.values(): walk(child)
    elif isinstance(item,list):
        for child in item: walk(child)
walk(value); raise SystemExit("entry root absent")
PY
)

"$runner" "$receipts/decision" "$repo" "$vela" review reject . "$proposal" \
  --if-entry-root "$entry_root" \
  --reason 'Qualification fixture only; rejection prevents any scientific or Standing interpretation.' \
  --as agent:qualification-owner --session-ref RUNNER-E2E-QUALIFICATION-2026-08-21 --json
"$runner" "$receipts/show" "$repo" "$vela" review show . "$proposal" --json
"$runner" "$receipts/status" "$repo" "$vela" status . --json
"$runner" "$receipts/replay" "$repo" "$vela" replay . --json

test -f "$key"
rm -f "$key" "$key.pub"
test ! -e "$key"
test ! -e "$key.pub"
