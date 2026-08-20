# Corrected image evidence

Outcome: **PASS** for the single authorized rebuild.

- Controlling producer: `44ba0077eda1e2321a96281cf8f207bee29b5be5` /
  tree `482ea8e60faab01f93d9997f0c2868013420d2ac`.
- Controlling evaluator: `9660c7928415a57df33c4e5f84c904b01da40216` /
  tree `75db43f713adc7b55829c9735af455e004649fa0`.
- PASS report/verdict SHA-256:
  `e9804d43cbecf7ac7bea0fca6b5544fe36eaffde16a643737f350256d69f7333` /
  `9b651286ccf160e557b9503cf6e133e5f4e4e0567a23a163c7d490197fd54485`.
- Build count: exactly one. Exit `0`; elapsed 27 seconds; stdout/stderr
  SHA-256 `60a907975d793d824cea44b2e467eecf943076a97c74adda20971d2d83889257` /
  `9951c705520db33e028952e84a271de57189f907040cbe59f986e4e00bee5668`.
- Image tag: `vela-results-breakthrough-01:approved-machine-id`.
- Image ID and local OCI digest:
  `sha256:76c64845ae35f57835a08f386d4206bf021ccf1169f8a35e59cc68d8e4408e7e`.
- Platform/context: `linux/arm64` on Docker Desktop `desktop-linux`;
  Docker client/server `29.2.1` / `28.3.2`.
- Dockerfile SHA-256:
  `f3b995d61b35bffee3e12003ee00fd01e5ce0eb857460be69524aa98fe28d9dd`.
- Vela context: commit `88fcc0105eba35ee22ed1816d3aabba3322bebc1`,
  tree `2cb85fe1e1c3525ba97ff2aec25945417ea7b372`, 412 files,
  manifest SHA-256
  `6589e7d2b1000641207804a170a864c0dc1f8e10426cc69361da814d44afa627`,
  Git archive tar SHA-256
  `05a87f07789e0c8d77d85665c25504712cd70bea328b2c0f9e7ce57dc5b01c24`.
- Digest-pinned `FROM` inputs:
  `rust:1.97.1-bookworm@sha256:0e2bcaef56d041a486784e54104a81aebe0da44bd03019bd70bc0401e42e4a97`
  and
  `vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01`.
- Machine ID: `af94b40fa642620275e6d617be97a542` plus one LF, 33 bytes,
  SHA-256
  `70130fcf77290eece0f9df935fe0990d77a98fa3df25219528a0aa2566f7a58c`.
  It is a fixed, non-secret, experiment-specific compatibility value; it is
  neither read nor mounted from the host and deliberately remains identical
  across this experiment's disposable containers.
- Binary SHA-256: Vela
  `59cc91e9d277d733a8f5b2892653cf5b540778ce26ac794521c63bba0036103b`,
  Codex
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`,
  Git `54af380ba6ca1b36305358e99427a31ae4b0af5dc5cb6d0198c6f2f16e97651d`,
  Python
  `304aa87a76ebb13fd22d253ac157f14980ff2cdb23e6274f3b045571405e07dc`.
  Versions are Vela 0.977.3, Codex 0.145.0, Git 2.39.5, Python 3.11.2,
  SQLite 3.40.1.

The retained command, Docker BuildKit transcript, image inspection, history,
and network-disabled binary/machine-ID probe are the reconstruction evidence.
No second build was performed. The image was not pushed to a registry.
