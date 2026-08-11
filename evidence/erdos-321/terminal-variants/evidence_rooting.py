"""Small RFC-8785-compatible rooting subset shared by the evidence tools."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any


class BuildError(RuntimeError):
    """Stable fail-closed evidence error."""


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def jcs(value: Any) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise BuildError("integer exceeds interoperable JSON range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BuildError("non-finite JSON number")
        raise BuildError("comparison documents do not admit floats")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(value, list):
        return b"[" + b",".join(jcs(item) for item in value) + b"]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise BuildError("JSON object keys must be strings")
        parts = []
        for key in sorted(value, key=lambda item: item.encode("utf-16-be", errors="surrogatepass")):
            parts.append(jcs(key) + b":" + jcs(value[key]))
        return b"{" + b",".join(parts) + b"}"
    raise BuildError(f"unsupported JSON value: {type(value)!r}")


def rendered(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


CONTENT_ROOT_DEFINITION = "sha256 of RFC-8785 JSON after removing only content_root"


def rooted(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    if "content_root" in result:
        raise BuildError("content root must be derived")
    result["content_root_definition"] = CONTENT_ROOT_DEFINITION
    result["content_root"] = f"sha256:{sha256_hex(jcs(result))}"
    return result
