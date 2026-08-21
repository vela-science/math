#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re

PATTERNS = {
    "private_key": re.compile(rb"BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY"),
    "bearer": re.compile(rb"Authorization\s*:\s*Bearer\s+\S+", re.I),
    "oauth_token": re.compile(rb'"(?:access_token|refresh_token)"\s*:\s*"[^\"]+"', re.I),
    "github_token": re.compile(rb"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument("--receipt", required=True, type=pathlib.Path)
    args = parser.parse_args()
    findings = []
    scanned = 0
    for path in sorted(p for p in args.root.rglob("*") if p.is_file()):
        data = path.read_bytes()
        scanned += 1
        for name, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append({
                    "path": str(path.relative_to(args.root)),
                    "pattern": name,
                    "file_sha256": hashlib.sha256(data).hexdigest(),
                })
    receipt = {
        "schema": "results-breakthrough-secret-scan.v1",
        "root": str(args.root),
        "files_scanned": scanned,
        "findings": findings,
        "outcome": "pass" if not findings else "quarantine",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
