#!/usr/bin/env python3
"""Deterministically verify the retained stock-Buzz run without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import signal
import stat
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
EMPTY = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
BUZZ_COMMIT = "397796c5f343db4251198f44505b1afebe88223f"
BUZZ_TREE = "aa2867f523032a0b87bfc8c70b152d6e117c9696"
MATH_COMMIT = "fab1c3ea6f342a491d5fdfd57fa1126970fb6e61"
MATH_TREE = "2668ca4c7ba345d43bc54ec951b818b469113e98"
COMMAND_IDS = (
    "inventory_before_containers", "inventory_before_networks", "inventory_before_volumes",
    "cargo_locked_release_build", "rustc_verbose_version", "bun_version", "cargo_version",
    "docker_version", "compose_pull", "compose_up", "compose_minio_init", "image_inspect_postgres_17-alpine",
    "image_inspect_redis_7-alpine", "image_inspect_minio_minio_latest",
    "image_inspect_minio_mc_latest", "buzz_database_migrate", "migration_database_readback",
    "buzz_channel_create", "buzz_channel_add_member", "buzz_channel_get",
    "buzz_channel_members", "buzz_target_send", "buzz_target_readback", "buzz_note_send",
    "buzz_result_send", "buzz_message_readback", "raw_event_database_readback",
    "buzz_relay_runtime", "compose_down", "inventory_after_containers",
    "inventory_after_networks", "inventory_after_volumes", "nostr_tools_frozen_install",
    "nostr_tools_cross_implementation_verify",
)
RETAINED = (
    "events.json", "execution-evidence.json", "nostr-verification.json", "target-packet.json",
    "workbench-note.json", "workbench-result.json", "package.json", "bun.lock",
    "run.py", "test_run.py", "test_verify.py", "verify.py", "verify-nostr.mjs",
)


def exact_command_argv(execution: dict, envelope: dict) -> tuple[list[str], ...]:
    channel = envelope["channel_id"]
    event_ids = [event["id"] for event in envelope["events"]]
    member = execution["activity"]["member_pubkey"]
    compose = [
        "docker", "compose", "--project-name", "vela-stock-buzz-proof",
        "--file", "docker-compose.yml", "--project-directory", ".",
    ]
    image_format = '{"id":"{{.Id}}","repo_digests":{{json .RepoDigests}}}'
    return (
        ["docker", "ps", "-a", "--filter", "name=^/buzz-", "--format", "{{.Names}}"],
        ["docker", "network", "ls", "--filter", "name=^buzz-net$", "--format", "{{.Name}}"],
        ["docker", "volume", "ls", "--filter", "name=^buzz-(postgres|minio|prometheus)-data$", "--format", "{{.Name}}"],
        ["cargo", "build", "--locked", "--release", "-p", "buzz-cli", "-p", "buzz-relay", "-p", "buzz-admin"],
        ["rustc", "-vV"],
        ["bun", "--version"],
        ["cargo", "-V"],
        ["docker", "version", "--format", '{"client":"{{.Client.Version}}","server":"{{.Server.Version}}"}'],
        [*compose, "pull", "postgres", "redis", "minio", "minio-init"],
        [*compose, "up", "-d", "--wait", "--wait-timeout", "60", "postgres", "redis", "minio"],
        [*compose, "up", "--no-deps", "--abort-on-container-exit", "--exit-code-from", "minio-init", "minio-init"],
        ["docker", "image", "inspect", "postgres:17-alpine", "--format", image_format],
        ["docker", "image", "inspect", "redis:7-alpine", "--format", image_format],
        ["docker", "image", "inspect", "minio/minio:latest", "--format", image_format],
        ["docker", "image", "inspect", "minio/mc:latest", "--format", image_format],
        ["target/release/buzz-admin", "migrate"],
        ["docker", "exec", "buzz-postgres", "psql", "-U", "buzz", "-d", "buzz", "-Atqc", "<allowlisted-migration-readback-sql>"],
        ["buzz", "channels", "create", "--name", "vela-erdos-321-bridge", "--type", "stream", "--visibility", "open", "--description", "Disposable rooted Vela target transport"],
        ["buzz", "channels", "add-member", "--channel", channel, "--pubkey", member, "--role", "member"],
        ["buzz", "channels", "get", "--channel", channel],
        ["buzz", "channels", "members", "--channel", channel],
        ["buzz", "messages", "send", "--channel", channel, "--content", "-"],
        ["buzz", "messages", "get", "--channel", channel, "--limit", "50"],
        ["buzz", "messages", "send", "--channel", channel, "--content", "-", "--reply-to", event_ids[0]],
        ["buzz", "messages", "send", "--channel", channel, "--content", "-", "--reply-to", event_ids[1]],
        ["buzz", "messages", "get", "--channel", channel, "--limit", "50"],
        ["docker", "exec", "buzz-postgres", "psql", "-U", "buzz", "-d", "buzz", "-Atqc", "<allowlisted-three-event-readback-sql>"],
        ["target/release/buzz-relay"],
        [*compose, "down", "-v", "--remove-orphans"],
        ["docker", "ps", "-a", "--filter", "name=^/buzz-", "--format", "{{.Names}}"],
        ["docker", "network", "ls", "--filter", "name=^buzz-net$", "--format", "{{.Name}}"],
        ["docker", "volume", "ls", "--filter", "name=^buzz-(postgres|minio|prometheus)-data$", "--format", "{{.Name}}"],
        ["bun", "install", "--frozen-lockfile"],
        ["bun", "run", "verify-nostr.mjs"],
    )


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def regular_bytes(path: Path, maximum: int = 10 * 1024 * 1024) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
        raise AssertionError(f"unsafe retained file: {path.name}")
    with path.open("rb") as handle:
        data = handle.read(maximum + 1)
    assert len(data) == info.st_size <= maximum, f"bounded read drift: {path.name}"
    return data


def load_json(root: Path, name: str) -> dict:
    value = json.loads(regular_bytes(root / name))
    assert isinstance(value, dict), f"{name}: object required"
    return value


def verify_root(document: dict, key: str, label: str) -> None:
    expected = document[key]
    candidate = dict(document)
    candidate.pop(key)
    assert expected == sha256(canonical(candidate)), f"{label}: rooted content drift"


def file_fact(path: Path) -> dict:
    data = regular_bytes(path)
    info = path.lstat()
    return {
        "byte_length": len(data),
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        "raw_sha256": sha256(data),
    }


def point_add(left, right):
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2 and (y1 != y2 or y1 == 0):
        return None
    slope = (
        (3 * x1 * x1) * pow(2 * y1, P - 2, P) % P
        if x1 == x2
        else (y2 - y1) * pow((x2 - x1) % P, P - 2, P) % P
    )
    x3 = (slope * slope - x1 - x2) % P
    return x3, (slope * (x1 - x3) - y1) % P


def scalar_mult(multiplier: int, point=G):
    result = None
    addend = point
    while multiplier:
        if multiplier & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        multiplier >>= 1
    return result


def lift_x(raw_x: bytes):
    x = int.from_bytes(raw_x, "big")
    if x >= P:
        return None
    y = pow((pow(x, 3, P) + 7) % P, (P + 1) // 4, P)
    if pow(y, 2, P) != (pow(x, 3, P) + 7) % P:
        return None
    return x, y if y % 2 == 0 else P - y


def tagged_hash(tag: str, data: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()


def verify_bip340(pubkey: str, message: bytes, signature: str) -> bool:
    if len(message) != 32 or len(pubkey) != 64 or len(signature) != 128:
        return False
    public_point = lift_x(bytes.fromhex(pubkey))
    if public_point is None:
        return False
    raw = bytes.fromhex(signature)
    r = int.from_bytes(raw[:32], "big")
    s = int.from_bytes(raw[32:], "big")
    if r >= P or s >= N:
        return False
    challenge = int.from_bytes(
        tagged_hash("BIP0340/challenge", raw[:32] + bytes.fromhex(pubkey) + message), "big"
    ) % N
    negative = (public_point[0], (-public_point[1]) % P)
    result = point_add(scalar_mult(s), scalar_mult(challenge, negative))
    return result is not None and result[1] % 2 == 0 and result[0] == r


def verify_event(event: dict) -> None:
    assert set(event) == {"id", "pubkey", "created_at", "kind", "tags", "content", "sig"}
    serial = [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]]
    digest = hashlib.sha256(json.dumps(serial, ensure_ascii=False, separators=(",", ":")).encode()).digest()
    assert event["id"] == digest.hex(), "Nostr event id drift"
    assert verify_bip340(event["pubkey"], digest, event["sig"]), "Nostr signature refused"


def verify(root: Path, expected_root: str | None = None) -> dict:
    root = root.resolve(strict=True)
    packet = load_json(root, "target-packet.json")
    note = load_json(root, "workbench-note.json")
    result = load_json(root, "workbench-result.json")
    envelope = load_json(root, "events.json")
    execution = load_json(root, "execution-evidence.json")
    cross_verification = load_json(root, "nostr-verification.json")
    manifest = load_json(root, "run-manifest.json")
    verify_root(packet, "packet_root", "target packet")
    verify_root(note, "note_root", "workbench note")
    verify_root(result, "result_root", "workbench result")
    verify_root(execution, "execution_root", "execution evidence")
    verify_root(manifest, "aggregate_evidence_root", "aggregate evidence")
    aggregate = manifest["aggregate_evidence_root"]
    if expected_root is not None:
        assert aggregate == expected_root, "aggregate evidence root differs from expected root"

    assert manifest["schema"] == "vela.stock-buzz-compatibility-run.v2"
    assert manifest["authority_effect"] == "none"
    assert manifest["math_source"]["commit"] == MATH_COMMIT
    assert manifest["math_source"]["tree"] == MATH_TREE
    assert manifest["buzz_source"] == {
        "commit": BUZZ_COMMIT, "tree": BUZZ_TREE, "origin": "https://github.com/block/buzz.git"
    }
    assert manifest["files"] == {name: file_fact(root / name) for name in RETAINED}
    assert manifest["execution_root"] == execution["execution_root"]
    assert manifest["result"] == {
        "status": "stock_buzz_transported_operator_authored_activity_no_candidate",
        "buzz_scientific_reasoning": False,
        "independent_adoption": False,
        "scientific_candidate_produced": False,
        "scientific_state_changed": False,
    }

    assert envelope["schema"] == "vela.stock-buzz-activity-events.v1"
    assert envelope["authority_effect"] == "none"
    events = envelope["events"]
    roles = envelope["roles"]
    assert len(events) == len(roles) == 3
    for event in events:
        verify_event(event)
    event_ids = [event["id"] for event in events]
    assert event_ids == [role["event_id"] for role in roles]
    assert [role["role"] for role in roles] == ["target_packet", "workbench_note", "workbench_result"]
    for role, event in zip(roles, events, strict=True):
        assert event["content"].encode() == regular_bytes(root / role["content_file"])
        assert event["kind"] == 9
        assert event["tags"][0] == ["h", envelope["channel_id"]]
    assert events[1]["tags"][1] == ["e", events[0]["id"], "", "reply"]
    assert events[2]["tags"][1:] == [
        ["e", events[0]["id"], "", "root"], ["e", events[1]["id"], "", "reply"]
    ]
    assert events[0]["pubkey"] != events[1]["pubkey"] == events[2]["pubkey"]

    assert packet["packet_root"] == note["packet_root"] == result["packet_root"]
    assert note["activity"] == {"channel_id": envelope["channel_id"], "received_event_id": events[0]["id"]}
    assert result["activity_event_ids"] == event_ids[:2]
    assert result["artifact_roots"] == [note["note_root"]]
    assert packet["authority_effect"] == note["authority_effect"] == result["authority_effect"] == "none"
    assert packet["authorship"] == {
        "scientific_content": "experiment_operator",
        "buzz_role": "transport_storage_and_readback_only",
    }
    assert note["authorship"]["scientific_decomposition"] == "experiment_operator"
    assert result["authorship"]["scientific_result"] == "experiment_operator"
    assert note["result_status"] == "operator_authored_decomposition_transported_no_candidate"
    assert result["result_status"] == "operator_authored_result_transported_no_candidate"

    assert execution["schema"] == "vela.stock-buzz-execution-evidence.v1"
    assert execution["source"]["commit"] == BUZZ_COMMIT
    assert execution["source"]["tree"] == BUZZ_TREE
    assert execution["source"]["license_expression"] == "Apache-2.0"
    assert execution["source"]["custody"] == {
        "canonical_top_level": True,
        "exact_in_worktree_git_directory": True,
        "ignored_residue_absent": True,
        "lazy_fetch_disabled": True,
        "partial_promisor_shallow_alternates_and_replacements_absent": True,
        "sparse_skip_worktree_and_assume_unchanged_absent": True,
        "required_worktree_bytes_equal_exact_git_blobs": True,
        "all_tracked_worktree_entries_equal_pinned_tree": True,
    }
    assert execution["source"]["tracked_tree"] == {
        "entry_count": 3862,
        "raw_byte_length": 72386539,
        "by_mode": {"100644": 3746, "100755": 66, "120000": 50},
        "inventory_root": "sha256:e304b9ec4cc6d69b4cb993d228be6f8d3e43396f01513927292b04559d5ca2cf",
        "inventory_root_definition": (
            "sha256 of mode + NUL + UTF-8 path + NUL + Git blob oid + NUL + "
            "raw SHA-256 hex + NUL + decimal byte length + LF for every pinned-tree "
            "entry in git ls-tree byte order"
        ),
    }
    assert execution["source"]["source_files"]["LICENSE"]["raw_sha256"] == (
        "sha256:108cb15997e51b75a8d18b0c1e2c52bd3879d051ab02118973387df1e4aab584"
    )
    for source_file in execution["source"]["source_files"].values():
        assert source_file["git_mode"] == "100644"
        assert re.fullmatch(r"[0-9a-f]{40}", source_file["git_blob_oid"])
    binaries = execution["build"]["binaries"]
    assert execution["build"]["fresh_external_target_directory"] is True
    assert set(binaries) == {"buzz", "buzz-relay", "buzz-admin"}
    assert all(value["mode"] == "0755" and value["byte_length"] > 1_000_000 for value in binaries.values())
    assert execution["runtime"]["selected_stock_services"] == ["postgres", "redis", "minio", "minio-init"]
    assert execution["runtime"]["relay_log"]["retained"] is False
    assert execution["runtime"]["relay_log"]["removed_with_external_build_directory"] is True
    assert set(execution["runtime"]["images"]) == {
        "postgres:17-alpine", "redis:7-alpine", "minio/minio:latest", "minio/mc:latest"
    }
    for image in execution["runtime"]["images"].values():
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", image["id"])
        assert len(image["repo_digests"]) == 1 and "@sha256:" in image["repo_digests"][0]

    ledger = execution["command_ledger"]
    assert len(COMMAND_IDS) == 34
    assert tuple(entry["command_id"] for entry in ledger) == COMMAND_IDS
    assert tuple(entry["argv"] for entry in ledger) == exact_command_argv(execution, envelope)
    for entry in ledger:
        assert entry["exit_code"] == 0
        if entry["command_id"] == "buzz_relay_runtime":
            assert entry["expected_signal"] == "SIGTERM"
        serialized_argv = canonical(entry["argv"]).decode().lower()
        assert "private-key" not in serialized_argv and "secret" not in serialized_argv
        for field in ("stdout_raw_sha256", "stderr_raw_sha256"):
            assert re.fullmatch(r"sha256:[0-9a-f]{64}", entry[field])
    teardown = execution["teardown"]
    assert teardown["before"] == teardown["after"] == {
        "containers": [], "networks": [], "volumes": []
    }
    assert teardown["disposable_containers_network_and_volumes_absent"] is True
    assert teardown["external_build_directory_and_relay_log_absent"] is True
    protected = execution["protected_vela_state"]
    assert protected["changed"] is False and protected["before"] == protected["after"]
    assert protected["before"] == {
        "diff_byte_length": 0, "diff_raw_sha256": EMPTY,
        "status_byte_length": 0, "status_raw_sha256": EMPTY,
    }
    privacy = execution["privacy"]
    assert privacy == {
        "ephemeral_private_keys_passed_only_via_buzz_child_process_environments": True,
        "private_keys_retained": False,
        "private_keys_serialized": False,
        "raw_relay_log_scanned_for_all_three_private_keys_before_hash_and_removal": True,
        "participant_or_evaluator_inputs_used": False,
        "repository_authority_credentials_used": False,
    }

    observations = execution["activity"]["observations"]
    assert observations["channel_metadata_readback"]["channel_id"] == envelope["channel_id"]
    memberships = observations["channel_membership_readback"]
    assert memberships == [
        {"pubkey": execution["activity"]["operator_pubkey"], "role": "owner"},
        {"pubkey": execution["activity"]["member_pubkey"], "role": "member"},
    ]
    assert [receipt["event_id"] for receipt in observations["message_receipts"]] == event_ids
    normalized = {event["id"]: event for event in observations["message_readback"]}
    for event in events:
        assert normalized[event["id"]] == {
            key: event[key] for key in ("content", "created_at", "id", "kind", "pubkey", "tags")
        }
    assert observations["migration_count"] > 0
    assert observations["relay_lifecycle"][0]["message"] == "Starting buzz-relay"
    assert observations["relay_lifecycle"][-1]["message"] == "Audit worker drained cleanly"

    assert cross_verification == execution["cross_implementation_signature_verification"]
    assert cross_verification["authority_effect"] == "none"
    assert cross_verification["event_ids"] == event_ids
    assert cross_verification["events_verified"] == 3
    assert cross_verification["nostr_tools_version"] == "2.23.12"
    assert cross_verification["verification_scope"] == "cross_implementation_signature_only"
    assert cross_verification["package_lock_raw_sha256"] == sha256(regular_bytes(root / "bun.lock"))
    runtime_evidence = b"\n".join(
        regular_bytes(root / name)
        for name in (
            "events.json", "execution-evidence.json", "nostr-verification.json",
            "target-packet.json", "workbench-note.json", "workbench-result.json",
            "run-manifest.json",
        )
    )
    assert b"BUZZ_PRIVATE_KEY" not in runtime_evidence and b"BUZZ_RELAY_PRIVATE_KEY" not in runtime_evidence
    assert b"private_build_input" not in runtime_evidence and b"evaluator_only" not in runtime_evidence
    assert b"packet_understood_no_candidate_produced" not in runtime_evidence
    assert b'"independent_verification"' not in runtime_evidence
    assert b"Buzz performed no scientific reasoning" in runtime_evidence
    return {
        "aggregate_evidence_root": aggregate,
        "authority_effect": "none",
        "events": 3,
        "ok": True,
        "stock_buzz_commit": BUZZ_COMMIT,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--expected-root")
    parser.add_argument("--print-root", action="store_true")
    args = parser.parse_args()
    result = verify(args.root, args.expected_root)
    if args.print_root:
        print(result["aggregate_evidence_root"])
    else:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"stock_buzz_evidence_refused: {error}", file=sys.stderr)
        raise SystemExit(1)
