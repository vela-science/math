#!/usr/bin/env python3
import argparse
import hashlib
import pathlib
import subprocess


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vela-repo", required=True, type=pathlib.Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    args = parser.parse_args()
    expected = args.manifest.read_text().splitlines()
    actual = ["mode\ttype\tgit_oid\tsha256\tbytes\tpath"]
    for record in git(args.vela_repo, "ls-tree", "-r", "-z", args.commit).split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split(" ")
        data = git(args.vela_repo, "cat-file", "blob", oid)
        actual.append(f"{mode}\t{kind}\t{oid}\t{hashlib.sha256(data).hexdigest()}\t{len(data)}\t{path.decode()}")
    if actual != expected:
        raise SystemExit("Vela build context differs from frozen manifest")
    print(f"context_files={len(actual) - 1}")
    print("context_manifest=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
