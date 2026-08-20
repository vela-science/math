#!/usr/bin/env python3
"""Generate a balanced concealed arm map from target IDs and exactly 32 random bytes."""

import argparse
import hashlib
import hmac
import itertools
import json
from pathlib import Path


def keyed(seed: bytes, label: str) -> bytes:
    return hmac.new(seed, label.encode("ascii"), hashlib.sha256).digest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("target_ids", nargs="+")
    args = parser.parse_args()

    seed = args.seed.read_bytes()
    targets = sorted(args.target_ids)
    if len(seed) != 32:
        raise SystemExit("seed must contain exactly 32 bytes")
    if targets != [f"T{i:02d}" for i in range(1, 11)]:
        raise SystemExit("target IDs must be exactly T01 through T10")

    permutations = list(itertools.permutations(("N", "G", "V")))
    complementary_pairs = [
        (permutations[0], permutations[3]),
        (permutations[0], permutations[4]),
        (permutations[1], permutations[2]),
        (permutations[1], permutations[5]),
        (permutations[2], permutations[5]),
        (permutations[3], permutations[4]),
    ]
    if any(any(left == right for left, right in zip(*pair, strict=True)) for pair in complementary_pairs):
        raise SystemExit("internal error: pair table is not position-wise complementary")
    pair_index = int.from_bytes(keyed(seed, "complementary-pair"), "big") % len(
        complementary_pairs
    )
    omitted_pair = set(complementary_pairs[pair_index])
    schedule = permutations + [p for p in permutations if p not in omitted_pair]
    ranked = sorted(
        enumerate(schedule),
        key=lambda item: keyed(seed, f"slot:{item[0]}:{''.join(item[1])}"),
    )

    mapping = {}
    balance = {label: {arm: 0 for arm in ("N", "G", "V")} for label in ("X", "Y", "Z")}
    for target, (_, permutation) in zip(targets, ranked, strict=True):
        target_map = dict(zip(("X", "Y", "Z"), permutation, strict=True))
        mapping[target] = target_map
        for label, arm in target_map.items():
            balance[label][arm] += 1

    if any(sorted(counts.values()) != [3, 3, 4] for counts in balance.values()):
        raise SystemExit("internal error: mapping is not balanced")

    document = {
        "algorithm": "hmac-sha256-balanced-10x3.v1",
        "balance": balance,
        "generated_from_random_bytes": 32,
        "mapping": mapping,
        "pilot_id": "RESULTS-BREAKTHROUGH-01",
        "schema": "results-breakthrough-concealed-arm-map.v1",
        "seed_hex": seed.hex(),
        "smoke_targets": ["T01", "T02"],
    }
    args.output.write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
