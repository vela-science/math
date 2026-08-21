# Independent review: Math Result Runner Vela 0.977.4 repin

Verdict: **PASS**

Reviewed producer commit `50e0846dcc6751e358fb047f4841f6fa50bb4d9b`
and tree `79e9482b9abe6999d36d63b1cfc62f6f964bda53`, whose sole parent is
canonical Math merge `7a535164d1a5f1139997f875a586f58fce7e2563`.
The remote feature ref and `origin/main` resolved to those frozen heads during
review.

## Findings

- The maintained runner remains byte-identical at SHA-256
  `6e5ea0fef6f7e4459061b723314b4aec56055ff303b8b110a21710f911644432`.
  The code change is the bounded disposable-Vela adapter correction at SHA-256
  `c96369703ed43b63539e3128ad1771d5fe54a36e8f63ad045529115902033dc7`:
  its existing `finally` guard now removes the full disposable HOME and fails
  closed if authority or actor key material remains. The regression tests cover
  failures after private-key creation, after public-key creation, and during
  `ssh-add`, plus successful final cleanup.
- `PIN.json` recomputes to
  `24e2282e151b1feb53072da58be81cbc561d35890c8248b3c46c8852b2e31c0f`.
  The source-owned `allowed_signers` blob and retained release-manifest bytes
  match their bound Git blob and SHA-256 values. OpenSSH verification accepted
  the detached release-manifest signature for `release@vela.space` in namespace
  `vela-release`.
- The annotated tag object is
  `388c3a5d1b71a8b6dacfcfa17ffcd395710f3858` and points to source commit/tree
  `1a2e0328620b4e8c4584c3d4baf257adb11f3d45` /
  `1bd8ed4e11d3745f159b32f23539f5174fd44803`. GitHub's immutable tag-object
  response reported `verified=true`, `reason=valid`. The source commit reports
  signature status `E`; the producer does not claim direct commit-signature
  verification.
- A fresh download of `vela-macos-aarch64.zip` produced 2,713,635 bytes and
  SHA-256 `023bf4d98766e9d7b1d0c7504fcade78220b3fe4f544daca1faaeace98d25d65`.
  Its sole executable reports `vela 0.977.4` and recomputes to
  `06f912d107d29e4ce1dadd19bf7ef849ec42d7e62cbc9332c9807e6b8c9bd05e`.
- Both final retained runs have exact summary hashes
  `5a5d2a538a77ee1531948d404bb2bc418290150bb8f50d166774801813607c6b`
  and `49fb2fd1f85ce33ac1a906deabef9903f525660f21ee1bef9610122850993ef3`.
  Independent parsing checked all 16 command receipts, their stdout/stderr
  hashes and exits, then replayed the adapter's lifecycle assertions. Each run
  contains one Submission, one truthful failing Verification, one rooted reject
  Decision, strict status/show/replay, zero accepted Claims, and
  `scientific_state_changed=false`. Repository roots recompute to the two roots
  recorded in `PIN.json`.
- Runs 1 and 2 remain retained as two operational cleanup failures. Their
  summary hashes match `PRE-FIX.json`; neither counts as a qualification pass,
  provider request, benchmark denominator entry, or scientific claim.
- The historical provider packet is unchanged from the canonical parent. Its
  manifest recomputes to
  `4546a3b38537ba7d146a3e6e81a865edfca71cc7dccab3ef4daee714542f49ce`
  with 35 declared regular files, no missing, extra, or duplicate paths, and
  exact size/hash matches. This repin made no provider request.
- Ruff 0.5.4 format/check, Python 3.11.2 compilation, and all 18 focused tests
  passed against the downloaded exact Vela binary. The tests included the
  signed disposable lifecycle and hostile cleanup, path, schema, output-bound,
  and late-file cases.
- A fresh remote clone reproduced commit/tree
  `50e0846dcc6751e358fb047f4841f6fa50bb4d9b` /
  `79e9482b9abe6999d36d63b1cfc62f6f964bda53`, archive SHA-256
  `31fbd97f6352f93881f1450e8c22b40aeb8a17f3c9bad8aa5b961a0a1366fa89`,
  and dry receipt SHA-256
  `d9a0f2faa3417ea70011c5f334a2a1fe5dc2a4b4988bbbf0203ee69b61012d6a`.
  The unchanged Docker image resolved on `desktop-linux` as `linux/arm64`.
  A network-none stdin sentinel over the feature clone exited 0 with stdout
  SHA-256 `8073252a57ee9f6d5879b5d4e3e0f46f34b4ea47e229d845029834483367b661`.
- A scan of all 80 tracked files in the new qualification packet found zero
  provider-key, bearer-token, OAuth/API-value, or private-key markers. The live
  signed test left neither the disposable private directory nor disposable
  HOME. All review execution used temporary repositories and disposable Vela
  authority only.

## Scope of PASS

This PASS authorizes merge consideration for this exact producer commit and
tree. Any byte change requires another review. The verdict covers operational
runner compatibility with the pinned Vela 0.977.4 artifact. It establishes no
scientific result, external validation, source-owner acceptance, canonical
authority action, or Standing change.
