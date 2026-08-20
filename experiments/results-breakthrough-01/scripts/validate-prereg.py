#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, re, sqlite3, subprocess


def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def git(repo, *args): return subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE).stdout


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True,type=pathlib.Path)
    parser.add_argument("--math",required=True,type=pathlib.Path)
    parser.add_argument("--fc",required=True,type=pathlib.Path)
    parser.add_argument("--lean-proofs",required=True,type=pathlib.Path)
    parser.add_argument("--vela",required=True,type=pathlib.Path)
    parser.add_argument("--evaluator",required=True,type=pathlib.Path)
    args=parser.parse_args(); root=args.root.resolve()
    json_files=sorted(root.rglob("*.json"))
    values={p:json.loads(p.read_text()) for p in json_files}
    unresolved="<UN"+"RESOLVED>"
    text_files=(p for p in root.rglob("*") if p.is_file() and (p.name=="Dockerfile" or p.suffix in {".json",".md",".py",".sh",".tsv",".txt"}))
    if any(unresolved in p.read_text() for p in text_files): raise SystemExit("unresolved marker found")
    if list(root.rglob("__pycache__")) or list(root.rglob("*.pyc")): raise SystemExit("compiled cache found")

    evaluator=values[root/"EVALUATOR-LOCK.json"]
    stage=evaluator["stage1"]
    assert git(args.evaluator,"rev-parse",stage["freeze_commit"]+"^{tree}").decode().strip()==stage["freeze_tree"]
    assert git(args.evaluator,"rev-parse",stage["receipt_commit"]+"^{tree}").decode().strip()==stage["receipt_tree"]
    assert sha(git(args.evaluator,"show",stage["freeze_commit"]+":RUBRIC.md"))==stage["rubric_sha256"]
    review=evaluator["producer_review"]
    assert git(args.evaluator,"rev-parse",review["evaluator_commit"]+"^{tree}").decode().strip()==review["evaluator_tree"]
    assert sha(git(args.evaluator,"show",review["evaluator_commit"]+":reviews/prereg-0bbf3b8/REPORT.md"))==review["report_sha256"]
    assert sha(git(args.evaluator,"show",review["evaluator_commit"]+":reviews/prereg-0bbf3b8/verdict.json"))==review["verdict_sha256"]

    assignments=values[root/"assignments.json"]
    cells=assignments["smoke_sequence"]+assignments["post_smoke_sequence"]
    assert len(cells)==len(set(cells))==30
    for target in [f"T{i:02d}" for i in range(1,11)]:
        assert sorted(cell.split("-")[1] for cell in cells if cell.startswith(target+"-"))==["G","N","V"]
    assert assignments["stage2_held_out_aggregate_sha256"] is None

    repo_by_uri={
        "https://github.com/google-deepmind/formal-conjectures.git":args.fc,
        "https://github.com/vela-science/math.git":args.math,
    }
    common=(root/"prompts/common-objective.txt").read_bytes()
    parameters=(root/"runtime/parameters.json").read_bytes(); tools=(root/"runtime/tool-allowlist.json").read_bytes()
    wrappers=[(root/"prompts"/f"arm-{arm}.txt").read_bytes() for arm in ("N","G","V")]
    assert len(set(wrappers))==1
    runtime_parameters=values[root/"runtime/parameters.json"]
    assert runtime_parameters["scientific_output_budget"]==8192
    assert runtime_parameters["scientific_output_budget_unit"]=="utf8_bytes_in_result_json"
    assert runtime_parameters["mounts"]["producer_facts"]=="/inputs/producer-facts:ro"
    readers=[values[root/"readers/reader-1.json"],values[root/"readers/reader-2.json"]]
    assert [r["reader"] for r in readers]==["independent-byte-reader","independent-semantic-reader"]
    assert all(r["verdict"]=="pass" and not r["discrepancies"] and r["candidate_output_accessed"] is False for r in readers)
    for target in [f"T{i:02d}" for i in range(1,11)]:
        pack=values[root/"fact-packs"/f"{target}.json"]
        lines=[]
        for fact in pack["facts"]:
            assert fact["fact_id"] not in [json.loads(line)["fact_id"] for line in lines]
            source=fact["source"]
            if source["uri"]=="producer-preregistration": data=(root/source["path"]).read_bytes()
            else: data=git(repo_by_uri[source["uri"]],"show",f'{source["commit_or_version"]}:{source["path"]}')
            assert len(data)==fact["byte_length"] and sha(data)==fact["payload_sha256"]
            lines.append(canonical({k:fact[k] for k in ("fact_id","payload_sha256","byte_length","role")}))
        computed=sha(("\n".join(lines)+"\n").encode())
        assert computed==pack["scientific_fact_root"]
        card=(root/"cards"/f"{target}.json").read_bytes(); normalized=sha(common+b"\n"+card)
        manifests=[values[root/"equivalence"/f"{target}-{arm}.json"] for arm in ("N","G","V")]
        assert {m["scientific_fact_root"] for m in manifests}=={computed}
        assert {m["normalized_prompt_sha256"] for m in manifests}=={normalized}
        assert len({canonical(m["runtime"]) for m in manifests})==1
        for manifest in manifests:
            assert manifest["reader_verdicts"]==[{"reader":r["reader"],"verdict":r["verdict"],"discrepancies":r["discrepancies"]} for r in readers]
            assert manifest["runtime"]["parameters_sha256"]==sha(parameters)
            assert manifest["runtime"]["tool_allowlist_sha256"]==sha(tools)
            for organization in manifest["organization_files"]:
                assert sha((root/organization["path"]).read_bytes())==organization["sha256"]

    duplicates=values[root/"duplicates/index.json"]
    assert duplicates["target_count"]==10 and len(duplicates["records"])==10
    for record in duplicates["records"]:
        expected=3 if record["target_id"]=="T02" else 0
        assert len(record["exact_declaration_matches"]["math"])==expected
        assert len(record["exact_declaration_matches"]["lean_proofs"])==0
    assert values[root/"duplicates/T02.json"]["external_linked_commits_present_in_mounted_fc_objects"]=={
        "6c7a16e8998d1c597fa2a5c6329bc9301fcc56e2":False,
        "6ac8d0cbe1a85e71747c62c1391a84788015ebc1":False,
    }

    dockerfile=(root/"Dockerfile").read_text()
    from_lines=[line for line in dockerfile.splitlines() if line.startswith("FROM ")]
    assert len(from_lines)==2 and all("@sha256:" in line for line in from_lines)
    assert "af94b40fa642620275e6d617be97a542" in dockerfile
    build=values[root/"build/BUILD-LOCK.json"]
    assert sha((root/"Dockerfile").read_bytes())==build["dockerfile_sha256"] and build["authorized_now"] is False
    subprocess.run(["python3",str(root/"scripts/verify-vela-context.py"),"--vela-repo",str(args.vela),"--commit",build["vela_commit"],"--manifest",str(root/"build/vela-context.tsv")],check=True,stdout=subprocess.PIPE)

    common_result=(root/"fixtures/common/result.json").read_bytes()
    for arm in ("native","graph"):
        fixture=root/"fixtures"/arm; receipt=values[fixture/"receipt.json"]
        assert receipt["model_sessions"]==0 and receipt["network"]=="none" and receipt["scientific_claim"] is False
        assert (fixture/"blind-bundle/result.json").read_bytes()==common_result
        for record in receipt["files"]:
            data=(fixture/record["path"]).read_bytes(); assert len(data)==record["bytes"] and sha(data)==record["sha256"]
    assert (root/"fixtures/native/blind-bundle/artifacts/fixture.txt").read_bytes()==(root/"fixtures/graph/blind-bundle/artifacts/fixture.txt").read_bytes()
    mount_receipt=values[root/"fixtures/source-mount-receipt.json"]
    assert mount_receipt["outcome"]=="pass"
    source_bindings=values[root/"runtime/source-bindings.json"]
    assert {
        record["name"]: (record["commit"],record["tree"],record["git_archive_tar_sha256"])
        for record in mount_receipt["repositories"]
    }=={
        name: (binding["commit"],binding["tree"],binding["git_archive_tar_sha256"])
        for name,binding in source_bindings.items()
    }
    db=root/"fixtures/graph/organization-only/graph.sqlite"; connection=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    assert connection.execute("pragma integrity_check").fetchone()[0]=="ok"
    assert [connection.execute(f"select count(*) from {t}").fetchone()[0] for t in ("objects","edges","events")]==[2,2,1]
    connection.close()

    source=values[root/"SOURCE-LOCK.json"]
    bundle=pathlib.Path(source["repositories"]["evaluator"]["bundle"]["external_path"])
    assert bundle.stat().st_size==source["repositories"]["evaluator"]["bundle"]["bytes"] and sha(bundle.read_bytes())==source["repositories"]["evaluator"]["bundle"]["sha256"]
    assert not (root/"launch/start-receipt.json").exists()
    sensitive=re.compile(rb"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----|Authorization:\s*Bearer\s+\S+|\"(?:access_token|refresh_token)\"\s*:\s*\"[^\"]+\"",re.I)
    for path in root.rglob("*"):
        if path.is_file() and sensitive.search(path.read_bytes()): raise SystemExit(f"credential-like bytes: {path}")
    print(f"json_files={len(json_files)}")
    print("targets=10")
    print("cells=30")
    print("equivalence_manifests=30")
    print("independent_readers=2")
    print("candidate_inference=false")
    print("validation=pass")
    return 0


if __name__=="__main__": raise SystemExit(main())
