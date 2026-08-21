#!/usr/bin/env bash
set -euo pipefail

readonly expected_image_id='sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e'
readonly expected_codex_sha256='134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477'
readonly expected_vela_sha256='59cc91e9d277d733a8f5b2892653cf5b540778ce26ac794521c63bba0036103b'
readonly expected_machine_id='af94b40fa642620275e6d617be97a542'
readonly expected_machine_id_sha256='70130fcf77290eece0f9df935fe0990d77a98fa3df25219528a0aa2566f7a58c'
readonly expected_source_lock_sha256='7e6b169c25a91332c6bd40714ef3b751b6ae55a261d74f0dd7b7767761b5b64a'
readonly expected_answer_schema_sha256='62f7bbc908dbb9020ea39430307c0c685ee30fce2dee496e54b739e4b5a702b6'

sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

codex_path=$(command -v codex)
vela_path=$(command -v vela)
codex_sha256=$(sha256_file "$codex_path")
vela_sha256=$(sha256_file "$vela_path")
machine_id=$(tr -d '\n' < /etc/machine-id)
machine_id_sha256=$(sha256_file /etc/machine-id)
machine_id_bytes=$(wc -c < /etc/machine-id | tr -d ' ')
source_lock_sha256=$(sha256_file /inputs/SOURCE-LOCK.json)
answer_schema_sha256=$(sha256_file /inputs/result.schema.json)

test "$codex_sha256" = "$expected_codex_sha256"
test "$vela_sha256" = "$expected_vela_sha256"
test "$machine_id" = "$expected_machine_id"
test "$machine_id_sha256" = "$expected_machine_id_sha256"
test "$machine_id_bytes" = 33
test "$source_lock_sha256" = "$expected_source_lock_sha256"
test "$answer_schema_sha256" = "$expected_answer_schema_sha256"
test -s /root/.codex/auth.json

python3 - <<'PY'
import pathlib

mountpoint = "/root/.codex/auth.json"
matches = []
for line in pathlib.Path("/proc/self/mountinfo").read_text().splitlines():
    fields = line.split()
    if len(fields) > 5 and fields[4] == mountpoint:
        matches.append(fields[5].split(","))
assert len(matches) == 1, matches
assert "ro" in matches[0], matches
PY

oauth_status=$(codex login status 2>&1)
test "$oauth_status" = 'Logged in using ChatGPT'

printf 'probe=pass\n'
printf 'accepted_image_id=%s\n' "$expected_image_id"
printf 'codex_path=%s\n' "$codex_path"
printf 'codex_sha256=%s\n' "$codex_sha256"
printf 'vela_path=%s\n' "$vela_path"
printf 'vela_sha256=%s\n' "$vela_sha256"
printf 'machine_id=%s\n' "$machine_id"
printf 'machine_id_sha256=%s\n' "$machine_id_sha256"
printf 'machine_id_bytes=%s\n' "$machine_id_bytes"
printf 'source_lock_sha256=%s\n' "$source_lock_sha256"
printf 'answer_schema_sha256=%s\n' "$answer_schema_sha256"
printf 'oauth_mount=read_only\n'
printf 'oauth_status=%s\n' "$oauth_status"
