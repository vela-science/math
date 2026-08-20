# Corrected-ordering Vela lifecycle fixture

Outcome: **PASS** for the single independently authorized replacement fixture.
The original failed fixture remains unchanged under
`evidence/vela-lifecycle-fixture/` and remains in the infrastructure
denominator.

## Authorization and immutable inputs

- Controlling producer: `50f0eba6c12422fa84a2d388af3ee928486618f6` /
  tree `c7140c6f9a760b56a5de84f5d4246d8fc36c479d`.
- Controlling evaluator: `03a15b4cda647ee24139921cbce10c47e780e655` /
  tree `0aa056d8bca4540ec8ad512833b4658272173f96`.
- PASS report/verdict SHA-256:
  `d1e948e1506153d3349a7c67893d70f78f648456ee9743672cb11289da362b57` /
  `426b57ed4f0ddb51425bfe0e73d3e5d57ddec05ef4d450dd81dee775f9646d26`.
- Corrected image digest:
  `sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e`;
  no image rebuild occurred.
- Review Method SHA-256 remained
  `03c3add32ac7f33c01afa084233ee2f43b1efc8a1b81873db5b995be0c0bc4e3`.
- The only executable change was V `prepare` ordering. Lifecycle SHA-256 moved
  from `669b68b9b7bff3b9ca7912c0693ecebccf769bc91d0f562b2516fe9eff659bbe`
  to `35f6b70adc1ad7dc6d70ea33769db80c8604ee306ef6e329a32f55f8ce09bf50`:
  the blind packet is still materialized outside the repository, `vela init`
  now runs against the empty `session/repo`, and the exact packet is copied and
  committed only after successful initialization. The ten V equivalence files
  changed only to bind this new adapter hash.

## Signed lifecycle

Exactly one `docker run --rm --network none` replacement fixture ran. It had
no OAuth or model mount, exited `0` in 5 elapsed seconds, and retained outer
stdout/stderr SHA-256
`c4cfff8f66ab86142bd99351330427a70110ce501f340265286d9e5347f498b8` /
`53859bb0328a4037e16a1ec25120fbb733d052f0c480311feded8782f9d70c40`.

All lifecycle command receipts exited `0`:

- init stdout SHA-256
  `aae6f29b571a11d237d4e45c107ec37f70598a747db54baff5762be77a2ac7fb`;
- Submission `vsb_33722f0776e05df4`, root
  `sha256:33722f0776e05df4013abe952179b6a5f8f9f59cb7771937fc4f653d83f5a79e`;
- Proposal `vpr_aff0c9c9ac1d47a6`, root
  `sha256:aff0c9c9ac1d47a67a5489c75152de96f60c77fc2ec8c858fad2d57d5a025f62`;
- Verification `vvr_b3e980319f24d991`, root
  `sha256:b3e980319f24d99157d3f2891aa998acad72272130ec48a848a816282a802236`,
  truthful outcome `fail`, method environment root
  `sha256:03c3add32ac7f33c01afa084233ee2f43b1efc8a1b81873db5b995be0c0bc4e3`;
- rooted reject used entry root
  `sha256:8989e4bedece167bd59933435ca903f1535bf45eb81861912eda21c78ff9ebd0`;
  Decision event `vev_70453acf93a79164` reports
  `scientific_state_changed:false` and final standing `rejected`;
- final disposable repository root
  `sha256:bc3e56d52da5eafa5af8991a8a817745eadee353858418a46fb0cf3e8eb0f486`,
  Git commit/tree `aca01bafd229478a181002b2cc587aa96c53fb8c` /
  `b182b3d247dc93be27b91495a299293fa210757d`;
- replay reports 0 accepted claims, 0 pending claims, one rejected review, one
  Submission, and one Verification. Status reports strict replay pass and zero
  blockers.

The retained Git log binds the init commit, candidate packet commit, signed
Submission commit, retained verdict/method commit, Verification commit, and
repository-authority reject commit in that order.

## Provider-loss and boundaries

The complete provider-loss bundle is 21,620 bytes, SHA-256
`4c5163f1027002148699409753dcf060f9cbc7cbe64974278c1d4b3831608ef5`.
`git bundle verify` reports complete history with `main` and `HEAD` at
`aca01bafd229478a181002b2cc587aa96c53fb8c`. Clone and full fsck exit `0`.
The reconstructed commit/tree exactly matches the source disposable
repository. Reconstructed replay/status/readback all exit `0`; readback is
byte-identical to the original (`a8c7e7fe...59236311`) and reports the rooted
rejection. Replay and status differ only in their truthful repository paths.
After these identities and both full fsck checks were retained, the two nested
disposable `.git` administrative directories were removed so the parent Math
repository would not encode them as unusable gitlinks. Both working trees and
the complete bundle remain; either repository is exactly recoverable with
`git clone provider-loss.bundle`.

Both disposable key files are absent after finalize. The inside-container scan
and final host scan pass; the host scan covered 248 files with zero findings.
Source/canonical pre/post receipts are byte-identical, SHA-256
`5f1c131852c65f1bb6f3e1ec019d035f895062e6cbf114bf5cdbfff13df9ad28`.
All four frozen source clones remain complete, clean, and unchanged; canonical
Math `.vela`/records/evidence/methods diff remains empty.

Denominator/accounting: two no-model infrastructure fixtures total—one prior
retained failure and this one pass; one authorized replacement attempt in this
delta; zero silent retries; zero candidate/evaluator/model/OAuth/credit
sessions; no Stage 2, launch receipt, source/provider mutation, or canonical
authority/Standing effect.
