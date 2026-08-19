#!/usr/bin/env python3
"""Tier 1: static conditionality audit of Formal Conjectures `formal_proof` links.

This script does the collection pass. It reads a checkout of
`google-deepmind/formal-conjectures` at a pinned commit, parses every
`formal_proof` attribute, and analyses the linked external Lean repositories
that `fetch.py` has already placed on disk. It never builds Lean and never
copies third-party source into this repository: it emits names, counts, and
locators only.

Output is `results.json`, which `evaluate.py` then verifies and reports on.

The four discriminators, and what each does NOT establish:

D1 conditional-on-uninhabited
    Does the target declaration take a binder that does not occur in its own
    conclusion, whose type is declared in the linked repository itself (not
    Mathlib, not core), and which nothing inhabits by a construction whose own
    arguments are all discharged? This is the Erdos 887 pattern. All three
    conditions are load-bearing and it is still a HEURISTIC. See README.md.

D2 sealed core
    Does the repository declare `opaque`, and does a bounded name-reachability
    walk from the target reach one? Reachability is approximated by identifier
    mention, not by elaborated dependency, so it both over- and under-reaches.

D3 the ordinary gate
    `sorry` / `sorryAx` / `axiom` / `native_decide` / `Lean.ofReduceBool`,
    scoped three ways: the target declaration, the target file, the repository.

D4 assumed-False fields
    Structure fields whose type is `False` or ends in `-> False`. A structure
    carrying such a field asserts the mathematics in its own inhabitation.

A flag is not an accusation. Disclosing an assumption in a structure binder is
a legitimate formalisation methodology, and the artifacts that motivated this
audit documented their own assumption layer. What the flags measure is whether
the ordinary community gate (builds / no sorry / clean axioms) is sufficient to
tell a closed proof from a conditional one. It is not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- FC parsing

FORMAL_PROOF = re.compile(
    r"(?P<cond>conditional\s+)?formal_proof\s+using\s+"
    r"(?P<kind>formal_conjectures|lean4|other_system)\s+at\s+"
    r'"(?P<link>[^"]*)"'
    r"(?:\s+assuming\s+(?P<assuming>[^\]]*?))?\s*(?=[\],])",
    re.S,
)
DECL_AFTER = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+)*"
    r"(?P<kw>theorem|lemma|def|abbrev|instance|example)\s+(?P<name>[^\s:{(\[⦃]+)",
    re.M,
)
GITHUB_LINK = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?\s]+?)(?:\.git)?"
    r"(?:/(?:blob|tree|raw)/(?P<rev>[^/#?]+)(?:/(?P<path>[^#?\s]*))?"
    r"|/(?:pull/\d+/commits|commit)/(?P<commit_rev>[0-9a-fA-F]{7,40}))?"
    r"/?(?:#L?(?P<line>\d+)(?:-L?\d+)?)?$"
)
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

FC_SKIP_PREFIXES = ("FormalConjecturesTest/", "FormalConjecturesUtil/", "docbuild/")

# ------------------------------------------------------------- Lean scanning

BLOCK_COMMENT = re.compile(r"/-.*?-/", re.S)
LINE_COMMENT = re.compile(r"--[^\n]*")
STRING_LIT = re.compile(r'"(?:[^"\\]|\\.)*"')

DECL_HEAD = re.compile(
    r"^(?P<attrs>(?:@\[[^\]]*\]\s*)*)"
    r"(?P<mods>(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|partial\s+|unsafe\s+|scoped\s+|local\s+)*)"
    r"(?P<kw>theorem|lemma|def|abbrev|instance|structure|class|inductive|opaque|axiom|example)"
    r"(?![A-Za-z0-9_'!?])"
    r"(?P<rest>[\s\S]*)",
)
DECL_START = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+|nonrec\s+|partial\s+|unsafe\s+|scoped\s+|local\s+)*"
    r"(?:theorem|lemma|def|abbrev|instance|structure|class|inductive|opaque|axiom|example|"
    r"namespace|end|section|open|import|variable|universe|attribute|macro|notation|"
    r"syntax|elab|set_option|deriving|@\[)",
    re.M,
)
NAMESPACE_RE = re.compile(r"^namespace\s+([^\s]+)", re.M)
END_RE = re.compile(r"^end(?:\s+([^\s]+))?\s*$", re.M)

GATE_PATTERNS = {
    "sorry": re.compile(r"(?<![A-Za-z0-9_'])sorry(?![A-Za-z0-9_'])"),
    "sorryAx": re.compile(r"(?<![A-Za-z0-9_'])sorryAx(?![A-Za-z0-9_'])"),
    "axiom": re.compile(r"^\s*axiom\s+", re.M),
    "native_decide": re.compile(r"(?<![A-Za-z0-9_'])native_decide(?![A-Za-z0-9_'])"),
    "ofReduceBool": re.compile(r"Lean\.ofReduceBool"),
}

IDENT = re.compile(r"(?<![A-Za-z0-9_'.])([A-Za-z_][A-Za-z0-9_'!?]*(?:\.[A-Za-z_][A-Za-z0-9_'!?]*)*)")

# Identifiers that are core/Mathlib type formers or otherwise never a local
# user-defined assumption. This list is deliberately small: the real filter is
# "was this name declared in the linked repository", and this only suppresses
# obviously-global names that also happen to be declared locally in some forks.
UNIVERSAL_HEADS = {
    "Type", "Sort", "Prop", "Nat", "Int", "Real", "Rat", "Complex", "Bool",
    "Finset", "Set", "List", "Array", "Fin", "Function", "Filter", "Polynomial",
    "Matrix", "ZMod", "NNReal", "ENNReal", "Ordinal", "Cardinal", "Multiset",
    "Subgroup", "Ideal", "Prod", "Sigma", "Subtype", "Option", "Quotient",
    "True", "False", "Decidable", "DecidableEq", "Fintype", "Inhabited",
    "Nonempty", "Unit", "Empty", "PNat", "NNRat", "Char", "String",
}


def strip_comments(text: str) -> str:
    """Blank out block comments, line comments and string literals in place.

    Offsets are preserved so a stripped index still maps to the original file.
    """
    out = list(text)

    def blank(match: re.Match[str]) -> None:
        for i in range(match.start(), match.end()):
            if out[i] != "\n":
                out[i] = " "

    for pattern in (BLOCK_COMMENT, STRING_LIT, LINE_COMMENT):
        for match in pattern.finditer("".join(out)):
            blank(match)
    return "".join(out)


def lean_files(root: Path) -> list[Path]:
    skip = {".git", ".lake", "lake-packages", "build", ".elan"}
    found = []
    for path in root.rglob("*.lean"):
        if any(part in skip for part in path.parts):
            continue
        found.append(path)
    return sorted(found)


def split_binders(rest: str) -> tuple[list[tuple[str, str]], str]:
    """Split a declaration signature into (binder_kind, binder_text) and the
    result type. Stops at the top-level `:=`, `where`, or `by`."""
    binders: list[tuple[str, str]] = []
    depth = 0
    i = 0
    start = None
    kind = None
    opens = {"(": ")", "{": "}", "[": "]", "⦃": "⦄", "⟨": "⟩"}
    closes = {v: k for k, v in opens.items()}
    result_start = None
    while i < len(rest):
        ch = rest[i]
        if ch in opens:
            if depth == 0 and ch in "({[⦃":
                start, kind = i, ch
            depth += 1
        elif ch in closes:
            depth -= 1
            if depth == 0 and start is not None and kind is not None:
                binders.append((kind, rest[start + 1 : i]))
                start = None
        elif depth == 0:
            if ch == ":" and rest[i : i + 2] != ":=":
                result_start = i + 1
                break
            if rest.startswith(":=", i):
                break
        i += 1
    if result_start is None:
        return binders, ""
    tail = rest[result_start:]
    # Trim the proof/value off the result type.
    cut = len(tail)
    depth = 0
    j = 0
    while j < len(tail):
        ch = tail[j]
        if ch in "({[⦃⟨":
            depth += 1
        elif ch in ")}]⦄⟩":
            depth -= 1
        elif depth == 0:
            if tail.startswith(":=", j):
                cut = j
                break
            if re.match(r"\bwhere\b", tail[j:]):
                cut = j
                break
            if re.match(r"\bby\b", tail[j:]):
                cut = j
                break
        j += 1
    return binders, tail[:cut]


def head_names(type_text: str) -> set[str]:
    """All identifiers mentioned in a type expression."""
    return {m.group(1) for m in IDENT.finditer(type_text)}


def result_head(type_text: str) -> str | None:
    """The outermost head symbol of a result type, after stripping leading
    foralls and arrow arguments."""
    text = type_text.strip()
    # Drop leading binders inside the result type.
    text = re.sub(r"^(?:∀|Π|forall)[^,]*,", "", text).strip()
    # Take the piece after the last top-level arrow.
    depth = 0
    last = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "({[⦃⟨":
            depth += 1
        elif ch in ")}]⦄⟩":
            depth -= 1
        elif depth == 0 and (text.startswith("→", i) or text.startswith("->", i)):
            last = i + (1 if ch == "→" else 2)
        i += 1
    text = text[last:].strip().lstrip("(").strip()
    m = re.match(r"([A-Za-z_][A-Za-z0-9_'!?]*(?:\.[A-Za-z_][A-Za-z0-9_'!?]*)*)", text)
    return m.group(1) if m else None


_MISSING = object()


class RepoIndex:
    """A parsed index of every top-level declaration in one repository checkout."""

    def __init__(self, root: Path):
        self.root = root
        self.decls: list[dict[str, Any]] = []
        self.by_short: dict[str, list[int]] = defaultdict(list)
        self.local_types: set[str] = set()
        self.opaque_names: set[str] = set()
        self.structure_fields: dict[str, list[tuple[str, str]]] = {}
        self.file_count = 0
        self.line_count = 0
        self.repo_gates: dict[str, int] = defaultdict(int)
        self._mentions: dict[int, set[str]] = {}
        self._resolved: dict[str, str | None] = {}
        self._types_by_short: dict[str, list[str]] = {}
        self._binder_types: dict[int, dict[str, list[str]]] = {}
        self.file_gates: dict[str, dict[str, int]] = {}
        self._build()

    def _build(self) -> None:
        for path in lean_files(self.root):
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            self.file_count += 1
            self.line_count += raw.count("\n") + 1
            self._scan_file(path, raw)
        for index, decl in enumerate(self.decls):
            decl["index"] = index
            self.by_short[decl["short_name"]].append(index)
            if decl["kw"] in {"structure", "class", "inductive"}:
                self.local_types.add(decl["full_name"])
            if decl["kw"] == "opaque":
                self.opaque_names.add(decl["full_name"])
                self.opaque_names.add(decl["short_name"])
        by_short: dict[str, list[str]] = defaultdict(list)
        for type_name in sorted(self.local_types):
            by_short[type_name.split(".")[-1]].append(type_name)
        self._types_by_short = dict(by_short)

    def _scan_file(self, path: Path, raw: str) -> None:
        text = strip_comments(raw)
        rel = str(path.relative_to(self.root))
        gates = {name: len(pattern.findall(text)) for name, pattern in GATE_PATTERNS.items()}
        self.file_gates[rel] = {k: v for k, v in gates.items() if v}
        for name, count in gates.items():
            self.repo_gates[name] += count
        # Track namespace stack by line.
        starts = [m.start() for m in DECL_START.finditer(text)]
        starts.append(len(text))
        ns_events: list[tuple[int, str, str | None]] = []
        for m in NAMESPACE_RE.finditer(text):
            ns_events.append((m.start(), "open", m.group(1)))
        for m in END_RE.finditer(text):
            ns_events.append((m.start(), "close", m.group(1)))
        ns_events.sort()

        def namespace_at(pos: int) -> str:
            stack: list[str] = []
            for at, kind, name in ns_events:
                if at >= pos:
                    break
                if kind == "open" and name:
                    stack.extend(name.split("."))
                elif kind == "close":
                    if name and stack:
                        parts = name.split(".")
                        for _ in parts:
                            if stack:
                                stack.pop()
                    elif stack:
                        pass  # `end` closing an anonymous section: leave stack.
            return ".".join(stack)

        for i, start in enumerate(starts[:-1]):
            chunk = text[start : starts[i + 1]]
            m = DECL_HEAD.match(chunk)
            if not m:
                continue
            rest = m.group("rest")
            name_match = re.match(r"\s*([^\s:{(\[⦃]+)", rest)
            if not name_match:
                continue
            short = name_match.group(1)
            if not re.match(r"^[A-Za-z_«]", short):
                continue
            sig_rest = rest[name_match.end() :]
            binders, result = split_binders(sig_rest)
            ns = namespace_at(start)
            full = f"{ns}.{short}" if ns else short
            line = text.count("\n", 0, start) + 1
            self.decls.append(
                {
                    "kw": m.group("kw"),
                    "short_name": short.split(".")[-1],
                    "qual_name": short,
                    "full_name": full,
                    "file": rel,
                    "line": line,
                    "binders": binders,
                    "result_type": result.strip(),
                    "signature": (m.group("kw") + " " + rest.strip())[:1200],
                    "chunk": chunk,
                }
            )
            if m.group("kw") in {"structure", "class"}:
                self.structure_fields[full] = self._fields(chunk)

    @staticmethod
    def _fields(chunk: str) -> list[tuple[str, str]]:
        """Field name and full field type, including multi-line field types.

        A structure field type routinely spans several lines. Reading only the
        first line makes every such field look untyped, which in turn makes
        every structure containing one look like a datatype. That silently
        disables the assumption-package test, so the continuation lines have to
        be joined.
        """
        marker = re.search(r"(?<![A-Za-z0-9_'])where(?![A-Za-z0-9_'])", chunk)
        if not marker:
            return []
        lines = chunk[marker.end() :].splitlines()
        entries: list[list[str]] = []
        base_indent: int | None = None
        for line in lines:
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            if base_indent is None:
                base_indent = indent
            if indent < base_indent:
                break
            starts_field = indent == base_indent and re.match(
                r"\s*[A-Za-z_][A-Za-z0-9_'!?]*(?:\s+[A-Za-z_][A-Za-z0-9_'!?]*)*\s*:(?!=)", line
            )
            if starts_field or not entries:
                entries.append([line.strip()])
            else:
                entries[-1].append(line.strip())
        fields = []
        for entry in entries:
            text = " ".join(entry)
            split = re.match(r"([A-Za-z_][A-Za-z0-9_'!?]*)\s*:(?!=)\s*(.+)$", text, re.S)
            if split:
                fields.append((split.group(1), split.group(2).strip()))
        return fields

    def mentions(self, index: int) -> set[str]:
        cached = self._mentions.get(index)
        if cached is None:
            cached = head_names(self.decls[index]["chunk"])
            self._mentions[index] = cached
        return cached

    def is_local_type(self, name: str) -> str | None:
        """Resolve an identifier to a locally declared type, or None."""
        cached = self._resolved.get(name, _MISSING)
        if cached is not _MISSING:
            return cached  # type: ignore[return-value]
        resolved = self._resolve(name)
        self._resolved[name] = resolved
        return resolved

    def _resolve(self, name: str) -> str | None:
        if name in UNIVERSAL_HEADS:
            return None
        if name in self.local_types:
            return name
        short = name.split(".")[-1]
        if short in UNIVERSAL_HEADS:
            return None
        matches = self._types_by_short.get(short)
        return matches[0] if matches else None


def binder_local_types(index: RepoIndex, decl: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Local types appearing in the declaration's binders.

    For each such type this also records whether ANY binder of that type is
    *unused*: its bound variable does not occur in the declaration's result
    type. That occurs-check is what separates the two shapes that otherwise
    look identical in the text.

        theorem t (circles : Fin n -> Circle2D) : ... circles ...

    Here `Circle2D` is a datatype the theorem quantifies over. The binder
    occurs in the conclusion, the statement is stronger for having it, and
    whether `Circle2D` is ever explicitly constructed is irrelevant.

        theorem t (X : ReconstructionSource) : <statement with no X in it>

    Here the binder occurs nowhere in the conclusion. It cannot be doing
    anything but supplying the proof, so the statement is an implication whose
    antecedent is `Nonempty ReconstructionSource`. If nothing closed-constructs
    that type, the antecedent is exactly the mathematics.
    """
    cached = index._binder_types.get(decl["index"])
    if cached is not None:
        return cached
    result_idents = head_names(decl["result_type"])
    found: dict[str, dict[str, Any]] = {}
    for kind, text in decl["binders"]:
        if ":" not in text:
            continue
        names_part, type_text = text.split(":", 1)
        bound = [n for n in re.findall(r"[A-Za-z_][A-Za-z0-9_'!?]*", names_part)]
        unused = bool(bound) and not any(name in result_idents for name in bound)
        for name in sorted(head_names(type_text)):
            resolved = index.is_local_type(name)
            if not resolved:
                continue
            entry = found.setdefault(
                resolved, {"binder_kinds": set(), "unused_in_result_type": False}
            )
            entry["binder_kinds"].add(kind)
            if unused and kind != "[":
                entry["unused_in_result_type"] = True
    for entry in found.values():
        entry["binder_kinds"] = sorted(entry["binder_kinds"])
    index._binder_types[decl["index"]] = found
    return found


