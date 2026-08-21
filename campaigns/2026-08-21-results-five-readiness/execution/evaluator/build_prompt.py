#!/usr/bin/env python3
"""Build the frozen evaluator prompt from locked candidate Result bytes."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
CASES = tuple(f"FIVE-{number:02d}" for number in range(1, 6))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


records = []
archive_parts = [b"RESULTS-FIVE-EVALUATOR-APPENDIX-V1\n"]
for case_id in CASES:
    directory = ROOT / "execution" / "candidates" / case_id
    result = (directory / "result.json").read_bytes()
    receipt = (directory / "receipt.json").read_bytes()
    record = {
        "case_id": case_id,
        "receipt_sha256": sha256(receipt),
        "result_bytes": len(result),
        "result_sha256": sha256(result),
    }
    records.append(record)
    archive_parts.append(
        (
            f"{case_id}\t{len(result)}\t{record['result_sha256']}\t"
            f"{record['receipt_sha256']}\n"
        ).encode()
    )
    archive_parts.append(result)

archive = b"".join(archive_parts)
compressed = gzip.compress(archive, compresslevel=9, mtime=0)
encoded = base64.b64encode(compressed)
template = (ROOT / "evaluator-template.txt").read_bytes()
instructions = b"""
--- LOCKED CANDIDATE APPENDIX ---
The following single-line block is base64 of deterministic gzip bytes. Decode it with Python base64.b64decode and gzip.decompress. The decoded binary stream starts with `RESULTS-FIVE-EVALUATOR-APPENDIX-V1` and then repeats: one UTF-8 tab-separated header line containing case_id, result byte length, result SHA-256, and receipt SHA-256, immediately followed by that many exact raw result.json bytes. Parse all five records and verify every result hash before evaluation. This lossless encoding keeps the frozen evaluator prompt within its 16384-byte cap; do not treat encoding as omission or summarization.
BEGIN_RESULTS_FIVE_GZIP_BASE64
"""
prompt = template + instructions + encoded + b"\nEND_RESULTS_FIVE_GZIP_BASE64\n"
if len(prompt) > 16384:
    raise SystemExit(f"prompt too large: {len(prompt)}")

(pathlib.Path(__file__).parent / "prompt.txt").write_bytes(prompt)
receipt = {
    "archive_bytes": len(archive),
    "archive_sha256": sha256(archive),
    "cases": records,
    "compressed_bytes": len(compressed),
    "compressed_sha256": sha256(compressed),
    "evaluator_template_sha256": sha256(template),
    "format": "results-five-evaluator-prompt-build-v1",
    "prompt_bytes": len(prompt),
    "prompt_sha256": sha256(prompt),
}
(pathlib.Path(__file__).parent / "prompt-build.json").write_text(
    json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
)
