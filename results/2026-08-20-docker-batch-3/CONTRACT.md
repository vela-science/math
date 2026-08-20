# Batch 3 candidate packet contract

Each of the ten assigned sessions is one denominator entry. There are no
silent retries. A process failure, invalid packet, abstention, or duplicate is
retained as its assigned result.

Candidate JSON must satisfy `result.schema.json`. In particular:

- `proposed_result` is a nonblank string even for a typed non-result;
- `result_status` distinguishes a checked proof, computational certificate,
  proof sketch, statement correction, dependency finding, and typed
  non-result;
- a proof sketch is never described as checked;
- a computational claim must cite the exact command and stdout retained in
  the session's `tool-calls.json`, or a retained certificate artifact;
- process exit success is not mathematical or Lean validation;
- exact source commits, paths, assumptions, dependencies, and limitations are
  retained;
- no candidate changes Vela authority or scientific standing.

The producer retains each unedited candidate packet, command, exit code, and
exact command output. Any later check is a separate producer-side fact, not a
silent promotion of the candidate's status.