def inhabitation(index: RepoIndex) -> dict[str, dict[str, Any]]:
    """Least fixpoint over closed inhabitation of every local type.

    A construction site for T is a declaration whose result type head is T, or
    an `instance` whose result head is T. The site is CLOSED when none of its
    own binders mention a local type that is not itself closed-inhabited.
    """
    sites: dict[str, list[int]] = defaultdict(list)
    for i, decl in enumerate(index.decls):
        if decl["kw"] in {"structure", "class", "inductive", "axiom", "opaque"}:
            continue
        head = result_head(decl["result_type"])
        if not head:
            continue
        resolved = index.is_local_type(head)
        if resolved:
            sites[resolved].append(i)

    closed: set[str] = set()
    changed = True
    while changed:
        changed = False
        for type_name, decl_indexes in sites.items():
            if type_name in closed:
                continue
            for i in decl_indexes:
                deps = binder_local_types(index, index.decls[i])
                if all(dep in closed for dep in deps if dep != type_name):
                    closed.add(type_name)
                    changed = True
                    break

    out: dict[str, dict[str, Any]] = {}
    for type_name in sorted(index.local_types):
        decl_indexes = sites.get(type_name, [])
        if not decl_indexes:
            state = "no_construction_found"
        elif type_name in closed:
            state = "closed_construction"
        else:
            state = "conditional_construction_only"
        out[type_name] = {
            "state": state,
            "construction_sites": len(decl_indexes),
            "example_sites": [
                f"{index.decls[i]['file']}:{index.decls[i]['line']}" for i in decl_indexes[:3]
            ],
        }
    return out


