# Runner end-to-end qualification

Outcome: **PASS**.

One tiny, non-scoring provider inference completed in the accepted Docker Desktop image with Codex 0.145.0 running from `/repo`, the mounted genuine clean Math Git checkout. The exact structured output was:

```json
{"message":"Codex executed inside the mounted Git repository.","qualification":"pass"}
```

Its SHA-256 is `b6a44156d823d6d149f7361154deda2f2a9fd15b72fea740dd34bc65e4c11d83`. The same bytes passed through the existing native Git recorder, JSON/SQLite graph recorder, and a disposable network-disabled Vela Submission → Verification → rooted rejection Decision → show/status/replay lifecycle.

The first CLI launch is permanently retained as a pre-provider setup failure: making the whole container root read-only prevented Codex's in-process app-server initialization. The single correction removed only that flag; the Git source checkout and OAuth file stayed read-only. The corrected launch made the run's only provider request and exited zero in 10 seconds.

Source commit `5de716c896065c03c0a470d015ba2a328a527f73`, tree `56e37a5058c80e69f3c343b8ae624c08b5417229`, clean status, complete-clone state, and archive digest are byte-identical before and after. Credential scans retain no secret bytes. Vela replay is strict PASS, with zero accepted claims and one rejected qualification-only Proposal; the disposable authority key was deleted.

This qualification has no benchmark denominator and makes no scientific, comparative, utility, truth, independence, source-authority, or Standing claim. It does not reopen RESULTS-BREAKTHROUGH-01.
