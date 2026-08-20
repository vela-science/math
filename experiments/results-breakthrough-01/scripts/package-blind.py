#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, shutil


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--session", required=True, type=pathlib.Path)
    parser.add_argument("--blind-label", required=True, choices=["X","Y","Z"])
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args=parser.parse_args()
    source=args.session/"blind-bundle"
    if not source.is_dir() or args.output.exists(): raise SystemExit("invalid blind packaging paths")
    shutil.copytree(source,args.output)
    files=[]
    for path in sorted(p for p in args.output.rglob("*") if p.is_file()):
        data=path.read_bytes(); files.append({"path":path.relative_to(args.output).as_posix(),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    manifest={"schema":"results-breakthrough-blind-bundle.v1","blind_label":args.blind_label,"files":files,"organization_bytes_included":False}
    (args.output/"blind-manifest.json").write_text(json.dumps(manifest,sort_keys=True,separators=(",",":"))+"\n")
    return 0


if __name__ == "__main__": raise SystemExit(main())
