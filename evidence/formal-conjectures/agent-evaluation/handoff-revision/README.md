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

## Result

The amended run completed all 30 fresh receiver contexts. The compact handoff
preserved the same 13/15 exact verdicts, 15/15 expected issue detections, 15/15
complete provenance bindings, zero unexpected issue codes, and zero authority
violations as the full bundle.

Its paired elapsed ratio was `0.9139`; the 90% sender-pair interval was
`0.8725` to `0.9556`. That is a bounded observed improvement, but it misses the
frozen `<= 0.80` support threshold. The hypothesis and generated interface
disposition therefore remain `false` and `revise`. Input use fell from 478,709
to 225,085 tokens, while output and reasoning tokens also fell.

`program-disposition.v0.2.json` records a separate operational choice: adopt
the compact handoff for receiver input and keep the full audit available by
rooted locator. It does not rewrite the negative threshold result or require
another evaluation before internal closeout.
