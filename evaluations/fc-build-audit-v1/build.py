#!/usr/bin/env python3
"""Build every Lean project Formal Conjectures links to, and read the axioms.

The static audit (`../fc-conditional-proof-audit-v1/`) resolved 415
`formal_proof` links into 143 (repository, revision) pairs and located a target
declaration for each link without elaborating any Lean. This program does the
part that audit deliberately did not do: for each of those 143 checkouts it
installs the toolchain the project itself pins, fetches the Mathlib cache where
the project depends on Mathlib, runs `lake build`, and — where the build
succeeds — elaborates `#print axioms` on the located target declarations.

Everything here is non-authoritative. No Submission, Verification, Decision,
Event or Standing is created and no `vela` command is run.

Third-party source is never vendored. Checkouts live in a scratch directory the
caller names; only names, counts, axiom identifiers, timings, and bounded
failure excerpts are written back into this repository. Several of the linked
repositories carry no LICENSE file — `plby/lean-proofs`, the single largest
source of links, is one of them.

Operating rules that the run depends on:

* **Strictly serial.** A Mathlib build tree is several gigabytes. One at a time.
* **`.lake` is deleted after every repository.** Without this the disk fills in
  under ten builds. The shared Mathlib olean tarball cache is pruned as well,
  but only under disk pressure: 97 of the 143 checkouts pin the same toolchain
  and dropping the tarballs every time would re-download gigabytes per
  repository for nothing.
* **Disk is checked before every build.** Below the floor the run stops cleanly
  and the partial state is a complete, publishable result.
* **Checkpoint after every repository.** A crash costs one repository.

    python3 build.py fetch --repos <scratch>/repos --state <scratch>/state.json
    python3 build.py run   --repos <scratch>/repos --state <scratch>/state.json \
        --budget-seconds 25200 --min-free-gb 15
    python3 build.py collect --state <scratch>/state.json --output builds.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
STATIC = BASE.parent / "fc-conditional-proof-audit-v1" / "results.json"

RESULTS_SCHEMA = "vela-math.fc-build-audit-builds.v1"
STATE_SCHEMA = "vela-math.fc-build-audit-state.v1"

# The closed outcome vocabulary. `evaluate.py` rejects anything outside it.
OUTCOMES = {
    "built",
    "build_failed",
    "build_timeout",
    "toolchain_unavailable",
    "no_manifest",
    "target_not_found",
    "fetch_failed",
    "skipped_disk_floor",
    "skipped_budget",
    "not_attempted",
    # 16 of the 415 `formal_proof` links do not point at a GitHub repository at
    # all, so there is nothing to check out and nothing to build. They stay in
    # the population — dropping them would quietly change the denominator.
    "no_github_checkout",
}

# The three axioms an ordinary Lean development is expected to reach.
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
# `native_decide` compiles the goal and runs it; the kernel does not re-check.
NATIVE_DECIDE_AXIOMS = {"Lean.ofReduceBool", "Lean.trustCompiler"}

MAX_EXCERPT = 400
DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)*"
    r"(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+|nonrec\s+)*"
    r"(theorem|lemma|def|abbrev|instance|structure|inductive|class|opaque|axiom)\s+"
    r"([^\s({\[:]+)"
)


def now() -> float:
    return time.monotonic()


def free_gb(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)


def run(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 900,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return 124, out, err
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def excerpt(text: str, limit: int = MAX_EXCERPT) -> str:
    """Bounded failure text.

    A Lean build failure names declarations and prints goal states, which are
    derived from third-party source. Keep the first error, capped, so the row
    is actionable without becoming a copy of anyone's proof.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    interesting = [line for line in lines if "error" in line.lower()] or lines
    joined = "\n".join(interesting[:6])
    if len(joined) > limit:
        joined = joined[: limit - 1] + "…"
    return joined


# --------------------------------------------------------------------------
# work list, derived entirely from the static audit
# --------------------------------------------------------------------------


def load_static(path: Path = STATIC) -> dict[str, Any]:
    return json.loads(path.read_text())


