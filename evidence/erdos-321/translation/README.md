# Erdős 321 translation experiment

This directory is one source-local experiment over the corrected Erdős 321
case. It adds no Vela protocol object and has no authority effect.

`build.py` deterministically produces:

- W3C Web Annotation selectors over two exact retained Lean source snapshots;
- a closed, RFC 8785-rooted semantic fact diff between correspondence v1 and v2;
- an explicit loss report;
- a Workflow Run RO-Crate 0.5 / RO-Crate 1.3 package with PROV-O relations; and
- a source-snapshot manifest and workflow description.

Every quote must occur exactly once in the retained source bytes. Missing or
ambiguous selectors fail instead of attaching to a nearby declaration. The
semantic fact set omits generated prose and keeps the raw sources beside it.

Verify without the network:

```bash
python3 evidence/erdos-321/translation/build.py --check
uvx --from roc-validator rocrate-validator validate \
  evidence/erdos-321/translation -v --no-paging -f json
```

The current `roc-validator` validates all 55 required inherited Workflow Run
RO-Crate 0.5 checks. It does not yet ship an RO-Crate 1.3 validation profile;
the metadata uses the official 1.3 context and is separately expanded as
JSON-LD during qualification.

The experiment does not compare the Star Fleet terminal theorem with Formal
Conjectures' solved lower or upper variants, rerun Lean, establish general
semantic-diff accuracy, or change Standing. Those losses are explicit in
`semantic-loss.v1.json`.
