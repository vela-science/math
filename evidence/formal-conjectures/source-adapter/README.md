# Formal Conjectures source adapter

This directory is Math's bounded, read-only adapter for the public Formal
Conjectures PR audit package at commit
`4b5df9dcc7f7f3458b593aa816b7a2476d71f8e5`. It copies the five exact core and
five exact observation records, the two source schemas, the source validator,
the packet README, and the Apache-2.0 license. No network access is needed to
validate or rebuild the Math projection.

`projection.v1.json` preserves the native pull-request identity, exact base and
head revisions, complete changed-path inventory, source-local checks and their
conditions, observation-time status, and the source record roots. It does not
copy the source packet's underlying Lean files, tool outputs, or acquisition
receipts. Those omissions are explicit in the rooted method and projection.

Every source outcome remains on the source axis. In particular, `unavailable`
means required source evidence was unavailable in that audit scope. It is not a
Vela Verification outcome and is never mapped to `fail`, `error`,
`inconclusive`, or `pass`. No audit result, review, approval, merge, or package
publication changes Math Standing. Only an authorized human Decision can do
that.

Run the offline gates with:

```bash
python3 -B evidence/formal-conjectures/source-adapter/test_adapter.py
python3 -B evidence/formal-conjectures/source-adapter/build.py --check --print-root
```