def false_fields(index: RepoIndex) -> list[dict[str, Any]]:
    out = []
    for type_name, fields in index.structure_fields.items():
        hits = [
            name
            for name, type_text in fields
            if re.search(r"(?:→|->)\s*False\s*$", type_text.strip())
            or type_text.strip() == "False"
            or re.search(r"(?<![A-Za-z0-9_'])False\s*$", type_text.strip())
        ]
        if hits:
            out.append({"type": type_name, "field_count": len(fields), "false_fields": hits})
    return sorted(out, key=lambda row: row["type"])


def reaches_opaque(index: RepoIndex, start: int, max_depth: int = 4) -> tuple[bool, list[str]]:
    """Bounded identifier-mention reachability from a declaration to an `opaque`.

    Approximate in both directions: it follows names that merely appear in a
    declaration body, and it stops at `max_depth`.
    """
    if not index.opaque_names:
        return False, []
    seen = {start}
    frontier = [start]
    path: list[str] = []
    for _ in range(max_depth):
        nxt: list[int] = []
        for i in frontier:
            for name in index.mentions(i):
                if name in index.opaque_names or name.split(".")[-1] in index.opaque_names:
                    return True, path + [index.decls[i]["full_name"], name]
                for j in index.by_short.get(name.split(".")[-1], [])[:6]:
                    if j not in seen:
                        seen.add(j)
                        nxt.append(j)
        if not nxt:
            break
        frontier = nxt
    return False, []


