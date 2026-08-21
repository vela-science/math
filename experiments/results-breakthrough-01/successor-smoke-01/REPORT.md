# RESULTS-BREAKTHROUGH-01 successor smoke terminal report

Outcome: **STOP — shared pre-inference infrastructure failure**.

The frozen freshness gate passed and the append-only start receipt assigned the fresh six-cell ITT denominator. All six candidate commands then ran once, sequentially and in the frozen order. Every invocation reached the Codex CLI but exited before provider inference with:

```text
Not inside a trusted directory and --skip-git-repo-check was not specified.
```

The frozen runner mounts an empty `/work` directory and neither initializes it as Git nor supplies Codex's repository-check override. The exact runner cannot be changed within this run. No retry, substitution, prompt/source/input edit, or additional preflight occurred.

## Accounting

- Fresh candidate denominator: 6/6 assigned; 6 infrastructure failures; 0 model attempts; 0 usable cells.
- Candidate CLI invocations: 6. Credit-relevant OAuth inference sessions: 0.
- Evaluator sessions: 0/2 executed. Recovery sessions: 0.
- Provider-reported incremental cost: unavailable; no invocation reached provider inference.
- Predecessor abort histories and costs remain separate and are not included here.

Each cell has an empty stdout digest `e3b0c442…b855`, identical retained stderr digest `d82a9144…9e1`, exit 1, a passing zero-finding credential scan, exact prompt/fact bytes, and no `result.json` or `blind-bundle`.

## Why evaluation did not run

The held-out contract requires the neutral custodian to package substantive locked outputs as X/Y/Z bundles before exactly two blinded evaluator sessions. No candidate produced an answer or bundle. Creating synthetic answers, assigning labels without the custodian mapping, or asking evaluators to score non-existent results would violate the frozen evaluator-visible answer contract. Thus packaging, evaluator inference, mapping reveal, and recovery were not reached.

## Smoke gate and integrity

The smoke gate fails and stops: information-equivalent result bundles, blind-package replay, four usable cells, and one usable cell per target are absent. NO_VALUE and paired scientific comparisons are not applicable because no scientific verdict exists.

Producer HEAD remained `d18d0d6002a6d5ef85320f705e2bbf99c2afe203` / tree `7911c4076cbcdee8c7e44968ccf6c2caa59b3458` throughout execution. Docker remained `desktop-linux` with accepted image `sha256:76c64845…08e7e`. All four source mounts remain exact, clean, complete, and non-shallow; canonical tracked records are unchanged; six secret scans report zero findings; Stage 2 map/key/seed were not accessed or revealed; no Vela lifecycle or authority action occurred.

The smallest handoff is independent review of this retained six-cell failure packet. Any repair—initializing `/work` as a disposable Git repository or freezing the Codex repository-check override—requires a distinct preregistration; this run cannot be patched or resumed. T03–T10 remain uninvoked.
