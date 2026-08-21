# Final bounded Math Result Runner re-review

Verdict: **BLOCKED**

Reviewed producer state:

- branch `codex/result-runner-v1`
- commit `985e7065a1befa525aef64f45cc61a1f087438d4`
- tree `7c98f9f67d9361ca969d2ca14ee866e23fe79f7c`
- parent `2ba67830a42e657567bd30755f560183e767c26c`
- remote branch equal to the reviewed commit

The code closes the four retained implementation defects. The producer commit
does not retain the full SQLite serializer receipt that its validation claims.
That evidence gap blocks merge and needs one metadata-only correction.

## Finding

### RR-04 [P1] The committed serializer summary omits its compile environment

`runner.py:800-823` defines the serializer identity with Python identity,
SQLite source/version, and `sqlite_compile_options`. It writes those fields to
`sqlite-projection.json`. `QUALIFICATION.json:22-30` records the other
serializer fields but omits `sqlite_compile_options`. The producer commit also
omits the `sqlite-projection.json` preimage whose SHA-256 appears at
`QUALIFICATION.json:19`.

`VALIDATION.json:17` therefore overstates the retained evidence when it says
`pass_python_sqlite_source_compile_environment_bound`. A projection hash binds
unknown bytes but does not let a reader inspect or replay the claimed compile
environment from this Git commit.

The independent replay generated the missing projection and matched every
declared output:

- projection SHA-256
  `957dc2f5deb808d0e2cdd8d2cf51a3074f8da097d45c392b14e338fb65d56eb6`
- database SHA-256
  `12bd395fa5acfa3c9091a6fd408ce0fbffd88af53e15f5f69840f4057e9e33d2`
- logical-content SHA-256
  `2b8d30c083a2be07a6b67f0c9990663906623125359ed24de725f028fe36fb2a`
- Native commit/tree
  `501e058abf304fb363e629508af051bce4154de5` /
  `ba38c2fb7bb4cf79137d7f57e1dae3d67550cae7`
- Graph JSON SHA-256
  `f301129777dbe45f686986dc9b44120e0304c28774c766b0bcee179f6ff95bc1`

The implementation and the supplied hashes pass. The producer commit remains
dependent on the evaluator's current machine for the missing preimage.

Smallest correction: add the generated `sqlite_compile_options` array to
`correction_validation.sqlite_serializer`, or commit the exact generated
`sqlite-projection.json` under a correction-validation path outside the
35-file provider packet. Update the qualification and validation hashes. This
change needs no code edit, provider request, Docker execution, Vela lifecycle,
or scientific run.

## Retained blocker disposition

- **RR-02 PASS.** `run_bounded()` runs a complete post-exit census after the
  child and stream/input joins. Ten hostile runs wrote a valid result plus a
  late 4,096-byte sibling against a 128-byte total limit; all ten returned
  `runtime_total_size_exceeded`.
- **RR-03 PASS.** The host subset supports closed objects, strings, `const`,
  `enum`, and length bounds. It rejects `pattern`, Python-only regex forms,
  other property types, and undeclared keywords before inference.
- **RR-04 BLOCKED on retained evidence.** Same-serializer Native/Graph replay,
  SQLite bytes, integrity, canonical logical root, and scoped wording pass.
  The committed correction receipt omits the serializer's compile-options
  preimage.
- **RR-05 PASS.** Cleanup ownership starts before agent/key setup. Injected
  failures after private-key creation, after public-key creation, and during
  `ssh-add` delete both key files. The exact signed Vela lifecycle also passes
  with failing Verification, rooted reject, strict replay, zero accepted
  Claims, and `scientific_state_changed=false`.

RR-01 behavior remains intact. RR-06's provider packet also remains intact:
the portable manifest SHA-256 is
`4546a3b38537ba7d146a3e6e81a865edfca71cc7dccab3ef4daee714542f49ce`,
and all 35 rows, sizes, and hashes recompute with no missing or extra files.
The correction changed no prompt, schema, provider output, method, image,
source receipt, or retained Vela receipt.

## Reproduced checks

- commit/tree/parent and remote equality: PASS
- supplied runner, Vela adapter, qualification, validation, and manifest
  hashes: PASS
- focused suite with exact Vela 0.977.3 binary SHA-256
  `3a1173918bdcb887155bab681411bf5e9ff64d925fe1b50369ac37ab020b94ad`:
  PASS 18/18
- Ruff 0.5.4 check/format, Python 3.11.2 compileall, `git diff --check`, and
  clean clone: PASS
- Docker dry path on `desktop-linux`, accepted `linux/arm64` image, `/repo`
  source root, and source before/after equality: PASS
- current Native/Graph twice-run equality, SQLite integrity, and canonical
  logical root: PASS
- retained provider manifest: PASS 35/35
- 51-file credential scan: PASS with zero findings
- complete committed SQLite serializer preimage: FAIL

## Merge gate

Do not merge `985e7065a1befa525aef64f45cc61a1f087438d4`. Return the metadata-only RR-04
correction above and request an exact commit-bound check of that delta. The
code, tests, image, provider packet, and scientific state need no rerun or
mutation.
