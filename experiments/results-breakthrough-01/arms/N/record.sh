#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then echo "usage: record.sh COMMON_PACKET OUTPUT_DIR" >&2; exit 64; fi
input=$1 output=$2 blind="$2/blind-bundle" repo="$2/organization-only/native-repo"
test -f "$input/result.json"
mkdir -p "$blind" "$repo"
cp "$input/result.json" "$blind/result.json"
if [[ -d "$input/artifacts" ]]; then cp -R "$input/artifacts" "$blind/artifacts"; fi
if [[ -d "$input/commands" ]]; then cp -R "$input/commands" "$blind/commands"; fi
cp "$blind/result.json" "$repo/result.json"
if [[ -d "$blind/artifacts" ]]; then cp -R "$blind/artifacts" "$repo/artifacts"; fi
if [[ -d "$blind/commands" ]]; then cp -R "$blind/commands" "$repo/commands"; fi
git -C "$repo" init -q -b main
git -C "$repo" config user.name 'RESULTS-BREAKTHROUGH-01 native fixture'
git -C "$repo" config user.email 'results-breakthrough-01@invalid.local'
git -C "$repo" add -- result.json
if [[ -d "$repo/artifacts" ]]; then git -C "$repo" add -- artifacts; fi
if [[ -d "$repo/commands" ]]; then git -C "$repo" add -- commands; fi
git -C "$repo" commit -q -m 'Retain source-native result packet'
mkdir -p "$output/organization-only"
git -C "$repo" rev-parse HEAD > "$output/organization-only/git-commit.txt"
git -C "$repo" rev-parse 'HEAD^{tree}' > "$output/organization-only/git-tree.txt"
