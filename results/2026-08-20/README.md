# Three Result candidates from the August audits

These are three bounded, rights-safe Result candidates selected from current
source heads. They are ordinary review packets, not a registry or a new Vela
object. They retain locators and short factual observations only; no
third-party source is copied here.

Math was refreshed from `origin/main` at
`d03e736d3ada31b5cfc02507d99e54f04d335b66` before this work began. All four
cited upstream repositories were still at the exact revisions resolved by
the audits on 2026-08-20.

| Candidate | Classification | Exact source heads | Source owner | One next human action |
| --- | --- | --- | --- | --- |
| `math-result-candidate-erdos-321-status-conflict-2026-08-20` | known-result / open-status conflict | `google-deepmind/formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`; `teorth/erdosproblems@931e7db4ee3c97705598f802e8358a201b9e422c` | the two repositories' maintainers, with `teorth/erdosproblems` owning the informal status | Resolve existing Formal Conjectures issue [#4444](https://github.com/google-deepmind/formal-conjectures/issues/4444) by determining whether `solved` covers the exact or an asymptotic occurrence before changing either source or Math Standing. |
| `math-result-candidate-erdos-750-conditional-stiebitz-2026-08-20` | conditional statement / scope | `google-deepmind/formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`; `Shashi456/erdos-formalizations@286f856aa3fc08957b80950fd18a45aab8d045ea` | `Shashi456/erdos-formalizations` owns the proof; Formal Conjectures owns the conditional label | The proof owner decides whether to sponsor or accept a proof of `Erdos750.stiebitz_lower_bound`; until then the link remains conditional. |
| `math-result-candidate-erdos-56-transitive-native-decide-2026-08-20` | trust disclosure that changes downstream use | `google-deepmind/formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`; `plby/lean-proofs@bebe632f2f6227a40e00b145bfbf7b3e1d68f8c2` | `plby/lean-proofs` owns the proof and its trust policy; Formal Conjectures owns its link classification | The proof owner states whether compiled reduction is intended for this Result and whether a contribution replacing it is welcome; the linked `src/v4.24.0` project and repository root have no licence file, so no source patch should be prepared first. |

## Authority boundary

- Source status is what the named upstream repository says at the named
  commit. It is not a Vela Decision.
- Mechanical verification is the recorded exact checkout build and axiom
  reading. It does not establish statement fidelity or acceptance.
- Review evidence consists of the current audit artifacts and the existing
  upstream issues named in each packet. It is not source-owner agreement.
- Only the relevant source owner can change upstream source status or proof
  bytes. The current Vela Math profile is expressly limited to Erdős 321, 94,
  and 887. Its Repository authority may consider the in-scope Erdős 321 case
  only after the status contradiction is resolved; it must not admit the
  Erdős 56 or 750 candidates. Those cases would require an appropriately
  scoped Repository and authority, not a profile migration invented here.

No `vela submit`, `vela verification record`, or `vela review` command was
executed for these candidates. Read-only `vela status` and `vela replay` were
run with `/Users/williamblair/.local/bin/vela` version `0.977.3`, digest
`sha256:3a1173918bdcb887155bab681411bf5e9ff64d925fe1b50369ac37ab020b94ad`.

Each packet contains seven observable facts, seven questions, explicit
nonclaims, and the three same-information views that can be constructed later.
The answer key is held outside candidate-facing Git; only its byte commitment
is retained in [`ADJUDICATION_COMMITMENT.md`](ADJUDICATION_COMMITMENT.md).