# --------------------------------------------------------------- link tiering


DIGITS = re.compile(r"\d+")

# How much weight each locator basis carries. Only `high` bases are used for the
# headline D1 rate; `medium` and `low` are reported separately because a wrong
# target produces both false flags (an auxiliary lemma parameterised over a
# development structure) and false clears (the real final theorem never read).
LOCATOR_CONFIDENCE = {
    "line_anchor": "high",
    "file_and_name_match": "high",
    "file_and_problem_number_match": "medium",
    "file_last_theorem": "low",
    "repo_wide_name_match": "medium",
    "line_anchor_before_first_declaration": "low",
    "path_not_found_in_checkout": "none",
    "unresolved": "none",
}


def locate_target(
    index: RepoIndex, path: str | None, line: int | None, fc_decl: str
) -> dict[str, Any]:
    """Find the declaration the link is pointing at.

    The Formal Conjectures attribute records a proof SYSTEM (`lean4`,
    `formal_conjectures`, `other_system`) and a URL. It does NOT record a target
    declaration name, so the target has to be recovered. That absence is itself
    a finding; see README.md.

    The ladder below returns ONE declaration, or a small named set, and records
    which rung it came from. Reading every theorem in the linked file is not an
    option: a proof file legitimately carries dozens of auxiliary lemmas
    parameterised over development structures, and treating those as the target
    manufactures D1 flags that say nothing about the conjecture.
    """
    short = fc_decl.split(".")[-1]
    numbers = set(DIGITS.findall(short))

    if not path:
        named = index.by_short.get(short, [])
        if named:
            return {"basis": "repo_wide_name_match", "decl_indexes": named[:4]}
        return {"basis": "unresolved", "decl_indexes": []}

    norm = path.rstrip("/")
    in_file = [i for i, d in enumerate(index.decls) if d["file"] == norm]
    if not in_file:
        return {"basis": "path_not_found_in_checkout", "decl_indexes": []}

    if line:
        # A `#L48` anchor usually points INSIDE the declaration it is about —
        # at its statement or its proof — so the target is the declaration
        # CONTAINING that line, not the next one after it. Taking the next one
        # walks past the linked proof into whatever follows, which in this
        # corpus is sometimes an unrelated `sorry`.
        containing = [i for i in in_file if index.decls[i]["line"] <= line]
        following = [i for i in in_file if index.decls[i]["line"] > line]
        nearest_after = min(following, key=lambda i: index.decls[i]["line"]) if following else None
        nearest_before = max(containing, key=lambda i: index.decls[i]["line"]) if containing else None
        # Unless the anchor sits on the attribute or docstring just above a
        # declaration, with no nearby declaration above it that could own the
        # line, in which case the one below is the target.
        if (
            nearest_after is not None
            and index.decls[nearest_after]["line"] - line <= 3
            and (nearest_before is None or line - index.decls[nearest_before]["line"] > 5)
        ):
            return {"basis": "line_anchor", "decl_indexes": [nearest_after]}
        if nearest_before is not None:
            return {"basis": "line_anchor", "decl_indexes": [nearest_before]}
        if nearest_after is not None:
            return {"basis": "line_anchor_before_first_declaration", "decl_indexes": [nearest_after]}
        return {"basis": "unresolved", "decl_indexes": []}

    named = [i for i in in_file if index.decls[i]["short_name"] == short]
    if named:
        return {"basis": "file_and_name_match", "decl_indexes": named[:4]}

    provable = [i for i in in_file if index.decls[i]["kw"] in {"theorem", "lemma"}]
    if numbers:
        numbered = [
            i
            for i in provable
            if numbers & set(DIGITS.findall(index.decls[i]["full_name"]))
            and "erdos" in index.decls[i]["full_name"].lower()
        ]
        if numbered:
            # A proof file names its auxiliary steps after the problem too
            # (`erdos639_pre`, `tree_from_many_clique_sizes`). Those legitimately
            # carry development structures as arguments, so including them
            # manufactures D1 flags about lemmas nobody linked. Take the final
            # `theorem`, falling back to the final `lemma`.
            best = [i for i in numbered if index.decls[i]["kw"] == "theorem"] or numbered
            return {
                "basis": "file_and_problem_number_match",
                "decl_indexes": [max(best, key=lambda i: index.decls[i]["line"])],
            }
    if provable:
        return {
            "basis": "file_last_theorem",
            "decl_indexes": [max(provable, key=lambda i: index.decls[i]["line"])],
        }
    return {"basis": "unresolved", "decl_indexes": []}


