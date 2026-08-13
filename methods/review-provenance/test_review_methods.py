#!/usr/bin/env python3
"""Offline contract checks for peer attributed review methods."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = sorted(ROOT.glob("statement-fidelity-*.v1.json"))
REPORTS = sorted(
    (ROOT.parents[1] / "evidence/formal-conjectures/reviews").glob(
        "*-statement-fidelity.v1.json"
    )
)
FIELDS = {
    "schema",
    "profile",
    "property",
    "question",
    "reviewer",
    "attested_by_actor_id",
    "procedure",
    "required_output",
    "does_not_establish",
}
REVIEWER_FIELDS = {"kind", "display_name", "identifier", "provider", "version"}


def load_strict(path: Path) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in items:
            if key in value:
                raise AssertionError(f"{path}: duplicate key {key}")
            value[key] = item
        return value

    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=pairs)
    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    assert raw == canonical + b"\n", f"{path}: method must be canonical JSON plus one LF"
    return value


def text(value: object, label: str) -> str:
    assert isinstance(value, str) and value and value == value.strip(), label
    return value


def main() -> None:
    assert len(FILES) >= 3, "expected human and multiple AI peer profiles"
    methods = [load_strict(path) for path in FILES]
    kinds: set[str] = set()
    for path, method in zip(FILES, methods, strict=True):
        assert set(method) == FIELDS, f"{path}: closed top-level fields"
        assert method["schema"] == "vela.review-method.v1"
        for field in ("profile", "property", "question", "attested_by_actor_id"):
            text(method[field], f"{path}: {field}")
        assert method["property"] == "statement_fidelity"
        reviewer = method["reviewer"]
        assert isinstance(reviewer, dict) and set(reviewer) == REVIEWER_FIELDS
        kind = text(reviewer["kind"], f"{path}: reviewer.kind")
        assert kind in {"human", "ai_model", "organization", "deterministic_tool"}
        kinds.add(kind)
        text(reviewer["display_name"], f"{path}: reviewer.display_name")
        text(reviewer["identifier"], f"{path}: reviewer.identifier")
        if kind == "ai_model":
            text(reviewer["provider"], f"{path}: AI provider")
            assert method["attested_by_actor_id"].startswith("agent:")
        if kind == "human":
            assert reviewer["provider"] is None and reviewer["version"] is None
            assert reviewer["identifier"] == method["attested_by_actor_id"]
            assert method["attested_by_actor_id"].startswith("human:")
        for field in ("procedure", "required_output", "does_not_establish"):
            values = method[field]
            assert isinstance(values, list) and values, f"{path}: {field}"
            for value in values:
                text(value, f"{path}: {field}")
        nonclaims = " ".join(method["does_not_establish"])
        assert "does not accept" in nonclaims
        assert "Standing" in nonclaims
    assert kinds == {"ai_model", "human"}
    assert REPORTS, "expected at least one retained attributed review"
    for report_path in REPORTS:
        report = load_strict(report_path)
        assert report["schema"] == "vela.math.attributed-review-report.v1"
        assert report["authority_effect"] == "none"
        assert report["outcome"] in {"pass", "fail", "inconclusive", "error"}
        assert report["reviewer"]["kind"] in {
            "human", "ai_model", "organization", "deterministic_tool"
        }
        assert report["findings"] and isinstance(report["findings"], list)
        assert isinstance(report["unsupported_clauses"], list)
        assert isinstance(report["ambiguous_clauses"], list)
        assert report["out_of_scope"] and isinstance(report["out_of_scope"], list)
        method_path = ROOT.parents[1] / report["method"]["path"]
        observed_method_root = "sha256:" + hashlib.sha256(method_path.read_bytes()).hexdigest()
        assert report["method"]["root"] == observed_method_root
        method = load_strict(method_path)
        assert report["does_not_establish"] == method["does_not_establish"]
        assert report["reviewer"]["kind"] == method["reviewer"]["kind"]
        assert report["reviewer"]["identifier"] == method["reviewer"]["identifier"]
        assert report["reviewer"]["attested_by_actor_id"] == method["attested_by_actor_id"]
        for root in (
            report["subject"]["proposal_root"],
            report["inputs"]["formal_conjectures"]["content_root"],
            report["inputs"]["repair"]["raw_sha256"],
            report["inputs"]["repair"]["repaired_content_root"],
            report["inputs"]["execution_result"]["root"],
            report["inputs"]["execution_result"]["check_result_root"],
            report["inputs"]["execution_result"]["packet_root"],
        ):
            assert isinstance(root, str) and root.startswith("sha256:") and len(root) == 71
    print(f"review provenance methods: {len(methods)}; reports: {len(REPORTS)} pass")


if __name__ == "__main__":
    main()
