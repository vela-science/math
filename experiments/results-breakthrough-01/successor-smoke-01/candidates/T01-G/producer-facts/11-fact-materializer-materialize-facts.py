#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, shutil


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--experiment-root",required=True,type=pathlib.Path)
    parser.add_argument("--fact-pack",required=True,type=pathlib.Path)
    parser.add_argument("--output",required=True,type=pathlib.Path)
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit("materialized fact directory already exists")
    args.output.mkdir(parents=True)
    pack=json.loads(args.fact_pack.read_text()); records=[]
    for index,fact in enumerate(pack["facts"]):
        source=fact["source"]
        if source["uri"]!="producer-preregistration": continue
        original=args.experiment_root/source["path"]
        data=original.read_bytes()
        if len(data)!=fact["byte_length"] or hashlib.sha256(data).hexdigest()!=fact["payload_sha256"]:
            raise SystemExit(f"producer fact mismatch: {fact['fact_id']}")
        name=f"{index:02d}-{fact['fact_id']}-{original.name}"
        target=args.output/name; shutil.copy2(original,target)
        records.append({"fact_id":fact["fact_id"],"path":name,"bytes":len(data),"sha256":fact["payload_sha256"]})
    manifest={"schema":"results-breakthrough-materialized-facts.v1","scientific_fact_root":pack["scientific_fact_root"],"files":records}
    (args.output/"manifest.json").write_text(json.dumps(manifest,sort_keys=True,separators=(",",":"))+"\n")
    return 0


if __name__=="__main__": raise SystemExit(main())
