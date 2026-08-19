#!/usr/bin/env python3
"""Step 1 of the Tier-1 audit: fetch each distinct (repository, revision) that
a Formal Conjectures `formal_proof` link points at.

One shallow fetch per pair. Nothing is vendored into this repository: the
checkouts land in a scratch directory the caller names, and only names, counts
and locators are ever written back into `results.json`. Several linked
repositories carry no LICENSE file, so third-party Lean source must not be
copied here under any circumstance.

Records for every pair: the requested revision, whether the link pinned a
commit or named a branch, the resolved SHA, and any failure. A repository that
404s and a revision that no longer exists are both findings, not errors.

    python3 fetch.py --fc <formal-conjectures-checkout> \
        --repos /path/to/scratch/repos --output /path/to/scratch/fetched.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

GITHUB_LINK = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?\s]+?)(?:\.git)?"
    r"(?:/(?:blob|tree|raw)/(?P<rev>[^/#?]+)(?:/(?P<path>[^#?\s]*))?"
    r"|/(?:pull/\d+/commits|commit)/(?P<commit_rev>[0-9a-fA-F]{7,40}))?"
    r"/?(?:#L?(?P<line>\d+)(?:-L?\d+)?)?$"
)
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def run(args: list[str], timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def fetch(job: tuple[Path, str, str, bool]) -> dict[str, object]:
    repos, repo, rev, pinned = job
    dest = repos / f"{repo.replace('/', '__')}@{rev}"
    out: dict[str, object] = {
        "repo": repo,
        "requested_rev": rev,
        "pinned": pinned,
        "dir": dest.name,
    }
    if (dest / ".git").exists():
        head = run(["git", "-C", str(dest), "rev-parse", "HEAD"])
        if head.returncode == 0:
            out["status"] = "ok"
            out["resolved_sha"] = head.stdout.strip()
            return out
    dest.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q", str(dest)])
    run(["git", "-C", str(dest), "remote", "add", "origin", f"https://github.com/{repo}.git"])
    r = run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", rev])
    if r.returncode != 0 and pinned:
        # Some servers refuse an arbitrary-SHA want; fall back to recent history.
        deep = run(["git", "-C", str(dest), "fetch", "-q", "--depth", "200", "origin"])
        if deep.returncode == 0 and run(
            ["git", "-C", str(dest), "cat-file", "-e", f"{rev}^{{commit}}"]
        ).returncode == 0:
            run(["git", "-C", str(dest), "checkout", "-q", rev])
            out["status"] = "ok"
            out["resolved_sha"] = run(
                ["git", "-C", str(dest), "rev-parse", "HEAD"]
            ).stdout.strip()
            return out
        out["status"] = "revision_unavailable"
        out["error"] = (r.stderr or deep.stderr).strip()[:300]
        return out
    if r.returncode != 0:
        out["status"] = "repo_unavailable"
        out["error"] = r.stderr.strip()[:300]
        return out
    run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"])
    out["status"] = "ok"
    out["resolved_sha"] = run(["git", "-C", str(dest), "rev-parse", "HEAD"]).stdout.strip()
    return out


def jobs_from(fc_root: Path, repos: Path) -> list[tuple[Path, str, str, bool]]:
    import analyze  # same directory; shares the single FC parser

    pairs = set()
    for row in analyze.parse_fc(fc_root):
        if not row["target_repo"]:
            continue
        rev = row["target_rev"] or "HEAD"
        pairs.add((repos, row["target_repo"], rev, bool(SHA_RE.match(rev))))
    return sorted(pairs, key=lambda job: (job[1], job[2]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fc", type=Path, required=True)
    parser.add_argument("--repos", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    args.repos.mkdir(parents=True, exist_ok=True)
    jobs = jobs_from(args.fc, args.repos)
    print(f"{len(jobs)} (repository, revision) pairs", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(fetch, jobs))
    for row in results:
        if row["status"] != "ok":
            print(f"{row['status']:22s} {row['repo']}@{row['requested_rev'][:12]}", file=sys.stderr)
    args.output.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    ok = sum(1 for row in results if row["status"] == "ok")
    print(f"fetched {ok}/{len(results)}", file=sys.stderr)


if __name__ == "__main__":
    main()
