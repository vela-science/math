#!/usr/bin/env python3
"""Validate public Stage 2 commitments and, when keys are supplied, held-out bytes."""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(document: object) -> bytes:
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def decrypt(ciphertext: Path, key: Path) -> bytes:
    with tempfile.NamedTemporaryFile() as output:
        subprocess.run(
            [
                "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                "-md", "sha256", "-pass", f"file:{key}", "-in", str(ciphertext),
                "-out", output.name,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return Path(output.name).read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluator-key", type=Path)
    parser.add_argument("--custodian-key", type=Path)
    parser.add_argument("--check-card-schema", type=Path)
    args = parser.parse_args()
    if any((args.evaluator_key, args.custodian_key, args.check_card_schema)) and not all(
        (args.evaluator_key, args.custodian_key, args.check_card_schema)
    ):
        raise SystemExit("private validation requires both keys and the frozen check-card schema")

    stage2 = Path(__file__).resolve().parents[1]
    experiment = stage2.parent
    repo = Path(git(stage2, "rev-parse", "--show-toplevel"))
    commitment = json.loads((stage2 / "COMMITMENT.json").read_text())
    assert commitment["schema"] == "results-breakthrough-stage2-commitment.v1"
    assert commitment["pilot_id"] == "RESULTS-BREAKTHROUGH-01"
    assert commitment["candidate_generation_started"] is False
    assert commitment["target_count"] == 10
    assert commitment["cell_count"] == 30
    assert commitment["smoke_targets"] == ["T01", "T02"]
    assert commitment["mapping_visible_to_candidates"] is False
    assert commitment["mapping_visible_to_scientific_evaluator_before_lock"] is False

    held_out = commitment["held_out_files"]
    lines = "".join(f'{item["path"]}\t{item["sha256"]}\n' for item in sorted(held_out, key=lambda x: x["path"]))
    assert sha256(lines.encode()) == commitment["held_out_aggregate_sha256"]
    assert len(held_out) == 15
    assert len([item for item in held_out if item["path"].startswith("evaluator/cards/")]) == 10

    expected_ciphertexts = set()
    for item in commitment["encrypted_files"]:
        path = stage2 / item["path"]
        data = path.read_bytes()
        assert len(data) == item["bytes"]
        assert sha256(data) == item["sha256"]
        expected_ciphertexts.add(path.resolve())
    actual_ciphertexts = {path.resolve() for path in (stage2 / "encrypted").rglob("*.enc")}
    assert actual_ciphertexts == expected_ciphertexts
    assert len(actual_ciphertexts) == 15

    accepted = commitment["accepted_producer_commit"]
    for relative in commitment["protected_tree_paths"]:
        assert git(repo, "rev-parse", f"HEAD:{relative}") == git(repo, "rev-parse", f"{accepted}:{relative}")
    assignments = json.loads((experiment / "assignments.json").read_text())
    assert assignments["candidate_cells"] == 30
    assert len(assignments["per_target_arm_order"]) == 10
    assert all(sorted(arms) == ["G", "N", "V"] for arms in assignments["per_target_arm_order"].values())
    source_lock = json.loads((experiment / "SOURCE-LOCK.json").read_text())
    assert source_lock["inference_started"] is False
    assert source_lock["authority_effect"] == "none"

    private_status = "not_requested"
    if args.evaluator_key:
        schema_data = args.check_card_schema.read_bytes()
        assert sha256(schema_data) == commitment["check_card_schema_sha256"]
        schema = json.loads(schema_data)
        required = set(schema["required"])
        allowed = set(schema["properties"])
        plaintext = {}
        held_by_path = {item["path"]: item for item in held_out}
        for item in commitment["encrypted_files"]:
            role = item["role"]
            key = args.evaluator_key if role == "evaluator" else args.custodian_key
            data = decrypt(stage2 / item["path"], key)
            held_path = item["plaintext_path"]
            expected = held_by_path[held_path]
            assert len(data) == expected["bytes"]
            assert sha256(data) == expected["sha256"]
            document = json.loads(data)
            assert canonical(document) == data
            plaintext[held_path] = document

        cards = [plaintext[f"evaluator/cards/T{i:02d}.json"] for i in range(1, 11)]
        for index, card in enumerate(cards, 1):
            assert card["target_id"] == f"T{index:02d}"
            assert set(card) == allowed
            assert required <= set(card)
        duplicate_index = plaintext["evaluator/duplicate-control-index.json"]
        assert len(duplicate_index["records"]) == 10
        t02 = next(item for item in duplicate_index["records"] if item["target_id"] == "T02")
        assert len(t02["exact_declaration_matches"]["math"]) == 3
        assert t02["exact_declaration_matches"]["lean_proofs"] == []
        assert set(t02["external_linked_commits_present_in_mounted_fc_objects"].values()) == {False}
        assert all(
            item["exact_declaration_matches"]["math"] == []
            and item["exact_declaration_matches"]["lean_proofs"] == []
            for item in duplicate_index["records"] if item["target_id"] != "T02"
        )
        rubric = plaintext["evaluator/rubric-binding.json"]
        assert rubric["verdicts"] == [
            "qualified_result", "valid_non_result", "needs_correction", "duplicate", "invalid"
        ]
        assert rubric["usable_verdicts"] == ["qualified_result", "valid_non_result"]
        assert rubric["fixed_cell_denominator"] == 30
        access_log = plaintext["evaluator/access-log.json"]
        assert access_log["candidate_generation_started"] is False
        assert access_log["candidate_outputs_accessed"] is False
        assert access_log["scientific_evaluator_outputs_accessed"] is False
        mapping = plaintext["custodian/arm-permutation.json"]
        assert mapping["generated_from_random_bytes"] == 32
        assert len(bytes.fromhex(mapping["seed_hex"])) == 32
        assert sorted(mapping["mapping"]) == [f"T{i:02d}" for i in range(1, 11)]
        assert all(sorted(cell.values()) == ["G", "N", "V"] for cell in mapping["mapping"].values())
        assert all(sorted(counts.values()) == [3, 3, 4] for counts in mapping["balance"].values())
        private_status = "pass"

    print(
        json.dumps(
            {
                "cell_count": 30,
                "ciphertext_count": 15,
                "held_out_aggregate_sha256": commitment["held_out_aggregate_sha256"],
                "held_out_file_count": 15,
                "private_validation": private_status,
                "public_validation": "pass",
                "target_count": 10,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
