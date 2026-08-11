#!/usr/bin/env python3
"""Build the rooted Erdős 321 terminal/fixed-variant comparison."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from evidence_rooting import BuildError, CONTENT_ROOT_DEFINITION, jcs, rendered, rooted, sha256_hex


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MATH_COMMIT = "fdb23666e7b5385a62cc97c58086bc67bd4e7fa9"
MATH_TREE = "809551a3bbdc18479604a5b16d5979b17343c204"
MATH_REMOTE = "https://github.com/vela-science/math.git"
SOURCE_COMMIT = "a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0"
SOURCE_TREE = "dbbe69fa2dbdd73f5e398bbd799115dbbdc9cc27"
SOURCE_REMOTE = "https://github.com/williamjblair/lean-proofs.git"
SOURCE_PROJECT_TREE = "c06136d9a9f7aacc83761c46b89108fe62f15902"
SOURCE_INVENTORY_ROOT = "sha256:bb0e0753023cece0600fd1c8775e13b169459d16e730e6f4244ecd02f019f0a0"
SOURCE_INVENTORY_COUNT = 79
SOURCE_INVENTORY_BYTES = 402_898
MATHLIB_REMOTE = "https://github.com/leanprover-community/mathlib4.git"
MATHLIB_COMMIT = "fabf563a7c95a166b8d7b6efca11c8b4dc9d911f"
MATHLIB_TREE = "1b8fcc589cb2eeb1258449f844eed7924edc9a04"
PNT_REMOTE = "https://github.com/AlexKontorovich/PrimeNumberTheoremAnd.git"
PNT_COMMIT = "a7eb3a8ae4bde79292fb5f04c32cd5ab6d8f226c"
PNT_TREE = "d98e2d87835961619623ce19ec96e827e6224d2f"
MAX_BLOB_BYTES = 1_048_576

OUTPUT_NAMES = (
    "source-lock.v0.1.json",
    "comparison.v0.1.json",
    "plan.v0.1.json",
)
INSTRUMENT_NAME = "reader-instrument.v0.1.json"
PARTICIPANT_PACKET_NAME = "participant-packet.v0.1.json"
IMPLEMENTATION_NAMES = ("evidence_rooting.py", "reader_protocol.py", "reader_scorer.py")

SOURCE_INPUTS = {
    "LICENSE": ("38e9c1da6e57a68e7503fc9a527975bd52a778d9", 1493, "0665bb5f63d444ca4dcc9ad89e274cf1d657928789bd1cae6ce2524423fe5902"),
    "NOTICE": ("c07aa73be9afd5d11d2d27bad7254f8fb3182c28", 1383, "0e2127467b2dc0fdebc6b4a774cb5baf03a13f0a585543f9775850368832f1aa"),
    ".github/workflows/starfleet.yml": ("bba7eb64699b77d9f7aeecf47ab1615f0958f9e8", 4094, "b93704505a7915310e7e0342efd20b723044cbb0e2cb8c686772370341f62835"),
    "starfleet/scripts/check_axioms.sh": ("9bb83a2a47efd42015d940252a03b5fd7e33ce26", 1853, "fe9188e16fbf0887d9cf80658dac0fcc55cf1bf8cca528a780c3a1e118af5b31"),
    "starfleet/erdos-321/lakefile.toml": ("1bc9e3e8a6a49c626cc82284f79ac28f274afbee", 1172, "e60ce2789c794bdaab5ae5581d990b345a67f4614390a6e142e4d1b7dc474f38"),
    "starfleet/erdos-321/lean-toolchain": ("18640c8b066b182147f324d3aefd8ee48ee45238", 25, "efac0b94923b2d8b6840cd35be9177ad0fc5ab2332f4f4311c98712cee92fdee"),
    "starfleet/erdos-321/Audit.lean": ("d5af77649ae1f2cf1e3df5f3e0428e3819ac07a3", 203, "d4924d44f44a9027cbcf49422258e417dd6ebd74e2e7c92deda6d7e1c06311c7"),
    "starfleet/erdos-321/Research.lean": ("a16028f8375fae5ce8be3440f8bee8b285222fe3", 2194, "7ecefd35c1601be5df2e15d891edd80f233e064087aa841193593187719be21c"),
    "starfleet/erdos-321/Research/Basic.lean": ("996f891b0e1d2af6da47f2cc4c63b806498d2ca5", 2192, "6f8edd294e9a5dfb2475468c23518722a736798ea3e6e51822f826c1e4672a74"),
    "starfleet/erdos-321/Research/FinalAsymptotic.lean": ("414d30123ecb0224087ad0e8b4e573d259d65255", 2316, "63dd7ba024ec235a47c1b90c638acae758a50f2d0ee4267e0f69b22cd5d9c0b5"),
    "starfleet/erdos-321/Research/TerminalAsymptotic.lean": ("2ad1281992256df6a18b0a0e42970eb7f02d8bea", 5865, "e49ed1e2bb892af4a290f38d24c41154404d9f46fc77f94c567ab6e88c56edf6"),
    "starfleet/erdos-321/Research/TerminalDepth.lean": ("515d25a364ca225e1a56df9d4f692a2e0c5e9a57", 5263, "6ea9f825c2d96e2484b8b87892aa2418b201412f3bfa5a1219bca3cd00053196"),
    "starfleet/erdos-321/Research/IteratedLogProduct.lean": ("b3f7cf291028afab6f5d143e901e84b481477883", 5773, "9d73660153f169ba622f2f23e0b36e41677558fc6349bd3ed725eaa61c100287"),
}

MATH_INPUTS = {
    "evidence/erdos-321/translation/sources/formal-conjectures-321.lean": ("e58fa81d7f81badaeca1e29dde1e1e1435d1d635", 4534, "601d8486743aede6803feaaefc7bbb73f0aa8873d0296a6a1c5400fd86c32357"),
    "evidence/erdos-321/translation/source-snapshots.v1.json": ("f1bb16f94ca9f39b6d0f0f0cb9113a6be7182957", 838, "518b17d19fde6432daff41ff26ba9ef8eec8da60bd4e5333d79435e196bbe3a6"),
    "evidence/erdos-321/definition-correspondence.v2.json": ("5442d664adc23ee25c60039c44e2d4b6857e7dba", 6189, "e7c303b037c3ad9491bec761cf7e48b6833b2fe54dbe71f603da1a24123322c2"),
}

MATHLIB_INPUTS = {
    "LICENSE": ("8dada3edaf50dbc082c9a125058f25def75e625a", 11357, "b40930bbcf80744c86c46a12bc9da056641d722716c378f5659b9e555ef833e1"),
    "lake-manifest.json": ("1db86ab034fd853428d3b661d4a9ad98b3bd0d6b", 2812, "6f226b135055dccff3e733abfc465a026f8ded1e6e235408365b54193186665d"),
    "lean-toolchain": ("18640c8b066b182147f324d3aefd8ee48ee45238", 25, "efac0b94923b2d8b6840cd35be9177ad0fc5ab2332f4f4311c98712cee92fdee"),
}

PNT_INPUTS = {
    "LICENSE": ("261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64", 11357, "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"),
    "lake-manifest.json": ("37f7cb604131acff147480a4f082e45f697fb518", 4418, "aed29135aa1334e41d82c631d8da0d04b5d0486c55bc784bbaa78fe5e9cda940"),
    "lakefile.toml": ("120437dde1daf1e050841416713f2714fcc18cb5", 935, "8e328d09973ab9be71556ad3e87248e7debbf431add15d7fc8cda98aa98dd8da"),
    "lean-toolchain": ("133a3f7d63769e53f3f4b43ee3eddcd6e2d3b238", 24, "e0a7032ab1976a37a3e1e823816b4f490d462c1e864b21e1999c33cdac76e263"),
}

SOURCE_EXTRA_PATHS = {
    ".github/workflows/starfleet.yml",
    "starfleet/scripts/check_axioms.sh",
    "starfleet/faithfulness.json",
    "starfleet/README.md",
    "starfleet/erdos-321/lakefile.toml",
    "starfleet/erdos-321/lean-toolchain",
    "LICENSE",
    "NOTICE",
}


def read_bounded_at(directory_fd: int, name: str, limit: int) -> tuple[bytes, os.stat_result]:
    try:
        before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > limit:
            raise BuildError(f"bounded regular file required: {name}")
        with os.fdopen(os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd), "rb") as handle:
            opened = os.fstat(handle.fileno())
            data = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
    except OSError as error:
        raise BuildError(f"bounded regular file unavailable: {name}") from error
    identity = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_size)
    if identity(before) != identity(opened) or identity(opened) != identity(after) or len(data) != before.st_size:
        raise BuildError(f"file changed during bounded read: {name}")
    return data, before


def validate_rooted(value: dict[str, Any], name: str) -> dict[str, Any]:
    observed_root = value.get("content_root")
    if value.get("content_root_definition") != CONTENT_ROOT_DEFINITION:
        raise BuildError(f"rooted input definition drift: {name}")
    preimage = {key: member for key, member in value.items() if key != "content_root"}
    if observed_root is None or f"sha256:{sha256_hex(jcs(preimage))}" != observed_root:
        raise BuildError(f"rooted input content root drift: {name}")
    return value


def read_local_file(name: str) -> tuple[bytes, os.stat_result]:
    directory = exact_real_directory(str(HERE))
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        data, info = read_bounded_at(directory_fd, name, MAX_BLOB_BYTES)
    finally:
        os.close(directory_fd)
    if stat.S_IMODE(info.st_mode) != 0o644:
        raise BuildError(f"rooted input mode drift: {name}")
    return data, info


def read_rooted_json(name: str) -> dict[str, Any]:
    data, _info = read_local_file(name)
    return validate_rooted(json.loads(data.decode("utf-8", errors="strict")), name)


def read_instrument() -> dict[str, Any]:
    instrument = read_rooted_json(INSTRUMENT_NAME)
    observed = []
    for name in IMPLEMENTATION_NAMES:
        data, info = read_local_file(name)
        observed.append({"path": name, "mode": "100644", "byte_length": info.st_size, "raw_sha256": f"sha256:{sha256_hex(data)}"})
    if instrument.get("implementation_locks") != observed:
        raise BuildError("reader implementation lock drift")
    return instrument


def git_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in {"XDG_CONFIG_HOME"}
    } | {
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }


def run_git(repo: Path, *args: str) -> bytes:
    try:
        process = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=git_environment(),
            timeout=15,
        )
    except subprocess.TimeoutExpired as error:
        raise BuildError("Git operation timed out") from error
    if process.returncode != 0:
        raise BuildError(f"Git refused {args[0] if args else 'operation'}")
    if len(process.stdout) > MAX_BLOB_BYTES:
        raise BuildError("Git output exceeds evidence limit")
    return process.stdout


def exact_real_directory(value: str) -> Path:
    absolute = Path(os.path.abspath(os.path.expanduser(value)))
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as error:
        raise BuildError("source repository is missing or unreadable") from error
    if resolved != absolute or not resolved.is_dir():
        raise BuildError("source repository must be a real non-symlink directory")
    return resolved


def verify_local_object_store(repo: Path, expected_remote: str) -> None:
    remote = run_git(repo, "config", "--local", "--get", "remote.origin.url").decode().strip()
    if remote != expected_remote:
        raise BuildError("source repository origin drift")
    common_raw = run_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()
    common = Path(common_raw).resolve(strict=True)
    if not common.is_dir():
        raise BuildError("Git common directory drift")
    forbidden_files = (
        common / "shallow",
        common / "info" / "grafts",
        common / "objects" / "info" / "alternates",
    )
    if any(path.exists() and path.stat().st_size > 0 for path in forbidden_files):
        raise BuildError("shallow, grafted, or alternate object store refused")
    # `git config --get-regexp` exits 1 when absent, so inspect the local file
    # directly through a bounded command that normalizes that expected result.
    probe = subprocess.run(
        [
            "git", "--no-replace-objects", "-C", str(repo), "config", "--local",
            "--get-regexp", r"^(extensions\.partialclone|remote\..*\.promisor)$",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=git_environment(),
        timeout=15,
    )
    if probe.returncode not in (0, 1):
        raise BuildError("Git promisor configuration check refused")
    if probe.stdout:
        raise BuildError("partial or promisor object store refused")


def read_locked_inputs(
    repo: Path,
    commit: str,
    tree: str,
    expected: dict[str, tuple[str, int, str]],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    resolved_commit = run_git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    resolved_tree = run_git(repo, "show", "-s", "--format=%T", commit).decode().strip()
    if resolved_commit != commit or resolved_tree != tree:
        raise BuildError("source commit or tree drift")
    inventory = []
    contents: dict[str, bytes] = {}
    for path, (blob, byte_length, raw_sha256) in sorted(expected.items()):
        row = run_git(repo, "ls-tree", commit, "--", path).decode("utf-8", errors="strict").strip()
        prefix = f"100644 blob {blob}\t{path}"
        if row != prefix:
            raise BuildError(f"source object drift: {path}")
        observed_size = run_git(repo, "cat-file", "-s", blob).decode().strip()
        if observed_size != str(byte_length) or byte_length > MAX_BLOB_BYTES:
            raise BuildError(f"source size drift: {path}")
        data = run_git(repo, "cat-file", "blob", blob)
        if len(data) != byte_length or sha256_hex(data) != raw_sha256:
            raise BuildError(f"source bytes drift: {path}")
        inventory.append({
            "path": path,
            "mode": "100644",
            "git_blob_sha1": blob,
            "byte_length": byte_length,
            "raw_sha256": f"sha256:{raw_sha256}",
        })
        contents[path] = data
    return inventory, contents


def source_tree_rows(source_repo: Path) -> dict[str, tuple[str, str, str]]:
    raw = run_git(source_repo, "ls-tree", "-r", "-z", SOURCE_COMMIT)
    rows: dict[str, tuple[str, str, str]] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, path_raw = entry.split(b"\t", 1)
        mode_raw, kind_raw, oid_raw = metadata.split(b" ", 2)
        path = path_raw.decode("utf-8", errors="strict")
        if path in rows:
            raise BuildError("duplicate source-tree path")
        rows[path] = (
            mode_raw.decode("ascii"),
            kind_raw.decode("ascii"),
            oid_raw.decode("ascii"),
        )
    return rows


def source_inventory(source_repo: Path) -> list[dict[str, Any]]:
    tree_rows = source_tree_rows(source_repo)
    module_prefix = "starfleet/erdos-321/"
    module_map = {
        path[len(module_prefix):-len(".lean")].replace("/", "."): path
        for path in tree_rows
        if path.startswith(module_prefix) and path.endswith(".lean")
    }
    import_pattern = re.compile(r"^\s*import\s+(.+?)\s*(?:--.*)?$")

    def imports_for(module: str) -> list[str]:
        path = module_map[module]
        mode, kind, oid = tree_rows[path]
        if mode != "100644" or kind != "blob":
            raise BuildError(f"Lean module object drift: {path}")
        size = int(run_git(source_repo, "cat-file", "-s", oid).decode().strip())
        if size > MAX_BLOB_BYTES:
            raise BuildError(f"Lean module exceeds evidence limit: {path}")
        text = run_git(source_repo, "cat-file", "blob", oid).decode("utf-8", errors="strict")
        imports = []
        for line in text.splitlines():
            match = import_pattern.match(line)
            if match:
                imports.extend(match.group(1).split())
        return [candidate for candidate in imports if candidate in module_map]

    selected_modules: set[str] = set()
    pending = ["Research", "Audit", "Erdos321Statement"]
    while pending:
        module = pending.pop()
        if module in selected_modules:
            continue
        if module not in module_map:
            raise BuildError(f"missing local entry module: {module}")
        selected_modules.add(module)
        pending.extend(imports_for(module))
    selected_paths = {module_map[module] for module in selected_modules} | SOURCE_EXTRA_PATHS
    inventory = []
    serialization = bytearray()
    for path in sorted(selected_paths, key=lambda value: value.encode("utf-8")):
        row = tree_rows.get(path)
        if row is None:
            raise BuildError(f"missing inventory path: {path}")
        mode, kind, oid = row
        if mode != "100644" or kind != "blob":
            raise BuildError(f"inventory object type drift: {path}")
        byte_length = int(run_git(source_repo, "cat-file", "-s", oid).decode().strip())
        if byte_length > MAX_BLOB_BYTES:
            raise BuildError(f"inventory object exceeds evidence limit: {path}")
        data = run_git(source_repo, "cat-file", "blob", oid)
        if len(data) != byte_length:
            raise BuildError(f"inventory byte length drift: {path}")
        raw_sha256 = sha256_hex(data)
        inventory.append({
            "path": path,
            "mode": mode,
            "git_blob_sha1": oid,
            "byte_length": byte_length,
            "raw_sha256": f"sha256:{raw_sha256}",
        })
        serialization.extend(
            mode.encode("ascii") + b"\0" + path.encode("utf-8") + b"\0"
            + raw_sha256.encode("ascii") + b"\0" + str(byte_length).encode("ascii") + b"\n"
        )
    root = f"sha256:{sha256_hex(bytes(serialization))}"
    if len(inventory) != SOURCE_INVENTORY_COUNT:
        raise BuildError("source inventory count drift")
    if sum(row["byte_length"] for row in inventory) != SOURCE_INVENTORY_BYTES:
        raise BuildError("source inventory byte total drift")
    if root != SOURCE_INVENTORY_ROOT:
        raise BuildError("source inventory root drift")
    return inventory


def require_markers(contents: dict[str, bytes]) -> None:
    terminal = contents["starfleet/erdos-321/Research/FinalAsymptotic.lean"].decode("utf-8")
    formal = contents["evidence/erdos-321/translation/sources/formal-conjectures-321.lean"].decode("utf-8")
    notice = contents["NOTICE"].decode("utf-8")
    license_text = contents["LICENSE"].decode("utf-8")
    lakefile = contents["starfleet/erdos-321/lakefile.toml"].decode("utf-8")
    workflow = contents[".github/workflows/starfleet.yml"].decode("utf-8")
    required = {
        "terminal theorem": (terminal, "theorem erdos321_asymptotic"),
        "terminal depth": (terminal, "IsTerminalLogDepth B n d"),
        "fixed lower variant": (formal, "theorem erdos_321.variants.lower"),
        "fixed upper variant": (formal, "theorem erdos_321.variants.upper"),
        "Star Fleet rights exclusion": (notice, "not covered by the MIT licence above"),
        "Star Fleet hosting permission": (notice, "hosted here with the author's permission"),
        "repository license": (license_text, "MIT License"),
        "pinned Mathlib": (lakefile, "fabf563a7c95a166b8d7b6efca11c8b4dc9d911f"),
        "pinned PNT": (lakefile, "a7eb3a8ae4bde79292fb5f04c32cd5ab6d8f226c"),
        "Erdos 321 CI job": (workflow, "verify-321:"),
    }
    for label, (document, marker) in required.items():
        if document.count(marker) != 1:
            raise BuildError(f"locked marker multiplicity drift: {label}")


def documents(
    source_repo: Path,
    mathlib_repo: Path,
    pnt_repo: Path,
) -> dict[str, dict[str, Any]]:
    verify_local_object_store(source_repo, SOURCE_REMOTE)
    verify_local_object_store(mathlib_repo, MATHLIB_REMOTE)
    verify_local_object_store(pnt_repo, PNT_REMOTE)
    verify_local_object_store(ROOT, MATH_REMOTE)
    critical_source_inventory, source_contents = read_locked_inputs(
        source_repo, SOURCE_COMMIT, SOURCE_TREE, SOURCE_INPUTS,
    )
    complete_inventory = source_inventory(source_repo)
    math_inventory, math_contents = read_locked_inputs(
        ROOT, MATH_COMMIT, MATH_TREE, MATH_INPUTS,
    )
    mathlib_inventory, _mathlib_contents = read_locked_inputs(
        mathlib_repo, MATHLIB_COMMIT, MATHLIB_TREE, MATHLIB_INPUTS,
    )
    pnt_inventory, _pnt_contents = read_locked_inputs(
        pnt_repo, PNT_COMMIT, PNT_TREE, PNT_INPUTS,
    )
    instrument = read_instrument()
    participant_packet = read_rooted_json(PARTICIPANT_PACKET_NAME)
    terminal_bytes = source_contents["starfleet/erdos-321/Research/FinalAsymptotic.lean"]
    formal_bytes = math_contents["evidence/erdos-321/translation/sources/formal-conjectures-321.lean"]
    correspondence_bytes = math_contents["evidence/erdos-321/definition-correspondence.v2.json"]
    spans = {
        "span_01": (terminal_bytes, 5, 9), "span_02": (terminal_bytes, 11, 15),
        "span_03": (terminal_bytes, 19, 20), "span_04": (terminal_bytes, 21, 24),
        "span_05": (formal_bytes, 31, 37), "span_06": (formal_bytes, 93, 95),
        "span_07": (formal_bytes, 108, 110), "span_08": (correspondence_bytes, 34, 63),
    }
    for locator, (document, first, last) in spans.items():
        excerpt = b"".join(document.splitlines(keepends=True)[first - 1:last])
        if participant_packet["evidence_locator_catalog"][locator]["raw_sha256"] != f"sha256:{sha256_hex(excerpt)}":
            raise BuildError(f"participant evidence span drift: {locator}")
    require_markers({**source_contents, **math_contents})
    project_tree = run_git(
        source_repo, "rev-parse", f"{SOURCE_COMMIT}:starfleet/erdos-321",
    ).decode().strip()
    if project_tree != SOURCE_PROJECT_TREE:
        raise BuildError("Erdos 321 project subtree drift")
    absent_manifest_path = "starfleet/erdos-321/lake-manifest.json"
    if run_git(source_repo, "ls-tree", "-z", SOURCE_COMMIT, "--", absent_manifest_path):
        raise BuildError("unexpected committed project lake manifest")

    source_lock = rooted({
        "format": "vela.math.erdos321-terminal-variant-source-lock.v0.1",
        "authority_effect": "none",
        "problem": "erdos:321",
        "math_base": {"commit": MATH_COMMIT, "tree": MATH_TREE, "objects": math_inventory},
        "terminal_source": {
            "repository": SOURCE_REMOTE,
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "project_subtree": SOURCE_PROJECT_TREE,
            "critical_objects": critical_source_inventory,
            "proof_ci_rights_inventory": complete_inventory,
            "inventory_definition": "recursive local import closure of Research, Audit, and Erdos321Statement plus eight exact proof/CI/rights paths",
            "inventory_serialization": "mode NUL path NUL lowercase raw SHA-256 hex NUL decimal byte length LF, UTF-8 path sorted",
            "inventory_count": SOURCE_INVENTORY_COUNT,
            "inventory_bytes": SOURCE_INVENTORY_BYTES,
            "inventory_root": SOURCE_INVENTORY_ROOT,
            "project_lake_manifest": {
                "path": absent_manifest_path, "status": "absent_at_pinned_tree", "expected_entries": 0,
                "git_blob_oid": None, "raw_sha256": None, "byte_length": None,
            },
        },
        "proof_environment": {
            "lean_toolchain": "leanprover/lean4:v4.31.0",
            "mathlib": {
                "repository": MATHLIB_REMOTE,
                "commit": MATHLIB_COMMIT,
                "tree": MATHLIB_TREE,
                "objects": mathlib_inventory,
                "license_spdx": "Apache-2.0",
            },
            "prime_number_theorem_and": {
                "repository": PNT_REMOTE,
                "commit": PNT_COMMIT,
                "tree": PNT_TREE,
                "objects": pnt_inventory,
                "license_spdx": "Apache-2.0",
            },
            "build_target": "Research",
            "axiom_audit": "starfleet/scripts/check_axioms.sh",
            "ci_job": ".github/workflows/starfleet.yml#verify-321",
            "ci_execution_result": "not asserted by this source-lock unit",
            "historical_reconstruction_status": "not exact",
            "dependency_resolution": {
                "status": "basis_unavailable_in_pinned_tree", "basis": "starfleet/erdos-321/lake-manifest.json is absent at the pinned project tree",
                "project_mathlib_commit": MATHLIB_COMMIT, "prime_number_theorem_and_commit": PNT_COMMIT,
                "prime_number_theorem_and_manifest_mathlib_commit": "db127794c79fdeb86f6b0cf6ff2c804026fbaff1",
                "conflict": "the project pins Mathlib fabf563a while the pinned PNT manifest records Mathlib db127794; no exact resolved joint environment is retained",
            },
            "mutable_historical_inputs": [
                "ubuntu-latest runner image",
                "actions/checkout@v4 floating major tag",
                "elan installer fetched from the master branch",
                "Mathlib cache service contents",
            ],
        },
        "rights": {
            "rights_class": "NOASSERTION", "handling": "reference_only", "downstream_redistribution_rights": "not_established",
            "repository_authored_material": "MIT at the pinned LICENSE object",
            "star_fleet_material": "copyright Colin Snyder; excluded from the repository MIT grant",
            "permission_basis": "pinned NOTICE proves hosting permission only within williamjblair/lean-proofs and records intent to add a source license",
            "detached_redistribution_license": "not established",
            "handling_detail": "reference pinned Git objects only; this unit copies no Star Fleet theorem source bytes",
            "formal_conjectures_snapshot": "Apache-2.0 header retained in the pinned Math blob",
            "mathlib_license_root": next(row["raw_sha256"] for row in mathlib_inventory if row["path"] == "LICENSE"),
            "prime_number_theorem_and_license_root": next(row["raw_sha256"] for row in pnt_inventory if row["path"] == "LICENSE"),
        },
    })

    comparison = rooted({
        "format": "vela.math.erdos321-terminal-variant-comparison.v0.1",
        "authority_effect": "none",
        "problem": "erdos:321",
        "source_lock_root": source_lock["content_root"],
        "source_locators": {
            "terminal": {
                "repository": SOURCE_REMOTE,
                "commit": SOURCE_COMMIT,
                "path": "starfleet/erdos-321/Research/FinalAsymptotic.lean",
                "declaration": "Erdos321.erdos321_asymptotic",
                "raw_sha256": "sha256:63dd7ba024ec235a47c1b90c638acae758a50f2d0ee4267e0f69b22cd5d9c0b5",
            },
            "fixed_variants": {
                "repository": "https://github.com/google-deepmind/formal-conjectures.git",
                "commit": "59f30aa314ba225fcd9268723ce8291616df1ab0",
                "path": "FormalConjectures/ErdosProblems/321.lean",
                "retained_math_path": "evidence/erdos-321/translation/sources/formal-conjectures-321.lean",
                "declarations": [
                    "Erdos321.erdos_321.variants.lower",
                    "Erdos321.erdos_321.variants.upper",
                ],
                "raw_sha256": "sha256:601d8486743aede6803feaaefc7bbb73f0aa8873d0296a6a1c5400fd86c32357",
            },
        },
        "quantity_boundary": {
            "status": "inherited established correspondence",
            "claim": "Star Fleet extremalSize N and Formal Conjectures R N denote the same quantity at the pinned commits",
            "basis": "evidence/erdos-321/definition-correspondence.v2.json",
            "not_reproved_here": True,
        },
        "statements": {
            "terminal": {
                "declaration": "Erdos321.erdos321_asymptotic", "shape": "eventual two-sided real bounds at an existential terminal depth d selected for each n",
                "scale": "n / Real.log n times an iterated real-log tail product", "constants": "existential N0, B, c, C with B at least 192, c positive, C nonnegative",
            },
            "fixed_lower": {
                "declaration": "Erdos321.erdos_321.variants.lower", "shape": "pointwise lower bound for every natural k satisfying 4 <= k and k <= Nat.log iterated k times at N",
                "scale": "N / Nat.log N times a finite product of natural iterated logs indexed 3 through k", "proof_body_status": "retained statement has `by sorry`; this is not kernel proof evidence",
            },
            "fixed_upper": {
                "declaration": "Erdos321.erdos_321.variants.upper", "shape": "pointwise upper bound for every natural r satisfying 1 <= r and 1 <= Nat.log iterated 2*r times at N",
                "scale": "an explicit natural-log-indexed factor times N / Nat.log N and a product indexed 3 through r", "proof_body_status": "retained statement has `by sorry`; this is not kernel proof evidence",
            },
        },
        "index_expansion_evidence": {
            "terminal_definition": "terminalReciprocalScale n d = n / Real.log n * iteratedLogTailProduct d (Real.log (Real.log n))",
            "terminal_product_reading": "the source docstring identifies factors log_3 n through log_(d+2) n",
            "fixed_lower_index": "Finset.Icc 3 k over Nat.log iterates",
            "fixed_upper_index": "Finset.Icc 3 r plus a separate Nat.log iterate at r",
            "bridge_status": "descriptive source comparison only; no Lean theorem equates these index systems",
        },
        "comparison": {
            "verdict": "same extremal quantity; overlapping iterated-log scale family; not the same statement; no implication or equivalence is established in either direction",
            "shared_features": [
                "two-sided control of the same extremal quantity after the inherited denotational bridge",
                "an n/log n leading factor",
                "products of iterated logarithms whose retained depth depends on logarithmic threshold conditions",
            ],
            "material_differences": [
                "the terminal theorem uses real iterated logarithms beginning at log log n; the fixed variants use iterated Nat.log",
                "the terminal theorem selects one existential adaptive depth d; the fixed variants quantify over supplied k or r satisfying different hypotheses",
                "the terminal theorem has unspecified asymptotic constants c and C; the fixed variants state explicit coefficient shapes",
                "the terminal and fixed products use different index coordinates, so visual similarity is not a Lean-level bridge",
            ],
            "per_variant_relations": [
                {
                    "variant": "lower", "candidate_index_alignment": "k = d + 2",
                    "alignment_status": "index alignment only; not a variable substitution theorem",
                    "terminal_quantifiers": "there exist N0, B, c, and C such that every n at least N0 admits a depth d", "fixed_quantifiers": "for every supplied N and k",
                    "fixed_conditions": "4 <= k and k <= Nat.log iterated k times at N", "condition_delta": "the terminal theorem supplies terminal real-log threshold conditions, not d >= 2 or the fixed lower hypotheses after k = d + 2",
                    "constant_delta": "the terminal lower coefficient is an existential positive real c; the fixed lower coefficient is the explicit unit coefficient in its Nat-valued expression", "conclusion": "no implication in either direction is established",
                },
                {
                    "variant": "upper", "candidate_index_alignment": "r = d + 2",
                    "alignment_status": "index alignment only; not a variable substitution theorem",
                    "terminal_quantifiers": "there exist N0, B, c, and C such that every n at least N0 admits a depth d", "fixed_quantifiers": "for every supplied N and r",
                    "fixed_conditions": "1 <= r and 1 <= Nat.log iterated 2*r times at N", "condition_delta": "r = d + 2 automatically supplies 1 <= r; the terminal theorem does not supply 1 <= Nat.log^[2*(d+2)] N or a Real.log-to-Nat.log bridge",
                    "constant_delta": "the terminal upper coefficient is an existential nonnegative real C; the fixed upper expression has the extra factor 1 / log 2 * log^[r] N", "conclusion": "no implication in either direction is established",
                },
            ],
            "formal_bridge_status": "not_constructed",
            "contradiction_status": "none_found_or_claimed",
        },
        "does_not_establish": [
            "that the terminal theorem proves either fixed Formal Conjectures variant",
            "that either fixed variant proves the terminal theorem",
            "that Erdős Problem 321 is resolved or that the bound is optimal",
            "that a green CI definition is an independently reproduced CI run",
            "that the Formal Conjectures lower or upper proof bodies are kernel evidence; both retained bodies use sorry",
            "that verification or this comparison has Decision or Standing authority",
        ],
        "next_obligation": "construct and kernel-check explicit bridges between the real-log terminal coordinates and each Nat.log fixed-variant hypothesis before asserting implication",
    })

    plan = rooted({
        "format": "vela.math.erdos321-terminal-variant-cold-reader-plan.v0.1",
        "authority_effect": "none",
        "status": "preregistered_not_run",
        "problem": "erdos:321",
        "source_lock_root": source_lock["content_root"],
        "comparison_root": comparison["content_root"],
        "reader_instrument_root": instrument["content_root"], "reader_instrument_path": INSTRUMENT_NAME,
        "participant_packet_root": participant_packet["content_root"], "participant_packet_path": PARTICIPANT_PACKET_NAME,
        "population": "readers who did not author or review this evidence unit or the underlying theorem",
        "public_instrument_boundary": "the plan and expected classifications are public; this is not a secret held-out or blinded benchmark",
        "reporting": {
            "measurements": instrument["measurements"],
            "separate_human_model_and_authority_outcomes": True,
            "no_acceptance_claim_from_correct_answers": True,
            "retain_verbatim_responses_and_timing_provenance": True,
        },
    })
    return {
        "source-lock.v0.1.json": source_lock,
        "comparison.v0.1.json": comparison,
        "plan.v0.1.json": plan,
    }


def output_inventory(outputs: dict[str, bytes]) -> list[dict[str, Any]]:
    return [
        {
            "path": name, "mode": "100644",
            "byte_length": len(outputs[name]), "raw_sha256": f"sha256:{sha256_hex(outputs[name])}",
        }
        for name in sorted(outputs)
    ]


def check_outputs(directory: Path, outputs: dict[str, bytes]) -> None:
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, expected in outputs.items():
            observed, info = read_bounded_at(directory_fd, name, len(expected))
            if stat.S_IMODE(info.st_mode) != 0o644 or info.st_size != len(expected) or observed != expected:
                raise BuildError(f"generated output drift: {name}")
    finally:
        os.close(directory_fd)


def write_outputs(directory: Path, outputs: dict[str, bytes]) -> None:
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, data in outputs.items():
            try:
                target_info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                target_info = None
            if target_info is not None and not stat.S_ISREG(target_info.st_mode):
                raise BuildError(f"output target is not a regular file: {name}")
            temporary = f".{name}.{secrets.token_hex(12)}"
            renamed = False
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
                with os.fdopen(descriptor, "wb") as handle:
                    if handle.write(data) != len(data):
                        raise BuildError(f"output write stalled: {name}")
                    handle.flush()
                    os.fsync(handle.fileno())
                    os.fchmod(handle.fileno(), 0o644)
                os.rename(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
                renamed = True
            finally:
                if not renamed:
                    try:
                        os.unlink(temporary, dir_fd=directory_fd)
                    except FileNotFoundError:
                        pass
    finally:
        os.close(directory_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean-proofs-repo", required=True)
    parser.add_argument("--mathlib-repo", required=True)
    parser.add_argument("--pnt-repo", required=True)
    parser.add_argument("--output-dir", default=str(HERE))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-root", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        source_repo = exact_real_directory(arguments.lean_proofs_repo)
        mathlib_repo = exact_real_directory(arguments.mathlib_repo)
        pnt_repo = exact_real_directory(arguments.pnt_repo)
        built = {
            name: rendered(value)
            for name, value in documents(source_repo, mathlib_repo, pnt_repo).items()
        }
        if tuple(sorted(built)) != tuple(sorted(OUTPUT_NAMES)):
            raise BuildError("output inventory drift")
        if arguments.check:
            check_outputs(exact_real_directory(arguments.output_dir), built)
        elif not arguments.print_root:
            write_outputs(exact_real_directory(arguments.output_dir), built)
        inventory = output_inventory(built)
        bundle_root = f"sha256:{sha256_hex(jcs(inventory))}"
        if arguments.print_root:
            print(bundle_root)
        return 0
    except (BuildError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"terminal_variant_evidence_refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