def analyse_link(row: dict[str, Any], index: RepoIndex, checkout: dict[str, Any]) -> dict[str, Any]:
    inhab = checkout["_inhabitation"]
    located = locate_target(index, row.get("target_path"), row.get("target_line"), row["fc_decl"])
    out: dict[str, Any] = {
        "target_locator_basis": located["basis"],
        "target_locator_confidence": LOCATOR_CONFIDENCE[located["basis"]],
        "target_candidate_count": len(located["decl_indexes"]),
    }
    if not located["decl_indexes"]:
        out["d1"] = "undetermined"
        out["d1_reason"] = "target declaration not located in checkout"
        out["d2"] = "undetermined"
        out["d3_target"] = "undetermined"
        out["d4_on_target"] = "undetermined"
        return out

    flagged_types: dict[str, dict[str, Any]] = {}
    conditional_types: dict[str, dict[str, Any]] = {}
    target_names: list[str] = []
    gates: dict[str, int] = defaultdict(int)
    opaque_hit = False
    opaque_path: list[str] = []
    target_files: set[str] = set()
    for position, i in enumerate(located["decl_indexes"]):
        decl = index.decls[i]
        if decl["kw"] not in {"theorem", "lemma", "def", "abbrev", "instance", "example"}:
            continue
        target_names.append(decl["full_name"])
        target_files.add(decl["file"])
        for type_name, info in binder_local_types(index, decl).items():
            state = inhab.get(type_name, {}).get("state")
            if not info["unused_in_result_type"]:
                # The binder occurs in the conclusion, so it is data the
                # theorem quantifies over, not an assumption it takes.
                continue
            entry = {
                "type": type_name,
                "binder_kinds": info["binder_kinds"],
                "unused_in_result_type": True,
                "on_declaration": decl["full_name"],
                "inhabitation": state,
                "construction_sites": inhab.get(type_name, {}).get("construction_sites", 0),
            }
            if state == "no_construction_found":
                flagged_types[type_name] = entry
            elif state == "conditional_construction_only":
                conditional_types[type_name] = entry
        for name, pattern in GATE_PATTERNS.items():
            gates[name] += len(pattern.findall(decl["chunk"]))
        if not opaque_hit and position < 5:
            hit, hpath = reaches_opaque(index, i)
            if hit:
                opaque_hit, opaque_path = True, hpath

    out["target_declarations"] = sorted(target_names)[:12]
    file_gates: dict[str, int] = defaultdict(int)
    for name in sorted(target_files):
        for token, count in index.file_gates.get(name, {}).items():
            file_gates[token] += count
    out["d3_target_file"] = dict(sorted(file_gates.items()))
    out["d1"] = (
        "flagged_uninhabited"
        if flagged_types
        else "flagged_conditional_construction"
        if conditional_types
        else "clear"
    )
    out["d1_uninhabited_binder_types"] = sorted(flagged_types.values(), key=lambda r: r["type"])
    out["d1_conditional_binder_types"] = sorted(
        conditional_types.values(), key=lambda r: r["type"]
    )
    out["d2"] = "reaches_opaque" if opaque_hit else (
        "opaque_present_not_reached" if index.opaque_names else "no_opaque"
    )
    out["d2_path"] = opaque_path[:6]
    out["d3_target"] = {k: v for k, v in sorted(gates.items()) if v}
    out["d4_on_target"] = sorted(
        {
            type_name
            for type_name in list(flagged_types) + list(conditional_types)
            if any(row2["type"] == type_name for row2 in checkout["d4_false_field_types"])
        }
    )

    # File-scope context. A proof file whose auxiliary lemmas are parameterised
    # over a never-closed-constructed development structure is an ordinary and
    # legitimate style; it is reported here so that style is not mistaken for a
    # conditional top-level theorem, and so a wrongly located target is visible.
    file_flagged = 0
    file_total = 0
    for name in sorted(target_files):
        for decl in index.decls:
            if decl["file"] != name or decl["kw"] not in {"theorem", "lemma"}:
                continue
            file_total += 1
            deps = binder_local_types(index, decl)
            if any(
                info["unused_in_result_type"]
                and inhab.get(dep, {}).get("state")
                in {"no_construction_found", "conditional_construction_only"}
                for dep, info in deps.items()
            ):
                file_flagged += 1
    out["file_scope"] = {
        "theorems_in_target_file": file_total,
        "theorems_with_an_unused_unclosed_local_binder": file_flagged,
    }
    return out


