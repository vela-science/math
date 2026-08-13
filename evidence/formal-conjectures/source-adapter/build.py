#!/usr/bin/env python3
"""Build or check the exact FC source-local Math projection."""

from __future__ import annotations

import argparse
from pathlib import Path

from adapter import PROJECTION_PATH, SOURCE, build_projection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-root", action="store_true")
    args = parser.parse_args()
    projection = build_projection()
    raw = SOURCE.canonical_bytes(projection) + b"\n"
    if args.check:
        if not PROJECTION_PATH.is_file() or PROJECTION_PATH.read_bytes() != raw:
            raise SystemExit("projection.v1.json does not match exact retained inputs")
    else:
        Path(PROJECTION_PATH).write_bytes(raw)
    if args.print_root:
        print(projection["root"]["value"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
