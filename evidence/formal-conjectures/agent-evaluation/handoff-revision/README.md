# Attributed agent handoff revision

The first attributed agent evaluation found a sender-review benefit but no
clear receiver-continuation benefit. This package tests the resulting interface
change. It compares the original full audit bundle with a compact, rooted
handoff built from the same exact sender output.

Each of the 15 original treatment senders supplies one paired receiver task in
each condition. The compact handoff retains the source identity, sender output
root, verdict, consequential issue codes, layer outcomes, evidence locators,
witness, unresolved claims, authority limits, and next action. It omits the
large raw audit and source payloads. A receiver may request those bytes by
their retained locators; this evaluation asks whether they are necessary for
the immediate continuation decision.

Actor class is provenance, not a quality rank. Every receiver uses a fresh
GPT-5.6 Sol task context. The paired contexts share model, provider, runtime,
operator account, original sender, and ground truth. They are not independent
replications. No output changes Formal Conjectures or Vela authority state.

## Reproduce

```bash
python3 -B evidence/formal-conjectures/agent-evaluation/handoff-revision/build_handoff_revision.py
python3 -B evidence/formal-conjectures/agent-evaluation/handoff-revision/test_handoff_revision.py
python3 -B evidence/formal-conjectures/agent-evaluation/handoff-revision/run_handoff_revision.py
python3 -B evidence/formal-conjectures/agent-evaluation/handoff-revision/analyze_handoff_revision.py
```

The design and allocation are frozen before receiver execution. Runs are
append-only: an existing observation causes the runner to refuse rather than
retry.

The first execution attempt is retained under
`failed-attempt-01-invalid-schema/`. The provider rejected `uniqueItems` before
inference in all 30 contexts, so the attempt contains no model output. The
rooted execution amendment removes that unsupported keyword, keeps the outcome
schema and allocation fixed, and permits one amended run.