# ------------------------------------------------------------------ driver


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def parse_fc(fc_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(fc_root.rglob("*.lean")):
        rel = str(path.relative_to(fc_root))
        if rel.startswith(FC_SKIP_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in FORMAL_PROOF.finditer(text):
            after = DECL_AFTER.search(text, m.end())
            link = m.group("link")
            gh = GITHUB_LINK.match(link.strip())
            rev = (gh.group("rev") or gh.group("commit_rev")) if gh else None
            rows.append(
                {
                    "fc_file": rel,
                    "fc_line": text.count("\n", 0, m.start()) + 1,
                    "fc_decl": after.group("name") if after else "",
                    "fc_decl_kind": after.group("kw") if after else "",
                    "fc_declares_conditional": bool(m.group("cond")),
                    "fc_assuming": (m.group("assuming") or "").split(),
                    "proof_kind": m.group("kind"),
                    "link": link,
                    "target_repo": f"{gh.group('owner')}/{gh.group('repo')}" if gh else None,
                    "target_rev": rev,
                    "target_path": gh.group("path") if gh else None,
                    "target_line": int(gh.group("line")) if gh and gh.group("line") else None,
                    "revision_pinning": (
                        "not_github"
                        if not gh
                        else "pinned_commit"
                        if rev and SHA_RE.match(rev)
                        else "branch_or_tag"
                        if rev
                        else "repository_root"
                    ),
                }
            )
    return rows


def checkout_dir(repos: Path, repo: str, rev: str | None) -> Path:
    return repos / f"{repo.replace('/', '__')}@{rev or 'HEAD'}"


def collect(fc_root: Path, repos: Path, fetched: Path, out_path: Path) -> dict[str, Any]:
    links = parse_fc(fc_root)
    fetch_rows = {
        (row["repo"], row["requested_rev"]): row for row in json.loads(fetched.read_text())
    }
    fc_sha = subprocess.run(
        ["git", "-C", str(fc_root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()

    checkouts: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in links:
        repo, rev = row["target_repo"], row["target_rev"] or "HEAD"
        result = dict(row)
        if not repo:
            result["assessment"] = "undetermined"
            result["assessment_reason"] = "link is not a GitHub repository URL"
            results.append(result)
            continue
        key = f"{repo}@{rev}"
        fetch_row = fetch_rows.get((repo, rev))
        directory = checkout_dir(repos, repo, rev)
        if not fetch_row or fetch_row["status"] != "ok" or not directory.exists():
            result["assessment"] = "undetermined"
            result["assessment_reason"] = fetch_row["status"] if fetch_row else "not_fetched"
            results.append(result)
            continue
        result["checkout"] = key
        result["resolved_sha"] = fetch_row["resolved_sha"]
        grouped[key].append(result)

    # One checkout at a time, so only one repository index is resident.
    for position, key in enumerate(sorted(grouped), start=1):
        repo, _, rev = key.rpartition("@")
        directory = checkout_dir(repos, repo, rev)
        print(f"  [{position}/{len(grouped)}] {key}", file=sys.stderr, flush=True)
        index = RepoIndex(directory)
        inhab = inhabitation(index)
        checkout = {
            "repo": repo,
            "requested_rev": rev,
            "revision_pinned_by_link": bool(SHA_RE.match(rev)),
            "resolved_sha": grouped[key][0]["resolved_sha"],
            "lean_files": index.file_count,
            "lean_lines": index.line_count,
            "declaration_count": len(index.decls),
            "local_type_count": len(index.local_types),
            "opaque_declaration_count": sum(
                1 for d in index.decls if d["kw"] == "opaque"
            ),
            "d3_repository": {k: v for k, v in sorted(index.repo_gates.items()) if v},
            "d4_false_field_types": false_fields(index),
            "uninhabited_local_type_count": sum(
                1 for v in inhab.values() if v["state"] == "no_construction_found"
            ),
            "_inhabitation": inhab,
        }
        for result in grouped[key]:
            result.update(analyse_link(result, index, checkout))
            result["assessment"] = "assessed"
            results.append(result)
        checkout.pop("_inhabitation")
        checkouts[key] = checkout
        del index

    payload = {
        "schema": "vela-math.fc-conditional-proof-results.v1",
        "authority_effect": "none",
        "source": {
            "repository": "google-deepmind/formal-conjectures",
            "commit": fc_sha,
        },
        "links": sorted(results, key=lambda r: (r["fc_file"], r["fc_line"])),
        "checkouts": [checkouts[k] for k in sorted(checkouts)],
    }
    payload["results_root"] = sha256(canonical(payload))
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    return payload


def calibrate(checkout: Path, prefix: str, out_path: Path) -> dict[str, Any]:
    """Run D1 against a known-conditional artifact and record what it says.

    The calibration artifact is not part of the Formal Conjectures population.
    It is the case that motivated the audit: an artifact that passes the
    ordinary gate and whose top-level theorems still take a never-constructed
    assumption package. If D1 does not separate its conditional theorems from
    its one unconditional one, D1 is not measuring what it claims to.
    """
    index = RepoIndex(checkout)
    inhab = inhabitation(index)
    sha = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    rows = []
    for decl in index.decls:
        if not decl["short_name"].startswith(prefix):
            continue
        if decl["kw"] not in {"theorem", "lemma"}:
            continue
        unused = {
            name: inhab.get(name, {}).get("state")
            for name, info in binder_local_types(index, decl).items()
            if info["unused_in_result_type"]
        }
        rows.append(
            {
                "declaration": decl["full_name"],
                "unused_local_binder_types": dict(sorted(unused.items())),
                "d1": (
                    "flagged_uninhabited"
                    if any(state == "no_construction_found" for state in unused.values())
                    else "flagged_conditional_construction"
                    if unused
                    else "clear"
                ),
            }
        )
    payload = {
        "schema": "vela-math.fc-conditional-proof-calibration.v1",
        "authority_effect": "none",
        "note": (
            "Not part of the Formal Conjectures population. Used only to check that D1 "
            "separates a conditional top-level theorem from an unconditional one. The "
            "artifact disclosed its own assumption layer; this is not an accusation."
        ),
        "artifact": {"repository": "jarekkoch-hub/erdos887-lean", "commit": sha},
        "ordinary_gate_on_artifact": {
            "sorry": index.repo_gates.get("sorry", 0),
            "axiom": index.repo_gates.get("axiom", 0),
            "opaque_declarations": sum(1 for d in index.decls if d["kw"] == "opaque"),
        },
        "declaration_prefix": prefix,
        "declarations": sorted(rows, key=lambda r: r["declaration"]),
    }
    payload["calibration_root"] = sha256(canonical(payload))
    out_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    collect_cmd = sub.add_parser("collect")
    collect_cmd.add_argument("--fc", type=Path, required=True)
    collect_cmd.add_argument("--repos", type=Path, required=True)
    collect_cmd.add_argument("--fetched", type=Path, required=True)
    collect_cmd.add_argument("--output", type=Path, required=True)
    cal = sub.add_parser("calibrate")
    cal.add_argument("--checkout", type=Path, required=True)
    cal.add_argument("--prefix", default="erdos_887")
    cal.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "calibrate":
        payload = calibrate(args.checkout, args.prefix, args.output)
        for row in payload["declarations"]:
            print(f"{row['d1']:36s} {row['declaration']}")
        return

    payload = collect(args.fc, args.repos, args.fetched, args.output)
    print(f"links: {len(payload['links'])}")
    print(f"checkouts: {len(payload['checkouts'])}")
    print(f"results_root: {payload['results_root']}")


if __name__ == "__main__":
    main()
