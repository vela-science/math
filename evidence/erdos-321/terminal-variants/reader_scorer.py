#!/usr/bin/env python3
"""Pure deterministic scorer for rooted terminal-variant reader responses."""

from __future__ import annotations

from typing import Any


class ScoreError(ValueError):
    """The response or scoring key is outside the frozen contract."""


RESPONSE_FIELDS = {
    "authority_classification",
    "confidence_percent",
    "material_difference_rows",
    "next_proof_obligation_classification",
    "next_proof_obligation_evidence_locators",
    "quantity_classification",
    "quantity_evidence_locators",
    "relation_lower",
    "relation_lower_evidence_locators",
    "relation_upper",
    "relation_upper_evidence_locators",
    "source_identity_tokens",
}

EXPECTED_KEY = {
    "authority_classification": "none",
    "deterministic_total_points": 11,
    "material_difference_evidence": {
        "constants": ["span_03", "span_06", "span_07"],
        "depth_selection": ["span_01", "span_04", "span_06", "span_07"],
        "logarithm_domain": ["span_02", "span_06", "span_07"],
        "quantifier_conditions": ["span_04", "span_06", "span_07"],
    },
    "material_difference_metric": "cued classification with exact per-dimension evidence locators; not unaided recall",
    "next_proof_obligation_classification": "kernel_checked_real_nat_log_bridge_before_implication",
    "next_proof_obligation_evidence": ["span_01", "span_02", "span_06", "span_07"],
    "quantity_classification": "same_extremal_quantity_under_inherited_correspondence",
    "quantity_evidence": ["span_08"],
    "relation_lower": "neither_established",
    "relation_lower_evidence": ["span_04", "span_06"],
    "relation_upper": "neither_established",
    "relation_upper_evidence": ["span_04", "span_07"],
    "source_identity_tokens": ["terminal_source", "fixed_source"],
}


def exact_strings(value: Any) -> set[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ScoreError("nonempty string array required")
    result = set(value)
    if len(result) != len(value):
        raise ScoreError("duplicate array member")
    return result


def score_response(
    response: dict[str, Any], instrument: dict[str, Any], participant_packet: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(response, dict) or set(response) != RESPONSE_FIELDS:
        raise ScoreError("response field set drift")
    confidence = response["confidence_percent"]
    if not isinstance(confidence, int) or isinstance(confidence, bool) or not 0 <= confidence <= 100:
        raise ScoreError("confidence must be an integer from 0 through 100")
    if instrument.get("scoring_key") != EXPECTED_KEY:
        raise ScoreError("scoring key drift")
    key = EXPECTED_KEY
    schema = participant_packet.get("response_schema")
    if not isinstance(schema, dict):
        raise ScoreError("participant response schema drift")
    enum_fields = (
        "authority_classification", "next_proof_obligation_classification",
        "quantity_classification", "relation_lower", "relation_upper",
    )
    if any(response[field] not in schema[field] for field in enum_fields):
        raise ScoreError("response enum drift")
    allowed_locators = set(participant_packet["evidence_locator_catalog"])
    locator_fields = (
        "next_proof_obligation_evidence_locators", "quantity_evidence_locators",
        "relation_lower_evidence_locators", "relation_upper_evidence_locators",
    )
    if any(not exact_strings(response[field]) <= allowed_locators for field in locator_fields):
        raise ScoreError("response evidence locator drift")
    source_tokens = exact_strings(response["source_identity_tokens"])
    if not source_tokens <= set(schema["source_identity_tokens"]):
        raise ScoreError("source identity token drift")
    rows = response["material_difference_rows"]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ScoreError("material difference rows required")
    material: dict[str, dict[str, Any]] = {}
    for row in rows:
        if set(row) != {"classification_token", "evidence_locators", "explanation"}:
            raise ScoreError("material difference row field drift")
        token = row["classification_token"]
        if token not in schema["material_difference_rows"]["classification_token"] or token in material:
            raise ScoreError("material difference token drift")
        if not isinstance(row["explanation"], str) or not row["explanation"].strip():
            raise ScoreError("material difference explanation required")
        if not exact_strings(row["evidence_locators"]) <= allowed_locators:
            raise ScoreError("material difference evidence locator drift")
        material[token] = row
    material_exact = set(material) == set(key["material_difference_evidence"])
    source_exact = source_tokens <= set(key["source_identity_tokens"])
    components = {
        "quantity": int(response["quantity_classification"] == key["quantity_classification"] and exact_strings(response["quantity_evidence_locators"]) == set(key["quantity_evidence"])),
        "relation_lower": int(response["relation_lower"] == key["relation_lower"] and exact_strings(response["relation_lower_evidence_locators"]) == set(key["relation_lower_evidence"])),
        "relation_upper": int(response["relation_upper"] == key["relation_upper"] and exact_strings(response["relation_upper_evidence_locators"]) == set(key["relation_upper_evidence"])),
        "source_terminal": int(source_exact and "terminal_source" in source_tokens),
        "source_fixed": int(source_exact and "fixed_source" in source_tokens),
        "authority": int(response["authority_classification"] == key["authority_classification"]),
        "next_obligation": int(response["next_proof_obligation_classification"] == key["next_proof_obligation_classification"] and exact_strings(response["next_proof_obligation_evidence_locators"]) == set(key["next_proof_obligation_evidence"])),
    }
    for token, evidence in key["material_difference_evidence"].items():
        row = material.get(token)
        components[f"material_{token}"] = int(material_exact and row is not None and exact_strings(row["evidence_locators"]) == set(evidence))
    total = sum(components.values())
    if set(components.values()) - {0, 1} or len(components) != 11 or total > 11:
        raise ScoreError("scoring component drift")
    return {"components": components, "deterministic_total": total, "maximum": 11}
