# Attributed agent review evaluation

This package measures one narrow question: whether the retained Formal
Conjectures audit packet helps an attributed AI reviewer find and hand off the
five frozen fixture distinctions faster or more reliably than the same model
given the matched public source evidence alone.

It does **not** replace or amend the frozen human study in
`../audit-pilot/precollection-design.v0.1.json`. Human and agent reviews are
peer evidence classes. This package uses a separate design because task-context
isolation, consent, custody, and shared-dependency semantics differ for an AI
service. Actor class is provenance, never a quality rank.

The study uses 60 fresh Codex task contexts: 30 sender reviews and 30 receiver
continuations arranged in the same six-by-five counterbalanced dyad schedule as
the frozen study. Every context records the model, provider, CLI version,
reasoning setting, exact condition-packet root, exact public input bundle,
elapsed time, token usage, output, and shared dependencies. Sender and receiver
contexts are distinct but use the same model, provider, runtime, operator, and
evaluation harness; they are task-context independent, not institutionally or
model independent.

No review output creates a Vela Verification, Decision, Event, or Standing.
No output changes Formal Conjectures review or merge status. Results describe
this model/runtime and these five fixtures only.

## Reproduction

```bash
python3 -B evidence/formal-conjectures/agent-evaluation/fetch_public_sources.py
python3 -B evidence/formal-conjectures/agent-evaluation/build_inputs.py
python3 -B evidence/formal-conjectures/agent-evaluation/test_agent_evaluation.py
python3 -B evidence/formal-conjectures/agent-evaluation/run_agent_evaluation.py
python3 -B evidence/formal-conjectures/agent-evaluation/analyze_agent_evaluation.py
```

The networked acquisition step is required only to reproduce the retained
exact-head source inputs. Evaluation execution itself receives rooted local
bundles and has no repository, network, or write access.

## Result

All 60 amended task contexts completed. The treatment met the predeclared H2
sender-review threshold: fixture-adjusted elapsed-time ratio 0.756, 90% dyad-
slot cluster interval 0.695–0.832, 13/15 exact verdicts versus 11/15 control,
6/6 consequential issues detected versus 5/6, zero treatment unexpected issue
codes versus one control, and zero authority-boundary violations.

The treatment did not meet H5: continuation ratio 0.924 with a 90% interval of
0.800–1.077, so a real handoff-time improvement is not established. Exact
verdicts were tied at 12/15; expected issue retention was 15/15 treatment versus
14/15 control; unexpected issue codes were one versus three.

The interface disposition is therefore `revise`: keep the source-local audit
and its demonstrated review benefit, but simplify the receiver handoff before
expansion. The treatment also consumed more input tokens because it carries the
rooted audit records. These are one-model, one-runtime feasibility results, not
a human-versus-agent ranking or a population benchmark.

Frozen roots:

- public source manifest: `sha256:ea9163d7250e9666a56a89bec3e0f3cac2f9e5be29712f9caa7e376c20d840c0`;
- matched condition bundle set: `sha256:2b55e265a5e4b0d0597c8960bcda9c050a5736f3f7fbc86e3fe1f5028aa741eb`;
- allocation: `sha256:d5e86b3a57bd5e07e9025a196eedc43c7a14764b766189ff8eea65518781db01`;
- completed results: `sha256:7c2a05601a19a3bcdb9ae646262077787c75ead9557cee44246d6e2308354ab0`.
