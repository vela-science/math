#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, shutil, sqlite3


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def digest(data): return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("common_packet", type=pathlib.Path)
    parser.add_argument("output_dir", type=pathlib.Path)
    args = parser.parse_args()
    if not (args.common_packet / "result.json").is_file(): raise SystemExit("missing result.json")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    blind = args.output_dir / "blind-bundle"
    organization = args.output_dir / "organization-only"
    blind.mkdir(); organization.mkdir()
    for name in ("result.json", "artifacts", "commands"):
        source, destination = args.common_packet / name, blind / name
        if source.is_dir(): shutil.copytree(source, destination)
        elif source.is_file(): shutil.copy2(source, destination)
    files = sorted(p for p in blind.rglob("*") if p.is_file())
    objects, edges = [], []
    for path in files:
        rel, data = path.relative_to(blind).as_posix(), path.read_bytes()
        object_id = "sha256:" + digest(data)
        objects.append({"id": object_id, "kind": "result" if rel == "result.json" else "artifact", "path": rel, "sha256": digest(data), "payload_json": None})
        edges.append({"src": "session:fixture", "dst": object_id, "relation": "retains"})
    graph = {"schema": "results-breakthrough-simple-graph.v1", "objects": objects, "edges": edges, "events": [{"seq": 1, "kind": "retained", "actor": "producer", "object_id": "session:fixture", "receipt_json": {}}]}
    (organization / "graph.json").write_text(canonical(graph) + "\n", encoding="utf-8")
    database = organization / "graph.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA page_size=4096"); connection.execute("PRAGMA journal_mode=OFF"); connection.execute("PRAGMA synchronous=OFF")
    connection.executescript("CREATE TABLE objects(id TEXT PRIMARY KEY,kind TEXT NOT NULL,sha256 TEXT NOT NULL,payload_json TEXT);CREATE TABLE edges(src TEXT NOT NULL,dst TEXT NOT NULL,relation TEXT NOT NULL,PRIMARY KEY(src,dst,relation));CREATE TABLE events(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,actor TEXT NOT NULL,object_id TEXT NOT NULL,receipt_json TEXT NOT NULL);")
    connection.executemany("INSERT INTO objects VALUES(?,?,?,?)", [(o["id"],o["kind"],o["sha256"],o["payload_json"]) for o in objects])
    connection.executemany("INSERT INTO edges VALUES(?,?,?)", [(e["src"],e["dst"],e["relation"]) for e in edges])
    event=graph["events"][0]; connection.execute("INSERT INTO events VALUES(?,?,?,?,?)",(event["seq"],event["kind"],event["actor"],event["object_id"],canonical(event["receipt_json"])))
    connection.commit(); connection.execute("VACUUM"); connection.close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
