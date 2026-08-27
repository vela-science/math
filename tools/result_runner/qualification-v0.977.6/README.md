# Vela 0.977.6 Math consumer qualification

This directory is the active signed Vela pin for Math strict reads and the
maintained Result Runner. It is bounded consumer/documentation qualification
evidence. It makes no scientific claim and has no authority or Standing
effect.

`release/` retains the exact public macOS arm64 release manifest, detached
OpenSSH signature, checksum sidecar, and source-owned `allowed_signers`
preimage. The signature verifies as `release@vela.space` in namespace
`vela-release`. The manifest binds tag `v0.977.6`, source commit
`9ac8e7730bfb63a3b8eb1d2e1d91081c3e703c59`, source tree
`1332713f627ac73c235e4f9a7afe206499717154`, archive SHA-256
`62ea9006e086b40f0431b2ce2cf74827518f37dc58e329353920083f50dad874`,
and binary SHA-256
`5b21415c98503b20518c0e68714b0b4f4b3c371525ea110563b89a53a0d3dbb3`.
The release distribution key is not a Repository-authority key.

`math-read/` retains exact CLI JSON stdout from a complete, clean public clone
of Math base `cf6d76687b205a39e2515e9fec7087c819454d2f` / tree
`f8e9e8d3b99226ed6bba62026396d5f17ea9351e`. No output was canonicalized.
The fixed qualification path is recorded by status/replay as emitted; it is a
disposable `/private/tmp` path and contains no user-home or credential path.
The two projection outputs are byte-identical and path-neutral.

Strict replay passes with Repository root
`sha256:a956b84c437202e5a02cc9e036a621bd14a302b34a75758115730bdbb77c52a4`,
three accepted Claims, zero pending review, unchanged authority keyset/policy,
and projection root
`sha256:b1cfb5e64c2046ed2b4ce5c9f9551e582004f4df31c402b417eb3c2159271138`.
The projection declares `authority_effect: none`.

The complete existing Result Runner test suite passed 30 of 30 tests under the
exact 0.977.6 binary, including its signed disposable rejection lifecycle.
Compileall and Ruff formatting passed. A plain Ruff 0.5.4 check reported three
pre-existing `E402` findings in unchanged out-of-scope import-bootstrap lines;
the exact limitation is retained in `disposable/qualification.json`. No model
or provider request was made, and the historical provider qualification was
not rerun.

This commit changes the enclosing Git tree by adding these receipts and
updating consumer documentation. Git tree identity covers every tracked file;
the Vela Repository root covers the canonical scientific-state manifest and
its rooted objects. Because `.vela/`, `records/`, `evidence/current/`, and
`methods/current/` remain byte-identical, the new Git tree does not create an
Event, Decision, authority mutation, or change in Standing.
