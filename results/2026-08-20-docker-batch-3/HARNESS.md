# Harness receipt

The exact Docker identity verified before inference. The first parallel launch
of sessions 1–5 exited before model inference with exit code 1 and the identical
message `No prompt provided via stdin.` (elapsed 0.77–0.84 seconds each). Docker
stdin had not been attached.

The invocation was corrected once by adding ordinary `docker run -i`. No prompt
had reached a model, no candidate packet existed, and no session credit was
consumed by those five pre-inference exits. The corrected invocation then ran
the ten assigned sessions once each. There were zero model retries and no
second materially identical setup failure.