def worklist(static: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per (repository, revision) pair, ordered by link count.

    Descending link count so that a partial run covers the highest-value
    repositories first: `plby/lean-proofs@main` alone carries 104 links.
    """
    by_key: dict[str, dict[str, Any]] = {}
    for checkout in static["checkouts"]:
        key = f"{checkout['repo']}@{checkout['requested_rev']}"
        by_key[key] = {
            "checkout": key,
            "repo": checkout["repo"],
            "requested_rev": checkout["requested_rev"],
            "resolved_sha": checkout["resolved_sha"],
            "revision_pinned_by_link": checkout["revision_pinned_by_link"],
            "links": [],
        }
    for link in static["links"]:
        key = link.get("checkout")
        if not key or key not in by_key:
            continue
        by_key[key]["links"].append(
            {
                "fc_decl": link["fc_decl"],
                "fc_file": link["fc_file"],
                "fc_line": link["fc_line"],
                "link": link["link"],
                "target_path": link.get("target_path"),
                "target_line": link.get("target_line"),
                "target_declarations": link.get("target_declarations") or [],
                # The static audit's confidence in the locator is carried
                # through unchanged. A LOW-confidence axiom reading is a
                # reading of whatever declaration the locator picked, and the
                # row must say so.
                "target_locator_confidence": link.get("target_locator_confidence"),
                "target_locator_basis": link.get("target_locator_basis"),
                "revision_pinning": link.get("revision_pinning"),
            }
        )
    entries = list(by_key.values())
    entries.sort(key=lambda entry: (-len(entry["links"]), entry["checkout"]))
    return entries


# --------------------------------------------------------------------------
# checkout
# --------------------------------------------------------------------------


def checkout_dir(repos: Path, entry: dict[str, Any]) -> Path:
    safe = entry["repo"].replace("/", "__")
    return repos / f"{safe}@{entry['requested_rev'].replace('/', '_')}"


def fetch_one(repos: Path, entry: dict[str, Any], timeout: int = 1800) -> dict[str, Any]:
    """Shallow-fetch at the SHA the static audit resolved.

    Pinning to the resolved SHA rather than re-resolving the branch keeps the
    build audit and the static audit talking about the same bytes. For the 142
    unpinned links that is the state the branch had on the static audit's
    freeze date, and the row records that the link itself named a branch.
    """
    dest = checkout_dir(repos, entry)
    sha = entry["resolved_sha"]
    if (dest / ".git").exists():
        code, out, _ = run(["git", "-C", str(dest), "rev-parse", "HEAD"], timeout=60)
        if code == 0 and out.strip().startswith(sha[:12]):
            return {"status": "ok", "dir": dest.name, "head": out.strip()}
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q", str(dest)], timeout=60)
    run(
        ["git", "-C", str(dest), "remote", "add", "origin", f"https://github.com/{entry['repo']}.git"],
        timeout=60,
    )
    code, _, err = run(
        ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", sha], timeout=timeout
    )
    if code != 0:
        code2, _, err2 = run(
            ["git", "-C", str(dest), "fetch", "-q", "--depth", "300", "origin"], timeout=timeout
        )
        if code2 != 0:
            return {"status": "fetch_failed", "error": excerpt(err or err2)}
    code, _, err = run(["git", "-C", str(dest), "checkout", "-q", sha], timeout=300)
    if code != 0:
        return {"status": "fetch_failed", "error": excerpt(err)}
    code, out, _ = run(["git", "-C", str(dest), "rev-parse", "HEAD"], timeout=60)
    return {"status": "ok", "dir": dest.name, "head": out.strip()}


# --------------------------------------------------------------------------
# project shape
# --------------------------------------------------------------------------


MANIFEST_NAMES = ("lakefile.toml", "lakefile.lean", "lakefile.olean")


def project_roots(root: Path) -> list[Path]:
    """Every directory that carries a Lake manifest and a `lean-toolchain`.

    A repository is not always one project. `plby/lean-proofs` keeps a
    directory per Lean version (`src/v4.24.0`, …), each its own project. The
    linked file decides which one matters.
    """
    found = []
    skip = {".git", ".lake", "node_modules", ".github"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in skip)
        names = set(filenames)
        if names & set(MANIFEST_NAMES) and "lean-toolchain" in names:
            found.append(Path(dirpath))
            # Descent CONTINUES past a project. A repository can be a Lake
            # project at its root and still hold further projects underneath:
            # `williamjblair/lean-proofs` is a project at `.` and keeps twelve
            # more under `starfleet/erdos-NNNN/`, each with its own lakefile and
            # toolchain, and every one of the 13 linked files lives in those
            # rather than in the root library. Stopping at the first manifest
            # found one project and reported all 13 links unreadable.
            #
            # Descending is safe because `.lake` is skipped above, so a
            # project's own vendored dependencies are never mistaken for
            # projects of this repository.
    return sorted(found, key=lambda path: len(path.parts))


def owning_project(root: Path, roots: list[Path], rel: str | None) -> Path | None:
    """The deepest project directory containing a linked file."""
    if not rel:
        return None
    target = (root / rel)
    best: Path | None = None
    for candidate in roots:
        try:
            target.resolve().relative_to(candidate.resolve())
        except ValueError:
            continue
        if best is None or len(candidate.parts) > len(best.parts):
            best = candidate
    return best


def pick_project(root: Path, roots: list[Path], link_paths: list[str]) -> tuple[Path | None, str]:
    """The project that contains the most linked files, else the shallowest one.

    Used for the repository-level summary and as the fallback for links whose
    path resolves into no project at all. It is deliberately *not* the whole
    story: `plby/lean-proofs@main` keeps one project per Lean version and its
    104 links land in three of them, so the run builds every project that owns
    a link rather than only this one.
    """
    if not roots:
        return None, "none"
    if len(roots) == 1:
        return roots[0], "sole_project"
    scores: Counter[Path] = Counter()
    for rel in link_paths:
        owner = owning_project(root, roots, rel)
        if owner is not None:
            scores[owner] += 1
    if scores:
        best, _ = max(scores.items(), key=lambda item: (item[1], -len(item[0].parts)))
        return best, "contains_linked_file"
    return roots[0], "shallowest_project"


def read_toolchain(project: Path) -> str | None:
    path = project / "lean-toolchain"
    if not path.exists():
        return None
    return path.read_text().strip().splitlines()[0].strip() if path.read_text().strip() else None


def depends_on_mathlib(project: Path) -> bool:
    for name in MANIFEST_NAMES:
        manifest = project / name
        if manifest.exists():
            try:
                text = manifest.read_text(errors="replace")
            except OSError:
                continue
            if "mathlib" in text.lower():
                return True
    manifest = project / "lake-manifest.json"
    if manifest.exists():
        return "mathlib" in manifest.read_text(errors="replace").lower()
    return False


def lean_libs(project: Path) -> list[str]:
    """Library roots declared by the manifest, best effort."""
    libs: list[str] = []
    toml = project / "lakefile.toml"
    if toml.exists():
        for match in re.finditer(r"\[\[lean_lib\]\]\s*(?:\n\s*[a-z_]+\s*=.*)*", toml.read_text()):
            block = match.group(0)
            name = re.search(r"name\s*=\s*\"?([A-Za-z0-9_.«»]+)\"?", block)
            if name:
                libs.append(name.group(1).strip("«»"))
    lean = project / "lakefile.lean"
    if lean.exists():
        for match in re.finditer(r"lean_lib\s+«?([A-Za-z0-9_.]+)»?", lean.read_text()):
            libs.append(match.group(1))
    seen: list[str] = []
    for lib in libs:
        if lib not in seen:
            seen.append(lib)
    return seen


LEAN_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_'!?]*$")


def escape_component(part: str) -> str:
    """French-quote one path component if it is not a Lean identifier.

    Formal Conjectures names its OEIS files after the sequence number, so
    `FormalConjectures/OEIS/103311.wip.lean` exists. Lake makes that the module
    `FormalConjectures.OEIS.«103311.wip»` — the file stem is ONE name component,
    internal dots and all — and both `lake build` and `import` need it spelled
    that way.

    Three spellings were tried against a Lake fixture and only one works:

        Lib.OEIS.103311.wip       lake: build failed
        Lib.OEIS.«103311».wip     lake: build failed
        Lib.OEIS.«103311.wip»     lake: built

    The middle one is the plausible-looking mistake — splitting the stem on its
    dot — and it is what this audit did until the fixture said otherwise. Under
    the first spelling all 38 links of one checkout reported `probe_failed`
    while every declaration was present and compiled.
    """
    return part if LEAN_IDENTIFIER.match(part) else f"«{part}»"


def redact(text: str, root: Path) -> str:
    """Drop machine-specific paths from retained text.

    Absolute scratch paths are ~150 characters and would eat the whole excerpt
    budget before reaching the actual Lean error, and they are noise in a
    published artifact besides.
    """
    return text.replace(str(root), "<checkout>").replace(str(Path.home()), "~")


def module_of(project: Path, root: Path, rel_path: str | None) -> str | None:
    """Lean module name for a linked file path, or None."""
    if not rel_path or not rel_path.endswith(".lean"):
        return None
    absolute = (root / rel_path).resolve()
    if not absolute.exists():
        return None
    try:
        inside = absolute.relative_to(project.resolve())
    except ValueError:
        return None
    parts = list(inside.with_suffix("").parts)
    if not parts:
        return None
    return ".".join(escape_component(part) for part in parts)


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def lake_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("ELAN_HOME", str(Path.home() / ".elan"))
    env["PATH"] = f"{Path.home() / '.elan' / 'bin'}:{env.get('PATH', '')}"
    # Non-interactive: elan must not stop to ask about installing a toolchain.
    env["ELAN_TOOLCHAIN_AUTO_INSTALL"] = "1"
    return env


def installed_toolchains(env: dict[str, str]) -> set[str]:
    code, out, _ = run(["elan", "toolchain", "list"], timeout=120, env=env)
    if code != 0:
        return set()
    names = set()
    for line in out.splitlines():
        name = line.split("(")[0].strip()
        if name:
            names.add(name)
            names.add(name.replace("leanprover/lean4:", ""))
    return names


def ensure_toolchain(toolchain: str, env: dict[str, str], timeout: int = 1800) -> dict[str, Any]:
    have = installed_toolchains(env)
    if toolchain in have or toolchain.replace("leanprover/lean4:", "") in have:
        return {"status": "present", "toolchain": toolchain}
    code, out, err = run(["elan", "toolchain", "install", toolchain], timeout=timeout, env=env)
    if code != 0:
        return {"status": "unavailable", "toolchain": toolchain, "error": excerpt(err or out)}
    return {"status": "installed", "toolchain": toolchain}


def lean_version(project: Path, env: dict[str, str]) -> str | None:
    code, out, _ = run(["lean", "--version"], cwd=project, timeout=300, env=env)
    return out.strip().splitlines()[0] if code == 0 and out.strip() else None


def mathlib_rev(project: Path) -> str | None:
    manifest = project / "lake-manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text())
    except (ValueError, OSError):
        return None
    for package in data.get("packages", []):
        name = package.get("name") or ""
        if str(name).lower().strip("«»") == "mathlib":
            return package.get("rev") or package.get("inputRev")
    return None


# A declaration's trustworthiness has two independent surfaces, and one verdict
# cannot carry both.
#
# The AXIOM CLOSURE is what `#print axioms` reports. It catches `sorryAx` and it
# catches `native_decide`, whose `Lean.ofReduceBool` route was shown unsound in
# 2023 (Carneiro). It is not sufficient on its own: `@[csimp]` can substitute an
# unverified implementation for a verified one without adding anything to the
# closure (lean4#7463, open), so a clean closure is a necessary condition rather
# than a proof of anything.
#
# The PROP HYPOTHESES are the propositional binders of the declaration's own
# type. A theorem stated as `theorem conj (h : HardThing) : Goal` has a clean
# closure, no `sorry`, and proves an implication. That is invisible to an axiom
# audit and visible in the type.
#
# The two are recorded as separate fields. Neither is a verdict.
PROP_HYPOTHESIS_PROBE = r"""
open Lean Meta Elab Command in
run_cmd liftTermElabM do
  let info ← getConstInfo `DECL
  forallTelescope info.type fun binders _ => do
    let mut props : Nat := 0
    for binder in binders do
      let ty ← inferType binder
      if (← isProp ty) then
        props := props + 1
        logInfo m!"VELA_PROP_HYP DECL @@ {← ppExpr ty}"
    logInfo m!"VELA_PROP_COUNT DECL {props} {binders.size}"
"""

MAX_HYPOTHESIS_RENDERING = 200
MAX_HYPOTHESES_RECORDED = 12


def hypothesis_probe_for(decl: str) -> str:
    return PROP_HYPOTHESIS_PROBE.replace("DECL", decl)


def parse_prop_hypotheses(text: str, decl: str) -> dict[str, Any]:
    """Read one declaration's hypothesis probe output, or say it was unavailable.

    The probe is a Lean metaprogram and this run spans sixteen toolchains from
    v4.22 to v4.33. Where it does not elaborate, the field says `unavailable`
    rather than `0`, because "no propositional hypotheses" and "the probe did
    not run" are completely different claims about a declaration.

    Every marker carries the declaration name because the probes for a whole
    project are elaborated in one file. Without the name, one declaration's
    hypotheses would be read as another's.
    """
    quoted = re.escape(decl)
    count = re.search(rf"VELA_PROP_COUNT {quoted} (\d+) (\d+)", text)
    if not count:
        return {"status": "unavailable"}
    renderings = re.findall(
        rf"VELA_PROP_HYP {quoted} @@ (.+?)(?=\n\S|\nVELA_|\Z)", text, re.S
    )
    trimmed = []
    for item in renderings[:MAX_HYPOTHESES_RECORDED]:
        flat = " ".join(item.split())
        if len(flat) > MAX_HYPOTHESIS_RENDERING:
            flat = flat[: MAX_HYPOTHESIS_RENDERING - 1] + "…"
        trimmed.append(flat)
    return {
        "status": "read",
        "prop_binders": int(count.group(1)),
        "total_binders": int(count.group(2)),
        "types": trimmed,
        "types_truncated": len(renderings) > MAX_HYPOTHESES_RECORDED,
    }


def read_one(text: str, decl: str, code: int) -> dict[str, Any]:
    """Turn probe output into one declaration's two-surface reading."""
    hypotheses = parse_prop_hypotheses(text, decl)
    if f"'{decl}' does not depend on any axioms" in text:
        return {"status": "read", "axioms": [], "prop_hypotheses": hypotheses}
    match = re.search(rf"'{re.escape(decl)}' depends on axioms: \[([^\]]*)\]", text)
    if match:
        axioms = [item.strip() for item in match.group(1).split(",") if item.strip()]
        return {"status": "read", "axioms": axioms, "prop_hypotheses": hypotheses}
    # Lean's wording varies across the sixteen toolchains in this run —
    # "unknown constant" in some, "Unknown constant" in others — so the match is
    # case-insensitive, and it is scoped to a message naming THIS declaration so
    # that a neighbour's failure in a batched file is not attributed here.
    mine = re.search(
        rf"(?:unknown identifier|unknown constant)[^\n]*{re.escape(decl)}", text, re.I
    )
    if mine:
        return {"status": "not_found", "error": excerpt(mine.group(0))}
    return {"status": "probe_failed" if code != 0 else "unparsed", "error": excerpt(text)}


def run_probe(project: Path, source: str, env: dict[str, str], timeout: int) -> tuple[int, str]:
    probe = project / "_vela_axiom_probe.lean"
    probe.write_text(source)
    try:
        code, stdout, stderr = run(
            ["lake", "env", "lean", str(probe)], cwd=project, timeout=timeout, env=env
        )
    finally:
        probe.unlink(missing_ok=True)
        (project / "_vela_axiom_probe.olean").unlink(missing_ok=True)
    return code, redact(f"{stdout}\n{stderr}", project)


def print_axioms(
    project: Path,
    modules: dict[str | None, set[str]],
    env: dict[str, str],
    timeout: int = 1800,
) -> dict[str, dict[str, Any]]:
    """Read both trust surfaces of every located target in one project.

    All of the project's targets are elaborated in a SINGLE Lean invocation.
    That is not a micro-optimisation: importing a Mathlib-dependent module costs
    30-60 seconds, and `plby/lean-proofs@main` has 100 target declarations, so
    one invocation each is an hour of re-importing Mathlib to read a hundred
    one-line answers.

    Lean reports every message a file produced and does not stop at the first
    error, so an unknown constant or a metaprogram that will not elaborate on
    some toolchain costs its own declaration and nothing else. Every marker
    carries its declaration name so the batch can be taken apart again. If the
    batch produces no usable reading at all — a module that cannot be imported
    alongside another, say — the run falls back to one invocation per
    declaration and records what that finds.
    """
    declarations = sorted({decl for decls in modules.values() for decl in decls})
    if not declarations:
        return {}
    # `import Lean` is required for the hypothesis metaprogram: the linked
    # module does not necessarily import it, and without it `run_cmd` and the
    # `Lean.Elab.Command` namespace do not resolve. It costs nothing — Lean core
    # ships with every toolchain and Mathlib imports it anyway.
    imports = ["import Lean"] + [
        f"import {name}" for name in sorted(m for m in modules if m)
    ]
    body = "\n".join(
        f"#print axioms {decl}\n{hypothesis_probe_for(decl)}" for decl in declarations
    )
    code, text = run_probe(project, "\n".join(imports) + "\n" + body, env, timeout)
    out = {decl: read_one(text, decl, code) for decl in declarations}
    if any(reading["status"] in {"read", "not_found"} for reading in out.values()):
        return out

    # The batch told us nothing. Fall back to one file per declaration, each
    # importing only the module that declaration actually came from.
    owner = {decl: module for module, decls in modules.items() for decl in decls}
    for decl in declarations:
        module = owner.get(decl)
        source = (
            "import Lean\n"
            + (f"import {module}\n" if module else "")
            + f"#print axioms {decl}\n"
            + hypothesis_probe_for(decl)
        )
        code, text = run_probe(project, source, env, timeout)
        out[decl] = read_one(text, decl, code)
    return out
    return out


def classify_axioms(axioms: list[str]) -> list[str]:
    """Named clauses an axiom set can fail. Empty means the standard set."""
    flags = []
    extra = set(axioms) - STANDARD_AXIOMS
    if "sorryAx" in extra:
        flags.append("sorryAx")
    if extra & NATIVE_DECIDE_AXIOMS:
        flags.append("native_decide")
    other = extra - NATIVE_DECIDE_AXIOMS - {"sorryAx"}
    if other:
        flags.append("nonstandard_axiom")
    # Sorted, because `evaluate.py` re-derives these flags independently and
    # compares them to what was recorded. Two implementations of one rule that
    # disagree on order disagree, and the test suite treats that as drift.
    return sorted(flags)


def prune_mathlib_cache() -> int:
    """Drop the shared olean tarball cache.

    `lake exe cache get` unpacks from `~/.cache/mathlib`, which keeps a tarball
    set per Mathlib revision at a few gigabytes each. Across 143 checkouts it
    is the second largest disk consumer after the build trees themselves.

    It is pruned under disk pressure rather than after every repository. 97 of
    the 143 checkouts pin the same Lean toolchain and many share a Mathlib
    revision, so keeping the tarballs turns most `cache get` calls into a local
    unpack instead of a multi-gigabyte download. Dropping it every time would
    cost more hours than the whole budget allows and buy nothing while disk is
    comfortable.
    """
    cache = Path.home() / ".cache" / "mathlib"
    if not cache.exists():
        return 0
    size = sum(item.stat().st_size for item in cache.rglob("*") if item.is_file())
    shutil.rmtree(cache, ignore_errors=True)
    return size


def strip_build_trees(root: Path) -> None:
    """Delete every `.lake` under a checkout. Mandatory after each repository.

    A Mathlib build tree is several gigabytes and 143 of them do not fit on any
    ordinary disk. This is the step that makes the run possible at all.
    """
    for lake in list(root.rglob(".lake")):
        shutil.rmtree(lake, ignore_errors=True)


def cleanup(root: Path, cache_floor_gb: float) -> dict[str, Any]:
    """Reclaim after a repository. The build tree always; the cache if tight."""
    strip_build_trees(root)
    freed = 0
    pruned = False
    if free_gb(root) < cache_floor_gb:
        freed = prune_mathlib_cache()
        pruned = True
    return {"cache_pruned": pruned, "cache_freed_bytes": freed}


def group_links_by_project(
    root: Path, roots: list[Path], entry: dict[str, Any], primary: Path
) -> dict[Path, dict[str, Any]]:
    """Which project owns each link, and which module inside it.

    A repository is not always one project and its links do not all land in the
    same one. `plby/lean-proofs@main` keeps a directory per Lean version and its
    104 links split 81 / 21 / 2 across three of them. Building only the busiest
    would report `target_not_found` for 23 links that are perfectly fine, so
    every project that owns a link is built.

    Links whose path resolves into no project — a bare repository root, a path
    that has since moved — are attached to the primary project, where the axiom
    probe will report `not_found` against a real build rather than nothing.
    """
    groups: dict[Path, dict[str, Any]] = {}
    for link in entry["links"]:
        rel = link.get("target_path")
        owner = owning_project(root, roots, rel) or primary
        group = groups.setdefault(owner, {"modules": {}, "links": 0, "unlocated": 0})
        group["links"] += 1
        module = module_of(owner, root, rel)
        declarations = link.get("target_declarations") or []
        if module is None:
            group["unlocated"] += 1
        for decl in declarations:
            group["modules"].setdefault(module, set()).add(decl)
    return groups


def build_project(
    root: Path,
    project: Path,
    group: dict[str, Any],
    env: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    """Toolchain, cache, build, axioms — for one Lake project."""
    started = now()
    sub: dict[str, Any] = {
        "project_dir": str(project.relative_to(root)) or ".",
        "links": group["links"],
        "outcome": "not_attempted",
        "toolchain_declared": None,
        "toolchain_used": None,
        "toolchain_install": None,
        "depends_on_mathlib": None,
        "mathlib_rev": None,
        "build_targets": [],
        "axioms": {},
        "error": None,
        "steps": {},
    }
    toolchain = read_toolchain(project)
    sub["toolchain_declared"] = toolchain
    if not toolchain:
        sub["outcome"] = "no_manifest"
        sub["error"] = "project has no readable lean-toolchain"
        sub["seconds"] = round(now() - started, 1)
        return sub

    step = now()
    installed = ensure_toolchain(toolchain, env)
    sub["steps"]["toolchain_seconds"] = round(now() - step, 1)
    sub["toolchain_install"] = installed["status"]
    if installed["status"] == "unavailable":
        sub["outcome"] = "toolchain_unavailable"
        sub["error"] = installed.get("error")
        sub["seconds"] = round(now() - started, 1)
        return sub

    sub["depends_on_mathlib"] = depends_on_mathlib(project)
    sub["toolchain_used"] = lean_version(project, env)

    def remaining() -> int:
        return max(60, int(timeout - (now() - started)))

    if sub["depends_on_mathlib"]:
        step = now()
        code, out, err = run(
            ["lake", "exe", "cache", "get"], cwd=project, timeout=remaining(), env=env
        )
        sub["steps"]["cache_seconds"] = round(now() - step, 1)
        sub["cache_get"] = "ok" if code == 0 else ("timeout" if code == 124 else "failed")
        if code != 0:
            sub["cache_error"] = excerpt(redact(err or out, project))
    sub["mathlib_rev"] = mathlib_rev(project)

    modules = sorted(module for module in group["modules"] if module)
    sub["build_targets"] = modules or ["<default>"]
    step = now()
    args = ["lake", "build"] + modules
    code, out, err = run(args, cwd=project, timeout=remaining(), env=env)
    sub["steps"]["build_seconds"] = round(now() - step, 1)
    if code != 0 and code != 124 and modules:
        # A linked path is not always inside a declared library root. Fall back
        # to the project's default target and record which one produced the row.
        step = now()
        code, out, err = run(["lake", "build"], cwd=project, timeout=remaining(), env=env)
        sub["steps"]["build_default_seconds"] = round(now() - step, 1)
        if code == 0:
            sub["build_targets"] = ["<default>"]
    if code != 0:
        sub["outcome"] = "build_timeout" if code == 124 else "build_failed"
        sub["error"] = (
            f"exceeded {timeout}s" if code == 124 else excerpt(redact(err or out, project))
        )
        sub["seconds"] = round(now() - started, 1)
        return sub

    step = now()
    axioms = print_axioms(project, group["modules"], env, remaining())
    sub["steps"]["axiom_seconds"] = round(now() - step, 1)
    sub["axioms"] = axioms
    read_any = any(item.get("status") == "read" for item in axioms.values())
    # `built` is reserved for a project whose target the kernel actually read.
    # A project that compiles but whose linked declaration cannot be elaborated
    # under the name the static audit recorded is `target_not_found`, and so is
    # a project none of whose links located a declaration at all.
    sub["outcome"] = "built" if read_any else "target_not_found"
    sub["seconds"] = round(now() - started, 1)
    return sub


# Worse outcomes sort later; the repository row reports the best evidence it
# actually obtained and names every project that did not get there.
OUTCOME_RANK = {
    "built": 0,
    "target_not_found": 1,
    "build_failed": 2,
    "build_timeout": 3,
    "toolchain_unavailable": 4,
    "no_manifest": 5,
    "fetch_failed": 6,
    "not_attempted": 7,
}


def build_one(
    repos: Path,
    entry: dict[str, Any],
    env: dict[str, str],
    timeout: int,
    cache_floor_gb: float,
) -> dict[str, Any]:
    started = now()
    row: dict[str, Any] = {
        "checkout": entry["checkout"],
        "repo": entry["repo"],
        "requested_rev": entry["requested_rev"],
        "resolved_sha": entry["resolved_sha"],
        "revision_pinned_by_link": entry["revision_pinned_by_link"],
        "link_count": len(entry["links"]),
        "outcome": "not_attempted",
        "toolchain_declared": None,
        "toolchain_used": None,
        "mathlib_rev": None,
        "depends_on_mathlib": None,
        "project_dir": None,
        "project_choice": None,
        "project_count": 0,
        "projects": [],
        "axioms": {},
        "axiom_flags": [],
        "error": None,
        "steps": {},
    }

    fetched = fetch_one(repos, entry)
    if fetched["status"] != "ok":
        row["outcome"] = "fetch_failed"
        row["error"] = fetched.get("error")
        row["seconds"] = round(now() - started, 1)
        return row
    root = checkout_dir(repos, entry)

    roots = project_roots(root)
    link_paths = [link["target_path"] for link in entry["links"] if link.get("target_path")]
    primary, choice = pick_project(root, roots, link_paths)
    if primary is None:
        row["outcome"] = "no_manifest"
        row["error"] = "no directory carries both a Lake manifest and a lean-toolchain"
        row["seconds"] = round(now() - started, 1)
        return row
    row["project_dir"] = str(primary.relative_to(root)) or "."
    row["project_choice"] = choice
    row["project_count"] = len(roots)

    groups = group_links_by_project(root, roots, entry, primary)
    # Busiest project first: a repository that runs out of budget should have
    # spent it on the projects most of its links point into.
    ordered = sorted(groups.items(), key=lambda item: (-item[1]["links"], str(item[0])))
    # The cap is per Lake project, not per repository, because a repository can
    # legitimately be several projects: `plby/lean-proofs@main` is three, each
    # with its own toolchain, its own Mathlib, and its own cache fetch. Charging
    # all three against one 45-minute budget would time out the last two and
    # lose 23 links that build perfectly well. Three projects' worth is the cap.
    repo_budget = timeout * min(len(ordered), 3)
    row["repository_budget_seconds"] = repo_budget
    deadline = started + repo_budget
    for project, group in ordered:
        left = int(deadline - now())
        if left < 120:
            sub = {
                "project_dir": str(project.relative_to(root)) or ".",
                "links": group["links"],
                "outcome": "build_timeout",
                "error": f"repository budget of {repo_budget}s exhausted before this project",
                "axioms": {},
                "seconds": 0.0,
            }
        else:
            sub = build_project(root, project, group, env, left)
            # Reclaim before the next project in the SAME repository, not just
            # between repositories. `plby/lean-proofs@main` is three Mathlib
            # projects; holding all three build trees at once is over twenty
            # gigabytes and would hit the disk floor inside one row.
            sub["cleanup"] = cleanup(project, cache_floor_gb)
        row["projects"].append(sub)
        row["axioms"].update(sub.get("axioms") or {})

    row["projects"].sort(key=lambda sub: (-sub["links"], sub["project_dir"]))
    # The repository's headline outcome is the busiest project's, not the best
    # one's. A repository whose main project fails must not read as `built`
    # because a one-link side project happened to compile.
    lead = row["projects"][0]
    row["outcome"] = lead["outcome"]
    row["project_outcomes"] = sorted(
        {sub["outcome"] for sub in row["projects"]},
        key=lambda name: OUTCOME_RANK.get(name, 9),
    )
    row["toolchain_declared"] = lead.get("toolchain_declared") or row["projects"][0].get(
        "toolchain_declared"
    )
    row["toolchain_used"] = lead.get("toolchain_used")
    row["mathlib_rev"] = lead.get("mathlib_rev")
    row["depends_on_mathlib"] = any(sub.get("depends_on_mathlib") for sub in row["projects"])
    row["error"] = lead.get("error") or next(
        (sub.get("error") for sub in row["projects"] if sub.get("error")), None
    )
    for key in ("toolchain_seconds", "cache_seconds", "build_seconds", "axiom_seconds"):
        total = sum(sub.get("steps", {}).get(key, 0) for sub in row["projects"])
        if total:
            row["steps"][key] = round(total, 1)

    flags: set[str] = set()
    for reading in row["axioms"].values():
        if reading.get("status") == "read":
            flags.update(classify_axioms(reading["axioms"]))
    row["axiom_flags"] = sorted(flags)
    row["seconds"] = round(now() - started, 1)
    row["cleanup"] = cleanup(root, cache_floor_gb)
    return row


# --------------------------------------------------------------------------
# checkpointed driver
# --------------------------------------------------------------------------


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text())
    return {"schema": STATE_SCHEMA, "authority_effect": "none", "rows": {}, "log": []}


def save_state(path: Path, state: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")
    tmp.replace(path)


def cmd_fetch(args: argparse.Namespace) -> int:
    static = load_static(args.static)
    entries = worklist(static)
    args.repos.mkdir(parents=True, exist_ok=True)
    state = load_state(args.state)
    shapes = state.setdefault("shapes", {})
    for index, entry in enumerate(entries, 1):
        result = fetch_one(args.repos, entry)
        root = checkout_dir(args.repos, entry)
        shape: dict[str, Any] = {"fetch": result["status"], "links": len(entry["links"])}
        if result["status"] == "ok":
            roots = project_roots(root)
            link_paths = [l["target_path"] for l in entry["links"] if l.get("target_path")]
            project, choice = pick_project(root, roots, link_paths)
            shape["projects"] = len(roots)
            shape["project_choice"] = choice
            if project is not None:
                shape["project_dir"] = str(project.relative_to(root)) or "."
                shape["toolchain"] = read_toolchain(project)
                shape["mathlib"] = depends_on_mathlib(project)
                shape["mathlib_rev"] = mathlib_rev(project)
        shapes[entry["checkout"]] = shape
        print(
            f"[{index:3d}/{len(entries)}] {entry['checkout'][:60]:60s} "
            f"{shape.get('toolchain') or shape['fetch']}",
            file=sys.stderr,
            flush=True,
        )
        save_state(args.state, state)
    toolchains = Counter(s.get("toolchain") for s in shapes.values() if s.get("toolchain"))
    print(f"\n{len(toolchains)} distinct toolchains:", file=sys.stderr)
    for name, count in toolchains.most_common():
        print(f"  {count:3d}  {name}", file=sys.stderr)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    static = load_static(args.static)
    entries = worklist(static)
    if args.only:
        wanted = set(args.only)
        entries = [entry for entry in entries if entry["checkout"] in wanted]
    if args.max_checkouts:
        # Coverage is deliberately capped by link weight rather than run to
        # exhaustion. A measured Mathlib project is 25-45 minutes and 143 of
        # them is over a day; the top checkouts carry most of the corpus, and a
        # thorough result over a stated majority is worth more than a thin pass
        # over everything. What is left out is recorded, not silently dropped.
        entries = entries[: args.max_checkouts]
    args.repos.mkdir(parents=True, exist_ok=True)
    state = load_state(args.state)
    rows = state.setdefault("rows", {})
    env = lake_env()
    deadline = now() + args.budget_seconds if args.budget_seconds else None

    for index, entry in enumerate(entries, 1):
        key = entry["checkout"]
        if key in rows and rows[key].get("outcome") not in {"not_attempted", None} and not args.force:
            continue
        if deadline and now() > deadline:
            print(f"budget exhausted before {key}", file=sys.stderr)
            state.setdefault("log", []).append({"event": "budget_exhausted", "before": key})
            save_state(args.state, state)
            break
        free = free_gb(args.repos)
        if free < args.min_free_gb:
            prune_mathlib_cache()
            free = free_gb(args.repos)
        if free < args.min_free_gb:
            print(f"disk floor {args.min_free_gb} GB hit ({free:.1f} GB free) before {key}", file=sys.stderr)
            state.setdefault("log", []).append(
                {"event": "disk_floor", "before": key, "free_gb": round(free, 1)}
            )
            save_state(args.state, state)
            break
        print(
            f"[{index:3d}/{len(entries)}] {key[:58]:58s} links={len(entry['links']):3d} "
            f"free={free:.1f}GB",
            file=sys.stderr,
            flush=True,
        )
        row = build_one(args.repos, entry, env, args.timeout, args.cache_floor_gb)
        row["free_gb_before"] = round(free, 1)
        rows[key] = row
        save_state(args.state, state)
        print(
            f"      -> {row['outcome']:22s} {row.get('seconds', 0):8.1f}s "
            f"{','.join(row['axiom_flags']) or 'standard-axioms'}",
            file=sys.stderr,
            flush=True,
        )
    done = sum(1 for row in rows.values() if row.get("outcome") not in {"not_attempted", None})
    state["scope"] = {
        "max_checkouts": args.max_checkouts or None,
        "checkouts_in_scope": len(entries),
        "links_in_scope": sum(len(entry["links"]) for entry in entries),
    }
    save_state(args.state, state)
    print(f"\n{done} of {len(worklist(static))} checkouts have an outcome", file=sys.stderr)
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    static = load_static(args.static)
    entries = {entry["checkout"]: entry for entry in worklist(static)}
    state = load_state(args.state)
    rows = state.get("rows", {})

    checkouts = []
    for key, entry in entries.items():
        row = dict(rows.get(key) or {})
        if not row:
            row = {
                "checkout": key,
                "repo": entry["repo"],
                "requested_rev": entry["requested_rev"],
                "resolved_sha": entry["resolved_sha"],
                "revision_pinned_by_link": entry["revision_pinned_by_link"],
                "link_count": len(entry["links"]),
                "outcome": "not_attempted",
                "axioms": {},
                "axiom_flags": [],
            }
        row.pop("free_gb_before", None)
        row.pop("cleanup", None)
        checkouts.append(row)
    checkouts.sort(key=lambda row: (-row.get("link_count", 0), row["checkout"]))

    links = []
    # Every link the static audit recorded appears here, including the ones with
    # no checkout to build. The denominator stays 415.
    for static_link in static["links"]:
        if not static_link.get("checkout"):
            links.append(
                {
                    "fc_decl": static_link["fc_decl"],
                    "fc_file": static_link["fc_file"],
                    "fc_line": static_link["fc_line"],
                    "checkout": None,
                    "link": static_link["link"],
                    "revision_pinning": static_link["revision_pinning"],
                    "target_path": static_link.get("target_path"),
                    "target_declarations": static_link.get("target_declarations") or [],
                    "target_locator_confidence": static_link.get("target_locator_confidence"),
                    "target_locator_basis": static_link.get("target_locator_basis"),
                    "build_outcome": "no_github_checkout",
                    "axiom_readings": {},
                    "axiom_flags": [],
                }
            )
    for entry in entries.values():
        row = rows.get(entry["checkout"]) or {}
        for link in entry["links"]:
            record = {
                "fc_decl": link["fc_decl"],
                "fc_file": link["fc_file"],
                "fc_line": link["fc_line"],
                "checkout": entry["checkout"],
                "link": link["link"],
                "revision_pinning": link["revision_pinning"],
                "target_path": link["target_path"],
                "target_declarations": link["target_declarations"],
                "target_locator_confidence": link["target_locator_confidence"],
                "target_locator_basis": link["target_locator_basis"],
                "build_outcome": row.get("outcome", "not_attempted"),
                "axiom_readings": {},
                "axiom_flags": [],
            }
            flags: set[str] = set()
            for decl in link["target_declarations"]:
                reading = (row.get("axioms") or {}).get(decl)
                if reading is None:
                    record["axiom_readings"][decl] = {"status": "not_read"}
                    continue
                record["axiom_readings"][decl] = reading
                if reading.get("status") == "read":
                    flags.update(classify_axioms(reading["axioms"]))
            record["axiom_flags"] = sorted(flags)
            links.append(record)
    links.sort(key=lambda record: (record["fc_file"], record["fc_line"], record["fc_decl"]))

    payload = {
        "schema": RESULTS_SCHEMA,
        "authority_effect": "none",
        "source": {
            "static_audit": "evaluations/fc-conditional-proof-audit-v1/results.json",
            "static_results_root": static["results_root"],
            "formal_conjectures": static["source"],
        },
        "host": {
            "platform": args.platform,
            "note": (
                "Wall-clock timings are one machine, one network, and a shared Mathlib "
                "olean cache pruned between checkouts. They bound effort, not difficulty."
            ),
        },
        "checkouts": checkouts,
        "links": links,
        "log": state.get("log", []),
    }
    payload["builds_root"] = "sha256:" + hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    args.output.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    counts = Counter(row["outcome"] for row in checkouts)
    for name, count in counts.most_common():
        print(f"{count:4d}  {name}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--static", type=Path, default=STATIC)
    common.add_argument("--state", type=Path, required=True)

    fetch = sub.add_parser("fetch", parents=[common])
    fetch.add_argument("--repos", type=Path, required=True)
    fetch.set_defaults(func=cmd_fetch)

    runner = sub.add_parser("run", parents=[common])
    runner.add_argument("--repos", type=Path, required=True)
    runner.add_argument("--timeout", type=int, default=2700, help="per-repository seconds")
    runner.add_argument("--budget-seconds", type=int, default=0)
    runner.add_argument("--min-free-gb", type=float, default=15.0)
    runner.add_argument("--cache-floor-gb", type=float, default=28.0)
    runner.add_argument("--force", action="store_true")
    runner.add_argument("--only", nargs="*", default=None)
    runner.add_argument("--max-checkouts", type=int, default=0)
    runner.set_defaults(func=cmd_run)

    collect = sub.add_parser("collect", parents=[common])
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--platform", default="arm64-apple-darwin")
    collect.set_defaults(func=cmd_collect)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
