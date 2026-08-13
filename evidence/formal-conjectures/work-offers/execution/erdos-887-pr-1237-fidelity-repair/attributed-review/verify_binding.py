#!/usr/bin/env python3
"""Validate the attributed-review work-offer binding and candidate result."""

from __future__ import annotations

from contextlib import contextmanager
import importlib.util
from pathlib import Path
from typing import Iterator


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "verify_binding.py"
SPEC = importlib.util.spec_from_file_location("verify_historical_binding", BASE_PATH)
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

# Preserve the tested helper surface while keeping the historical verifier
# byte-identical for the retained human-specific execution binding.
BindingError = BASE.BindingError
WORK_OFFERS = BASE.WORK_OFFERS
REPO_ROOT = BASE.REPO_ROOT
PACKET = BASE.PACKET
INDEX = BASE.INDEX
canonical = BASE.canonical
load = BASE.load
raw_root = BASE.raw_root
rooted = BASE.rooted
result_artifact_path = BASE.result_artifact_path


@contextmanager
def attributed_contract() -> Iterator[None]:
    original_file = BASE.__file__
    original_here = BASE.HERE
    original_load = BASE.load
    original_packet = BASE.PACKET
    original_index = BASE.INDEX
    BASE.__file__ = str(Path(__file__).resolve())
    BASE.HERE = HERE
    BASE.load = globals()["load"]
    BASE.PACKET = globals()["PACKET"]
    BASE.INDEX = globals()["INDEX"]
    try:
        yield
    finally:
        BASE.__file__ = original_file
        BASE.HERE = original_here
        BASE.load = original_load
        BASE.PACKET = original_packet
        BASE.INDEX = original_index


def verify_binding() -> dict[str, str]:
    with attributed_contract():
        return BASE.verify_binding()


def verify_result(path: Path, binding: dict[str, str]) -> str:
    with attributed_contract():
        return BASE.verify_result(path, binding)


def main() -> int:
    with attributed_contract():
        return BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
